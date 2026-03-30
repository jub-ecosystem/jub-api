from pydantic import BaseModel,Field
from typing import Optional,List
import jubapi.models.v2 as M
# from jubapi.models.v2 import ObservatoryX,CatalogX


    

class SearchQueryDTO(BaseModel):
    query: str
    observatory_id: Optional[str] = None
    limit: Optional[int] = 10
    skip: Optional[int] = 0

class ProductXDTO(BaseModel):
    product_id: str
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    attributes:List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


    @staticmethod
    def from_model(model) -> 'ProductXDTO':
        return ProductXDTO(
            product_id = model.product_id,
            name       = model.name,
            description= model.description,
            created_at = model.created_at.isoformat(),
            updated_at = model.updated_at.isoformat()
        )

class ObservatoryXDTO(BaseModel):
    observatory_id: str
    title: str
    description: str = ""
    image_url: Optional[str] = None
    metadata: dict = {}
    created_at: str
    updated_at: str
    @staticmethod
    def from_model(model: M.ObservatoryX) -> 'ObservatoryXDTO':
        return ObservatoryXDTO(
            observatory_id = model.observatory_id,
            title          = model.title,
            description    = model.description,
            metadata       = model.metadata,
            created_at     = model.created_at.isoformat(),
            updated_at     = model.updated_at.isoformat()
        )

class CatalogXDTO(BaseModel):
    catalog_id: str
    root_group_id:Optional[str] = Field(default=None)
    name: str
    value: str
    catalog_type: str
    parent_catalog_id: Optional[str] = None
    level: int = 0
    description: str = ""
    metadata: dict = {}
    created_at: str
    updated_at: str
    @staticmethod
    def from_model(model: M.CatalogX) -> 'CatalogXDTO':
        return CatalogXDTO(
            catalog_id        = model.catalog_id,
            name              = model.name,
            value             = model.value,
            description       = model.description,
            metadata          = model.metadata,
            catalog_type      = model.catalog_type,
            parent_catalog_id = model.parent_catalog_id,
            level             = model.level,
            root_group_id     = model.root_group_id,
            created_at        = model.created_at.isoformat(),
            updated_at        = model.updated_at.isoformat()
        )


# from pydantic import BaseModel, Field
# from typing import List, Optional

# --- ALIASES & ITEMS ---
class AliasDTO(BaseModel):
    alias_id: str
    value: str
    description: str = ""

class CatalogItemDTO(BaseModel):
    catalog_item_id: str
    name: str
    value: str
    code: int
    value_type: str
    description: str = ""
    parent_id: Optional[str] = None
    temporal_value: Optional[str] = None
    aliases: List[AliasDTO] = Field(default_factory=list)

# --- ROOT ENTITIES ---
class CatalogDTO(BaseModel):
    catalog_id: str
    value: str
    catalog_type: str
    name: str
    description: str = ""
    items: List[CatalogItemDTO] = Field(default_factory=list)

class ObservatoryDTO(BaseModel):
    observatory_id: str
    title: str
    description: str = ""
    linked_catalogs: List[str] = Field(default_factory=list)

class ProductDTO(BaseModel):
    product_id: str
    obs_id: str
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)

# --- MAIN PAYLOAD ---
class JubFile(BaseModel):
    catalogs: List[CatalogDTO] = Field(default_factory=list)
    observatories: List[ObservatoryDTO] = Field(default_factory=list)
    products: List[ProductDTO] = Field(default_factory=list)



class AppearanceSettingsDTO(BaseModel):
    theme: str = "light"
    font_size: int = 14

class ExplorationSettingsDTO(BaseModel):
    enable_tutorial: bool = True
    default_view: str = "grid"
    items_per_page: int = 10

class ExportSettingsDTO(BaseModel):
    format: str = "pdf"
    include_metadata: bool = True

class UserPreferencesDTO(BaseModel):
    appearance: AppearanceSettingsDTO = Field(default_factory=AppearanceSettingsDTO)
    exploration: ExplorationSettingsDTO = Field(default_factory=ExplorationSettingsDTO)
    export: ExportSettingsDTO = Field(default_factory=ExportSettingsDTO)
    def to_model(self) -> M.UserPreferences:
        return M.UserPreferences(
            appearance = M.AppearanceSettings(
                theme=self.appearance.theme,
                font_size=self.appearance.font_size
            ),
            exploration = M.ExplorationSettings(
                enable_tutorial=self.exploration.enable_tutorial,
                default_view=self.exploration.default_view,
                items_per_page=self.exploration.items_per_page
            ),
            export = M.ExportSettings(
                default_format=self.export.format,
                include_metadata=self.export.include_metadata
            )
        )
    @staticmethod
    def from_model(model: M.UserPreferences) -> 'UserPreferencesDTO':
        return UserPreferencesDTO(
            appearance = AppearanceSettingsDTO(
                theme=model.appearance.theme,
                font_size=model.appearance.font_size
            ),
            exploration = ExplorationSettingsDTO(
                enable_tutorial=model.exploration.enable_tutorial,
                default_view=model.exploration.default_view,
                items_per_page=model.exploration.items_per_page
            ),
            export = ExportSettingsDTO(
                format=model.export.default_format,
                include_metadata=model.export.include_metadata
            )
        )

    # preferences: dict = Field(default_factory=dict)

class UserProfileDTO(BaseModel):
    user_id: str
    username: str
    fullname: str
    first_name: str
    last_name: str
    email: str
    settings: UserPreferencesDTO = Field(default_factory=UserPreferencesDTO)
    created_at: str
    updated_at: str
    is_disabled: bool = Field(default=False)


    @staticmethod
    def from_model(model: M.UserProfileX) -> 'UserProfileDTO':
        return UserProfileDTO(
            user_id    = model.user_id,
            fullname   = f"{model.first_name} {model.last_name}",
            first_name = model.first_name,
            last_name  = model.last_name,
            email      = model.email,
            created_at = model.created_at.isoformat(),
            updated_at = model.updated_at.isoformat(),
            settings   = UserPreferencesDTO.from_model(model.settings),
            username   = model.username,
            is_disabled= model.disabled
        )

class AutenticationResponsetDTO(BaseModel):
    access_token: str
    temporal_secret_key: Optional[str] = None
    user_profile: UserProfileDTO