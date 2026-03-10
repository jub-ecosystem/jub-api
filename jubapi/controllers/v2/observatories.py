import os
from fastapi.routing import APIRouter
from fastapi import Depends,Query
import jubapi.services.v2 as S
import jubapi.middlewares as MX
from jubapi.log.log import Log

router = APIRouter(prefix="/observatories", tags=["observatories"])

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)

@router.get("/")
async def get_observatories(
    observatory_service:S.ObservatoriesService  = Depends(MX.get_observatories_service),
    page_index:int = Query(0, ge=0, description="Page index for pagination (0-based)"),
    limit:int = Query(10, ge=1, le=100, description="Number of items per page (1-100)")
):
    result = await observatory_service.get_observatories(limit=limit,page_index=page_index)
    if result.is_err:
        e = result.unwrap_err()
        log.error({
            "error": str(e),
            "page_index": page_index,
            "limit": limit
        })
        raise e.to_http_exception()
    return result.unwrap()
    # return {"message": "List of observatories"}
