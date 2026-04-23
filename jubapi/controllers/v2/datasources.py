import os
from typing import List
from fastapi import Depends, status
from fastapi.routing import APIRouter

import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.dto.v2 as DTO
import jubapi.models.v2 as M
from jubapi.log.log import Log

log = Log(name=__name__, path=os.environ.get("JUB_LOG_PATH", "/log"))

router = APIRouter(prefix="/datasources", tags=["datasources_v2"])


@router.post("", response_model=DTO.DataSourceDTO, status_code=status.HTTP_201_CREATED)
async def register_data_source(
    payload: DTO.DataSourceCreateDTO,
    svc: S.DataIngestionService = Depends(MX.get_data_ingestion_service),
):
    result = await svc.register_data_source(
        name        = payload.name,
        description = payload.description or "",
        bucket_id   = payload.bucket_id or "",
    )
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return DTO.DataSourceDTO.from_model(result.unwrap())


@router.get("", response_model=List[DTO.DataSourceDTO])
async def list_data_sources(
    svc: S.DataIngestionService = Depends(MX.get_data_ingestion_service),
):
    result = await svc.source_repo.find({}, limit=200)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return [DTO.DataSourceDTO.from_model(s) for s in result.unwrap()]


@router.get("/{source_id}", response_model=DTO.DataSourceDTO)
async def get_data_source(
    source_id: str,
    svc: S.DataIngestionService = Depends(MX.get_data_ingestion_service),
):
    result = await svc.source_repo.get_by_id(source_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return DTO.DataSourceDTO.from_model(result.unwrap())


@router.delete("/{source_id}", response_model=DTO.DataSourceDeleteResponseDTO)
async def delete_data_source(
    source_id: str,
    svc: S.DataIngestionService = Depends(MX.get_data_ingestion_service),
):
    # Count records before deletion so we can report them
    count_result = await svc.record_repo.count({"source_id": source_id})
    records_removed = count_result.unwrap() if count_result.is_ok else 0

    result = await svc.delete_data_source(source_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return DTO.DataSourceDeleteResponseDTO(deleted=result.unwrap(), records_removed=records_removed)


@router.post("/{source_id}/records", status_code=status.HTTP_201_CREATED)
async def ingest_records(
    source_id: str,
    records: List[DTO.DataRecordCreateDTO],
    svc: S.DataIngestionService = Depends(MX.get_data_ingestion_service),
):
    models = [
        M.DataRecord(
            record_id              = r.record_id,
            source_id              = source_id,
            spatial_id             = r.spatial_id,
            temporal_id            = r.temporal_id,
            interest_ids           = r.interest_ids,
            numerical_interest_ids = r.numerical_interest_ids,
            raw_payload            = r.raw_payload,
        )
        for r in records
    ]
    result = await svc.ingest_parsed_records(source_id, models)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return {"inserted": result.unwrap()}


@router.post("/{source_id}/query")
async def query_records(
    source_id: str,
    payload: DTO.DataSourceQueryDTO,
    svc: S.DataQueryService = Depends(MX.get_data_query_service),
):
    result = await svc.query(source_id, payload.query)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    records = result.unwrap()
    # Paginate in-memory after the DB query (filter already applied)
    skip  = payload.skip or 0
    limit = payload.limit or 100
    
    return records[skip: skip + limit]
