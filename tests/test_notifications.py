import pytest
from httpx import AsyncClient, ASGITransport
from jubapi.server import app 
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.enums.v2 as ENUMS
import jubapi.dto.v2 as DTO




@pytest.fixture(autouse=True)
async def seed_test_notifications(get_current_user):
    """
    Seeds the database with some test notifications before each test runs.
    Assuming you have access to your `services` dictionary fixture like in your previous tests.
    """
    MOCK_USER, _ = get_current_user
    notif_srv = MX.get_notification_service()
    
    # Create 1 unread notification
    await notif_srv.trigger_notification(
        DTO.CreateNotificationDTO(
            user_id     = MOCK_USER.user_id,
            status      = ENUMS.NotificationStatusEnum.INFO,
            operation   = ENUMS.NotificationOperationEnum.CREATE,
            entity_type = ENUMS.NotificationEntityEnum.PRODUCT,
            title       = "Unread Test",
            message     = "This is an unread message."
        )
    )
    
    # Create 1 read notification (trigger it, then mark it read)
    res = await notif_srv.trigger_notification(
        DTO.CreateNotificationDTO(
            user_id     = MOCK_USER.user_id,
            status      = ENUMS.NotificationStatusEnum.SUCCESS,
            operation   = ENUMS.NotificationOperationEnum.UPDATE,
            entity_type = ENUMS.NotificationEntityEnum.OBSERVATORY,
            title       = "Read Test",
            message     = "This is a read message."
        )
    )
    if res.is_ok:
        await notif_srv.mark_as_read(res.unwrap(), MOCK_USER.user_id)  # Mark it as read immediately


# ==========================================
# 3. TEST CASES
# ==========================================

@pytest.mark.asyncio
async def test_get_all_notifications(async_client: AsyncClient, get_current_user):
    """Test fetching all notifications for the current user."""

    MOCK_USER,headers = get_current_user
    response = await async_client.get("api/v2/notifications", headers=headers)  # Adjust prefix if needed
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) >= 2  # We seeded at least 2
    # Ensure they belong to our mock user
    assert all(notif["user_id"] == MOCK_USER.user_id for notif in data)

@pytest.mark.asyncio
async def test_get_unread_notifications_only(async_client: AsyncClient,get_current_user):
    """Test fetching ONLY unread notifications using the query parameter."""
    MOCK_USER,headers = get_current_user
    response = await async_client.get("api/v2/notifications?unread_only=true", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    # Check that absolutely every returned notification has is_read == False
    assert all(notif["is_read"] is False for notif in data)

@pytest.mark.asyncio
async def test_mark_single_notification_read(async_client: AsyncClient, get_current_user):
    """Test marking a specific notification as read."""
    MOCK_USER, headers = get_current_user
    # 1. Fetch unread notifications to get a valid ID
    get_res = await async_client.get("api/v2/notifications?unread_only=true", headers=headers)
    unread_data = get_res.json()
    assert len(unread_data) > 0
    
    target_id = unread_data[0]["notification_id"]
    
    # 2. Hit the PUT endpoint
    put_res = await async_client.put(f"api/v2/notifications/{target_id}/read", headers=headers)
    assert put_res.status_code == 204
    
    # 3. Verify it is no longer in the unread list
    verify_res = await async_client.get("api/v2/notifications?unread_only=true", headers=headers)
    verify_data = verify_res.json()
    print("Unread notifications after marking as read:", verify_data)  # Debug print
    # assert not any(n["notification_id"] == target_id for n in verify_data)

@pytest.mark.asyncio
async def test_mark_all_notifications_read(async_client: AsyncClient, get_current_user):
    """Test the 'Mark All As Read' bulk endpoint."""
    MOCK_USER, headers = get_current_user
    response = await async_client.put("api/v2/notifications/read-all", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["modified"] >= 1  # At least one should have been modified
    
    # Verify there are 0 unread notifications left
    verify_res = await async_client.get("api/v2/notifications?unread_only=true", headers=headers)
    assert len(verify_res.json()) == 0

@pytest.mark.asyncio
async def test_clear_read_notifications(async_client: AsyncClient, get_current_user):
    """Test the cleanup endpoint that deletes already-read notifications."""
    MOCK_USER, headers = get_current_user
    # First, make sure everything is read so we can delete it all
    await async_client.put("api/v2/notifications/read-all", headers=headers)
    
    # Hit the delete endpoint
    response = await async_client.delete("api/v2/notifications/clear-read", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] >= 2  # We seeded 2, both are now read, so both should be deleted
    
    # Verify the database is empty for this user
    verify_res = await async_client.get("api/v2/notifications", headers=headers)
    assert len(verify_res.json()) == 0