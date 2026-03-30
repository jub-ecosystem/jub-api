from pydantic import BaseModel, Field,StringConstraints,AfterValidator
from typing import Optional, Dict, Annotated
from enum import Enum
import re

import datetime as DT



def to_upper_snake(v: str) -> str:
    v = re.sub(r'([a-z])([A-Z])', r'\1_\2', v)
    v = re.sub(r'[^A-Za-z0-9]+', '_', v)
    r = v.upper().strip('_')
    return r

UpperSnakeStr =Annotated[str, 
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(to_upper_snake)
]


class TimestampedModel(BaseModel):
   created_at: DT.datetime = Field(default_factory=lambda: DT.datetime.now(DT.timezone.utc))
   updated_at: DT.datetime = Field(default_factory=lambda: DT.datetime.now(DT.timezone.utc))


class Descriptable(TimestampedModel):
  description: Optional[str] = Field(default="")
  metadata: Optional[Dict[str, str]] = Field(default_factory=dict)


class ObservatoryX(Descriptable):
  observatory_id: str
  title: str
  image_url: Optional[str] = None
  @staticmethod
  def from_doc(doc: Dict) -> 'ObservatoryX':
    return ObservatoryX(
        observatory_id = str(doc.get("observatory_id")),
        title          = doc['title'],
        description    = doc.get('description', ''),
        metadata       = doc.get('metadata', {}),
        created_at     = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
        updated_at     = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
    )

 
class ProductX(Descriptable):
    product_id: str
    name: str

class CatalogType(str, Enum):
    INTEREST   = "INTEREST"
    TEMPORAL   = "TEMPORAL"
    SPATIAL    = "SPATIAL"
    OBSERVABLE = "OBSERVABLE"
    REFERENCE  = "REFERENCE"


class CatalogX(Descriptable):
    catalog_id: str
    root_group_id: Optional[str ] = Field(default=None)
    name: str
    value: UpperSnakeStr 
    catalog_type: CatalogType
    parent_catalog_id: Optional[str] = None
    level: int = 0

class CatalogItemValueType(str, Enum):
    STRING   = "STRING"
    NUMBER   = "NUMBER"
    BOOLEAN  = "BOOLEAN"
    DATETIME = "DATETIME"
class CatalogItemX(Descriptable):
  catalog_item_id: str
  name: str
  value: UpperSnakeStr
  code: int
  value_type: CatalogItemValueType
  temporal_value: Optional[DT.datetime] = None

  @staticmethod
  def from_doc(doc: Dict) -> 'CatalogItemX':
    return CatalogItemX(
        catalog_item_id = str(doc.get("catalog_item_id")),
        name            = doc['name'],
        value           = doc['value'],
        code            = doc['code'],
        value_type      = CatalogItemValueType(doc['value_type']),
        temporal_value  = doc.get('temporal_value'),
        description     = doc.get('description', ''),
        metadata        = doc.get('metadata', {}),
        created_at      = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
        updated_at      = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
    )


class CatalogItemAlias(Descriptable):
    catalog_item_alias_id: str
    value: str
    value_type: CatalogItemValueType

    @staticmethod
    def from_doc(doc: Dict) -> 'CatalogItemAlias':
        return CatalogItemAlias(
            catalog_item_alias_id = str(doc.get("catalog_item_alias_id")),
            value                 = doc.get("value",None),
            value_type            = CatalogItemValueType(doc['value_type']),
            description           = doc.get('description', ''),
            metadata              = doc.get('metadata', {}),
            created_at            = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
            updated_at            = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
        )


    
# Links
class ObservatoryToCatalogLink(TimestampedModel):
  observatory_id: str
  catalog_id: str 
  level:int=0

class CatalogToCatalogItemLink(TimestampedModel):
  catalog_id: str
  catalog_item_id: str

class CatalogItemToCatalogAliasLink(TimestampedModel):
    catalog_item_id: str
    catalog_item_alias_id: str

class ObservatoryToProductLink(TimestampedModel):
  observatory_id: str
  product_id: str
  
class CatalogItemToProductLink(TimestampedModel):
    product_id: str
    catalog_item_id: str
  
class CatalogItemRelationship(TimestampedModel):
    parent_id: str # e.g., ID for "MX"
    child_id: str  # e.g., ID for "SLP"
  

# ==========================================
# 1. ENUMS FOR STRICT VALIDATION
# ==========================================
class ThemeEnum(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

class ViewModeEnum(str, Enum):
    GRID = "grid"      # Cuadrícula
    LIST = "list"      # Lista

class ExportFormatEnum(str, Enum):
    JSON = "json"
    YML = "yml"        # For exporting DSL queries

# ==========================================
# 2. CONFIGURATION SUB-MODELS
# ==========================================
class AppearanceSettings(BaseModel):
    theme: ThemeEnum = Field(
        default=ThemeEnum.SYSTEM, 
        description="User interface theme preference (Light, Dark, or System default)"
    )
    reduce_animations: bool = Field(
        default=False, 
        description="Improves performance on lower-end devices"
    )
    font_size: int = Field(
        default=14, 
        ge=10, le=24, # Added min/max limits for safety
        description="Base font size for the application"
    )

class ExplorationSettings(BaseModel):
    items_per_page: int = Field(
        default=24, 
        ge=10, le=100, # Added min/max limits for safety
        description="Number of results to display per page"
    )
    default_view: ViewModeEnum = Field(
        default=ViewModeEnum.GRID, 
        description="Default view mode (Grid or List)"
    )
    enable_tutorial: bool = Field(
        default=True,
        description="Show onboarding tutorial for new users"
    )

class ExportSettings(BaseModel):
    default_format: ExportFormatEnum = Field(
        default=ExportFormatEnum.YML, 
        description="Default format for exporting products or queries"
    )
    include_metadata:bool = Field(
       default=False,
       description="This includes metadata on the exported formats"
    )

# Group all settings together
class UserPreferences(BaseModel):
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
    exploration: ExplorationSettings = Field(default_factory=ExplorationSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    @staticmethod
    def default()->'UserPreferences':
        return UserPreferences(
            appearance=AppearanceSettings(),
            exploration=ExplorationSettings(),
            export=ExportSettings()
        )
       

# ==========================================
# 3. THE MAIN USER PROFILE MODEL
# ==========================================
class UserProfileX(TimestampedModel):
    """
    Core model representing a user and their settings in the database.
    """
    user_id: str = Field(..., description="Unique identifier for the user")
    username: str = Field(..., description="Display name of the user")
    email: str = Field(..., description="Email address of the user")
    first_name: Optional[str] = Field(default=None, description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    fullname: Optional[str] = Field(default=None, description="User's full name")
    disabled: bool = Field(default=False, description="Indicates if the user's account is disabled")
    settings: UserPreferences = Field(default_factory=UserPreferences)
    @staticmethod
    def from_doc(doc: Dict) -> 'UserProfileX':
        settings_doc = doc.get('settings', {})

        appearance = AppearanceSettings.model_validate(settings_doc.get('appearance', {}))
        exploration = ExplorationSettings.model_validate(settings_doc.get('exploration', {}))
        export = ExportSettings.model_validate(settings_doc.get('export', {}))

        settings = UserPreferences(
           appearance=appearance,
           exploration=exploration,
           export=export
        )
        return UserProfileX(
            user_id    = str(doc.get("user_id")),
            username   = doc.get('username', ''),
            email      = doc.get('email', ''),
            first_name = doc.get('first_name'),
            last_name  = doc.get('last_name'),
            fullname   = doc.get('fullname'),
            disabled   = doc.get('disabled', False),
            settings   = settings,
            created_at = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
            updated_at = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
        )