from fastapi import Depends
import jubapi.services.v2 as S
import jubapi.middlewares as MX
import jubapi.models.v2 as M
import jubapi.dto.v2 as DTO
import time as T    
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
        t0 = T.monotonic()
        result = await service.signup(dto)
        if result.is_err:
            e = result.unwrap_err()
            L.error({
                "action":"controller.users.signup",
                "error": e.detail,
                "input": dto.model_dump(),
            })
            raise e.to_http_exception()
        L.info({
            "action":"controller.users.signup",
            "duration_ms": (T.monotonic() - t0) * 1000,
            "msg": f"User {dto.username} signed up successfully",
            "input": dto.model_dump(),
        })
        return result.unwrap()
    except Exception as e:
        L.error({"action": "controller.users.signup", "error": str(e), "input": dto.model_dump()})
        raise EX.UnknownError(detail="Unexpected error during signup").to_http_exception()

@router.post("/auth")
async def login(dto: XoloDTO.AuthAttemptDTO, service: S.UsersProfileXService = Depends(MX.get_user_profile_service)):
    try:
        t0 = T.monotonic()
        result = await service.login(dto)
        if result.is_err:
            e = result.unwrap_err()
            L.error({
                "action":"controller.users.login",
                "error": e.detail,
                "input": dto.model_dump(),
            })
            raise e.to_http_exception()
            # raise EX.(detail="Login failed", code=e.code).to_http_exception()
        L.info({
            "action":"controller.users.login",
            "duration_ms":(T.monotonic() - t0) * 1000,
            "msg": f"User {dto.username} logged in successfully",
            "input": dto.model_dump(),
        })
        return result.unwrap()
    except Exception as e:
        L.error({"action": "controller.users.login", "error": str(e), "input": dto.model_dump()})
        raise EX.UnknownError(detail="Unexpected error during login").to_http_exception()

@router.get("/me")
async def get_current_user(user: DTO.UserProfileDTO = Depends(MX.get_current_user)):
    t0 = T.monotonic()
    L.info({"action": "controller.users.get_current_user", "duration_ms": (T.monotonic() - t0) * 1000, "msg": f"Successfully retrieved current user profile for user {user.user_id}", "input": {"user_id": user.user_id}})
    return user


@router.get("/{user_id}/settings")
async def get_user_settings(
    user_id: str,
    user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    service: S.UsersProfileXService = Depends(MX.get_user_profile_service)
):
    t0 = T.monotonic()
    if user_id != user.user_id:
        L.warning({"action": "controller.users.get_user_settings", "msg": f"User {user.user_id} attempted to access settings for user {user_id}", "input": {"user_id": user.user_id, "target_user_id": user_id}})
        raise EX.ForbiddenError(detail="You can only access your own settings").to_http_exception()

    result = await service.get_user_preferences(user_id)
    if result.is_err:
        e = result.unwrap_err()
        L.error({"action": "controller.users.get_user_settings", "error": e.detail, "input": {"user_id": user_id}})
        raise e.to_http_exception()
    L.info({"action": "controller.users.get_user_settings", "duration_ms": (T.monotonic() - t0) * 1000, "msg": f"Successfully retrieved user preferences for user {user_id}", "input": {"user_id": user_id}})
    return result.unwrap()


@router.put("/{user_id}/settings")
async def update_user_settings(
    user_id: str,
    dto: DTO.UserPreferencesDTO,
    user: DTO.UserProfileDTO = Depends(MX.get_current_user),
    service: S.UsersProfileXService = Depends(MX.get_user_profile_service),
):
    t0 = T.monotonic()
    if user_id != user.user_id:
        L.warning({"action": "controller.users.update_user_settings", "msg": f"User {user.user_id} attempted to update settings for user {user_id}", "input": {"user_id": user.user_id, "target_user_id": user_id}})
        raise EX.ForbiddenError(detail="You can only update your own settings").to_http_exception()

    result = await service.update_user_preferences(user_id, dto)
    if result.is_err:
        e = result.unwrap_err()
        L.error({"action": "controller.users.update_user_settings", "error": e.detail, "input": {"user_id": user_id, "dto": dto.model_dump()}})
        raise e.to_http_exception()

    L.info({"action": "controller.users.update_user_settings", "duration_ms": (T.monotonic() - t0) * 1000, "msg": f"Successfully updated user preferences for user {user_id}", "input": {"user_id": user_id, "dto": dto.model_dump()}})
    return result.unwrap()