from fastapi import Depends
from fastapi.routing import APIRouter
import jubapi.middlewares as M
import jubapi.services.v2 as S
import jubapi.dto.v2 as DTO

import os
from jubapi.log.log import Log

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
async def search(query:DTO.SearchQueryDTO, search:S.SearchService = Depends(M.get_search_service)):
    result = await search.search(query=query.query, observatory_id=query.observatory_id, limit=query.limit, skip=query.skip)

    if result.is_err:
        log.error({
            "error": str(result.unwrap_err()),
            "query": query
        })    
        e = result.unwrap_err()    
        raise e.to_http_exception()
    
    response = result.unwrap()

    return response


@router.post("/observatories")
async def search_observatories(query:DTO.SearchQueryDTO, search:S.SearchService = Depends(M.get_search_service)):
    result = await search.search_observatories(query=query.query)
    if result.is_err:
        log.error({
            "error": str(result.unwrap_err()),
            "query": str(query)
        })    
        e = result.unwrap_err()    
        raise e.to_http_exception()
    
    response = result.unwrap()

    return response