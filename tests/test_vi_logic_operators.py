"""
Regression tests for AND/OR/SINGLE logic in execute_query (_build_required_sets).

Before the fix, VI(SEX.AMBOS AND MORTALITY_AGE_GROUPS.AG_75_79) always returned []
because the AND branch intersected catalog_item_ids from different catalogs —
the intersection is always empty. OR masked the bug by unioning instead.

Seed layout
───────────────────────────────────────────────────────────────────────────────
  Catalogs
    cat_sex   (INTEREST): AMBOS, HOMBRES
    cat_age   (INTEREST): AG_75_79, AG_80_84

  Observatory: obs_logic_test

  Products
    p_ambos_ag75   tags=[AMBOS, AG_75_79]   ← only product with BOTH interest tags
    p_ambos_only   tags=[AMBOS]
    p_ag75_only    tags=[AG_75_79]
    p_hombres_ag80 tags=[HOMBRES, AG_80_84]
"""

import pytest
from typing import Set

import jubapi.repositories.v2 as R
import jubapi.models.v2 as M
import jubapi.services.v2 as S
import jubapi.enums.v2 as ENUMS
from jubapi.db.constants import CollectionNames as CN


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
async def services(test_db):
    obs_repo   = R.ObservatoriesRepository(test_db[CN.OBSERVATORIES.value])
    prod_repo  = R.ProductsRepository(test_db[CN.PRODUCTS.value])
    cat_repo   = R.CatalogsRepository(test_db[CN.CATALOGS.value])
    item_repo  = R.CatalogItemsRepository(test_db[CN.CATALOG_ITEMS.value])
    alias_repo = R.CatalogItemAliasesRepository(test_db[CN.CATALOG_ITEM_ALIASES.value])

    lm = S.GraphLinkManager(
        observatory_product_link_repository        = R.ObservatoryToProductLinkRepository(test_db[CN.OBSERVATORY_PRODUCT_LINKS.value]),
        observatory_catalog_link_repository        = R.ObservatoryToCatalogLinkRepository(test_db[CN.OBSERVATORY_CATALOG_LINKS.value]),
        catalog_catalog_item_link_repository       = R.CatalogToCatalogItemLinkRepository(test_db[CN.CATALOG_CATALOG_ITEM_LINKS.value]),
        product_catalog_item_link_repository       = R.ProductToCatalogItemLinkRepository(test_db[CN.PRODUCT_CATALOGS_ITEM_LINKS.value]),
        catalog_item_relationship_repository       = R.CatalogItemRelationshipRepository(test_db[CN.CATALOG_ITEM_RELATIONSHIPS.value]),
        catalog_item_catalog_alias_link_repository = R.CatalogItemToCatalogAliasLinkRepository(test_db[CN.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value]),
        observatory_service_link_repository        = R.ObservatoryToServiceLinkRepository(test_db[CN.OBSERVATORY_SERVICE_LINKS.value]),
        observatory_datasource_link_repository     = R.ObservatoryToDataSourceLinkRepository(test_db[CN.OBSERVATORY_DATASOURCE_LINKS.value]),
        product_product_link_repository            = R.ProductToProductLinkRepository(test_db[CN.PRODUCT_PRODUCT_LINKS.value]),
    )

    search_svc = S.SearchService(
        observatory_product_link_repository        = lm.observatory_product_link_repository,
        product_catalog_item_link_repository       = lm.product_catalog_item_link_repository,
        catalog_item_relationship_repository       = lm.catalog_item_relationship_repository,
        catalog_item_repository                    = item_repo,
        product_repository                         = prod_repo,
        catalog_alias_repository                   = alias_repo,
        catalog_item_catalog_alias_link_repository = lm.catalog_item_catalog_alias_link_repository,
        observatory_catalog_link_repository        = lm.observatory_catalog_link_repository,
        catalog_catalog_item_link_repository       = lm.catalog_catalog_item_link_repository,
        observatory_repository                     = obs_repo,
        catalog_repository                         = cat_repo,
        data_records_repository                    = R.DataRecordsRepository(test_db[CN.DATA_RECORDS.value]),
    )

    return {
        "search":  search_svc,
        "catalog": S.CatalogService(cat_repo, item_repo, alias_repo, lm),
        "product": S.ProductService(prod_repo, lm),
    }


@pytest.fixture(scope="function")
async def seed(services):
    cat_svc  = services["catalog"]
    prod_svc = services["product"]

    # Catalogs
    await cat_svc.catalog_repository.insert(M.CatalogX(
        catalog_id="cat_sex", name="Sex", value="SEX",
        catalog_type=ENUMS.CatalogType.INTEREST,
    ))
    await cat_svc.catalog_repository.insert(M.CatalogX(
        catalog_id="cat_age", name="Age Groups", value="MORTALITY_AGE_GROUPS",
        catalog_type=ENUMS.CatalogType.INTEREST,
    ))

    # Items — catalog_item_id == value so _resolve_identifier finds them by either field
    def item(iid: str) -> M.CatalogItemX:
        return M.CatalogItemX(
            catalog_item_id=iid, name=iid, value=iid,
            code=0, value_type=ENUMS.CatalogItemValueType.STRING, description="",
        )

    for iid in ["AMBOS", "HOMBRES"]:
        await cat_svc.catalog_item_repository.insert(item(iid))
        await cat_svc.link_manager.link_catalog_to_item("cat_sex", iid)

    for iid in ["AG_75_79", "AG_80_84"]:
        await cat_svc.catalog_item_repository.insert(item(iid))
        await cat_svc.link_manager.link_catalog_to_item("cat_age", iid)

    # Observatory
    obs = M.ObservatoryX(title="Logic Test Obs", observatory_id="obs_logic_test", name="Logic Test Obs", description="")
    await services["product"].link_manager.observatory_product_link_repository.collection.database[
        CN.OBSERVATORIES.value
    ].insert_one(obs.model_dump())

    # Products
    await prod_svc.insert_product(
        M.ProductX(product_id="p_ambos_ag75", name="Ambos+AG75", description=""),
        "obs_logic_test", ["AMBOS", "AG_75_79"],
    )
    await prod_svc.insert_product(
        M.ProductX(product_id="p_ambos_only", name="Ambos only", description=""),
        "obs_logic_test", ["AMBOS"],
    )
    await prod_svc.insert_product(
        M.ProductX(product_id="p_ag75_only", name="AG75 only", description=""),
        "obs_logic_test", ["AG_75_79"],
    )
    await prod_svc.insert_product(
        M.ProductX(product_id="p_hombres_ag80", name="Hombres+AG80", description=""),
        "obs_logic_test", ["HOMBRES", "AG_80_84"],
    )

    return services


def pids(result) -> Set[str]:
    assert result.is_ok, f"expected Ok but got Err: {result}"
    return {p.product_id for p in result.unwrap()}


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE — baseline
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_single_ambos(seed):
    result = await seed["search"].execute_query("jub.v1.VI(SEX.AMBOS)", "obs_logic_test")
    found = pids(result)
    assert "p_ambos_ag75" in found
    assert "p_ambos_only" in found
    assert "p_ag75_only" not in found
    assert "p_hombres_ag80" not in found


@pytest.mark.asyncio
async def test_single_ag_75_79(seed):
    result = await seed["search"].execute_query("jub.v1.VI(MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test")
    found = pids(result)
    assert "p_ambos_ag75" in found
    assert "p_ag75_only" in found
    assert "p_ambos_only" not in found
    assert "p_hombres_ag80" not in found


# ─────────────────────────────────────────────────────────────────────────────
# OR — union
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_or_returns_union(seed):
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.AMBOS OR MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    found = pids(result)
    assert "p_ambos_ag75" in found
    assert "p_ambos_only" in found
    assert "p_ag75_only" in found
    assert "p_hombres_ag80" not in found


# ─────────────────────────────────────────────────────────────────────────────
# AND — regression for the bug
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_and_returns_only_product_with_both_tags(seed):
    """Core regression: only p_ambos_ag75 has both AMBOS and AG_75_79."""
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.AMBOS AND MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    found = pids(result)
    assert found == {"p_ambos_ag75"}, (
        f"Expected only p_ambos_ag75 but got {found}. "
        "If empty, the AND intersection bug is not fixed."
    )


@pytest.mark.asyncio
async def test_and_excludes_partial_matches(seed):
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.AMBOS AND MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    found = pids(result)
    assert "p_ambos_only" not in found, "p_ambos_only has AMBOS but not AG_75_79 — must be excluded"
    assert "p_ag75_only" not in found, "p_ag75_only has AG_75_79 but not AMBOS — must be excluded"


@pytest.mark.asyncio
async def test_and_no_match_returns_empty(seed):
    """HOMBRES and AG_75_79 belong to no single product."""
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.HOMBRES AND MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    assert result.is_ok
    assert result.unwrap() == []


# ─────────────────────────────────────────────────────────────────────────────
# Wildcard transparency in AND
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wildcard_in_and_is_transparent(seed):
    """VI(SEX.* AND MORTALITY_AGE_GROUPS.AG_75_79) — SEX.* is a global wildcard,
    so only the AG_75_79 constraint applies."""
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.* AND MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    found = pids(result)
    assert "p_ambos_ag75" in found
    assert "p_ag75_only" in found
    assert "p_ambos_only" not in found
    assert "p_hombres_ag80" not in found


# ─────────────────────────────────────────────────────────────────────────────
# Scoped to observatory
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_and_scoped_to_observatory(seed):
    """Same AND query with explicit observatory_id produces the same result."""
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.AMBOS AND MORTALITY_AGE_GROUPS.AG_75_79)", "obs_logic_test"
    )
    found = pids(result)
    assert found == {"p_ambos_ag75"}


@pytest.mark.asyncio
async def test_and_without_scope_finds_same_product(seed):
    """Without observatory_id, the AND query still resolves to the same product."""
    result = await seed["search"].execute_query(
        "jub.v1.VI(SEX.AMBOS AND MORTALITY_AGE_GROUPS.AG_75_79)"
    )
    found = pids(result)
    assert "p_ambos_ag75" in found
