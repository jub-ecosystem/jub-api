import os
import time as T
from typing import List
from fastapi import Depends, APIRouter, status
import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.dto.v2 as DTO
from jubapi.log.log import Log
import jubapi.errors as EX

router = APIRouter(prefix="/tasks")


L = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)

@router.get("/stats", response_model=DTO.TasksStatsDTO)
async def get_tasks_stats(
    service: S.TasksService = Depends(MX.get_tasks_service),
    user: DTO.UserProfileDTO = Depends(MX.get_current_user)
):
    try:
        t0 = T.monotonic()
        stats_result = await service.get_stats(user_id=user.user_id)
        if stats_result.is_err:
            e = stats_result.unwrap_err()
            L.error({
                "action":"tasks.get_stats",
                "input":{"user_id": user.user_id},
                "error":str(e),
                "duration_ms": (T.monotonic() - t0) * 1000
            })
            raise e.to_http_exception()
        
        stats = stats_result.unwrap()
        L.info({
            "action":"tasks.get_stats",
            "input":{"user_id": user.user_id},
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        return stats
    except Exception as e:
        L.error({
            "action":"tasks.get_stats",
            "input":{"user_id": user.user_id},
            "error":str(e),
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        raise EX.UnknownError(detail="Unexpected error while fetching tasks stats").to_http_exception()

@router.get("", response_model=List[DTO.TaskXDTO])
async def get_my_tasks(
    limit: int = 50,
    skip: int = 0,
    current_user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    task_srv: S.TasksService = Depends(MX.get_tasks_service) 
):
    """
    Fetches the recent tasks for the authenticated user to populate the UI list.
    """
    t0 = T.monotonic()
    result = await task_srv.get_user_tasks(current_user.user_id, skip, limit)
    
    if result.is_err:
        L.error({
            "action":"tasks.get_my_tasks",
            "input":{"user_id": current_user.user_id, "skip": skip, "limit": limit},
            "error":str(result.unwrap_err()),
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        raise result.unwrap_err().to_http_exception()
    
    L.info({
        "action":"tasks.get_my_tasks",
        "input":{"user_id": current_user.user_id, "skip": skip, "limit": limit},
        "duration_ms": (T.monotonic() - t0) * 1000
    })
    return result.unwrap()


@router.get("/{task_id}", response_model=DTO.TaskXDTO)
async def get_task_details(
    task_id:str,
    current_user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    task_srv: S.TasksService = Depends(MX.get_tasks_service)
):
    t0 = T.monotonic()
    result = await task_srv.get_task_details(task_id,current_user.user_id)
    
    if result.is_err:
        L.error({
            "action":"tasks.get_task_details",
            "input":{"user_id": current_user.user_id, "task_id": task_id},
            "error":str(result.unwrap_err()),
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        raise result.unwrap_err().to_http_exception()
    L.info({
        "action":"tasks.get_task_details",
        "input":{"user_id": current_user.user_id, "task_id": task_id},
        "duration_ms": (T.monotonic() - t0) * 1000
    })
    return result.unwrap()


@router.post("/{task_id}/complete", response_model=DTO.TaskCompleteResponseDTO)
async def complete_task(
    task_id:  str,
    payload:  DTO.TaskCompleteDTO,
    task_srv: S.TasksService          = Depends(MX.get_tasks_service),
    obs_svc:  S.ObservatoriesService  = Depends(MX.get_observatories_service),
):
    """
    Called by external systems (indexers, provisioners) when their work is done.

    - `success: true`  → marks task SUCCESS and **enables** the associated observatory.
    - `success: false` → marks task FAILED; observatory stays disabled.

    No user authentication required — this is a machine-to-machine endpoint.
    """
    t0 = T.monotonic()
    task_result = await task_srv.complete_task(task_id, payload.success, payload.message)
    if task_result.is_err:
        L.error({
            "action":"tasks.complete_task",
            "input":{"task_id": task_id, "success": payload.success, "message": payload.message},
            "error":str(task_result.unwrap_err()),
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        raise task_result.unwrap_err().to_http_exception()

    task             = task_result.unwrap()
    obs_enabled      = False

    if payload.success:
        enable_result = await obs_svc.enable_observatory(task.observatory_id)
        obs_enabled   = enable_result.is_ok
        if not obs_enabled:
            L.error({
                "action":"tasks.complete_task.enable_observatory",
                "input":{"observatory_id": task.observatory_id},
                "error":str(enable_result.unwrap_err()),
                "duration_ms": (T.monotonic() - t0) * 1000
            })
        else:
            L.info({
                "action":"tasks.complete_task.enable_observatory",
                "input":{"observatory_id": task.observatory_id},
                "duration_ms": (T.monotonic() - t0) * 1000
            })
    

    return DTO.TaskCompleteResponseDTO(
        task_id             = task_id,
        status              = task.current_status,
        observatory_id      = task.observatory_id,
        observatory_enabled = obs_enabled,
    )


@router.put("/{task_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def retry_failed_task(
    task_id: str,
    current_user:DTO.UserProfileDTO = Depends(MX.get_current_user),
    task_srv: S.TasksService = Depends(MX.get_tasks_service)
):
    """
    Triggers a retry for a failed task. 
    Appends a new attempt to the history and resets the progress state.
    """
    t0 = T.monotonic()
    result = await task_srv.retry_task(task_id,current_user.user_id)
    
    if result.is_err:
        # If the task doesn't exist or is already running
        L.error({
            "action":"tasks.retry_failed_task",
            "input":{"user_id": current_user.user_id, "task_id": task_id},
            "error":str(result.unwrap_err()),
            "duration_ms": (T.monotonic() - t0) * 1000
        })
        raise result.unwrap_err().to_http_exception()
    L.info({
        "action":"tasks.retry_failed_task",
        "input":{"user_id": current_user.user_id, "task_id": task_id},
        "duration_ms": (T.monotonic() - t0) * 1000
    })
    # return {"status": "success", "message": "Task queued for retry."}