import os
from typing import List
from fastapi.routing import APIRouter
from fastapi import Depends
import jubapi.services.v2 as S
import jubapi.middlewares as MX
from jubapi.log.log import Log
import jubapi.dto.v2 as DTO

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

log = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)

@router.post("")
async def create_catalog(payload: DTO.CatalogCreateDTO, srv: S.CatalogService = Depends(MX.get_catalog_service)):
    result = await srv.create_catalog_bulk(payload)
    if result.is_err:
        e = result.unwrap_err()
        log.error(f"Failed to create catalog: {e.detail}")
        
        raise e.to_http_exception()
        # raise MX.HTTPException(status_code=result.err().status_code, detail=result.err().message)
    
    return DTO.CatalogCreatedResponseDTO(catalog_id=result.unwrap())
@router.post("/bulk")
async def create_catalog_bulk(payload: List[DTO.CatalogCreateDTO], srv: S.CatalogService = Depends(MX.get_catalog_service)):
    result = [await srv.create_catalog_bulk(p) for p in payload]
    if any(r.is_err for r in result):
        e = next(r.unwrap_err() for r in result if r.is_err)
        log.error(f"Failed to create catalog: {e.detail}")
        
        raise e.to_http_exception()
        # raise MX.HTTPException(status_code=result.err().status_code, detail=result.err().message)
    
    return DTO.CatalogCreatedBulkResponseDTO(catalog_ids=[r.unwrap() for r in result])


@router.get("", response_model=List[DTO.CatalogSummaryDTO])
async def list_catalogs(srv: S.CatalogService = Depends(MX.get_catalog_service)):
    """Returns a lightweight list of all available catalogs."""
    result = await srv.list_catalogs()
    if result.is_err:
        log.error(f"Failed to list catalogs: {result.unwrap_err().detail}")
        raise result.unwrap_err().to_http_exception()
    return result.unwrap()

@router.get("/{catalog_id}", response_model=DTO.CatalogResponseDTO)
async def get_catalog(catalog_id: str, srv: S.CatalogService = Depends(MX.get_catalog_service)):
    """Fetches a specific catalog with all its items, aliases, and hierarchy populated."""
    result = await srv.get_catalog_details(catalog_id)
    if result.is_err:
        log.error(f"Failed to get catalog {catalog_id}: {result.unwrap_err().detail}")
        raise result.unwrap_err().to_http_exception()
    return result.unwrap()