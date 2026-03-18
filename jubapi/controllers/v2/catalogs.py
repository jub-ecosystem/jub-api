import os
from fastapi.routing import APIRouter
from fastapi import Depends,Query
import jubapi.services.v2 as S
import jubapi.middlewares as MX
from jubapi.log.log import Log

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)