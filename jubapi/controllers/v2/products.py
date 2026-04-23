import os
from typing import List
from fastapi import Depends, Query, status, UploadFile, File, Form, BackgroundTasks
from fastapi.routing import APIRouter
from nanoid import generate as nanoid

import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.dto.v2 as DTO
import jubapi.enums.v2 as ENUMS
from jubapi.storage import StorageBackend
from jubapi.log.log import Log

router = APIRouter(prefix="/products", tags=["products_v2"])

log = Log(name=__name__, path=os.environ.get("JUB_LOG_PATH", "/log"))


# ==========================================
# CRUD
# ==========================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DTO.ProductSimpleDTO,
    summary="Create a single product",
    description=(
        "Creates one product and links it to an observatory with optional catalog-item tags. "
        "Use **POST /observatories/{id}/products/bulk** to create multiple products at once."
    ),
)
async def create_product(
    payload: DTO.ProductCreateDTO,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    product_id = payload.product_id or nanoid(size=12)
    model = M.ProductX(
        product_id  = product_id,
        name        = payload.name,
        description = payload.description or "",
    )
    result = await svc.insert_product(
        product          = model,
        observatory_id   = payload.observatory_id,
        catalog_item_ids = payload.catalog_item_ids or [],
    )
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    # Re-fetch for full timestamps
    fetched = await svc.get_product_by_id(result.unwrap())
    if fetched.is_err:
        raise fetched.unwrap_err().to_http_exception()
    return DTO.ProductSimpleDTO.from_model(fetched.unwrap())


@router.get("", response_model=List[DTO.ProductSimpleDTO])
async def list_products(
    limit: int = Query(100, ge=1, le=500),
    svc: S.ProductService = Depends(MX.get_product_service),
):
    result = await svc.list_products(limit=limit)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return result.unwrap()


@router.get("/{product_id}", response_model=DTO.ProductSimpleDTO)
async def get_product(
    product_id: str,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    result = await svc.get_product_by_id(product_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return DTO.ProductSimpleDTO.from_model(result.unwrap())


@router.put("/{product_id}", response_model=DTO.ProductSimpleDTO)
async def update_product(
    product_id: str,
    payload: DTO.ProductUpdateDTO,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        result = await svc.get_product_by_id(product_id)
        if result.is_err:
            raise result.unwrap_err().to_http_exception()
        return DTO.ProductSimpleDTO.from_model(result.unwrap())

    result = await svc.update_product(product_id, update_data)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return result.unwrap()


@router.delete("/{product_id}", response_model=DTO.ProductDeleteResponseDTO)
async def delete_product(
    product_id: str,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    result = await svc.delete_product(product_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return DTO.ProductDeleteResponseDTO(deleted=result.unwrap())


# ==========================================
# Catalog-item tag management
# ==========================================

@router.get("/{product_id}/tags")
async def get_tags(
    product_id: str,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    # Ensure product exists
    check = await svc.get_product_by_id(product_id)
    if check.is_err:
        raise check.unwrap_err().to_http_exception()

    result = await svc.get_product_tags(product_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return {"product_id": product_id, "catalog_item_ids": result.unwrap()}


@router.post("/{product_id}/tags", status_code=status.HTTP_201_CREATED)
async def add_tags(
    product_id: str,
    payload: DTO.TagProductDTO,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    result = await svc.tag_product(product_id, payload.catalog_item_ids)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
    return {"product_id": product_id, "added": result.unwrap()}


@router.delete("/{product_id}/tags/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag(
    product_id: str,
    catalog_item_id: str,
    svc: S.ProductService = Depends(MX.get_product_service),
):
    check = await svc.get_product_by_id(product_id)
    if check.is_err:
        raise check.unwrap_err().to_http_exception()

    result = await svc.untag_product(product_id, catalog_item_id)
    if result.is_err:
        raise result.unwrap_err().to_http_exception()


# ==========================================
# FILE UPLOAD  (queued background ingestion)
# ==========================================

async def _process_upload(
    product_id: str,
    job_id:     str,
    filename:   str,
    data:       bytes,
    storage:    StorageBackend,
    task_svc:   S.TasksService,
) -> None:
    """
    Background worker: persist the file via StorageBackend, then mark the job task
    as SUCCESS or FAILED.  This runs after the HTTP response has already been sent.
    """
    try:
        key = f"products/{product_id}/{job_id}/{filename}"
        await storage.put(key, data)
        await task_svc.complete_task(job_id, success=True)
    except Exception as exc:
        log.error(f"Upload processing failed for product {product_id}: {exc}")
        await task_svc.complete_task(job_id, success=False, error_msg=str(exc))


@router.post("/{product_id}/upload", status_code=status.HTTP_202_ACCEPTED,
             response_model=DTO.ProductUploadResponseDTO)
async def upload_product_file(
    product_id:      str,
    background_tasks: BackgroundTasks,
    user_id:         str               = Form(..., description="User queuing this upload."),
    file:            UploadFile         = File(..., description="Data file to ingest for this product."),
    prod_svc:        S.ProductService   = Depends(MX.get_product_service),
    task_svc:        S.TasksService     = Depends(MX.get_tasks_service),
    storage:         StorageBackend     = Depends(MX.get_storage_backend),
):
    """
    Accepts a file for a product and queues it for background ingestion.

    Returns immediately with a `job_id` (a task ID).  The background worker
    persists the file via the configured `StorageBackend`, then marks the job
    SUCCESS or FAILED.  Poll `GET /tasks/{job_id}` to track progress.

    The external indexing system should call `POST /tasks/{job_id}/complete`
    once it has finished indexing the stored file.
    """
    check = await prod_svc.get_product_by_id(product_id)
    if check.is_err:
        raise check.unwrap_err().to_http_exception()
    product = check.unwrap()

    # Determine the observatory this product belongs to (needed for the task)
    obs_link = await prod_svc.get_product_observatory(product_id)
    observatory_id = obs_link.unwrap() if obs_link.is_ok else "unknown"

    # Create a PENDING task so the job is trackable
    task_result = await task_svc.create_task(DTO.CreateTaskDTO(
        user_id        = user_id,
        observatory_id = observatory_id,
        title          = f"Index: {product.name} — {file.filename}",
        description    = f"File ingestion queued for product {product_id}.",
        operation      = ENUMS.TaskOperationEnum.INDEX,
    ))
    if task_result.is_err:
        raise task_result.unwrap_err().to_http_exception()

    job_id = task_result.unwrap()

    # Read bytes now (UploadFile is not safe to pass across async boundaries)
    data = await file.read()

    # Queue the actual processing — response is returned immediately
    background_tasks.add_task(
        _process_upload, product_id, job_id, file.filename, data, storage, task_svc
    )

    return DTO.ProductUploadResponseDTO(job_id=job_id, product_id=product_id)
