"""
Integration tests for /api/v2/observatories/ endpoints.

Covers:
  GET  /observatories/          list observatories (pagination)
"""

import pytest
from httpx import AsyncClient
from jubapi.db.constants import CollectionNames

BASE = "/api/v2/observatories"


@pytest.fixture(autouse=True)
async def clean(test_db):
    await test_db[CollectionNames.OBSERVATORIES.value].drop()
    await test_db[CollectionNames.OBSERVATORY_CATALOG_LINKS.value].drop()
    await test_db[CollectionNames.OBSERVATORY_PRODUCT_LINKS.value].drop()
    yield


@pytest.fixture
async def seeded_observatories(async_client: AsyncClient, get_current_user):
    """Creates 5 observatories via the catalogs POST flow (direct DB insert via service layer).
    We insert directly using the test_db to avoid requiring a separate create endpoint.
    """
    from jubapi.db import get_collection
    from jubapi.db.constants import CollectionNames as CN
    import jubapi.models.v2 as M

    col = get_collection(CN.OBSERVATORIES.value)
    for i in range(1, 6):
        obs = M.ObservatoryX(
            observatory_id=f"obs_{i:03d}",
            title=f"Observatory {i}",
            description=f"Test observatory number {i}",
        )
        await col.insert_one(obs.model_dump())
    return async_client


# ==========================================
# List observatories
# ==========================================

@pytest.mark.asyncio
async def test_list_observatories_empty(async_client: AsyncClient):
    resp = await async_client.get(BASE)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_observatories_returns_all(seeded_observatories: AsyncClient):
    resp = await seeded_observatories.get(BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5
    titles = {o["title"] for o in body}
    for i in range(1, 6):
        assert f"Observatory {i}" in titles


@pytest.mark.asyncio
async def test_list_observatories_pagination_limit(seeded_observatories: AsyncClient):
    resp = await seeded_observatories.get(BASE, params={"limit": 2, "page_index": 0})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_observatories_pagination_second_page(seeded_observatories: AsyncClient):
    page0 = (await seeded_observatories.get(BASE, params={"limit": 2, "page_index": 0})).json()
    page1 = (await seeded_observatories.get(BASE, params={"limit": 2, "page_index": 1})).json()
    ids0 = {o["observatory_id"] for o in page0}
    ids1 = {o["observatory_id"] for o in page1}
    assert ids0.isdisjoint(ids1), "Pages must not overlap"


@pytest.mark.asyncio
async def test_list_observatories_returns_correct_shape(seeded_observatories: AsyncClient):
    resp = await seeded_observatories.get(BASE)
    assert resp.status_code == 200
    obs = resp.json()[0]
    assert "observatory_id" in obs
    assert "title" in obs
    assert "description" in obs
