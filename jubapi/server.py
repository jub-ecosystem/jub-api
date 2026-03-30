import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from jubapi.log.log import Log
from jubapi.db import connect_to_mongo,close_mongo_connection
from jubapi.controllers.v1 import observatories_router,catalogs_router,products_router
from jubapi.controllers.v2 import observatories_router_v2,search_router_v2,catalogs_router_v2,jub_router_v2,users_router_v2
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
app.include_router(observatories_router_v2,prefix="/api/v2",tags=["observatories_v2"])
app.include_router(catalogs_router_v2,prefix="/api/v2",tags=["catalogs_v2"])
app.include_router(search_router_v2,prefix="/api/v2",tags=["search_v2"])
app.include_router(jub_router_v2,prefix="/api/v2",tags=["JubV2"])
app.include_router(users_router_v2,prefix="/api/v2",tags=["users_v2"])