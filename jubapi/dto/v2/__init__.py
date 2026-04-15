from pydantic import BaseModel,Field
from typing import Optional,List
import jubapi.models.v2 as M
import jubapi.enums.v2 as ENUMS
# from jubapi.models.v2 import ObservatoryX,CatalogX

class TasksStatsDTO(BaseModel):
    pending: int = Field(default=0, description="Number of tasks currently pending")
    running: int = Field(default=0, description="Number of tasks currently running")
    success: int = Field(default=0, description="Number of tasks completed successfully")
    failed: int = Field(default=0, description="Number of tasks that have failed")

class TaskXDTO(BaseModel):
    task_id: str
    user_id: str
    observatory_id: str
    title: str
    description: str
    operation: ENUMS.TaskOperationEnum
    current_status: ENUMS.TaskStatusEnum
    progress_message: Optional[str] = None
    created_at: str
    updated_at: str

    @staticmethod
    def from_model(model: M.TaskX) -> 'TaskXDTO':
        return TaskXDTO(
            task_id        = model.task_id,
            user_id        = model.user_id,
            observatory_id = model.observatory_id,
            title          = model.title,
            description    = model.description,
            operation      = model.operation,
            current_status = model.current_status,
            progress_message  = model.progress_message,
            created_at     = model.created_at.isoformat(),
            updated_at     = model.updated_at.isoformat()
        )

class NotificationReadAllResponseDTO(BaseModel):
    modified: int
class NotificationClearReadResponseDTO(BaseModel):
    deleted: int
    

class SearchQueryDTO(BaseModel):
    query: str
    observatory_id: Optional[str] = None
    limit: Optional[int] = 10
    skip: Optional[int] = 0

class VariableMetadataDTO(BaseModel):
    code:Optional[int] = Field(default=None, description="Optional code associated with the catalog item, if applicable")
    name: Optional[str] = Field(default=None, description="Name of the catalog item")
    value:Optional[str] = Field(default=None, description="Value of the catalog item")
    description: Optional[str] = Field(default=None, description="Description of the catalog item")


class ProductXDTO(BaseModel):
    product_id: str
    name: str
    # code: Optional[int] = None
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    attributes:List[str] = Field(default_factory=list)
    spatial_variable:VariableMetadataDTO = Field(default_factory=VariableMetadataDTO)
    temporal_variable:VariableMetadataDTO = Field(default_factory=VariableMetadataDTO)
    interest_variable:List[VariableMetadataDTO] = Field(default_factory=list)
    # metadata: ItemMetadataDTO = Field(default_factory=ItemMetadataDTO)
    created_at: str
    updated_at: str


    @staticmethod
    def from_model(model:M.ProductX) -> 'ProductXDTO':
        return ProductXDTO(
            product_id = model.product_id,
            name       = model.name,
            # code= model.,
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
    theme: str = Field(default="light", description="Theme of the application, e.g., 'light' or 'dark'")
    font_size: int = Field(default=14, description="Font size for the application interface")
    reduce_animations: bool = Field(default=False, description="Whether to reduce animations for better performance or accessibility")

class ExplorationSettingsDTO(BaseModel):
    enable_tutorial: bool = Field(default=True, description="Whether to enable the tutorial for new users")
    default_view: str  = Field(default="list", description="Default view for exploring content, e.g., 'list' or 'grid'")
    items_per_page: int  = Field(default=12, description="Number of items to display per page in listings")

class ExportSettingsDTO(BaseModel):
    default_format: str = Field(default="yml", description="Default export format, e.g., 'csv', 'json' or 'yml'")
    include_metadata: bool = Field(default=True, description="Whether to include metadata in the export")

class UserPreferencesDTO(BaseModel):
    appearance: AppearanceSettingsDTO
    # Field(default_factory=AppearanceSettingsDTO)
    exploration: ExplorationSettingsDTO 
    # = Field(default_factory=ExplorationSettingsDTO)
    export: ExportSettingsDTO
    # ExportSettingsDTO = Field(default_factory=ExportSettingsDTO)
    def to_model(self) -> M.UserPreferences:
        return M.UserPreferences(
            appearance = M.AppearanceSettings(
                theme=self.appearance.theme,
                font_size=self.appearance.font_size,
                reduce_animations=self.appearance.reduce_animations
            ),
            exploration = M.ExplorationSettings(
                enable_tutorial=self.exploration.enable_tutorial,
                default_view=self.exploration.default_view,
                items_per_page=self.exploration.items_per_page
            ),
            export = M.ExportSettings(
                default_format=self.export.default_format,
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
                default_format=model.export.default_format,
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
    temporal_secret_key: Optional[str] = Field(default=None, description="Temporal secret key for internal service-to-service authentication, if applicable")
    user_profile: UserProfileDTO


class CreateNotificationDTO(BaseModel):
    user_id: str
    status: ENUMS.NotificationStatusEnum
    operation: ENUMS.NotificationOperationEnum
    entity_type: ENUMS.NotificationEntityEnum
    title: str
    message: str
    entity_id: Optional[str] = Field(default=None, description="ID of the related entity, e.g., observatory_id or product_id")

class CreateTaskDTO(BaseModel):
    user_id: str
    observatory_id: str
    title: str
    description: str
    operation: ENUMS.TaskOperationEnum