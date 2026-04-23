"""
Integration tests for /api/v2/datasources endpoints.

Covers:
  - POST   /datasources                    register a data source
  - GET    /datasources                    list all sources
  - GET    /datasources/{source_id}        get a single source
  - DELETE /datasources/{source_id}        delete source + cascade records
  - POST   /datasources/{source_id}/records  ingest records
  - POST   /datasources/{source_id}/query    query records with DSL
"""

import pytest
import datetime
from httpx import AsyncClient
from jubapi.db.constants import CollectionNames

BASE = "/api/v2/datasources"


@pytest.fixture(autouse=True)
async def clean_collections(test_db):
    """Wipes datasource and record collections before every test in this module."""
    await test_db[CollectionNames.DATA_SOURCES.value].drop()
    await test_db[CollectionNames.DATA_RECORDS.value].drop()
    yield


def utc(year: int, month: int = 1, day: int = 1) -> str:
    """Returns an ISO 8601 UTC datetime string for easy test data construction."""
    return datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc).isoformat()


# ============================================================
# Helpers
# ============================================================

async def _register(client: AsyncClient, name: str = "Test Source") -> dict:
    """Creates a datasource and returns the JSON response."""
    resp = await client.post(BASE, json={"name": name, "description": "unit test", "format": "csv"})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _ingest(client: AsyncClient, source_id: str, records: list) -> dict:
    resp = await client.post(f"{BASE}/{source_id}/records", json=records)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_record(record_id: str, spatial: str, year: int, interests: list = None) -> dict:
    return {
        "record_id": record_id,
        "spatial_id": spatial,
        "temporal_id": utc(year),
        "interest_ids": interests or [],
        "numerical_interest_ids": {},
        "raw_payload": {},
    }


# ============================================================
# 1. Registration
# ============================================================

@pytest.mark.asyncio
async def test_register_datasource_success(async_client: AsyncClient):
    resp = await async_client.post(BASE, json={
        "name": "My CSV",
        "description": "Test data",
        "format": "csv",
        "bucket_id": "/data/my.csv",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "source_id" in body
    assert body["name"] == "My CSV"
    assert body["description"] == "Test data"


@pytest.mark.asyncio
async def test_register_datasource_minimal_payload(async_client: AsyncClient):
    """Only name is required; other fields default gracefully."""
    resp = await async_client.post(BASE, json={"name": "Minimal"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Minimal"


@pytest.mark.asyncio
async def test_register_datasource_missing_name_returns_422(async_client: AsyncClient):
    resp = await async_client.post(BASE, json={"description": "no name"})
    assert resp.status_code == 422


# ============================================================
# 2. Listing
# ============================================================

@pytest.mark.asyncio
async def test_list_datasources_empty(async_client: AsyncClient):
    resp = await async_client.get(BASE)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_datasources_returns_all(async_client: AsyncClient):
    await _register(async_client, "Source A")
    await _register(async_client, "Source B")

    resp = await async_client.get(BASE)
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert "Source A" in names
    assert "Source B" in names


# ============================================================
# 3. Get by ID
# ============================================================

@pytest.mark.asyncio
async def test_get_datasource_success(async_client: AsyncClient):
    created = await _register(async_client)
    source_id = created["source_id"]

    resp = await async_client.get(f"{BASE}/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["source_id"] == source_id


@pytest.mark.asyncio
async def test_get_datasource_not_found_returns_404(async_client: AsyncClient):
    resp = await async_client.get(f"{BASE}/does_not_exist")
    assert resp.status_code == 404


# ============================================================
# 4. Deletion (cascade)
# ============================================================

@pytest.mark.asyncio
async def test_delete_datasource_removes_source_and_records(async_client: AsyncClient):
    created = await _register(async_client)
    source_id = created["source_id"]

    await _ingest(async_client, source_id, [
        _make_record("rec_1", "MX", 2025),
        _make_record("rec_2", "TAM", 2025),
    ])

    resp = await async_client.delete(f"{BASE}/{source_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True
    assert body["records_removed"] == 2

    # Source is gone
    assert (await async_client.get(f"{BASE}/{source_id}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_datasource_not_found_returns_404(async_client: AsyncClient):
    resp = await async_client.delete(f"{BASE}/ghost_source")
    assert resp.status_code == 404


# ============================================================
# 5. Record ingestion
# ============================================================

@pytest.mark.asyncio
async def test_ingest_records_success(async_client: AsyncClient):
    source = await _register(async_client)
    source_id = source["source_id"]

    records = [
        _make_record("r1", "MX",  2024),
        _make_record("r2", "TAM", 2024),
        _make_record("r3", "NL",  2025),
    ]
    resp = await async_client.post(f"{BASE}/{source_id}/records", json=records)
    assert resp.status_code == 201
    assert resp.json()["inserted"] == 3


@pytest.mark.asyncio
async def test_ingest_records_into_nonexistent_source_returns_404(async_client: AsyncClient):
    records = [_make_record("r1", "MX", 2025)]
    resp = await async_client.post(f"{BASE}/fake_src/records", json=records)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingest_empty_list_returns_zero(async_client: AsyncClient):
    source = await _register(async_client)
    resp = await async_client.post(f"{BASE}/{source['source_id']}/records", json=[])
    assert resp.status_code == 201
    assert resp.json()["inserted"] == 0


# ============================================================
# 6. DSL querying
# ============================================================

@pytest.fixture
async def seeded_source(async_client: AsyncClient):
    """Creates a source with realistic records and returns (client, source_id)."""
    source = await _register(async_client, "Health 2025")
    sid = source["source_id"]
    records = [
        _make_record("rec_001", "MX",  2025, ["SEX_MALE",   "CIE10_E11"]),
        _make_record("rec_002", "MX",  2025, ["SEX_FEMALE", "CIE10_E11"]),
        _make_record("rec_003", "TAM", 2025, ["SEX_MALE",   "CIE10_I10"]),
        _make_record("rec_004", "TAM", 2026, ["SEX_FEMALE", "CIE10_I10"]),
        _make_record("rec_005", "NL",  2026, ["SEX_MALE",   "CIE10_E11"]),
    ]
    await _ingest(async_client, sid, records)
    return async_client, sid


@pytest.mark.asyncio
async def test_query_spatial_filter(seeded_source):
    client, sid = seeded_source
    resp = await client.post(f"{BASE}/{sid}/query", json={"query": "jub.v1.VS(MX)"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all(r["spatial_id"] == "MX" for r in results)


@pytest.mark.asyncio
async def test_query_temporal_filter(seeded_source):
    client, sid = seeded_source
    resp = await client.post(f"{BASE}/{sid}/query", json={"query": "jub.v1.VT(2026)"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all(r["source_id"] == sid for r in results)


@pytest.mark.asyncio
async def test_query_interest_filter(seeded_source):
    client, sid = seeded_source
    resp = await client.post(
        f"{BASE}/{sid}/query",
        json={"query": "jub.v1.VI(SEX.FEMALE)"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all("SEX_FEMALE" in r["interest_ids"] for r in results)


@pytest.mark.asyncio
async def test_query_combined_filters(seeded_source):
    client, sid = seeded_source
    resp = await client.post(
        f"{BASE}/{sid}/query",
        json={"query": "jub.v1.VS(TAM).VT(2025)"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["record_id"] == "rec_003"


@pytest.mark.asyncio
async def test_query_returns_only_own_source_records(async_client: AsyncClient):
    """Records from a different source must not bleed into query results."""
    src_a = await _register(async_client, "Source A")
    src_b = await _register(async_client, "Source B")

    await _ingest(async_client, src_a["source_id"], [_make_record("a1", "MX", 2025)])
    await _ingest(async_client, src_b["source_id"], [_make_record("b1", "MX", 2025)])

    resp = await async_client.post(
        f"{BASE}/{src_a['source_id']}/query",
        json={"query": "jub.v1.VS(MX)"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["record_id"] == "a1"


@pytest.mark.asyncio
async def test_query_invalid_dsl_returns_422(async_client: AsyncClient):
    source = await _register(async_client)
    # Missing "jub.v1." prefix — parser will reject this
    resp = await async_client.post(
        f"{BASE}/{source['source_id']}/query",
        json={"query": "VS(MX)"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_impossible_logic_returns_422(async_client: AsyncClient):
    source = await _register(async_client)
    # AND inside VS is semantically impossible — translator raises ValueError
    resp = await async_client.post(
        f"{BASE}/{source['source_id']}/query",
        json={"query": "jub.v1.VS(MX AND TAM)"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_no_match_returns_empty_list(seeded_source):
    client, sid = seeded_source
    resp = await client.post(
        f"{BASE}/{sid}/query",
        json={"query": "jub.v1.VS(NONEXISTENT_STATE)"},
    )
    assert resp.status_code == 200
    assert resp.json() == []
