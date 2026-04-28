import pytest
from httpx import AsyncClient

# ==========================================
# E2E TESTS: BULK CATALOG INGESTION (NO MOCKS)
# ==========================================

@pytest.mark.asyncio
async def test_api_create_catalog_bulk_success(async_client: AsyncClient, test_db, get_current_user):
    """
    E2E Test: Creates a Catalog with Items, Aliases, and Hierarchy in a single request.
    Hits the REAL test database and verifies the nested payload is unpacked correctly.
    """
    MOCK_USER, headers = get_current_user

    # 1. The God Payload
    payload = {
        "name": "Geografía de Prueba",
        "value": "GEO_PRUEBA",
        "catalog_type": "SPATIAL",
        "description": "Catálogo generado por test de integración",
        "items": [
            {
                "name": "Estado Test",
                "value": "ESTADO_T",
                "code": 10,
                "value_type": "STRING",
                "aliases": [
                    { "value": "EDO_T", "value_type": "STRING", "description": "Alias corto" }
                ],
                "children": [
                    {
                        "name": "Ciudad Test",
                        "value": "CIUDAD_T",
                        "code": 101,
                        "value_type": "STRING",
                        "aliases": [],
                        "children": []
                    }
                ]
            }
        ]
    }

    # 2. Fire the real HTTP request
    response = await async_client.post("/api/v2/catalogs", json=payload, headers=headers)

    # 3. Validate HTTP Response
    assert response.status_code == 200
    
    # Assuming your router returns the generated catalog_id directly or wrapped in a dict
    response_data = response.json()
    catalog_id = response_data if isinstance(response_data, str) else response_data.get("catalog_id")
    assert "cat_" in catalog_id

    # 4. The Ultimate Proof: Check the REAL database directly
    # (Adjust collection names based on how your Mongo repositories are named)
    
    # A. Did the root catalog save?
    saved_catalog = await test_db.catalogs.find_one({"catalog_id": catalog_id})
    assert saved_catalog is not None
    assert saved_catalog["name"] == "Geografía de Prueba"

    # B. Did the nested child (Ciudad Test) save?
    saved_child = await test_db.catalog_items.find_one({"value": "CIUDAD_T"})
    assert saved_child is not None
    assert saved_child["code"] == 101

    # C. Did the alias save?
    saved_alias = await test_db.catalog_item_aliases.find_one({"value": "EDO_T"})
    assert saved_alias is not None


@pytest.mark.asyncio
async def test_api_create_catalog_bulk_validation_error(async_client: AsyncClient, get_current_user):
    """
    Ensures FastAPI's Pydantic layer automatically blocks invalid payloads 
    before they ever reach your database.
    """
    MOCK_USER, headers = get_current_user

    # Missing required 'catalog_type' and 'value' at the root level
    bad_payload = {
        "name": "Bad Catalog",
        "description": "This should fail",
        "items": []
    }

    response = await async_client.post("/api/v2/catalogs", json=bad_payload, headers=headers)

    # FastAPI should intercept this and return a 422 Unprocessable Entity
    assert response.status_code == 422
    
    # Verify the error tells the user exactly which fields are missing
    errors = response.json()["detail"]
    missing_fields = [err["loc"][-1] for err in errors]
    
    assert "catalog_type" in missing_fields
    assert "value" in missing_fields


@pytest.mark.asyncio
async def test_api_create_catalog_bulk_nested_validation_error(async_client: AsyncClient, get_current_user):
    """
    Proves that Pydantic is checking the DEEP nested objects, not just the root.
    """
    MOCK_USER, headers = get_current_user

    payload_with_bad_child = {
        "name": "Valid Root",
        "value": "VALID_ROOT",
        "catalog_type": "SPATIAL",
        "items": [
            {
                "name": "Valid Item",
                "value": "VALID_ITEM",
                "code": 1,
                "value_type": "STRING",
                "children": [
                    {
                        # Missing 'value', 'code', and 'value_type' here!
                        "name": "Invalid Deep Child"
                    }
                ]
            }
        ]
    }

    response = await async_client.post("/api/v2/catalogs", json=payload_with_bad_child, headers=headers)

    assert response.status_code == 422
    errors = response.json()["detail"]
    
    # Pydantic will point exactly to the location of the error in the array tree
    # e.g., body -> items -> 0 -> children -> 0 -> value
    error_locations = [str(err["loc"]) for err in errors]
    assert any("children" in loc for loc in error_locations)


@pytest.mark.asyncio
async def test_api_list_catalogs(async_client: AsyncClient, get_current_user):
    """
    Prueba que el endpoint /catalogs devuelva la lista resumida.
    """
    MOCK_USER, headers = get_current_user

    # 1. Sembrar un catálogo usando tu propio endpoint (Read-After-Write)
    payload = {
        "name": "Catálogo Resumen Test",
        "value": "CAT_RESUMEN",
        "catalog_type": "SPATIAL",
        "items": [] # No necesitamos items para probar el resumen
    }
    post_res = await async_client.post("/api/v2/catalogs", json=payload, headers=headers)
    assert post_res.status_code == 200

    # 2. Hacer el GET al listado
    response = await async_client.get("/api/v2/catalogs", headers=headers)
    
    # 3. Validar
    assert response.status_code == 200
    catalogs = response.json()
    
    # Asegurarnos de que sea una lista y contenga nuestro catálogo
    assert isinstance(catalogs, list)
    assert len(catalogs) > 0
    
    # Buscar el catálogo específico que acabamos de crear
    my_catalog = next((c for c in catalogs if c["value"] == "CAT_RESUMEN"), None)
    assert my_catalog is not None
    assert my_catalog["name"] == "Catálogo Resumen Test"
    
    # Confirmar que es el DTO ligero (no debe traer el arreglo enorme de 'items')
    assert "items" not in my_catalog


@pytest.mark.asyncio
async def test_api_get_catalog_details_success(async_client: AsyncClient, get_current_user):
    """
    Verifies that when requesting a specific ID,
    the backend reconstructs the entire tree (items, aliases, and children).
    """
    MOCK_USER, headers = get_current_user

    complex_payload = {
        "name": "Catálogo Complejo",
        "value": "CAT_COMPLEJO",
        "catalog_type": "INTEREST",
        "items": [
            {
                "name": "Padre",
                "value": "ITEM_PADRE",
                "code": 100,
                "value_type": "STRING",
                "aliases": [
                    { "value": "ALIAS_PADRE", "value_type": "STRING" }
                ],
                "children": [
                    {
                        "name": "Hijo",
                        "value": "ITEM_HIJO",
                        "code": 101,
                        "value_type": "STRING",
                        "aliases": [],
                        "children": []
                    }
                ]
            }
        ]
    }
    
    post_res = await async_client.post("/api/v2/catalogs", json=complex_payload, headers=headers)
    
    post_data = post_res.json()
    catalog_id = post_data if isinstance(post_data, str) else post_data.get("catalog_id")

    response = await async_client.get(f"/api/v2/catalogs/{catalog_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["catalog_id"] == catalog_id
    assert data["name"] == "Catálogo Complejo"
    
    items = data["items"]
    assert len(items) == 1
    root_item = items[0]
    assert root_item["value"] == "ITEM_PADRE"
    
    assert len(root_item["aliases"]) == 1
    assert root_item["aliases"][0]["value"] == "ALIAS_PADRE"
    
    assert len(root_item["children"]) == 1
    child_item = root_item["children"][0]
    assert child_item["value"] == "ITEM_HIJO"
    assert child_item["code"] == 101


@pytest.mark.asyncio
async def test_api_get_catalog_not_found(async_client: AsyncClient, get_current_user):
    """
    Verify that requesting a non-existent catalog ID returns a 404 with an appropriate error message.
    """
    MOCK_USER, headers = get_current_user

    response = await async_client.get("/api/v2/catalogs/cat_no_existo_123", headers=headers)
    
    assert response.status_code == 404
    assert "not found" in response.text.lower()