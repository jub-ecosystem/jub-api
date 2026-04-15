import os
from typing import List, Dict
from fastapi import Depends,APIRouter,status
import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.dto.v2 as DTO
import commonx.dto.xolo as XoloDTO
# from fastapi import APIRouter
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
        stats_result = await service.get_stats(user_id=user.user_id)
        if stats_result.is_err:
            e = stats_result.unwrap_err()
            L.error(f"Error fetching tasks stats for user {user.user_id}: {e.detail}")
            raise e.to_http_exception()
        
        stats = stats_result.unwrap()
        return stats
    except Exception as e:
        L.error(f"Unexpected error while fetching tasks stats: {str(e)}")
        raise EX.UnknownError(detail="Unexpected error while fetching tasks stats").to_http_exception()

@router.get("", response_model=List[DTO.TaskXDTO])
async def get_my_tasks(
    limit: int = 50,
    current_user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    task_srv: S.TasksService = Depends(MX.get_tasks_service) 
):
    """
    Fetches the recent tasks for the authenticated user to populate the UI list.
    """
    result = await task_srv.get_user_tasks(current_user.user_id, limit)
    
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
        
    return result.unwrap()


@router.get("/{task_id}", response_model=DTO.TaskXDTO)
async def get_task_details(
    task_id:str,
    current_user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    task_srv: S.TasksService = Depends(MX.get_tasks_service)
):
    result = await task_srv.get_task_details(task_id,current_user.user_id)
    
    if result.is_err:
        raise result.unwrap_err().to_http_exception()
        
    return result.unwrap()


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

    result = await task_srv.retry_task(task_id,current_user.user_id)
    
    if result.is_err:
        # If the task doesn't exist or is already running
        raise result.unwrap_err().to_http_exception()
        
    # return {"status": "success", "message": "Task queued for retry."}