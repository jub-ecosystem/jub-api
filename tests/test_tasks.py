import pytest
from httpx import AsyncClient, ASGITransport
from jubapi.server import app
import jubapi.middlewares as MX
import jubapi.dto.v2 as DTO
import jubapi.enums.v2 as ENUMS

# ==========================================
# 2. FIXTURES
# ==========================================


@pytest.fixture(autouse=True)
async def seed_test_tasks(get_current_user) -> None:
    """
    Seeds the database with test tasks before the tests run.
    Uses the TaskService to create initial states.
    """
    MOCK_USER, _ = get_current_user
    task_srv = MX.get_tasks_service(
        notification_service = MX.get_notification_service(),
        repository           = MX.get_tasks_repository()
    )
    # 1. Create a running task
    await task_srv.create_task(
        DTO.CreateTaskDTO(
            user_id        = MOCK_USER.user_id,
            observatory_id = "obs_test_1",
            title          = "Running Task",
            description    = "Testing running state",
            operation      = ENUMS.TaskOperationEnum.CREATE
        )
    )
    
    # 2. Create a failed task (so we can test the retry endpoint)
    res_failed = await task_srv.create_task(
        DTO.CreateTaskDTO(
            user_id        = MOCK_USER.user_id,
            observatory_id = "obs_test_2",
            title          = "Failed Task",
            description    = "Testing failed state",
            operation      = ENUMS.TaskOperationEnum.UPDATE
        )
    )
    if res_failed.is_ok:
        task_id = res_failed.unwrap()
        await task_srv.complete_task(task_id, success=False, error_msg="Simulated failure")


# ==========================================
# 3. TEST CASES
# ==========================================

@pytest.mark.asyncio
async def test_get_my_tasks(async_client: AsyncClient, get_current_user):
    """Tests fetching the task list for the authenticated user."""
    MOCK_USER, headers = get_current_user
    response = await async_client.get("api/v2/tasks", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) >= 2
    # Verify the tasks belong to the mock user
    assert all(task["user_id"] == MOCK_USER.user_id for task in data)

@pytest.mark.asyncio
async def test_get_my_tasks_with_limit(async_client: AsyncClient, get_current_user):
    """Tests the limit query parameter."""
    MOCK_USER, headers = get_current_user
    response = await async_client.get("api/v2/tasks?limit=1", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

@pytest.mark.asyncio
async def test_get_tasks_stats(async_client: AsyncClient, get_current_user):
    """Tests the /stats endpoint returning the TasksStatsDTO."""
    MOCK_USER, headers = get_current_user
    response = await async_client.get("api/v2/tasks/stats", headers=headers)
    
    assert response.status_code == 200
    data =DTO.TasksStatsDTO.model_validate(response.json())
    # print(data)
    # print(da)
    assert data.pending >0 and data.failed>0

@pytest.mark.asyncio
async def test_retry_failed_task(async_client: AsyncClient, get_current_user):
    """Tests retrying a failed task and verifying its status changes."""
    MOCK_USER, headers = get_current_user
    # 1. Fetch current tasks to find a failed one
    list_res = await async_client.get("api/v2/tasks", headers=headers)
    tasks = list_res.json()
    failed_tasks = [t for t in tasks if t["current_status"] == ENUMS.TaskStatusEnum.FAILED.value]
    
    assert len(failed_tasks) > 0, "No failed tasks found to test retry."
    target_task_id = failed_tasks[0]["task_id"]
    
    # 2. Trigger the retry endpoint
    retry_res = await async_client.put(f"api/v2/tasks/{target_task_id}/retry", headers=headers)
    assert retry_res.status_code == 204
    
    # 3. Verify the status was reset to PENDING
    verify_res = await async_client.get(f"api/v2/tasks/{target_task_id}", headers=headers)
    assert verify_res.status_code == 200
    task_details = DTO.TaskXDTO.model_validate(verify_res.json())
    assert task_details.current_status == ENUMS.TaskStatusEnum.PENDING.value
    # updated_task = verify_res.json()
    # assert updated_task["current_status"] == ENUMS.TaskStatusEnum.PENDING.value