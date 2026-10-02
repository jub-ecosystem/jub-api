import os
import time
from typing import List, Optional
from fastapi.routing import APIRouter
from fastapi import Depends, Query, status
import jubapi.enums.v2 as ENUMS
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
async def create_catalog(
    payload: DTO.CatalogCreateDTO, 
    srv: S.CatalogService = Depends(MX.get_catalog_service),
    _: DTO.UserProfileDTO = Depends(MX.get_current_user)   # Ensure user is authenticated for this action
):
    t0 = time.monotonic()
    result = await srv.create_catalog_bulk(payload)
    if result.is_err:
        e = result.unwrap_err()
        log.error({"action": "controller.catalog.create", "error": str(e.detail), "input": {"name": payload.name}})
        raise e.to_http_exception()
    log.info({"action": "controller.catalog.create", "duration_ms": int((time.monotonic()-t0)*1000), "result": {"catalog_id": result.unwrap()}})
    return DTO.CatalogCreatedResponseDTO(catalog_id=result.unwrap())


@router.post("/bulk")
async def create_catalog_bulk(
    payload: List[DTO.CatalogCreateDTO], 
    srv: S.CatalogService = Depends(MX.get_catalog_service),
    _: DTO.UserProfileDTO = Depends(MX.get_current_user)   # Ensure user is authenticated for this action
):
    t0 = time.monotonic()
    results = [await srv.create_catalog_bulk(p) for p in payload]
    if any(r.is_err for r in results):
        e = next(r.unwrap_err() for r in results if r.is_err)
        log.error({"action": "controller.catalog.create_bulk", "error": str(e.detail), "input": {"count": len(payload)}})
        raise e.to_http_exception()
    ids = [r.unwrap() for r in results]
    log.info({"action": "controller.catalog.create_bulk", "duration_ms": int((time.monotonic()-t0)*1000), "result": {"count": len(ids)}})
    return DTO.CatalogCreatedBulkResponseDTO(catalog_ids=ids)


@router.post("/bulk/{observatory_id}/link")
async def create_catalog_bulk_and_link(
    observatory_id: str,
    payload: List[DTO.CatalogCreateDTO],
    srv: S.CatalogService = Depends(MX.get_catalog_service),
    observatory_srv: S.ObservatoriesService = Depends(MX.get_observatories_service),
    _: DTO.UserProfileDTO = Depends(MX.get_current_user)   # Ensure user is authenticated for this action
):
    t0 = time.monotonic()
    results = [await srv.create_catalog_bulk(p) for p in payload]
    if any(r.is_err for r in results):
        e = next(r.unwrap_err() for r in results if r.is_err)
        log.error({"action": "controller.catalog.create_bulk_link", "error": str(e.detail), "input": {"observatory_id": observatory_id, "count": len(payload)}})
        raise e.to_http_exception()

    response = DTO.CatalogCreatedBulkResponseDTO(catalog_ids=[r.unwrap() for r in results])
    for catalog_id in response.catalog_ids:
        link_result = await observatory_srv.graph_link_manager.link_observatory_to_catalog(observatory_id, catalog_id)
        if link_result.is_err:
            e = link_result.unwrap_err()
            log.error({"action": "controller.catalog.create_bulk_link", "error": str(e.detail), "input": {"observatory_id": observatory_id, "catalog_id": catalog_id}})
            raise e.to_http_exception()
    log.info({"action": "controller.catalog.create_bulk_link", "duration_ms": int((time.monotonic()-t0)*1000), "result": {"observatory_id": observatory_id, "count": len(response.catalog_ids)}})
    return response


@router.get("", response_model=DTO.PageDTO[DTO.CatalogSummaryDTO])
async def list_catalogs(
    catalog_type: Optional[List[ENUMS.CatalogType]] = Query(None, description="Filter by catalog type. Repeat to match several: ?catalog_type=SPATIAL&catalog_type=TEMPORAL"),
    q: Optional[str] = Query(None, max_length=100, description="Case-insensitive search on catalog name or value"),
    skip: int = Query(0, ge=0, description="Number of catalogs to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of catalogs to return"),
    srv: S.CatalogService = Depends(MX.get_catalog_service),
    _: DTO.UserProfileDTO = Depends(MX.get_current_user)   # Ensure user is authenticated for this action
):
    """Returns a paginated, lightweight list of catalogs, optionally filtered by type and name/value."""
    t0 = time.monotonic()
    inputs = {"catalog_type": catalog_type, "q": q, "skip": skip, "limit": limit}
    result = await srv.list_catalogs(catalog_types=catalog_type, q=q, skip=skip, limit=limit)
    if result.is_err:
        log.error({"action": "controller.catalog.list", "error": str(result.unwrap_err().detail), "input": inputs})
        raise result.unwrap_err().to_http_exception()
    page = result.unwrap()
    log.info({"action": "controller.catalog.list", "duration_ms": int((time.monotonic()-t0)*1000), "input": inputs, "result": {"count": len(page.items), "total": page.total}})
    return page


@router.get("/{catalog_id}", response_model=DTO.CatalogResponseDTO)
async def get_catalog(catalog_id: str, srv: S.CatalogService = Depends(MX.get_catalog_service), _: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    """Fetches a specific catalog with all its items, aliases, and hierarchy populated."""
    t0 = time.monotonic()
    result = await srv.get_catalog_details(catalog_id)
    if result.is_err:
        log.error({"action": "controller.catalog.get", "error": str(result.unwrap_err().detail), "input": {"catalog_id": catalog_id}})
        raise result.unwrap_err().to_http_exception()
    log.info({"action": "controller.catalog.get", "duration_ms": int((time.monotonic()-t0)*1000), "input": {"catalog_id": catalog_id}})
    return result.unwrap()


@router.put("/{catalog_id}", response_model=DTO.CatalogSummaryDTO)
async def update_catalog(catalog_id: str, payload: DTO.CatalogUpdateDTO, srv: S.CatalogService = Depends(MX.get_catalog_service), _: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    t0 = time.monotonic()
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = await srv.update_catalog(catalog_id, data)
    if result.is_err:
        log.error({"action": "controller.catalog.update", "error": str(result.unwrap_err().detail), "input": {"catalog_id": catalog_id}})
        raise result.unwrap_err().to_http_exception()
    cat = result.unwrap()
    log.info({"action": "controller.catalog.update", "duration_ms": int((time.monotonic()-t0)*1000), "input": {"catalog_id": catalog_id}})
    return DTO.CatalogSummaryDTO(catalog_id=cat.catalog_id, name=cat.name, value=cat.value, catalog_type=cat.catalog_type)


@router.get("/{catalog_id}/items", response_model=List[DTO.CatalogItemXResponseDTO])
async def get_catalog_items(catalog_id: str, srv: S.CatalogService = Depends(MX.get_catalog_service), _: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    t0 = time.monotonic()
    result = await srv.get_catalog_items(catalog_id)
    if result.is_err:
        log.error({"action": "controller.catalog.get_items", "error": str(result.unwrap_err().detail), "input": {"catalog_id": catalog_id}})
        raise result.unwrap_err().to_http_exception()
    log.info({"action": "controller.catalog.get_items", "duration_ms": int((time.monotonic()-t0)*1000), "input": {"catalog_id": catalog_id}})
    return result.unwrap()

@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog(catalog_id: str, srv: S.CatalogService = Depends(MX.get_catalog_service), _: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    t0 = time.monotonic()
    result = await srv.delete_catalog(catalog_id)
    if result.is_err:
        log.error({"action": "controller.catalog.delete", "error": str(result.unwrap_err().detail), "input": {"catalog_id": catalog_id}})
        raise result.unwrap_err().to_http_exception()
    log.info({"action": "controller.catalog.delete", "duration_ms": int((time.monotonic()-t0)*1000), "input": {"catalog_id": catalog_id}})
