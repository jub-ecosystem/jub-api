"""
Unit/integration tests for ObservatoriesRepository and ObservatoriesService.

Tests each service method in isolation using a clean test database.
"""

import pytest
import jubapi.models.v2 as M
import jubapi.repositories.v2 as R
import jubapi.services.v2 as S
import jubapi.enums.v2 as ENUMS
import jubapi.errors as EX
from jubapi.db.constants import CollectionNames


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
async def repos(test_db):
    link_manager = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(test_db[CollectionNames.OBSERVATORY_PRODUCT_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(test_db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(test_db[CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value]),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(test_db[CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(test_db[CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(test_db[CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
    )
    return {
        "obs":         R.ObservatoriesRepository(test_db[CollectionNames.OBSERVATORIES.value]),
        "products":    R.ProductsRepository(test_db[CollectionNames.PRODUCTS.value]),
        "link_manager": link_manager,
        "review": R.ReviewRepository(test_db[CollectionNames.OBSERVATORY_REVIEWS.value])
    }


@pytest.fixture
async def obs_service(repos):
    return S.ObservatoriesService(
        observatory_repository              = repos["obs"],
        observatory_product_link_repository = repos["link_manager"].observatory_product_link_repository,
        product_repository                  = repos["products"],
        graph_link_manager                  = repos["link_manager"],
        review_repository                   = repos["review"]
    )


def make_obs(obs_id: str, title: str = None) -> M.ObservatoryX:
    return M.ObservatoryX(
        observatory_id=obs_id,
        title=title or f"Observatory {obs_id}",
        description="Test observatory",
    )


# ==========================================
# Repository tests
# ==========================================

@pytest.mark.asyncio
async def test_repo_insert_and_get(repos):
    repo: R.ObservatoriesRepository = repos["obs"]
    obs = make_obs("obs_repo_01")
    result = await repo.insert(obs)
    assert result.is_ok
    assert result.unwrap() == "obs_repo_01"

    fetched = await repo.get_by_id("obs_repo_01")
    assert fetched.is_ok
    assert fetched.unwrap().title == obs.title


@pytest.mark.asyncio
async def test_repo_get_nonexistent_returns_err(repos):
    repo: R.ObservatoriesRepository = repos["obs"]
    result = await repo.get_by_id("does_not_exist")
    assert result.is_err
    assert isinstance(result.unwrap_err(), EX.NotFound)


@pytest.mark.asyncio
async def test_repo_delete(repos):
    repo: R.ObservatoriesRepository = repos["obs"]
    await repo.insert(make_obs("obs_del"))
    delete_result = await repo.delete("obs_del")
    assert delete_result.is_ok
    assert (await repo.get_by_id("obs_del")).is_err


@pytest.mark.asyncio
async def test_repo_find_all(repos):
    repo: R.ObservatoriesRepository = repos["obs"]
    for i in range(3):
        await repo.insert(make_obs(f"obs_find_{i}"))
    result = await repo.find({}, limit=10)
    assert result.is_ok
    assert len(result.unwrap()) == 3


@pytest.mark.asyncio
async def test_repo_update(repos):
    repo: R.ObservatoriesRepository = repos["obs"]
    await repo.insert(make_obs("obs_upd"))
    update_result = await repo.update("obs_upd", {"title": "Updated Title"})
    assert update_result.is_ok
    assert update_result.unwrap().title == "Updated Title"


# ==========================================
# Service — create / get / list / delete
# ==========================================

@pytest.mark.asyncio
async def test_service_create_observatory(obs_service):
    obs = make_obs("obs_svc_01")
    result = await obs_service.create_observatory(obs)
    assert result.is_ok
    assert result.unwrap() == "obs_svc_01"


@pytest.mark.asyncio
async def test_service_create_duplicate_returns_err(obs_service):
    obs = make_obs("obs_dup")
    await obs_service.create_observatory(obs)
    second = await obs_service.create_observatory(obs)
    assert second.is_err


@pytest.mark.asyncio
async def test_service_get_observatory(obs_service):
    await obs_service.create_observatory(make_obs("obs_get_01", "My Observatory"))
    result = await obs_service.get_observatory("obs_get_01")
    assert result.is_ok
    dto = result.unwrap()
    assert dto.observatory_id == "obs_get_01"
    assert dto.title == "My Observatory"


@pytest.mark.asyncio
async def test_service_get_nonexistent_returns_err(obs_service):
    result = await obs_service.get_observatory("ghost_obs")
    assert result.is_err


@pytest.mark.asyncio
async def test_service_list_observatories(obs_service):
    for i in range(4):
        await obs_service.create_observatory(make_obs(f"obs_list_{i}"))
    result = await obs_service.get_observatories(limit=10)
    assert result.is_ok
    assert len(result.unwrap()) == 4


@pytest.mark.asyncio
async def test_service_list_pagination(obs_service):
    for i in range(5):
        await obs_service.create_observatory(make_obs(f"obs_page_{i}"))
    page0 = (await obs_service.get_observatories(page_index=0, limit=2)).unwrap()
    page1 = (await obs_service.get_observatories(page_index=1, limit=2)).unwrap()
    ids0 = {o.observatory_id for o in page0}
    ids1 = {o.observatory_id for o in page1}
    assert ids0.isdisjoint(ids1)


@pytest.mark.asyncio
async def test_service_delete_observatory(obs_service):
    await obs_service.create_observatory(make_obs("obs_del_svc"))
    result = await obs_service.delete_observatory("obs_del_svc")
    assert result.is_ok
    assert (await obs_service.get_observatory("obs_del_svc")).is_err


# ==========================================
# Service — catalog linking
# ==========================================

@pytest.mark.asyncio
async def test_service_add_catalog_link(obs_service, repos):
    await obs_service.create_observatory(make_obs("obs_cat_link"))
    result = await obs_service.add_catalog("obs_cat_link", "cat_spatial", level=0)
    assert result.is_ok

    # Verify the link exists in the DB
    count = await repos["link_manager"].observatory_catalog_link_repository.collection.count_documents(
        {"observatory_id": "obs_cat_link", "catalog_id": "cat_spatial"}
    )
    assert count == 1


@pytest.mark.asyncio
async def test_service_add_multiple_catalogs(obs_service, repos):
    await obs_service.create_observatory(make_obs("obs_multi_cat"))
    for i, cat_id in enumerate(["cat_spatial", "cat_time", "cat_sex"]):
        result = await obs_service.add_catalog("obs_multi_cat", cat_id, level=i)
        assert result.is_ok

    count = await repos["link_manager"].observatory_catalog_link_repository.collection.count_documents(
        {"observatory_id": "obs_multi_cat"}
    )
    assert count == 3


@pytest.mark.asyncio
async def test_service_get_catalogs_for_observatory(obs_service, repos):
    await obs_service.create_observatory(make_obs("obs_get_cats"))

    # Insert a catalog directly so we can verify the lookup pipeline
    await repos["link_manager"].observatory_catalog_link_repository.collection.insert_one(
        {"observatory_id": "obs_get_cats", "catalog_id": "cat_spatial", "level": 0}
    )
    await repos["link_manager"].observatory_catalog_link_repository.collection.insert_one(
        {"observatory_id": "obs_get_cats", "catalog_id": "cat_time", "level": 1}
    )

    # get_catalogs_by_observatory_id does a $lookup against the catalogs collection;
    # because we haven't inserted catalog docs, the list will be empty — but the
    # call must not error out.
    result = await obs_service.get_catalogs_by_observatory_id("obs_get_cats")
    assert result.is_ok


# ==========================================
# Service — product linking
# ==========================================

@pytest.mark.asyncio
async def test_service_product_link_counted(obs_service, repos):
    await obs_service.create_observatory(make_obs("obs_prod_link"))
    await repos["link_manager"].link_observatory_to_product("obs_prod_link", "prod_01")
    await repos["link_manager"].link_observatory_to_product("obs_prod_link", "prod_02")

    result = await repos["link_manager"].count_products_linked_to_observatory("obs_prod_link")
    assert result.is_ok
    assert result.unwrap() == 2


@pytest.mark.asyncio
async def test_service_product_link_exists(obs_service, repos):
    await obs_service.create_observatory(make_obs("obs_exists"))
    await repos["link_manager"].link_observatory_to_product("obs_exists", "prod_X")

    exists = await repos["link_manager"].exists_product_linked_to_observatory("obs_exists", "prod_X")
    assert exists.is_ok
    assert exists.unwrap() is True

    not_exists = await repos["link_manager"].exists_product_linked_to_observatory("obs_exists", "prod_GHOST")
    assert not_exists.unwrap() is False
