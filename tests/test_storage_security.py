"""
Path-traversal protection for product file storage.

Covers:
  jubapi.storage   key_for / safe_filename / is_safe_id and LocalStorageBackend
                   (every key must stay inside <base>/products)
  POST   /products                      product_id must be a safe path segment
  POST   /observatories/{id}/products/bulk
  POST   /products/{id}/upload          file name is reduced to its last component
  GET    /products/{id}/download        job_id cannot escape the product folder
"""

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

import jubapi.middlewares as MX
from jubapi.server import app
from jubapi.storage import InvalidStorageKey, LocalStorageBackend, is_safe_id, safe_filename


# ==========================================
# Unit: helpers
# ==========================================

@pytest.mark.parametrize("value", ["p_01", "product-3-527", "-abc_DEF12", "a.b", "x" * 128])
def test_is_safe_id_accepts(value):
    assert is_safe_id(value)


@pytest.mark.parametrize("value", [".", "..", ".hidden", "a/b", "a\\b", "", " x", "x" * 129, None])
def test_is_safe_id_rejects(value):
    assert not is_safe_id(value)


@pytest.mark.parametrize("filename, expected", [
    ("photo.jpg",                 "photo.jpg"),
    ("../../../../escaped.txt",   "escaped.txt"),
    ("/etc/passwd",               "passwd"),
    ("C:\\Users\\x\\photo.jpg",   "photo.jpg"),
    ("a\x00b.jpg",                "ab.jpg"),
])
def test_safe_filename_keeps_last_component(filename, expected):
    assert safe_filename(filename) == expected


@pytest.mark.parametrize("filename", ["", ".", "..", "../", "dir/.."])
def test_safe_filename_rejects_unusable_names(filename):
    with pytest.raises(InvalidStorageKey):
        safe_filename(filename)


# ==========================================
# Unit: LocalStorageBackend
# ==========================================

@pytest.fixture
def storage(tmp_path: Path) -> LocalStorageBackend:
    return LocalStorageBackend(base_path=str(tmp_path / "base"))


@pytest.mark.parametrize("part", ["..", ".", "a/b", "a\\b", "a\x00b"])
def test_key_for_rejects_unsafe_segments(storage, part):
    with pytest.raises(InvalidStorageKey):
        storage.key_for("product", part)


async def test_put_get_list_inside_namespace(storage):
    key = storage.key_for("p1", "job1", "photo.jpg")
    await storage.put(key, b"data")
    assert await storage.list(storage.prefix_for("p1")) == [key]
    assert (await storage.get(key))[0] == b"data"


@pytest.mark.parametrize("key", ["products/../../escaped.txt", "products/../escaped.txt", "../escaped.txt", "/tmp/escaped.txt"])
async def test_put_refuses_keys_outside_namespace(storage, tmp_path, key):
    with pytest.raises(InvalidStorageKey):
        await storage.put(key, b"x")
    assert not list(tmp_path.rglob("escaped.txt"))


async def test_get_and_list_refuse_keys_outside_namespace(storage, tmp_path):
    (tmp_path / "secret.txt").write_text("secret")
    with pytest.raises(InvalidStorageKey):
        await storage.get("products/../../secret.txt")
    with pytest.raises(InvalidStorageKey):
        await storage.list("products/../..")


async def test_delete_prefix_cannot_wipe_the_namespace(storage):
    key = storage.key_for("other-product", "job", "photo.jpg")
    await storage.put(key, b"keep me")

    for prefix in ("products/..", "products", "products/", "products/."):
        with pytest.raises(InvalidStorageKey):
            await storage.delete_prefix(prefix)

    assert (await storage.get(key))[0] == b"keep me"


async def test_delete_prefix_removes_only_that_product(storage):
    await storage.put(storage.key_for("p1", "j", "a.jpg"), b"1")
    await storage.put(storage.key_for("p10", "j", "b.jpg"), b"2")
    assert await storage.delete_prefix(storage.prefix_for("p1")) == 1
    assert await storage.list(storage.prefix_for("p10")) == [storage.key_for("p10", "j", "b.jpg")]


async def test_symlink_out_of_namespace_is_refused(storage, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (storage.base / "products").mkdir(parents=True, exist_ok=True)
    (storage.base / "products" / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(InvalidStorageKey):
        await storage.put("products/link/escaped.txt", b"x")
    assert not (outside / "escaped.txt").exists()


# ==========================================
# API
# ==========================================

@pytest.fixture
def api_storage(tmp_path: Path):
    """Routes the API's file storage to a temporary folder."""
    backend = LocalStorageBackend(base_path=str(tmp_path / "base"))
    app.dependency_overrides[MX.get_storage_backend] = lambda: backend
    yield backend
    app.dependency_overrides.pop(MX.get_storage_backend, None)


async def _create_product(client: AsyncClient) -> str:
    obs_id = f"obs_{uuid4().hex[:8]}"
    resp = await client.post("/api/v2/observatories", json={"observatory_id": obs_id, "title": "storage security"})
    assert resp.status_code in (200, 201), resp.text
    product_id = f"prod_{uuid4().hex[:8]}"
    resp = await client.post("/api/v2/products", json={"product_id": product_id, "name": "p", "observatory_id": obs_id})
    assert resp.status_code in (200, 201), resp.text
    return product_id


@pytest.mark.parametrize("product_id", ["..", ".", "a/b", ".hidden"])
async def test_create_product_rejects_unsafe_id(async_client: AsyncClient, product_id):
    resp = await async_client.post("/api/v2/products", json={"product_id": product_id, "name": "p", "observatory_id": "obs_x"})
    assert resp.status_code == 422


async def test_bulk_products_rejects_unsafe_id(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v2/observatories/obs_x/products/bulk",
        json={"products": [{"product_id": "..", "name": "p"}]},
    )
    assert resp.status_code == 422


async def test_upload_traversal_filename_is_stored_inside_product(async_client: AsyncClient, api_storage, tmp_path):
    product_id = await _create_product(async_client)

    resp = await async_client.post(
        f"/api/v2/products/{product_id}/upload",
        files={"file": ("../../../../escaped.txt", b"escaped", "text/plain")},
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    stored = list(tmp_path.rglob("escaped.txt"))
    assert stored == [api_storage.base / "products" / product_id / job_id / "escaped.txt"]

    resp = await async_client.get(f"/api/v2/products/{product_id}/download")
    assert resp.status_code == 200
    assert resp.content == b"escaped"


async def test_upload_rejects_unusable_filename(async_client: AsyncClient, api_storage):
    product_id = await _create_product(async_client)
    resp = await async_client.post(
        f"/api/v2/products/{product_id}/upload",
        files={"file": ("..", b"x", "text/plain")},
    )
    assert resp.status_code == 422


async def test_download_rejects_traversal_job_id(async_client: AsyncClient, api_storage):
    product_id = await _create_product(async_client)
    resp = await async_client.get(f"/api/v2/products/{product_id}/download", params={"job_id": ".."})
    assert resp.status_code == 400
