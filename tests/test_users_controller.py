import pytest
from jubapi.server import app
from fastapi.testclient import TestClient
import commonx.dto.xolo as XoloDTO
import jubapi.dto.v2 as DTO
from uuid import uuid4
# import jubapi.middlewares as MX
# from jubapi.dto.v2 import 


@pytest.mark.asyncio
async def test_signup():
    with TestClient(app) as client:
        
        uid = uuid4().hex[:6]
        username = f"testuser{uid}"
        scope = "jub"
        data = XoloDTO.SignUpDTO(
            username      = username,
            password      = "password123",
            email         = f"{username}@x.com",
            expiration    = "1h",
            first_name    = "John",
            last_name     = "Doe",
            scope         = scope,
            profile_photo = ""
        ).model_dump()

        response = client.post("/api/v2/users/signup", json=data)
        assert response.status_code == 200
        payload_login = XoloDTO.AuthAttemptDTO(
            username   = username,
            password   = "password123",
            scope      = scope,
            expiration = "1h"
        )
        response_login = client.post("/api/v2/users/auth", json=payload_login.model_dump())
        assert response_login.status_code == 200

        raw_auth_response = response_login.json()
        print("Raw auth response:", raw_auth_response)
        
        auth_response = DTO.AutenticationResponsetDTO.model_validate(raw_auth_response)
        token = auth_response.access_token
        headers ={"Authorization": f"Bearer {token}", "Temporal-Secret-Key": auth_response.temporal_secret_key or ""} 
        response = client.get("/api/v2/users/me", headers=headers)
        assert response.status_code == 200

        new_user_preference = DTO.UserPreferencesDTO(
            appearance= DTO.AppearanceSettingsDTO(
                theme="dark",
                font_size=24
            ),
            exploration= DTO.ExplorationSettingsDTO(
                default_view="list",
                items_per_page=48,
                enable_tutorial=False
            ),
            export= DTO.ExportSettingsDTO(
                default_format="json",
                include_metadata=True
            )

        )
        url = f"/api/v2/users/{auth_response.user_profile.user_id}/settings"
        print("Update URL:", url)

        response = client.put(
            url     = url,
            headers = headers,
            json    = new_user_preference.model_dump()
        )
        update_response = response.json()
        print("Update response:", update_response)
        assert response.status_code == 200

        # # assert response.json() == {"message": "User created successfully"}