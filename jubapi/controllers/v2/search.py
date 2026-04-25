from fastapi import Depends, Query
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


@router.post(
    "",
    summary="Search products by DSL",
    description=(
        "Runs a JUB DSL query against the product catalog and returns hydrated ProductXDTOs. "
        "Each DTO includes resolved spatial, temporal, and interest variable metadata. "
        "Example: `jub.v1.VS(MX).VT(>= 2020).VI(SEX_FEMALE AND C_MAMA)`"
    ),
)
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


@router.post(
    "/records",
    summary="Fetch raw data records by DSL",
    description=(
        "Translates the DSL into a MongoDB `$match` filter and returns the matching raw DataRecord documents. "
        "Values in VS() and VI() are resolved via catalog lookup (catalog_item_id, value, code, or alias). "
        "Use `source_id` in the query body to scope results to a single data source."
    ),
)
async def search_records(query: DTO.SearchQueryDTO, search: S.SearchService = Depends(M.get_search_service)):
    result = await search.search_data_records(
        query_str      = query.query,
        observatory_id = query.observatory_id,
        limit          = query.limit,
        skip           = query.skip
    )

    if result.is_err:
        log.error({
            "error": str(result.unwrap_err()),
            "query": query.model_dump()
        })    
        raise result.unwrap_err().to_http_exception()
    
    x = result.unwrap()
    log.info({
        "message": "Search records successful",
        "query": query.model_dump(),
        "result_count": len(x)
    })
    return x


@router.post(
    "/plot",
    summary="Generate ECharts plot data",
    description=(
        "Runs a full DSL aggregation and returns an ECharts-ready JSON object.\n\n"
        "Pipeline: `$match` (VS/VT/VI resolved to catalog_item_ids) → `$group` (BY catalog membership) → `$sort`.\n\n"
        "Axis labels replace raw catalog_item_ids with the catalog item `name` field.\n\n"
        "DSL example: `jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO).VO(AVG(TASA_100K)).BY(CIE10_CANCER)`\n\n"
        "VO operators: `COUNT`, `AVG(field)`, `SUM(field)` — `field` must be a key in `numerical_interest_ids`."
    ),
)
async def generate_plot(query: DTO.PlotQueryDTO, search: S.SearchService = Depends(M.get_search_service)):
    log.debug({
        "message": "Received plot generation request",
        "query": query.model_dump()    
    })
    result = await search.generate_plot(
        query_str      = query.query,
        source_id      = query.source_id,
        chart_type     = query.chart_type
    )

    if result.is_err:
        log.error({
            "error": str(result.unwrap_err()),
            "query": query.model_dump()
        })    
        raise result.unwrap_err().to_http_exception()
    
    return result.unwrap()

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


@router.post("/services", summary="Search services by DSL", description=(
    "Queries services using the SVC DSL. Examples:\n\n"
    "- `jub.v1.SVC(*)` — all services\n"
    "- `jub.v1.SVC(name=cancer)` — name contains 'cancer' (case-insensitive)\n"
    "- `jub.v1.SVC(public=true)` — public only\n"
    "- `jub.v1.SVC(owner=usr_abc)` — by owner\n"
    "- `jub.v1.SVC(name=cancer,public=true)` — combine filters with comma"
))
async def search_services(
    query: DTO.ServiceQueryDTO,
    svc:   S.ServiceXService = Depends(M.get_service_x_service),
):
    result = await svc.query_services_hydrated(query.query, skip=query.skip, limit=query.limit)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return result.unwrap()