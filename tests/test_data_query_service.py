import pytest
import asyncio
import datetime as DT
import jubapi.models.v2 as M
import jubapi.repositories.v2 as R
import jubapi.services.v2 as S
import jubapi.errors as EX


@pytest.fixture
async def seeded_db(test_db):
    """Seeds the database with realistic healthcare records."""
    def from_string_to_datetime(date_str):
        return DT.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    
    realistic_records = [
        # Source 1: Health 2025 Database
        {
            "record_id": "rec_001", 
            "source_id": "src_health_01", 
            "spatial_id": "MX", 
            "temporal_id": from_string_to_datetime("2025-01-01T00:00:00Z"), 
            "interest_ids": ["SEX_MALE", "CIE10_I10"] # Hypertension
        },
        {
            "record_id": "rec_002", 
            "source_id": "src_health_01", 
            "spatial_id": "TAM", 
            "temporal_id": from_string_to_datetime("2025-01-01T00:00:00Z"), 
            "interest_ids": ["SEX_FEMALE", "CIE10_C50"] # Breast Cancer
        },
        {
            "record_id": "rec_003", 
            "source_id": "src_health_01", 
            "spatial_id": "MX", 
            "temporal_id": from_string_to_datetime("2026-01-01T00:00:00Z"), 
            "interest_ids": ["SEX_MALE", "CIE10_E11"] # Type 2 Diabetes
        },
        {
            "record_id": "rec_004", 
            "source_id": "src_health_01", 
            "spatial_id": "NL", 
            "temporal_id": from_string_to_datetime("2026-01-01T00:00:00Z"), 
            "interest_ids": ["SEX_FEMALE", "CIE10_I10"] # Hypertension
        },
        
        # Source 2: A completely different dataset to ensure isolation
        {
            "record_id": "rec_005", 
            "source_id": "src_other_db", 
            "spatial_id": "MX", 
            "temporal_id": from_string_to_datetime("2025-01-01T00:00:00Z"), 
            "interest_ids": ["SEX_MALE"]
        }
    ]
    await test_db.data_records.insert_many(realistic_records)
    return test_db

@pytest.fixture
def query_service(seeded_db):
    """Initializes the query service with the seeded repository."""
    return S.DataQueryService(
        record_repo               = R.DataRecordsRepository(seeded_db.data_records),
        catalog_item_repo         = R.CatalogItemsRepository(seeded_db.catalog_items),
        catalog_alias_repo        = R.CatalogItemAliasesRepository(seeded_db.catalog_item_aliases),
        catalog_item_alias_link_repo = R.CatalogItemToCatalogAliasLinkRepository(seeded_db.catalog_item_catalog_alias_links),
    )


# ==========================================
# 2. QUERY SERVICE INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_query_single_spatial_filter(query_service:S.DataQueryService):
    """Verifies that querying by a single spatial ID works."""
    source_id = "src_health_01"
    dsl = "jub.v1.VS(MX)"
    
    result  = await query_service.query(source_id, dsl)

    assert result.is_ok
    
    records = result.unwrap()
    
    # Should only return MX records from src_health_01 (rec_001, rec_003)
    assert len(records) == 2
    assert all(r.spatial_id == "MX" for r in records)
    assert all(r.source_id == source_id for r in records)

@pytest.mark.asyncio
async def test_query_complex_and_logic(query_service:S.DataQueryService):
    """Verifies that combining VS, VT, and multiple VI (AND logic) works."""
    source_id = "src_health_01"

    # Find females in Tamaulipas with Breast Cancer in 2025
    dsl     = "jub.v1.VS(TAM).VT(2025).VI(SEX.FEMALE AND CIE10.C50)"
    result  = await query_service.query(source_id, dsl)
    assert result.is_ok
    records = result.unwrap()
    
    # Should specifically match rec_002
    assert len(records) == 1
    assert records[0].record_id == "rec_002"
    assert "SEX_FEMALE" in records[0].interest_ids

@pytest.mark.asyncio
async def test_query_temporal_range(query_service):
    """Verifies that temporal range queries (> and <) work."""
    source_id = "src_health_01"
    dsl = "jub.v1.VT(>= 2025 AND <= 2026)"
    
    result = await query_service.query(source_id, dsl)
    
    assert result.is_ok
    records = result.unwrap()
    
    # Should return all 4 records from src_health_01
    assert len(records) == 4

@pytest.mark.asyncio
async def test_query_syntax_error_returns_validation_err(query_service:S.DataQueryService):
    """Verifies that a badly formatted DSL string is caught safely."""
    source_id = "src_health_01"
    # Missing the "jub.v1." prefix
    bad_dsl = "VS(MX)" 
    
    result = await query_service.query(source_id, bad_dsl)
    
    assert result.is_err
    err = result.unwrap_err()
    assert isinstance(err, EX.ValidationError)

@pytest.mark.asyncio
async def test_query_logical_error_returns_validation_err(query_service:S.DataQueryService):
    """Verifies that impossible logic (e.g., AND inside VS) is caught safely."""
    source_id = "src_health_01"
    # A single record cannot be in MX and TAM simultaneously
    impossible_dsl = "jub.v1.VS(MX AND TAM)" 
    
    result = await query_service.query(source_id, impossible_dsl)
    
    assert result.is_err
    err = result.unwrap_err()
    assert isinstance(err, EX.ValidationError)
    # The error message from our updated ASTToMongoTranslator
    # assert "Logical AND is not allowed in Spatial"


# ============================================================
# RESOLUTION TESTS: catalog_item_id ≠ value (realistic case)
#
# The key invariant: DataRecord.spatial_id stores the
# catalog_item_id, NOT the human-readable value/code.
# The resolver must bridge whatever the user types to the
# actual catalog_item_id before building the $match.
# ============================================================

@pytest.fixture
async def resolved_db(test_db):
    """
    Catalog where catalog_item_id is intentionally different from value/code,
    and data_records whose spatial_id equals the catalog_item_id (not the value).
    """
    dt = DT.datetime(2025, 1, 1, tzinfo=DT.timezone.utc)

    await test_db.catalog_items.insert_many([
        # catalog_item_id ("STATE_MX") is different from value ("MX") and code (9)
        {"catalog_item_id": "STATE_MX",  "value": "MX",  "code": 9,  "name": "México",     "value_type": "STRING", "catalog_type": "SPATIAL"},
        {"catalog_item_id": "STATE_TAM", "value": "TAM", "code": 28, "name": "Tamaulipas", "value_type": "STRING", "catalog_type": "SPATIAL"},
        {"catalog_item_id": "INT_MALE",  "value": "SEX_MALE", "code": 1, "name": "Male",   "value_type": "STRING", "catalog_type": "INTEREST"},
    ])
    await test_db.catalog_item_aliases.insert_many([
        {"catalog_item_alias_id": "ALIAS_MX", "value": "Mexico", "code": 0, "value_type": "STRING"},
    ])
    await test_db.catalog_item_catalog_alias_links.insert_many([
        {"catalog_item_alias_id": "ALIAS_MX", "catalog_item_id": "STATE_MX"},
    ])
    # Records store the catalog_item_id in spatial_id — NOT the value
    await test_db.data_records.insert_many([
        {"record_id": "r1", "source_id": "src_1", "spatial_id": "STATE_MX",  "temporal_id": dt, "interest_ids": ["INT_MALE"], "numerical_interest_ids": {}, "raw_payload": {}},
        {"record_id": "r2", "source_id": "src_1", "spatial_id": "STATE_MX",  "temporal_id": dt, "interest_ids": [],            "numerical_interest_ids": {}, "raw_payload": {}},
        {"record_id": "r3", "source_id": "src_1", "spatial_id": "STATE_TAM", "temporal_id": dt, "interest_ids": [],            "numerical_interest_ids": {}, "raw_payload": {}},
    ])
    return test_db


@pytest.fixture
def resolved_query_service(resolved_db):
    return S.DataQueryService(
        record_repo              = R.DataRecordsRepository(resolved_db.data_records),
        catalog_item_repo        = R.CatalogItemsRepository(resolved_db.catalog_items),
        catalog_alias_repo       = R.CatalogItemAliasesRepository(resolved_db.catalog_item_aliases),
        catalog_item_alias_link_repo = R.CatalogItemToCatalogAliasLinkRepository(resolved_db.catalog_item_catalog_alias_links),
    )


@pytest.mark.asyncio
async def test_resolve_spatial_by_value(resolved_query_service):
    """VS(MX) — value must resolve to catalog_item_id 'STATE_MX'."""
    result = await resolved_query_service.query("src_1", "jub.v1.VS(MX)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 2, f"Expected 2 records, got {len(records)}: {[r.spatial_id for r in records]}"
    assert all(r.spatial_id == "STATE_MX" for r in records)


@pytest.mark.asyncio
async def test_resolve_spatial_by_code(resolved_query_service):
    """VS(28) — numeric code must resolve to catalog_item_id 'STATE_TAM'."""
    result = await resolved_query_service.query("src_1", "jub.v1.VS(28)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 1, f"Expected 1 record, got {len(records)}"
    assert records[0].spatial_id == "STATE_TAM"


@pytest.mark.asyncio
async def test_resolve_spatial_by_catalog_item_id(resolved_query_service):
    """VS(STATE_MX) — direct catalog_item_id must match 2 records."""
    result = await resolved_query_service.query("src_1", "jub.v1.VS(STATE_MX)")
    assert result.is_ok, result.unwrap_err()
    assert len(result.unwrap()) == 2


@pytest.mark.asyncio
async def test_resolve_spatial_by_alias(resolved_query_service):
    """VS(Mexico) — alias value must resolve to 'STATE_MX'."""
    result = await resolved_query_service.query("src_1", "jub.v1.VS(Mexico)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 2, f"Expected 2 records via alias, got {len(records)}"
    assert all(r.spatial_id == "STATE_MX" for r in records)