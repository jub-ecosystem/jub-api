import pytest
# import asyncio
# from jubapi.querylang.v2.parser import QueryAST
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import jubapi.repositories.v2 as R
import jubapi.models.v2 as M
import jubapi.services.v2 as S
from jubapi.db.constants import CollectionNames
import jubapi.enums.v2 as ENUMS


# @pytest.fixture(scope="function")
# async def db():
#     """Provides a clean test database."""
#     client = MongoClient("mongodb://localhost:27027/")
#     db = client.jub
#     yield db
#     await client.drop_database('jub_test')

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
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(test_db[CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(test_db[CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(test_db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(test_db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(test_db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value])
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
    return {
        "catalog": S.CatalogService(catalog_repository, catalog_item_repository, catalog_item_alias_repository, link_manager),
        "product": S.ProductService(product_repository, link_manager),
        "observatory": S.ObservatoriesService(
            observatory_product_link_repository = link_manager.observatory_product_link_repository,
            observatory_repository              = observatory_repository,
            product_repository                  = product_repository,
            graph_link_manager                  = link_manager
        ),
        "search": search_service,
        "db": test_db # Passed for direct assertions
    }

@pytest.fixture(autouse=True)
async def seed_database_2(services):
    """Seeds the database before the tests run with complex hierarchies and multiple observatories."""
    cat_srv:S.CatalogService = services["catalog"]
    prod_srv:S.ProductService = services["product"]
    observatory_srv:S.ObservatoriesService = services["observatory"]
    

    existing_prod = await prod_srv.get_product_by_id("p_01")
    if existing_prod.is_ok:
        return
    # ==========================================
    # 0. SETUP OBSERVATORIES & ASSIGN CATALOGS
    # ==========================================
    # We create 10 observatories and link the 5 catalogs to all of them
    catalogs_to_link = ["cat_spatial", "cat_time", "cat_sex", "cat_cie10", "cat_plot"]
    
    for i in range(1, 11):
        obs_id = f"obs_{i}"
        for priority, cat_id in enumerate(catalogs_to_link):
            await observatory_srv.add_catalog(obs_id, cat_id, priority)

    # ==========================================
    # 1. TEMPORAL CATALOG (2000 to 2026)
    # ==========================================
    for year in range(2000, 2027):
        await cat_srv.add_item_to_catalog(
            "cat_time", 
            M.CatalogItemX(
                catalog_item_id = f"Y{year}",
                name            = str(year),
                value           = str(year),
                code            = year,
                temporal_value  = f"{year}-01-01T00:00:00Z",
                value_type      = ENUMS.CatalogItemValueType.DATETIME,
                description     = ""
            )
        )

    # ==========================================
    # 2. SPATIAL CATALOG (MX -> 10 States -> 2 Munis)
    # ==========================================
    # Root Node
    await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
        catalog_item_id="MX", name="Mexico", value="MX", code=0, value_type="STRING", description=""
    ))
    
    states_munis = {
        "TAM": ["Victoria", "Tampico"],
        "NL": ["Monterrey", "San Pedro"],
        "CDMX": ["Coyoacan", "Tlalpan"],
        "JAL": ["Guadalajara", "Zapopan"],
        "VER": ["Veracruz", "Xalapa"],
        "YUC": ["Merida", "Valladolid"],
        "PUE": ["Puebla", "Cholula"],
        "GTO": ["Leon", "Irapuato"],
        "CHIH": ["Chihuahua", "Juarez"],
        "OAX": ["Oaxaca", "Huatulco"]
    }
    
    state_code = 1
    for state_id, munis in states_munis.items():
        # Insert State
        await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
            catalog_item_id=state_id, name=state_id, value=state_id, code=state_code, value_type=ENUMS.CatalogItemValueType.STRING, description=""
        ), parent_id="MX")
        
        # Insert Municipalities (using first 3 letters as ID for simplicity)
        muni_code = state_code * 100
        for muni_name in munis:
            muni_id = f"{state_id}_{muni_name[:3].upper()}" 
            await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
                catalog_item_id=muni_id, name=muni_name, value=muni_id, code=muni_code, value_type=ENUMS.CatalogItemValueType.STRING, description=""
            ), parent_id=state_id)
            muni_code += 1
        state_code += 1

    # ==========================================
    # 3. INTEREST CATALOGS (Sex, CIE10, Plot)
    # ==========================================
    # SEX
    await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="FEMALE", name="Female", value="FEMALE", code=1, value_type=ENUMS.CatalogItemValueType.STRING, description=""))
    await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="MALE", name="Male", value="MALE", code=2, value_type=ENUMS.CatalogItemValueType.STRING, description=""))

    # PLOT TYPE
    plot_types = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]
    for idx, p in enumerate(plot_types):
        await cat_srv.add_item_to_catalog("cat_plot", M.CatalogItemX(
            catalog_item_id=p, name=f"{p} Chart", value=p, code=idx, value_type=ENUMS.CatalogItemValueType.STRING, description=""
        ))

# ==========================================
    # 3. INTEREST CATALOG (Perfect Hierarchy)
    # ==========================================
    
    # Level 1: Chapters (Roots)
    cie10_chapters = {
        "II": "Neoplasias (C00-D48)",
        "IV": "Enfermedades endocrinas, nutricionales y metabólicas (E00-E90)",
        "IX": "Enfermedades del aparato circulatorio (I00-I99)"
    }
    
    for cap_id, desc in cie10_chapters.items():
        await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
            catalog_item_id=cap_id, 
            name=desc, 
            value=cap_id, # DSL matches 'II', 'IV', 'IX'
            code=0, 
            value_type=ENUMS.CatalogItemValueType.STRING, 
            description=""
        ))

    # Level 2: Categories
    cie10_categories = {
        "C50": ("Tumor maligno de la mama", "II"),
        "C34": ("Tumor maligno de los bronquios y del pulmón", "II"),
        "E11": ("Diabetes mellitus tipo 2", "IV"),
        "I10": ("Hipertensión esencial", "IX")
    }

    for cat_id, (desc, parent_cap) in cie10_categories.items():
        await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
            catalog_item_id=cat_id, 
            name=f"{cat_id} - {desc}", 
            value=cat_id, # DSL matches 'C50', 'E11', etc.
            code=0, 
            value_type=ENUMS.CatalogItemValueType.STRING, 
            description=""
        ), parent_id=parent_cap)

    # Level 3: Subcategories (The leaf nodes)
    # Split the medical codes (e.g., E11.2 -> parent "E11", child "2")
    cie10_subcategories = {
        "C50": [("1", "Porción no especificada"), ("2", "Cuadrante superior interno"), ("3", "Cuadrante inferior interno")],
        "C34": [("1", "Lóbulo superior"), ("2", "Lóbulo medio")],
        "E11": [("1", "Con cetoacidosis"), ("2", "Con complicaciones renales"), ("3", "Con complicaciones oftálmicas")],
        "I10": [("1", "Benigna"), ("2", "Maligna"), ("3", "No especificada")]
    }

    for parent_cat, subcodes in cie10_subcategories.items():
        for sub_val, desc in subcodes:
            # Create a unique ID for the DB (e.g., "E11_2")
            unique_db_id = f"{parent_cat}_{sub_val}" 
            
            await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
                catalog_item_id=unique_db_id, 
                name=f"{parent_cat}.{sub_val} - {desc}", 
                value=sub_val, # DSL matches '1', '2', '3'
                code=0, 
                value_type=ENUMS.CatalogItemValueType.STRING, 
                description=""
            ), parent_id=parent_cat)

# ==========================================
    # 4. SEED PRODUCTS
    # ==========================================
    # Let's seed some highly specific products to test intersections.
    
    # Obs 1: Breast Cancer in Tamaulipas (Line Plot over time)
    await prod_srv.insert_product(M.ProductX(product_id="p_01", name="Breast Cancer TAM Line", description=""), "obs_1", ["TAM", "FEMALE", "Y2026", "C50_1", "LINE"])
    
    # Obs 2: Diabetes in Monterrey, NL (Bar Chart)
    await prod_srv.insert_product(M.ProductX(product_id="p_02", name="Diabetes Monterrey Bar", description=""), "obs_2", ["NL_MON", "MALE", "Y2025", "E11_2", "BAR"])
    
    # Obs 3: General Hypertension in Mexico (Pie Chart)
    # Note: Tagged with the category root "I10"
    await prod_srv.insert_product(M.ProductX(product_id="p_03", name="Hypertension MX General", description=""), "obs_3", ["MX", "FEMALE", "Y2020", "I10", "PIE"])
    
    # Obs 4: Lung Cancer in Victoria, TAM (Heatmap spanning multiple years)
    await prod_srv.insert_product(M.ProductX(product_id="p_04", name="Lung Cancer Victoria Multi-year", description=""), "obs_4", ["TAM_VIC", "MALE", "Y2015", "Y2016", "Y2017", "C34_1", "HEATMAP"])
    
    # Obs 5: Breast cancer across entire country (Scatter)
    await prod_srv.insert_product(M.ProductX(product_id="p_05", name="Breast Cancer MX Scatter", description=""), "obs_5", ["MX", "FEMALE", "Y2024", "C50_2", "SCATTER"])
    
    # Obs 6: Hypertension in CDMX (Line Chart)
    await prod_srv.insert_product(M.ProductX(product_id="p_06", name="Hypertension CDMX Coyoacan", description=""), "obs_6", ["CDMX_COY", "MALE", "Y2023", "I10_1", "LINE"])

    # Obs 7 to 10: Just filling in with some mixed data for query testing
    await prod_srv.insert_product(M.ProductX(product_id="p_07", name="Diabetes JAL Multi-sex", description=""), "obs_7", ["JAL", "MALE", "FEMALE", "Y2022", "E11_1", "BAR"])
    await prod_srv.insert_product(M.ProductX(product_id="p_08", name="Lung Cancer YUC", description=""), "obs_8", ["YUC", "FEMALE", "Y2021", "C34_2", "PIE"])
    await prod_srv.insert_product(M.ProductX(product_id="p_09", name="Hypertension PUE", description=""), "obs_9", ["PUE", "MALE", "Y2010", "I10_3", "HEATMAP"])
    await prod_srv.insert_product(M.ProductX(product_id="p_10", name="Breast Cancer GTO", description=""), "obs_10", ["GTO", "FEMALE", "Y2005", "C50_3", "LINE"])

@pytest.fixture(autouse=True)
async def seed_database(services):
    """Seeds the database before the tests run."""
    cat_srv:S.CatalogService = services["catalog"]
    prod_srv: S.ProductService = services["product"]
    observatory_srv: S.ObservatoriesService = services["observatory"]
    
    # 1. Seed Temporal Catalog Items (The key to making time work in the graph)
    # The 'value' field must be a sortable string (like ISO dates or year strings)
    # so the math operators (>, <, >=) work natively in MongoDB.
    # await services[""]
    exiting_product = await prod_srv.get_product_by_id("p1")
    if exiting_product.is_ok:
        return
    await observatory_srv.add_catalog("obs_test", "cat_spatial", 0)
    await observatory_srv.add_catalog("obs_test", "cat_time", 1)

    await cat_srv.add_item_to_catalog("cat_time", M.CatalogItemX(
        catalog_item_id = "Y2020",
        name            = "2020",
        value           = "2020",
        code            = 2020,
        temporal_value  = "2020-01-01T00:00:00Z",
        value_type      = ENUMS.CatalogItemValueType.DATETIME,
        description     = ""
    ))
    await cat_srv.add_item_to_catalog(
        "cat_time", 
        M.CatalogItemX(
            catalog_item_id = "Y2023",
            name            = "2023",
            value           = "2023",
            temporal_value  = "2023-01-01T00:00:00Z",
            code            = 2023,
            value_type      = ENUMS.CatalogItemValueType.DATETIME,
            description     = ""
        )
    )
    await cat_srv.add_item_to_catalog(
        "cat_time", 
        M.CatalogItemX(
            catalog_item_id = "Y2024",
            name            = "2024",
            value           = "2024",
            temporal_value  = "2024-01-01T00:00:00Z",
            code            = 2024,
            value_type      = ENUMS.CatalogItemValueType.DATETIME,
            description     = ""
        )
    )
    await cat_srv.add_item_to_catalog(
        "cat_time", 
        M.CatalogItemX(
            catalog_item_id = "Y2025",
            name            = "2025",
            value           = "2025",
            temporal_value  = "2025-01-01T00:00:00Z",
            code            = 2025,
            value_type      = ENUMS.CatalogItemValueType.DATETIME,
            description     = ""
        )
    )

    # 2. Seed Spatial & Interest Items (Simplified for tests)
    await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(catalog_item_id="TAM", name="Tamaulipas", value="TAM", code=1, value_type=ENUMS.CatalogItemValueType.STRING, description=""))
    await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(catalog_item_id="VIC", name="Victoria", value="VIC", code=2, value_type=ENUMS.CatalogItemValueType.STRING, description=""), parent_id="TAM")
    await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(catalog_item_id="SLP", name="San Luis Potosi", value="SLP", code=3, value_type=ENUMS.CatalogItemValueType.STRING, description=""))
    
    await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="FEMALE", name="Female", value="FEMALE", code=1, value_type=ENUMS.CatalogItemValueType.STRING, description=""))
    await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="MALE", name="Male", value="MALE", code=2, value_type=ENUMS.CatalogItemValueType.STRING, description=""))

    # 3. Seed Products
    # Product 1: Victoria, Female, 2024
    await prod_srv.insert_product(M.ProductX(product_id="p1", name="VIC_FEM_2024", description=""), "obs_test", ["VIC", "FEMALE", "Y2024"])
    
    # Product 2: Tamaulipas (State), Male, 2023
    await prod_srv.insert_product(M.ProductX(product_id="p2", name="TAM_MALE_2023", description=""), "obs_test", ["TAM", "MALE", "Y2023"])
    
    # Product 3: Disjointed Dates! SLP, Female, covers both 2020 AND 2025
    await prod_srv.insert_product(M.ProductX(product_id="p3", name="SLP_FEM_MULTI_DATE", description=""), "obs_test", ["SLP", "FEMALE", "Y2020", "Y2025"])


@pytest.mark.asyncio
async def test_vs_spatial_hierarchy(services):
    search_srv:S.SearchService = services["search"]
    
    # Query: Anything inside Tamaulipas
    res = await search_srv.execute_query("jub.v1.VS(TAM.*)", "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    
    # Should find p1 (VIC is inside TAM) and p2 (Tagged directly with TAM)
    assert "p1" in products
    assert "p2" in products
    assert "p3" not in products # SLP is not inside TAM

@pytest.mark.asyncio
async def test_vt_exact_time(services):
    search_srv: S.SearchService = services["search"]
    
    # Query: Exactly 2024
    res = await search_srv.execute_query("jub.v1.VT(2024)", "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    assert "p1" in products # p1 is 2024
    assert "p2" not in products
    assert "p3" not in products

@pytest.mark.asyncio
async def test_vt_math_operator_greater_than(services):
    search_srv = services["search"]
    
    # Query: Any time strictly greater than 2023
    # The code maps '>' to '$gt' and searches the CatalogItem 'value' field.
    # It will find IDs ['Y2024', 'Y2025'].
    res = await search_srv.execute_query("jub.v1.VT(> 2023)", "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    assert "p1" in products # p1 has Y2024
    assert "p3" in products # p3 has Y2025
    assert "p2" not in products # p2 is exactly 2023 (not >)

@pytest.mark.asyncio
async def test_vt_multi_date_product(services):
    search_srv = services["search"]
    
    # Query: Exactly 2020
    # Proves we can find products that have disjointed dates
    res = await search_srv.execute_query("jub.v1.VT(2020)", "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    assert products == ["p3"] # p3 is tagged with both Y2020 and Y2025

@pytest.mark.asyncio
async def test_vt_math_operator_range(services):
    search_srv:S.SearchService = services["search"]
    
    # Query: Time between 2021 and 2024 inclusive
    res = await search_srv.execute_query("jub.v1.VT(>= 2021 AND <= 2024)", "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    print(f"Products found in range query: {products}")
    assert "p1" in products # 2024
    assert "p2" in products # 2023
    assert "p3" not in products # 2020 is too early, 2025 is too late

@pytest.mark.asyncio
async def test_complex_combination(services):
    search_srv = services["search"]
    
    # Query: Female AND (inside Tamaulipas) AND (after 2023)
    query_str = "jub.v1.VS(TAM.*).VI(FEMALE).VT(> 2023)"
    res = await search_srv.execute_query(query_str, "obs_test")
    
    assert res.is_ok
    products = [p.product_id for p in res.unwrap()]
    
    # Only p1 matches all three conditions
    assert len(products) == 1
    assert "p1" in products