from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest
from dotenv import load_dotenv
import os
from jubapi.server import app
from uuid import uuid4
import commonx.dto.xolo as XoloDTO
import jubapi.dto.v2 as DTO
from jubapi.db.constants import CollectionNames
from typing import Tuple, Dict
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

# import commonx.dto.e as DTO

JUB_ENV_FILE_PATH = os.environ.get("JUB_ENV_FILE_PATH", ".env.test")
os.environ.setdefault("JUB_ENV_FILE_PATH", JUB_ENV_FILE_PATH)
env_exists        = os.path.exists(JUB_ENV_FILE_PATH)

print(f"Loading environment variables from: {JUB_ENV_FILE_PATH} - Exists: {env_exists}")
if env_exists:
    load_dotenv(JUB_ENV_FILE_PATH, override=True)


@pytest.fixture
async def async_client():
    """Creates the async test client connected to the FastAPI app."""
    transport = ASGITransport(app=app)
    # Notice the base_url points directly to the prefix defined in your router
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# @pytest.fixture()
async def connect_to_database():
    from jubapi.db import connect_to_mongo
    print("Connecting to the database...")
    await connect_to_mongo()
    # await asyncio.sleep(0.1)  # simulate async connection

@pytest.fixture( autouse=True)
async def before_all():
    from jubapi.db import close_mongo_connection
    await connect_to_database()
    print("Database connected before tests")
    yield 
    print("Disconnecting from database...")
    await close_mongo_connection()


@pytest.fixture(scope="function")
async def test_db():
    """
    Sets up a clean MongoDB test database before tests run,
    and drops it completely after all tests in this module finish.
    """
    client = MongoClient("mongodb://localhost:27027/")
    db = client.jub_test
    
    db.drop_collection(CollectionNames.DATA_SOURCES.value)
    db.drop_collection(CollectionNames.DATA_RECORDS.value)
    db.drop_collection(CollectionNames.USER_PROFILES.value)
    db.drop_collection(CollectionNames.OBSERVATORIES.value)
    db.drop_collection(CollectionNames.PRODUCTS.value)
    db.drop_collection(CollectionNames.CATALOGS.value)
    db.drop_collection(CollectionNames.CATALOG_ITEMS.value)
    db.drop_collection(CollectionNames.CATALOG_ITEM_VALUES.value)
    db.drop_collection(CollectionNames.CATALOG_ITEM_ALIASES.value)
    db.drop_collection(CollectionNames.OBSERVATORY_PRODUCT_LINKS.value)
    db.drop_collection(CollectionNames.PRODUCT_CATALOGS_ITEM_LINKS.value)
    db.drop_collection(CollectionNames.CATALOG_ITEM_RELATIONSHIPS.value)
    db.drop_collection(CollectionNames.CATALOG_CATALOG_ITEM_LINKS.value)
    db.drop_collection(CollectionNames.CATALOG_ITEM_CATALOG_ALIAS_LINKS.value)
    db.drop_collection(CollectionNames.OBSERVATORY_CATALOG_LINKS.value)
    # db
    # Yield the db to the tests
    yield db
    
    # Teardown: Clean up after tests are done
    client.drop_database('jub_test')



@pytest.fixture()
async def get_current_user(async_client)->Tuple[DTO.UserProfileDTO,Dict[str,str]]:
    # with TestClient(app) as client:
        
        uid = uuid4().hex[:6]
        username = f"testuser{uid}"
        scope = "jub"
        data = XoloDTO.SignUpDTO(
            username      = username,
            password      = "password123",
            email         = f"{username}@x.com",
            expiration    = "1h",
            first_name    = "John",
            last_name     = "Doe",
            scope         = scope,
            profile_photo = ""
        ).model_dump()

        response = await async_client.post("/api/v2/users/signup", json=data)
        assert response.status_code == 200
        payload_login = XoloDTO.AuthAttemptDTO(
            username   = username,
            password   = "password123",
            scope      = scope,
            expiration = "1h"
        )
        response_login = await async_client.post("/api/v2/users/auth", json=payload_login.model_dump())
        assert response_login.status_code == 200

        raw_auth_response = response_login.json()
        print("Raw auth response:", raw_auth_response)
        
        auth_response = DTO.AutenticationResponsetDTO.model_validate(raw_auth_response)
        token = auth_response.access_token
        headers ={"Authorization": f"Bearer {token}", "Temporal-Secret-Key": auth_response.temporal_secret_key or ""} 
        response = await async_client.get("/api/v2/users/me", headers=headers)

        # return XoloDTO.U
        return auth_response.user_profile,headers