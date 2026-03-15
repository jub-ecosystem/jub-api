import pytest
# import asyncio
# from jubapi.querylang.v2.parser import QueryAST
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import jubapi.repositories.v2 as R
import jubapi.models.v2 as M
import jubapi.services.v2 as S
from jubapi.db import CollectionNames
import random


@pytest.fixture(scope="function")
async def db():
    """Provides a clean test database."""
    client = MongoClient("mongodb://localhost:27027/")
    db = client.jub_test
    yield db
    # await client.drop_database('jub_test')

@pytest.fixture(scope="function")
async def services(db):
    """Initializes all required repositories and services."""
    # 1. Repositories
    observatory_repository        = R.ObservatoriesRepository(db[CollectionNames.OBSERVATORIES.value])
    product_repository            = R.ProductsRepository(db[CollectionNames.PRODUCTS.value])
    catalog_repository            = R.CatalogsRepository(db[CollectionNames.CATALOGS.value])
    catalog_item_repository       = R.CatalogItemsRepository(db[CollectionNames.CATALOG_ITEMS.value])
    catalog_item_value_repository = R.CatalogItemAliasesRepository(db[CollectionNames.CATALOG_ITEM_VALUES.value])
    
    # 2. Link Manager
    link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(db[CollectionNames.OBSERVATORY_PRODUCT_LINKS.value]),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(db[CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(db[CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value])
    )
    search_service = S.SearchService(
        observatory_product_link_repository        = link_manager.observatory_product_link_repository,
        product_catalog_item_link_repository       = link_manager.product_catalog_item_link_repository,
        catalog_item_relationship_repository       = link_manager.catalog_item_relationship_repository,
        catalog_item_repository                    = catalog_item_repository,
        product_repository                         = product_repository,
        catalog_alias_repository                   = catalog_item_value_repository,
        catalog_item_catalog_alias_link_repository = link_manager.catalog_item_catalog_alias_link_repository,
        observatory_catalog_link_repository        = link_manager.observatory_catalog_link_repository,
        catalog_catalog_item_link_repository       = link_manager.catalog_catalog_item_link_repository,
        observatory_repository                     = observatory_repository,
        catalog_repository                         = catalog_repository

    )

    # 3. Services
    return {
        "catalog": S.CatalogService(catalog_repository, catalog_item_repository, catalog_item_value_repository, link_manager),
        "product": S.ProductService(product_repository, link_manager),
        "observatory": S.ObservatoriesService(
            observatory_product_link_repository = link_manager.observatory_product_link_repository,
            observatory_repository              = observatory_repository,
            product_repository                  = product_repository,
            graph_link_manager                  = link_manager
        ),
        "search": search_service,
        "db": db # Passed for direct assertions
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
            catalog_item_alias_id= alias_1_name,
            value= alias_1_name,
            value_type= item.value_type,
            description= f"Alias 1 for {item.name}"
        )
        catalog_item_alias2 = M.CatalogItemAlias(
            catalog_item_alias_id= alias_2_name,
            value= alias_2_name,
            value_type= item.value_type,
            description= f"Alias 2 for {item.name}"
        )
       
        await cat_srv.add_alias_to_catalog_item(item.catalog_item_id, catalog_item_alias1)
        await cat_srv.add_alias_to_catalog_item(item.catalog_item_id, catalog_item_alias2)


    # ==========================================
    # 0.A SETUP THE ROOT CATALOGS
    # ==========================================
    catalogs_to_create = [
        M.CatalogX(catalog_id="cat_spatial", value="SPATIAL", catalog_type=M.CatalogType.SPATIAL, name="Spatial Catalog", description="Geographic dimensions"),
        M.CatalogX(catalog_id="cat_time", value="TEMPORAL", catalog_type=M.CatalogType.TEMPORAL, name="Temporal Catalog", description="Time dimensions"),
        M.CatalogX(catalog_id="cat_sex", value="SEX", catalog_type=M.CatalogType.INTEREST, name="Sex Catalog", description="Biological sex variables"),
        M.CatalogX(catalog_id="cat_cie10", value="CIE10", catalog_type=M.CatalogType.INTEREST, name="CIE-10 Catalog", description="Medical diagnoses"),
        M.CatalogX(catalog_id="cat_plot", value="PLOT_TYPE", catalog_type=M.CatalogType.INTEREST, name="Plot Type Catalog", description="Visualization types")
    ]
    catalogs_to_link = ["cat_spatial", "cat_time", "cat_sex", "cat_cie10", "cat_plot"]
    
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
                value_type      = M.CatalogItemValueType.DATETIME,
                description     = ""
            )
        )

    # ==========================================
    # 2. SPATIAL CATALOG
    # ==========================================
    await create_item_with_aliases("cat_spatial", M.CatalogItemX(
        catalog_item_id="MX", name="Mexico", value="MX", code=0, value_type=M.CatalogItemValueType.STRING, description=""
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
            catalog_item_id=state_id, name=state_id, value=state_id, code=state_code, value_type=M.CatalogItemValueType.STRING, description=""
        ), parent_id="MX")
        
        muni_code = state_code * 100
        for muni_name in munis:
            muni_id = f"{state_id}_{muni_name[:3].upper()}" 
            await create_item_with_aliases("cat_spatial", M.CatalogItemX(
                catalog_item_id=muni_id, name=muni_name, value=muni_id, code=muni_code, value_type=M.CatalogItemValueType.STRING, description=""
            ), parent_id=state_id)
            muni_code += 1
        state_code += 1

    # ==========================================
    # 3. INTEREST CATALOGS
    # ==========================================
    await create_item_with_aliases("cat_sex", M.CatalogItemX(catalog_item_id="FEMALE", name="Female", value="FEMALE", code=1, value_type=M.CatalogItemValueType.STRING, description=""))
    await create_item_with_aliases("cat_sex", M.CatalogItemX(catalog_item_id="MALE", name="Male", value="MALE", code=2, value_type=M.CatalogItemValueType.STRING, description=""))

    plot_types = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]
    for idx, p in enumerate(plot_types):
        await create_item_with_aliases("cat_plot", M.CatalogItemX(
            catalog_item_id=p, name=f"{p} Chart", value=p, code=idx, value_type=M.CatalogItemValueType.STRING, description=""
        ))

    cie10_chapters = {"II": "Neoplasias (C00-D48)", "IV": "Enfermedades endocrinas", "IX": "Enfermedades del aparato circulatorio"}
    for cap_id, desc in cie10_chapters.items():
        await create_item_with_aliases("cat_cie10", M.CatalogItemX(
            catalog_item_id=cap_id, name=desc, value=cap_id, code=0, value_type=M.CatalogItemValueType.STRING, description=""
        ))

    cie10_categories = {"C50": ("Tumor maligno de la mama", "II"), "C34": ("Tumor maligno bronquios/pulmón", "II"), "E11": ("Diabetes tipo 2", "IV"), "I10": ("Hipertensión", "IX")}
    for cat_id, (desc, parent_cap) in cie10_categories.items():
        await create_item_with_aliases("cat_cie10", M.CatalogItemX(
            catalog_item_id=cat_id, name=f"{cat_id} - {desc}", value=cat_id, code=0, value_type=M.CatalogItemValueType.STRING, description=""
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
                catalog_item_id=unique_db_id, name=f"{parent_cat}.{sub_val} - {desc}", value=sub_val, code=0, value_type=M.CatalogItemValueType.STRING, description=""
            ), parent_id=parent_cat)

    # ==========================================
    # 4. SEED RANDOMIZED UNIQUE PRODUCTS
    # ==========================================
    spatial_pool = ["MX", "TAM", "TAM_VIC", "NL_MON", "CDMX_COY", "JAL", "YUC", "PUE", "GTO", "CHIH"]
    time_pool    = [f"Y{year}" for year in range(2000, 2027)]
    sex_pool     = ["FEMALE", "MALE"]
    cie10_pool   = ["C50_1", "C50_2", "C50_3", "C34_1", "C34_2", "E11_1", "E11_2", "I10_1", "I10_2", "I10_3"]
    plot_pool    = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]

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
            
            tags = [sp_tag, sx_tag, tm_tag, ci_tag, pl_tag]
            prod_name = f"Data {p_id} - {sp_tag} {ci_tag} {tm_tag}"
            
            res = await prod_srv.insert_product(
                M.ProductX(product_id=p_id, name=prod_name, description="Autogenerated test product"), 
                obs_id, 
                tags
            )
            assert res.is_ok, f"Failed to insert product {p_id}: {res.error}"

# @pytest.fixture(autouse=True)
# async def seed_database_2(services):
#     """Seeds the database before the tests run with complex hierarchies and multiple observatories."""
#     cat_srv:S.CatalogService = services["catalog"]
#     prod_srv:S.ProductService = services["product"]
#     observatory_srv:S.ObservatoriesService = services["observatory"]
    

#     existing_prod = await prod_srv.get_product_by_id("p_01")
#     if existing_prod.is_ok:
#         return
    


#     # ==========================================
#     # 0. SETUP OBSERVATORIES & ASSIGN CATALOGS
#     # ==========================================
#     # We create 10 observatories and link the 5 catalogs to all of them
#     # catalogs_to_link = ["cat_spatial", "cat_time", "cat_sex", "cat_cie10", "cat_plot"]
#     # ==========================================
#     # 0.A SETUP THE ROOT CATALOGS
#     # ==========================================
#     catalogs_to_create = [
#         M.CatalogX(catalog_id="cat_spatial",value="SPATIAL",catalog_type=M.CatalogType.SPATIAL, name="Spatial Catalog", description="Geographic dimensions"),
#         M.CatalogX(catalog_id="cat_time",value="TEMPORAL",catalog_type=M.CatalogType.TEMPORAL, name="Temporal Catalog", description="Time dimensions"),
#         M.CatalogX(catalog_id="cat_sex",value="SEX",catalog_type= M.CatalogType.INTEREST, name="Sex Catalog", description="Biological sex variables"),
#         M.CatalogX(catalog_id="cat_cie10",value="CIE10",catalog_type=M.CatalogType.INTEREST, name="CIE-10 Catalog", description="Medical diagnoses"),
#         M.CatalogX(catalog_id="cat_plot",value="PLOT_TYPE",catalog_type=M.CatalogType.INTEREST, name="Plot Type Catalog", description="Visualization types")
#     ]
#     catalogs_to_link = ["cat_spatial", "cat_time", "cat_sex", "cat_cie10", "cat_plot"]
#     for cat in catalogs_to_create:
#         # Assumes your service has a create method for the root CatalogX entity
#         await cat_srv.create_catalog(cat)
    
#     for i in range(1, 11):
#         obs_id = f"obs_{i}"
#         # 1. Explicitly create the Observatory entity
#         await observatory_srv.create_observatory(
#             M.ObservatoryX(observatory_id=obs_id, title=f"Observatory {i}", description=f"Test Obs {i}")
#         )
#         for priority, cat_id in enumerate(catalogs_to_link):
#             await observatory_srv.add_catalog(obs_id, cat_id, priority)

#     # ==========================================
#     # 1. TEMPORAL CATALOG (2000 to 2026)
#     # ==========================================
#     for year in range(2000, 2027):
#         await cat_srv.add_item_to_catalog(
#             "cat_time", 
#             M.CatalogItemX(
#                 catalog_item_id = f"Y{year}",
#                 name            = str(year),
#                 value           = str(year),
#                 code            = year,
#                 temporal_value  = f"{year}-01-01T00:00:00Z",
#                 value_type      = M.CatalogItemValueType.DATETIME,
#                 description     = ""
#             )
#         )

#     # ==========================================
#     # 2. SPATIAL CATALOG (MX -> 10 States -> 2 Munis)
#     # ==========================================
#     # Root Node
#     await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
#         catalog_item_id="MX", name="Mexico", value="MX", code=0, value_type="STRING", description=""
#     ))
    
#     states_munis = {
#         "TAM": ["Victoria", "Tampico"],
#         "NL": ["Monterrey", "San Pedro"],
#         "CDMX": ["Coyoacan", "Tlalpan"],
#         "JAL": ["Guadalajara", "Zapopan"],
#         "VER": ["Veracruz", "Xalapa"],
#         "YUC": ["Merida", "Valladolid"],
#         "PUE": ["Puebla", "Cholula"],
#         "GTO": ["Leon", "Irapuato"],
#         "CHIH": ["Chihuahua", "Juarez"],
#         "OAX": ["Oaxaca", "Huatulco"]
#     }
    
#     state_code = 1
#     for state_id, munis in states_munis.items():
#         # Insert State
#         await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
#             catalog_item_id=state_id, name=state_id, value=state_id, code=state_code, value_type=M.CatalogItemValueType.STRING, description=""
#         ), parent_id="MX")
        
#         # Insert Municipalities (using first 3 letters as ID for simplicity)
#         muni_code = state_code * 100
#         for muni_name in munis:
#             muni_id = f"{state_id}_{muni_name[:3].upper()}" 
#             await cat_srv.add_item_to_catalog("cat_spatial", M.CatalogItemX(
#                 catalog_item_id=muni_id, name=muni_name, value=muni_id, code=muni_code, value_type=M.CatalogItemValueType.STRING, description=""
#             ), parent_id=state_id)
#             muni_code += 1
#         state_code += 1

#     # ==========================================
#     # 3. INTEREST CATALOGS (Sex, CIE10, Plot)
#     # ==========================================
#     # SEX
#     await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="FEMALE", name="Female", value="FEMALE", code=1, value_type=M.CatalogItemValueType.STRING, description=""))
#     await cat_srv.add_item_to_catalog("cat_sex", M.CatalogItemX(catalog_item_id="MALE", name="Male", value="MALE", code=2, value_type=M.CatalogItemValueType.STRING, description=""))

#     # PLOT TYPE
#     plot_types = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]
#     for idx, p in enumerate(plot_types):
#         await cat_srv.add_item_to_catalog("cat_plot", M.CatalogItemX(
#             catalog_item_id=p, name=f"{p} Chart", value=p, code=idx, value_type=M.CatalogItemValueType.STRING, description=""
#         ))

# # ==========================================
#     # 3. INTEREST CATALOG (Perfect Hierarchy)
#     # ==========================================
    
#     # Level 1: Chapters (Roots)
#     cie10_chapters = {
#         "II": "Neoplasias (C00-D48)",
#         "IV": "Enfermedades endocrinas, nutricionales y metabólicas (E00-E90)",
#         "IX": "Enfermedades del aparato circulatorio (I00-I99)"
#     }
    
#     for cap_id, desc in cie10_chapters.items():
#         await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
#             catalog_item_id=cap_id, 
#             name=desc, 
#             value=cap_id, # DSL matches 'II', 'IV', 'IX'
#             code=0, 
#             value_type=M.CatalogItemValueType.STRING, 
#             description=""
#         ))

#     # Level 2: Categories
#     cie10_categories = {
#         "C50": ("Tumor maligno de la mama", "II"),
#         "C34": ("Tumor maligno de los bronquios y del pulmón", "II"),
#         "E11": ("Diabetes mellitus tipo 2", "IV"),
#         "I10": ("Hipertensión esencial", "IX")
#     }

#     for cat_id, (desc, parent_cap) in cie10_categories.items():
#         await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
#             catalog_item_id=cat_id, 
#             name=f"{cat_id} - {desc}", 
#             value=cat_id, # DSL matches 'C50', 'E11', etc.
#             code=0, 
#             value_type=M.CatalogItemValueType.STRING, 
#             description=""
#         ), parent_id=parent_cap)

#     # Level 3: Subcategories (The leaf nodes)
#     # Split the medical codes (e.g., E11.2 -> parent "E11", child "2")
#     cie10_subcategories = {
#         "C50": [("1", "Porción no especificada"), ("2", "Cuadrante superior interno"), ("3", "Cuadrante inferior interno")],
#         "C34": [("1", "Lóbulo superior"), ("2", "Lóbulo medio")],
#         "E11": [("1", "Con cetoacidosis"), ("2", "Con complicaciones renales"), ("3", "Con complicaciones oftálmicas")],
#         "I10": [("1", "Benigna"), ("2", "Maligna"), ("3", "No especificada")]
#     }

#     for parent_cat, subcodes in cie10_subcategories.items():
#         for sub_val, desc in subcodes:
#             # Create a unique ID for the DB (e.g., "E11_2")
#             unique_db_id = f"{parent_cat}_{sub_val}" 
            
#             await cat_srv.add_item_to_catalog("cat_cie10", M.CatalogItemX(
#                 catalog_item_id=unique_db_id, 
#                 name=f"{parent_cat}.{sub_val} - {desc}", 
#                 value=sub_val, # DSL matches '1', '2', '3'
#                 code=0, 
#                 value_type=M.CatalogItemValueType.STRING, 
#                 description=""
#             ), parent_id=parent_cat)

#     # ==========================================
#     # 4. SEED PRODUCTS (100 Total: 10 per Observatory)
#     # ==========================================
    
#     # Define the pools of valid item IDs we just seeded
#     spatial_pool = ["MX", "TAM", "TAM_VIC", "NL_MON", "CDMX_COY", "JAL", "YUC", "PUE", "GTO", "CHIH"]
#     time_pool    = [f"Y{year}" for year in range(2000, 2027)]
#     sex_pool     = ["FEMALE", "MALE"]
#     cie10_pool   = ["C50_1", "C50_2", "C50_3", "C34_1", "C34_2", "E11_1", "E11_2", "I10_1", "I10_2", "I10_3"]
#     plot_pool    = ["LINE", "BAR", "PIE", "SCATTER", "HEATMAP"]

#     product_counter = 0

#     for obs_idx in range(1, 11):
#         obs_id = f"obs_{obs_idx}"
        
#         for prod_idx in range(1, 11):
#             product_counter += 1
#             p_id = f"p_{obs_idx:02d}_{prod_idx:02d}" # e.g., p_01_01, p_01_02... p_10_10
            
#             # Use modulo to deterministically cycle through the pools so we get a good mix of data
#             sp_tag = spatial_pool[product_counter % len(spatial_pool)]
#             tm_tag = time_pool[product_counter % len(time_pool)]
#             sx_tag = sex_pool[product_counter % len(sex_pool)]
#             ci_tag = cie10_pool[product_counter % len(cie10_pool)]
#             pl_tag = plot_pool[product_counter % len(plot_pool)]
            
#             tags = [sp_tag, sx_tag, tm_tag, ci_tag, pl_tag]
            
#             # Create a descriptive name so it's easy to read during test debugging
#             prod_name = f"Data {p_id} - {sp_tag} {ci_tag} {tm_tag}"
            
#             res = await prod_srv.insert_product(
#                 M.ProductX(product_id=p_id, name=prod_name, description="Autogenerated test product"), 
#                 obs_id, 
#                 tags
#             )
#             assert res.is_ok, f"Failed to insert product {p_id}: {res.error}"

@pytest.mark.asyncio
async def test_search_observatories(services):
    search_service:S.SearchService = services["search"]
    query  = "jub.v1.VS(MX.TAM).VT(>=2000 AND <=2026).VI(SEX.MALE AND CIE10.E11.2 AND PLOT_TYPE.BAR)"
    result = await search_service.search_observatories(query=query)
    assert result.is_ok

@pytest.mark.asyncio
async def test_search_products(services):
    search_service:S.SearchService = services["search"]
    query  = "jub.v1.VT(>=2000 AND <=2026).VI(PLOT_TYPE.BAR)"
    result = await search_service.search(query=query)
    assert result.is_ok
