import pytest
import jubapi.repositories.v2 as R
import jubapi.models.v2 as M
import jubapi.services.v2 as S
import jubapi.enums.v2 as ENUMS
from jubapi.db.constants import CollectionNames


@pytest.fixture(scope="function")
async def svc(test_db):
    link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(test_db[CollectionNames.OBSERVATORY_PRODUCT_LINKS.value]),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(test_db[CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(test_db[CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(test_db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(test_db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(test_db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value]),
        observatory_service_link_repository        = R.ObservatoryToServiceLinkRepository(test_db[CollectionNames.OBSERVATORY_SERVICE_LINKS.value]),
        observatory_datasource_link_repository     = R.ObservatoryToDataSourceLinkRepository(test_db[CollectionNames.OBSERVATORY_DATASOURCE_LINKS.value]),
        product_product_link_repository            = R.ProductToProductLinkRepository(test_db[CollectionNames.PRODUCT_PRODUCT_LINKS.value]),
    )
    return {
        "catalog": S.CatalogService(
            R.CatalogsRepository(test_db[CollectionNames.CATALOGS.value]),
            R.CatalogItemsRepository(test_db[CollectionNames.CATALOG_ITEMS.value]),
            R.CatalogItemAliasesRepository(test_db[CollectionNames.CATALOG_ITEM_ALIASES.value]),
            link_manager,
        ),
        "product": S.ProductService(
            R.ProductsRepository(test_db[CollectionNames.PRODUCTS.value]),
            link_manager,
        ),
    }


async def _seed(svc):
    catalog_svc: S.CatalogService = svc["catalog"]
    product_svc: S.ProductService = svc["product"]

    cat = M.CatalogX(
        catalog_id="cat_sex", root_group_id="cat_sex", name="Sex",
        value="SEX", catalog_type=ENUMS.CatalogType.INTEREST, level=0,
    )
    await catalog_svc.create_catalog(cat)

    for item_id, name in [("MALE", "Male"), ("FEMALE", "Female")]:
        item = M.CatalogItemX(
            catalog_item_id=item_id, name=name, value=item_id,
            code=1, value_type=ENUMS.CatalogItemValueType.STRING, description="",
        )
        await catalog_svc.add_item_to_catalog("cat_sex", item)

    product = M.ProductX(product_id="prod_01", name="Test Product", description="", metadata={})
    await product_svc.product_repository.insert(product)

    return product_svc, catalog_svc


@pytest.mark.asyncio
async def test_tag_product_from_catalog_links_all_items(svc):
    product_svc, _ = await _seed(svc)

    result = await product_svc.tag_product_from_catalog("prod_01", "cat_sex")

    assert result.is_ok
    assert result.unwrap() == 2

    tags_result = await product_svc.get_product_tags("prod_01")
    assert tags_result.is_ok
    assert set(tags_result.unwrap()) == {"MALE", "FEMALE"}


@pytest.mark.asyncio
async def test_tag_product_from_catalog_is_idempotent(svc):
    product_svc, _ = await _seed(svc)

    await product_svc.tag_product_from_catalog("prod_01", "cat_sex")
    result = await product_svc.tag_product_from_catalog("prod_01", "cat_sex")

    assert result.is_ok
    assert result.unwrap() == 2

    tags_result = await product_svc.get_product_tags("prod_01")
    assert len(tags_result.unwrap()) == 2


@pytest.mark.asyncio
async def test_tag_product_from_catalog_product_not_found(svc):
    _, _ = await _seed(svc)
    product_svc: S.ProductService = svc["product"]

    result = await product_svc.tag_product_from_catalog("nonexistent_product", "cat_sex")

    assert result.is_err


@pytest.mark.asyncio
async def test_tag_product_from_catalog_empty_catalog(svc):
    catalog_svc: S.CatalogService = svc["catalog"]
    product_svc: S.ProductService = svc["product"]

    empty_cat = M.CatalogX(
        catalog_id="cat_empty", root_group_id="cat_empty", name="Empty",
        value="EMPTY", catalog_type=ENUMS.CatalogType.INTEREST, level=0,
    )
    await catalog_svc.create_catalog(empty_cat)

    product = M.ProductX(product_id="prod_02", name="Another Product", description="", metadata={})
    await product_svc.product_repository.insert(product)

    result = await product_svc.tag_product_from_catalog("prod_02", "cat_empty")

    assert result.is_ok
    assert result.unwrap() == 0
