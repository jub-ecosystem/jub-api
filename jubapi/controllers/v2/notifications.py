from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
# from jubapi.controllers.v2.users import get_current_user
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.services.v2 as S
import jubapi.dto.v2 as DTO
router = APIRouter(prefix="/notifications", tags=["Notifications"])

# --- DEPENDENCIES ---
# Assume these functions are defined in your dependency injection file
# def get_notification_service(...) -> NotificationService:
# def get_current_user(...) -> UserProfileX:

@router.get("", response_model=List[M.Notification])
async def fetch_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user = Depends(MX.get_current_user),
    notif_srv: S.NotificationService = Depends(MX.get_notification_service)
):
    """
    Fetches the current user's notifications. 
    Pass ?unread_only=true to only get unread messages for the bell badge.
    """
    result = await notif_srv.get_user_notifications(current_user.user_id, unread_only, limit)
    if result.is_err:
        raise HTTPException(status_code=500, detail=str(result.unwrap_err()))
    return result.unwrap()

@router.put("/{notification_id}/read",status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: str,
    current_user = Depends(MX.get_current_user), # Ensures only logged-in users can do this
    notif_srv: S.NotificationService = Depends(MX.get_notification_service),
    
):
    """Marks a specific notification as read when the user clicks on it."""
    result = await notif_srv.mark_as_read(notification_id,current_user.user_id)
    if result.is_err:
        raise HTTPException(status_code=404, detail="Notification not found or could not be updated")
    return None
    # return {"status": "success", "message": "Marked as read"}

@router.put("/read-all")
async def mark_all_notifications_read(
    current_user = Depends(MX.get_current_user),
    notif_srv: S.NotificationService = Depends(MX.get_notification_service)
)->DTO.NotificationReadAllResponseDTO:
    """Marks all unread notifications as read (e.g., a 'Mark all as read' button)."""
    result = await notif_srv.mark_all_as_read(current_user.user_id)
    if result.is_err:
        raise HTTPException(status_code=500, detail="Failed to update notifications")
    
    modified_count = result.unwrap()
    return DTO.NotificationReadAllResponseDTO(modified=modified_count)

@router.delete("/clear-read")
async def clear_read_notifications(
    current_user = Depends(MX.get_current_user),
    notif_srv: S.NotificationService = Depends(MX.get_notification_service)
)->DTO.NotificationClearReadResponseDTO:
    """Deletes all previously read notifications to clean up the user's inbox."""
    result = await notif_srv.clear_read_notifications(current_user.user_id)
    if result.is_err:
        raise HTTPException(status_code=500, detail="Failed to delete notifications")
    
    deleted_count = result.unwrap()
    return DTO.NotificationClearReadResponseDTO(deleted=deleted_count)