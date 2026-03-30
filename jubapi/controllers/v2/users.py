from fastapi import Depends
import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.dto.v2 as DTO
import commonx.dto.xolo as XoloDTO
from fastapi import APIRouter
import os
from jubapi.log.log import Log
import jubapi.errors as EX

router = APIRouter(prefix="/users")


L = Log(
    name = __name__,
    path = os.environ.get("JUB_LOG_PATH", "/log")
)


@router.post("/signup")
async def signup(
    dto: XoloDTO.SignUpDTO,
    service: S.UsersProfileXService = Depends(MX.get_user_profile_service)
):
    try:
        result = await service.signup(dto)
        if result.is_err:
            e = result.unwrap_err()
            L.error({
                "msg": f"Error during signup: {e.detail}",
            })
            raise EX.JubError(msg="Signup failed", code=e.code).to_http_exception()
        
        return result.unwrap()
    except Exception as e:
        L.error(f"Unexpected error during signup: {str(e)}")
        raise EX.UnknownError(detail="Unexpected error during signup").to_http_exception()

@router.post("/auth")
async def login(dto: XoloDTO.AuthAttemptDTO, service: S.UsersProfileXService = Depends(MX.get_user_profile_service)):
    try:
        result = await service.login(dto)
        if result.is_err:
            e = result.unwrap_err()
            L.error({
                "msg": f"Error during login: {e.detail}",
                # "raw_error": e.detail.raw_error
            })
            raise e
            # raise EX.(detail="Login failed", code=e.code).to_http_exception()
        
        return result.unwrap()
    except Exception as e:
        L.error(f"Unexpected error during login: {str(e)}")
        raise EX.UnknownError(detail="Unexpected error during login").to_http_exception()

@router.get("/me")
async def get_current_user(user: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    return user


@router.put("/{user_id}/settings")
async def update_user_settings(
    user_id: str,
    dto: DTO.UserPreferencesDTO,
    user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    service: S.UsersProfileXService = Depends(MX.get_user_profile_service),
):
    try:
        if user_id != user.user_id:
            L.warning(f"User {user.user_id} attempted to update settings for user {user_id}")
            raise EX.ForbiddenError(detail="You can only update your own settings").to_http_exception()
        
        result = await service.update_user_preferences(user_id, dto)
        if result.is_err:
            e = result.unwrap_err()
            L.error({
                "msg": f"Error updating user preferences for user {user_id}: {e.detail}",
            })
            raise e
            # raise EX.JubError(detail="Failed to update user preferences").to_http_exception()
        
        return result.unwrap()
    except Exception as e:
        L.error(f"Unexpected error updating user preferences for user {user_id}: {str(e)}")
        raise EX.UnknownError(detail="Unexpected error updating user preferences").to_http_exception()