import pytest
import datetime as DT
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
from typing import List
import jubapi.repositories.v2 as R
import jubapi.models.v2 as M
import jubapi.services.v2 as S
from jubapi.db.constants import CollectionNames
import jubapi.enums.v2 as ENUMS
import jubapi.dto.v2 as DTO
import random

@pytest.fixture(scope="function")
async def services(test_db):
    """Initializes all required repositories and services."""
    # 1. Repositories
    observatory_repository        = R.ObservatoriesRepository(test_db[CollectionNames.OBSERVATORIES.value])
    product_repository            = R.ProductsRepository(test_db[CollectionNames.PRODUCTS.value])
    catalog_repository            = R.CatalogsRepository(test_db[CollectionNames.CATALOGS.value])
    catalog_item_repository       = R.CatalogItemsRepository(test_db[CollectionNames.CATALOG_ITEMS.value])
    catalog_item_alias_repository = R.CatalogItemAliasesRepository(test_db[CollectionNames.CATALOG_ITEM_ALIASES.value])
    
    # 2. Link Manager
    link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(test_db[CollectionNames.OBSERVATORY_PRODUCT_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(test_db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(test_db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value]),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(test_db[CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(test_db[CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(test_db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
        observatory_service_link_repository        = R.ObservatoryToServiceLinkRepository(test_db[CollectionNames.OBSERVATORY_SERVICE_LINKS.value]),
        observatory_datasource_link_repository     = R.ObservatoryToDataSourceLinkRepository(test_db[CollectionNames.OBSERVATORY_DATASOURCE_LINKS.value]),
        product_product_link_repository            = R.ProductToProductLinkRepository(test_db[CollectionNames.PRODUCT_PRODUCT_LINKS.value]),
    )
    search_service = S.SearchService(
        observatory_product_link_repository        = link_manager.observatory_product_link_repository,
        product_catalog_item_link_repository       = link_manager.product_catalog_item_link_repository,
        catalog_item_relationship_repository       = link_manager.catalog_item_relationship_repository,
        catalog_item_repository                    = catalog_item_repository,
        product_repository                         = product_repository,
        catalog_alias_repository                   = catalog_item_alias_repository,
        catalog_item_catalog_alias_link_repository = link_manager.catalog_item_catalog_alias_link_repository,
        observatory_catalog_link_repository        = link_manager.observatory_catalog_link_repository,
        catalog_catalog_item_link_repository       = link_manager.catalog_catalog_item_link_repository,
        observatory_repository                     = observatory_repository,
        catalog_repository                         = catalog_repository,
        data_records_repository                    = R.DataRecordsRepository(test_db[CollectionNames.DATA_RECORDS.value]),
    )

    # 3. Services
    review_repository = R.ReviewRepository(
        test_db[CollectionNames.OBSERVATORY_REVIEWS.value]
    )
    return {
        "catalog": S.CatalogService(catalog_repository, catalog_item_repository, catalog_item_alias_repository, link_manager),
        "product": S.ProductService(product_repository, link_manager),
        "observatory": S.ObservatoriesService(
            observatory_product_link_repository = link_manager.observatory_product_link_repository,
            observatory_repository              = observatory_repository,
            product_repository                  = product_repository,
            graph_link_manager                  = link_manager,
            review_repository                   = review_repository,
            service_repository                  = R.ServiceRepository(test_db[CollectionNames.SERVICES.value]),
            datasource_repository               = R.DataSourceRepository(test_db[CollectionNames.DATA_SOURCES.value]),
        ),
        "search": search_service,
        "db": test_db # Passed for direct assertions
    }




@pytest.fixture(autouse=True)
async def seed_database_2(services):
    """Seeds the database before the tests run with complex hierarchies, catalogs, aliases, and observatories."""
    cat_srv: S.CatalogService = services["catalog"]
    prod_srv: S.ProductService = services["product"]
    observatory_srv: S.ObservatoriesService = services["observatory"]
    
    existing_prod = await prod_srv.get_product_by_id("p_01_01")
    if existing_prod.is_ok:
        return

    # ==========================================
    # HELPER: Create Item and 2 Aliases
    # ==========================================
    async def create_item_with_aliases(catalog_id: str, item: M.CatalogItemX, parent_id: str = None):
        """Helper to insert an item and automatically generate 2 aliases for it."""
        # 1. Create the item
        await cat_srv.add_item_to_catalog(catalog_id, item, parent_id=parent_id)
        
        # 2. Create 2 unique aliases for the item
        # (Adjust this method call to match your CatalogService's exact method for aliases)
        alias_1_name = f"{item.value}_ALIAS_1"
        alias_2_name = f"{item.value}_ALIAS_2"
        
        # Example: assuming you pass the item ID and the string alias name
        catalog_item_alias1 = M.CatalogItemAlias(
            catalog_item_alias_id = alias_1_name,
            value                 = alias_1_name,
            value_type            = item.value_type,
            catalog_type          = item.catalog_type,
            description           = f"Alias 1 for {item.name}"
        )

        catalog_item_alias2 = M.CatalogItemAlias(
            catalog_item_alias_id = alias_2_name,
            value                 = alias_2_name,
            value_type            = item.value_type,
            catalog_type          = item.catalog_type,
            description           = f"Alias 2 for {item.name}"
        )
       
        await cat_srv.add_alias_to_catalog_item(item.catalog_item_id, catalog_item_alias1)
        await cat_srv.add_alias_to_catalog_item(item.catalog_item_id, catalog_item_alias2)


    # ==========================================
    # 0.A SETUP THE ROOT CATALOGS
    # ==========================================
    catalogs_to_create = [
        M.CatalogX(
            catalog_id   = "cat_spatial",
            value        = "SPATIAL",
            catalog_type = ENUMS.CatalogType.SPATIAL,
            name         = "Spatial Catalog",
            description  = "Geographic dimensions"
        ),

        M.CatalogX(catalog_id="cat_time", value="TEMPORAL", catalog_type=ENUMS.CatalogType.TEMPORAL, name="Temporal Catalog", description="Time dimensions"),
        M.CatalogX(catalog_id="cat_sex", value="SEX", catalog_type=ENUMS.CatalogType.INTEREST, name="Sex Catalog", description="Biological sex variables"),
        M.CatalogX(catalog_id="cat_cie10", value="CIE10", catalog_type=ENUMS.CatalogType.INTEREST, name="CIE-10 Catalog", description="Medical diagnoses"),
        M.CatalogX(catalog_id="cat_plot", value="PLOT_TYPE", catalog_type=ENUMS.CatalogType.INTEREST, name="Plot Type Catalog", description="Visualization types"),
        M.CatalogX(catalog_id="cat_age", value="AGE_CAT", catalog_type=ENUMS.CatalogType.INTEREST, name="Age Metrics", description="Continuous numerical variables")
    ]
    
    
    catalogs_to_link = ["cat_spatial", "cat_time", "cat_sex", "cat_cie10", "cat_plot", "cat_age"]
    
    for cat in catalogs_to_create:
        await cat_srv.create_catalog(cat)
    
    # ==========================================
    # 0.B SETUP OBSERVATORIES
    # ==========================================
    for i in range(1, 11):
        obs_id = f"obs_{i}"
        await observatory_srv.create_observatory(
            M.ObservatoryX(observatory_id=obs_id, title=f"Observatory {i}", description=f"Test Obs {i}")
        )
        for priority, cat_id in enumerate(catalogs_to_link):
            await observatory_srv.add_catalog(obs_id, cat_id, priority)



    # ==========================================
    # 1. TEMPORAL CATALOG (2000 to 2026)
    # ==========================================
    for year in range(2000, 2027):
        await create_item_with_aliases(
            "cat_time", 
            M.CatalogItemX(
                catalog_item_id = f"Y{year}",
                name            = str(year),
                value           = str(year),
                code            = year,
                temporal_value  = f"{year}-01-01T00:00:00Z",
                value_type      = ENUMS.CatalogItemValueType.DATETIME,
                catalog_type    = ENUMS.CatalogType.TEMPORAL,
                description     = ""
            )
        )

    # ==========================================
    # 2. SPATIAL CATALOG
    # ==========================================
    await create_item_with_aliases("cat_spatial", 
        M.CatalogItemX(
            catalog_item_id = "MX",
            name            = "Mexico",
            value           = "MX",
            code            = 0,
            value_type      = ENUMS.CatalogItemValueType.STRING,
            catalog_type    = ENUMS.CatalogType.SPATIAL,
            description     = ""
    ))
    
    states_munis = {
        "TAM": ["Victoria", "Tampico"], "NL": ["Monterrey", "San Pedro"],
        "CDMX": ["Coyoacan", "Tlalpan"], "JAL": ["Guadalajara", "Zapopan"],
        "VER": ["Veracruz", "Xalapa"], "YUC": ["Merida", "Valladolid"],
        "PUE": ["Puebla", "Cholula"], "GTO": ["Leon", "Irapuato"],
        "CHIH": ["Chihuahua", "Juarez"], "OAX": ["Oaxaca", "Huatulco"]
    }
    
    state_code = 1
    for state_id, munis in states_munis.items():
        await create_item_with_aliases("cat_spatial", M.CatalogItemX(
            catalog_item_id=state_id, name=state_id, value=state_id, code=state_code, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.SPATIAL, description=""
        ), parent_id="MX")
        
        muni_code = state_code * 100
        for muni_name in munis:
            muni_id = f"{state_id}_{muni_name[:3].upper()}" 
            await create_item_with_aliases("cat_spatial", M.CatalogItemX(
                catalog_item_id=muni_id, name=muni_name, value=muni_id, code=muni_code, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.SPATIAL, description=""
            ), parent_id=state_id)
            muni_code += 1
        state_code += 1

    # ==========================================
    # 3. INTEREST CATALOGS
    # ==========================================
    await create_item_with_aliases("cat_sex", 
        M.CatalogItemX(
            catalog_item_id = "FEMALE",
            name            = "Female",
            value           = "FEMALE",
            code            = 1,
            value_type      = ENUMS.CatalogItemValueType.STRING,
            catalog_type    = ENUMS.CatalogType.INTEREST,
            description     = ""
        )
    )
    
    await create_item_with_aliases("cat_sex", 
        M.CatalogItemX(
            catalog_item_id = "MALE",
            name            = "Male",
            value           = "MALE",
            code            = 2,
            value_type      = ENUMS.CatalogItemValueType.STRING,
            catalog_type    = ENUMS.CatalogType.INTEREST,
            description     = ""
        )
    )
    

    for i in range(1,100):
        await create_item_with_aliases("cat_age", M.CatalogItemX(
            catalog_item_id = f"AGE_{i}",
            name            = f"Patient Age {i}",
            value           = f"AGE_{i}",
            code            = i,
            value_type      = ENUMS.CatalogItemValueType.NUMBER,   # <-- Set to NUMBER
            catalog_type    = ENUMS.CatalogType.INTEREST,
            description     = "Continuous numerical age metric"
        ))
    plot_types = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]
    for idx, p in enumerate(plot_types):
        await create_item_with_aliases("cat_plot", M.CatalogItemX(
            catalog_item_id=p, name=f"{p} Chart", value=p, code=idx, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.INTEREST, description=""
        ))

    cie10_chapters = {"II": "Neoplasias (C00-D48)", "IV": "Enfermedades endocrinas", "IX": "Enfermedades del aparato circulatorio"}
    for cap_id, desc in cie10_chapters.items():
        await create_item_with_aliases("cat_cie10", M.CatalogItemX(
            catalog_item_id=cap_id, name=desc, value=cap_id, code=0, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.INTEREST, description=""
        ))

    cie10_categories = {"C50": ("Tumor maligno de la mama", "II"), "C34": ("Tumor maligno bronquios/pulmón", "II"), "E11": ("Diabetes tipo 2", "IV"), "I10": ("Hipertensión", "IX")}
    for cat_id, (desc, parent_cap) in cie10_categories.items():
        await create_item_with_aliases("cat_cie10", M.CatalogItemX(
            catalog_item_id=cat_id, name=f"{cat_id} - {desc}", value=cat_id, code=0, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.INTEREST, description=""
        ), parent_id=parent_cap)

    cie10_subcategories = {
        "C50": [("1", "Porción no especificada"), ("2", "Cuadrante superior interno"), ("3", "Cuadrante inferior interno")],
        "C34": [("1", "Lóbulo superior"), ("2", "Lóbulo medio")],
        "E11": [("1", "Con cetoacidosis"), ("2", "Con complicaciones renales"), ("3", "Con complicaciones oftálmicas")],
        "I10": [("1", "Benigna"), ("2", "Maligna"), ("3", "No especificada")]
    }

    for parent_cat, subcodes in cie10_subcategories.items():
        for sub_val, desc in subcodes:
            unique_db_id = f"{parent_cat}_{sub_val}" 
            await create_item_with_aliases("cat_cie10", M.CatalogItemX(
                catalog_item_id=unique_db_id, name=f"{parent_cat}.{sub_val} - {desc}", value=sub_val, code=0, value_type=ENUMS.CatalogItemValueType.STRING, catalog_type=ENUMS.CatalogType.INTEREST, description=""
            ), parent_id=parent_cat)

    # ==========================================
    # 4. SEED RANDOMIZED UNIQUE PRODUCTS
    # ==========================================
    spatial_pool = ["MX", "TAM", "TAM_VIC", "NL_MON", "CDMX_COY", "JAL", "YUC", "PUE", "GTO", "CHIH"]
    time_pool    = [f"Y{year}" for year in range(2000, 2027)]
    sex_pool     = ["FEMALE", "MALE"]
    cie10_pool   = ["C50_1", "C50_2", "C50_3", "C34_1", "C34_2", "E11_1", "E11_2", "I10_1", "I10_2", "I10_3"]
    plot_pool    = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]
    age_pool     = [f"AGE_{i}" for i in range(1,100)]  # Since AGE is continuous, we can just use the same item but differentiate in the product name/description if needed

    # Set seed so the random counts are identical every time Pytest runs
    random.seed(42) 
    product_counter = 0

    for obs_idx in range(1, 11):
        obs_id = f"obs_{obs_idx}"
        
        # Randomly assign between 3 and 15 products to this specific observatory
        num_products_for_obs = random.randint(3, 15)
        
        for prod_idx in range(1, num_products_for_obs + 1):
            product_counter += 1
            
            # Format the product ID: e.g., p_01_01, p_01_02, etc. Ensures complete uniqueness.
            p_id = f"p_{obs_idx:02d}_{prod_idx:02d}" 
            
            sp_tag = spatial_pool[product_counter % len(spatial_pool)]
            tm_tag = time_pool[product_counter % len(time_pool)]
            sx_tag = sex_pool[product_counter % len(sex_pool)]
            ci_tag = cie10_pool[product_counter % len(cie10_pool)]
            pl_tag = plot_pool[product_counter % len(plot_pool)]
            ag_tag = age_pool[product_counter % len(age_pool)]
            tags = [sp_tag, sx_tag, tm_tag, ci_tag, pl_tag]
            if ag_tag:
                tags.append(ag_tag)
            prod_name = f"Data {p_id} - {sp_tag} {ci_tag} {tm_tag} _ {pl_tag} {ag_tag}"
            
            res = await prod_srv.insert_product(
                M.ProductX(
                    product_id  = p_id,
                    name        = prod_name,
                    description = "Autogenerated test product"
                ), 
                obs_id, 
                tags
            )
            assert res.is_ok, f"Failed to insert product {p_id}: {res.error}"




@pytest.mark.asyncio
async def test_search_age_range(services):
    search_service:S.SearchService = services["search"]
    query  = "jub.v1.VI(AGE = 20)"
    result = await search_service.search(query=query)
    assert result.is_ok
    products = result.unwrap()
    assert len(products)== 1, "Expected at least one product for AGE = 20"
    query2 = "jub.v1.VI(AGE >= 20 AND AGE <= 30)"
    result2 = await search_service.search(query=query2,limit=100)
    assert result2.is_ok
    products2:List[DTO.ProductXDTO] = result2.unwrap()
    # xs = list(map(lambda p: p.name, products2))
    print("Products for AGE between 20 and 30:", products2)
    assert len(products2) >= 11, "Expected at least 11 products for AGE between 20 and 30 (inclusive)"

@pytest.mark.asyncio
async def test_search_observatories(services):
    search_service:S.SearchService = services["search"]
    query  = "jub.v1.VS(MX.TAM).VT(>=2015).VI(SEX.MALE AND CIE10.E11.2 AND PLOT_TYPE.BAR)"
    result = await search_service.search_observatories(query=query)
    assert result.is_ok

@pytest.mark.asyncio
async def test_search_products(services):
    search_service:S.SearchService = services["search"]
    query  = "jub.v1.VT(>=2000 AND <=2026).VI(PLOT_TYPE.BAR)"
    result = await search_service.search(query=query)
    assert result.is_ok


# ============================================================
# RESOLUTION TESTS for SearchService.search_data_records
# and SearchService.generate_plot
#
# Uses catalog items where catalog_item_id ≠ value (realistic)
# and records whose spatial_id is the catalog_item_id.
# Values (ALPHA/BETA) are chosen to never collide with the
# "MX", "TAM" etc. created by seed_database_2.
# ============================================================

@pytest.fixture
async def records_for_resolution(services):
    """Inserts unique catalog items and data_records for resolver tests."""
    db  = services["db"]
    dt  = DT.datetime(2025, 1, 1, tzinfo=DT.timezone.utc)

    # catalog_item_id is intentionally different from value and code
    await db[CollectionNames.CATALOG_ITEMS.value].insert_many([
        {"catalog_item_id": "ID_ALPHA", "value": "ALPHA", "code": 99001, "name": "Alpha State", "value_type": "STRING", "catalog_type": "SPATIAL"},
        {"catalog_item_id": "ID_BETA",  "value": "BETA",  "code": 99002, "name": "Beta State",  "value_type": "STRING", "catalog_type": "SPATIAL"},
    ])
    await db[CollectionNames.CATALOG_ITEM_ALIASES.value].insert_many([
        {"catalog_item_alias_id": "ALIAS_ALPHA", "value": "AlphaAlias", "code": 0, "value_type": "STRING"},
    ])
    await db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value].insert_many([
        {"catalog_item_alias_id": "ALIAS_ALPHA", "catalog_item_id": "ID_ALPHA"},
    ])
    # Records store the catalog_item_id, NOT the value
    await db[CollectionNames.DATA_RECORDS.value].insert_many([
        {"record_id": "dr1", "source_id": "src_t", "spatial_id": "ID_ALPHA", "temporal_id": dt, "interest_ids": [], "numerical_interest_ids": {}, "raw_payload": {}},
        {"record_id": "dr2", "source_id": "src_t", "spatial_id": "ID_ALPHA", "temporal_id": dt, "interest_ids": [], "numerical_interest_ids": {}, "raw_payload": {}},
        {"record_id": "dr3", "source_id": "src_t", "spatial_id": "ID_BETA",  "temporal_id": dt, "interest_ids": [], "numerical_interest_ids": {}, "raw_payload": {}},
    ])
    return services


@pytest.mark.asyncio
async def test_search_records_resolves_by_value(records_for_resolution):
    """search_data_records: VS(ALPHA) must resolve value → 'ID_ALPHA' → 2 records."""
    search: S.SearchService = records_for_resolution["search"]
    result = await search.search_data_records("jub.v1.VS(ALPHA)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 2, f"Expected 2, got {len(records)}: {[r['spatial_id'] for r in records]}"
    assert all(r["spatial_id"] == "ID_ALPHA" for r in records)


@pytest.mark.asyncio
async def test_search_records_resolves_by_code(records_for_resolution):
    """search_data_records: VS(99002) must resolve code → 'ID_BETA' → 1 record."""
    search: S.SearchService = records_for_resolution["search"]
    result = await search.search_data_records("jub.v1.VS(99002)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 1, f"Expected 1, got {len(records)}"
    assert records[0]["spatial_id"] == "ID_BETA"


@pytest.mark.asyncio
async def test_search_records_resolves_by_alias(records_for_resolution):
    """search_data_records: VS(AlphaAlias) must resolve alias → 'ID_ALPHA' → 2 records."""
    search: S.SearchService = records_for_resolution["search"]
    result = await search.search_data_records("jub.v1.VS(AlphaAlias)")
    assert result.is_ok, result.unwrap_err()
    records = result.unwrap()
    assert len(records) == 2, f"Expected 2 via alias, got {len(records)}"
    assert all(r["spatial_id"] == "ID_ALPHA" for r in records)


@pytest.mark.asyncio
async def test_generate_plot_resolves_by_value(records_for_resolution):
    """generate_plot: VS(ALPHA).VO(COUNT) must resolve value → 'ID_ALPHA' → count=2."""
    search: S.SearchService = records_for_resolution["search"]
    result = await search.generate_plot("jub.v1.VS(ALPHA).VO(COUNT)", observatory_id="", chart_type="bar")
    assert result.is_ok, result.unwrap_err()
    data = result.unwrap()
    assert data is not None


# ============================================================
# VO + BY GROUPING TESTS
#
# Validates that VO(AVG/COUNT) and BY(prefix) produce the
# correct number of bars in the ECharts output.
#
# Key data contract:
#   interest_ids stores catalog_item_ids whose PREFIX equals
#   the BY() argument.  E.g. BY(CANCER) groups records whose
#   interest_ids contain elements starting with "CANCER_".
# ============================================================

@pytest.fixture
async def plot_records(services):
    """
    Seeds catalog items with ARBITRARY IDs (no prefix format required),
    links them to a catalog, and creates matching data_records.
    BY() must group by catalog membership — not by ID prefix.
    """
    db  = services["db"]
    dt  = DT.datetime(2025, 1, 1, tzinfo=DT.timezone.utc)

    # Catalog — BY(CANCER) will resolve to this catalog's items
    await db[CollectionNames.CATALOGS.value].insert_many([
        {"catalog_id": "cat_cancer", "value": "CANCER", "catalog_type": "INTEREST",
         "name": "Cancer Types", "level": 0},
    ])
    # Items with ARBITRARY IDs — no "CANCER_" prefix needed
    await db[CollectionNames.CATALOG_ITEMS.value].insert_many([
        {"catalog_item_id": "ITEM_001", "value": "C_MAMA",   "code": 101, "name": "Breast",  "value_type": "STRING", "catalog_type": "INTEREST"},
        {"catalog_item_id": "ITEM_002", "value": "C_OVARIO", "code": 102, "name": "Ovarian", "value_type": "STRING", "catalog_type": "INTEREST"},
        {"catalog_item_id": "ITEM_003", "value": "C_HIGADO", "code": 103, "name": "Liver",   "value_type": "STRING", "catalog_type": "INTEREST"},
    ])
    # Links that tell BY() which items belong to "CANCER" catalog
    await db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value].insert_many([
        {"catalog_id": "cat_cancer", "catalog_item_id": "ITEM_001"},
        {"catalog_id": "cat_cancer", "catalog_item_id": "ITEM_002"},
        {"catalog_id": "cat_cancer", "catalog_item_id": "ITEM_003"},
    ])
    # Records store catalog_item_ids (arbitrary IDs, not prefixed)
    await db[CollectionNames.DATA_RECORDS.value].insert_many([
        {"record_id": "p1", "source_id": "src_p", "spatial_id": "MX", "temporal_id": dt,
         "interest_ids": ["ITEM_001"], "numerical_interest_ids": {"TASA_100K": 10.0}, "raw_payload": {}},
        {"record_id": "p2", "source_id": "src_p", "spatial_id": "MX", "temporal_id": dt,
         "interest_ids": ["ITEM_001"], "numerical_interest_ids": {"TASA_100K": 30.0}, "raw_payload": {}},
        {"record_id": "p3", "source_id": "src_p", "spatial_id": "MX", "temporal_id": dt,
         "interest_ids": ["ITEM_002"], "numerical_interest_ids": {"TASA_100K": 50.0}, "raw_payload": {}},
        {"record_id": "p4", "source_id": "src_p", "spatial_id": "MX", "temporal_id": dt,
         "interest_ids": ["ITEM_003"], "numerical_interest_ids": {"TASA_100K": 80.0}, "raw_payload": {}},
    ])
    return services


@pytest.mark.asyncio
async def test_by_produces_multiple_bars(plot_records):
    """
    BY(CANCER) must produce 3 bars by looking up catalog membership,
    NOT by matching a prefix in the catalog_item_id string.
    """
    search: S.SearchService = plot_records["search"]
    dsl = "jub.v1.VI(C_MAMA OR C_OVARIO OR C_HIGADO).VO(COUNT).BY(CANCER)"
    result = await search.generate_plot(dsl, observatory_id="", chart_type="bar")
    assert result.is_ok, result.unwrap_err()

    data = result.unwrap()
    x_axis: list = data["xAxis"]["data"]
    assert len(x_axis) == 3, (
        f"Expected 3 bars (one per cancer type), got {len(x_axis)}: {x_axis}"
    )
    assert set(x_axis) == {"Breast", "Ovarian", "Liver"}


@pytest.mark.asyncio
async def test_vo_avg_computes_correctly(plot_records):
    """VO(AVG(TASA_100K)) over 2 C_MAMA records: (10+30)/2 = 20."""
    search: S.SearchService = plot_records["search"]
    dsl = "jub.v1.VI(C_MAMA).VO(AVG(TASA_100K))"
    result = await search.generate_plot(dsl, observatory_id="", chart_type="bar")
    assert result.is_ok, result.unwrap_err()

    data = result.unwrap()
    series_val = data["series"][0]["data"][0]
    assert series_val == 20.0, f"Expected AVG=20.0, got {series_val}"
