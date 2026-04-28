import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from jubapi.log.log import Log
from jubapi.db import connect_to_mongo,close_mongo_connection
from jubapi.controllers.v1 import observatories_router,catalogs_router,products_router
import jubapi.controllers.v2 as ControllersV2
import jubapi.config as Cfg

log       = Log(
    name                   = Cfg.JUB_LOG_NAME,  
    path                   = Cfg.JUB_LOG_PATH,
    console_handler_filter = lambda x : Cfg.JUB_LOG_DEBUG,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan function for the FastAPI application. This function is used to connect to the MongoDB database when the application starts and to close the connection when the application stops.
    """
    await connect_to_mongo()
    yield 
    await close_mongo_connection()

app = FastAPI(
    lifespan  = lifespan,
    root_path = Cfg.JUB_ROOT_PATH,
    title     = Cfg.JUB_OPENAPI_TITLE,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins     = Cfg.JUB_CORS_ORIGINS,
    allow_credentials = Cfg.JUB_CORS_CREDENTIALS,
    allow_methods     = Cfg.JUB_CORS_METHODS,
    allow_headers     = Cfg.JUB_CORS_HEADERS
)
def generate_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title       = Cfg.JUB_OPENAPI_TITLE,
        version     = Cfg.JUB_OPENAPI_VERSION,
        summary     = Cfg.JUB_OPENAPI_VERSION,
        description = Cfg.JUB_OPENAPI_DESCRIPTION,
        routes      = app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url":  Cfg.JUB_OPENAPI_LOGO
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
app.openapi = generate_openapi

app.include_router(observatories_router,tags=["observatories"])
app.include_router(catalogs_router,tags=["catalogs"])
app.include_router(products_router,tags=["products"])
# V2
app.include_router(ControllersV2.observatories,prefix="/api/v2",tags=["observatories_v2"])
app.include_router(ControllersV2.catalogs,prefix="/api/v2",tags=["catalogs_v2"])
app.include_router(ControllersV2.search,prefix="/api/v2",tags=["search_v2"])
app.include_router(ControllersV2.jub,prefix="/api/v2",tags=["JubV2"])
app.include_router(ControllersV2.users,prefix="/api/v2",tags=["users_v2"])
app.include_router(ControllersV2.notifications,prefix="/api/v2",tags=["notifications_v2"])
app.include_router(ControllersV2.tasks,prefix="/api/v2",tags=["tasks_v2"])
app.include_router(ControllersV2.datasources,prefix="/api/v2",tags=["datasources_v2"])
app.include_router(ControllersV2.products,prefix="/api/v2",tags=["products_v2"])
app.include_router(ControllersV2.catalog_items,prefix="/api/v2",tags=["catalog_items_v2"])
app.include_router(ControllersV2.building_blocks,prefix="/api/v2",tags=["building_blocks"])
app.include_router(ControllersV2.patterns,prefix="/api/v2",tags=["patterns"])
app.include_router(ControllersV2.stages,prefix="/api/v2",tags=["stages"])
app.include_router(ControllersV2.workflows,prefix="/api/v2",tags=["workflows"])
app.include_router(ControllersV2.services,prefix="/api/v2",tags=["services"])