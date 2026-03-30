import pytest 
from jubapi.models.v2 import UserProfileX, UserPreferences, AppearanceSettings, ExplorationSettings, ExportSettings, ThemeEnum, ViewModeEnum, ExportFormatEnum


def test_user_profile_creation():
    # Create a user profile with default settings
    user_profile = UserProfileX(
        user_id="user123",
        username="TestUser",
        email="x@x.com"
    )
    
    assert user_profile.user_id == "user123"
    assert user_profile.username == "TestUser"
    assert user_profile.email == "x@x.com"
    
    # Check default settings
    assert user_profile.settings.appearance.theme == ThemeEnum.SYSTEM
    assert user_profile.settings.appearance.reduce_animations == False
    assert user_profile.settings.exploration.items_per_page == 24
    assert user_profile.settings.exploration.default_view == ViewModeEnum.GRID
    assert user_profile.settings.export.default_format == ExportFormatEnum.JSON

def test_user_profile_custom_settings():
    # Create a user profile with custom settings
    custom_settings = UserPreferences(
        appearance=AppearanceSettings(theme=ThemeEnum.DARK, reduce_animations=True),
        exploration=ExplorationSettings(items_per_page=50, default_view=ViewModeEnum.LIST),
        export=ExportSettings(default_format=ExportFormatEnum.YML)
    )
    
    user_profile = UserProfileX(
        user_id="user456",
        username="CustomUser",
        email="x@x.com",
        settings=custom_settings
    )
    
    assert user_profile.user_id == "user456"
    assert user_profile.username == "CustomUser"
    assert user_profile.email == "x@x.com"
    
    # Check custom settings
    assert user_profile.settings.appearance.theme == ThemeEnum.DARK
    assert user_profile.settings.appearance.reduce_animations == True
    assert user_profile.settings.exploration.items_per_page == 50
    assert user_profile.settings.exploration.default_view == ViewModeEnum.LIST
    assert user_profile.settings.export.default_format == ExportFormatEnum.YML