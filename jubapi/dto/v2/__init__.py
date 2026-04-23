from pydantic import BaseModel,Field
from typing import Optional,List,Dict
import jubapi.models.v2 as M
import jubapi.enums.v2 as ENUMS
import datetime as DT
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
    progress_message: Optional[str] = Field(default=None, description="Optional progress message for the task")
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
    observatory_id: Optional[str] = Field(default=None, description="Optional observatory context for the search query")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Maximum number of search results to return")
    skip: Optional[int] = Field(default=0, ge=0, description="Number of search results to skip for pagination")

class VariableMetadataDTO(BaseModel):
    code:Optional[int] = Field(default=None, description="Optional code associated with the catalog item, if applicable")
    name: Optional[str] = Field(default=None, description="Name of the catalog item")
    value:Optional[str] = Field(default=None, description="Value of the catalog item")
    description: Optional[str] = Field(default=None, description="Description of the catalog item")


class ProductXDTO(BaseModel):
    product_id: str
    name: str
    # code: Optional[int] = None
    description: str = Field(default="", description="Description of the product")
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
    description: str = Field(default="", description="Description of the observatory")
    image_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
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
    root_group_id:Optional[str] = Field(default=None, description="Optional root group ID for the catalog")
    name: str
    value: str
    catalog_type: str
    parent_catalog_id: Optional[str] = Field(default=None, description="Optional parent catalog ID for hierarchical catalogs")
    level: int = Field(default=0, description="Depth level in the catalog hierarchy, where 0 is a root catalog")
    description: str = Field(default="", description="Description of the catalog")
    metadata: dict = Field(default_factory=dict, description="Additional metadata for the catalog as key-value pairs")
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
    description: str = Field(default="", description="Description of the alias")

class CatalogItemDTO(BaseModel):
    catalog_item_id: str
    name: str
    value: str
    code: int
    value_type: str
    description: str = Field(default="", description="Description of the catalog item")
    parent_id: Optional[str] = Field(default=None, description="ID of the parent catalog item for hierarchical relationships")
    temporal_value: Optional[str] = Field(default=None, description="Optional temporal value for the catalog item, if applicable")
    aliases: List[AliasDTO] = Field(default_factory=list)

# --- ROOT ENTITIES ---
class CatalogDTO(BaseModel):
    catalog_id: str
    value: str
    catalog_type: str
    name: str
    description: str = Field(default="", description="Description of the catalog")
    items: List[CatalogItemDTO] = Field(default_factory=list)

class ObservatoryDTO(BaseModel):
    observatory_id: str
    title: str
    description: str = Field(default="", description="Description of the observatory")
    linked_catalogs: List[str] = Field(default_factory=list)

class ProductDTO(BaseModel):
    product_id: str
    obs_id: str
    name: str
    description: str = Field(default="", description="Description of the product")
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
    exploration: ExplorationSettingsDTO 
    export: ExportSettingsDTO
    def default() -> 'UserPreferencesDTO':
        return UserPreferencesDTO(
            appearance = AppearanceSettingsDTO(),
            exploration = ExplorationSettingsDTO(),
            export = ExportSettingsDTO()
        )
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

class PlotQueryDTO(BaseModel):
    """
    Request body for `POST /search/plot`.

    Build the DSL query using these variable types:
    - `VS(value)` — spatial filter (state, municipality, …)
    - `VT(>= 2020)` — temporal filter
    - `VI(C_MAMA OR C_OVARIO)` — interest/category filter
    - `VO(AVG(TASA_100K))` — metric: AVG, SUM, or COUNT
    - `BY(CIE10_CANCER)` — group by a catalog; produces one bar per catalog item

    Example: `jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO).VO(AVG(TASA_100K)).BY(CIE10_CANCER)`
    """
    query: str = Field(
        ...,
        description="Full JUB DSL string. Must start with `jub.v1.`. See PlotQueryDTO docstring for syntax reference.",
    )
    source_id: Optional[str] = Field(
        default=None,
        description="Scope results to one data source. Omit to aggregate across all sources.",
    )
    observatory_id: Optional[str] = Field(
        default=None,
        description="Informational — not used for record filtering (DataRecord has no observatory_id field).",
    )
    chart_type: str = Field(
        default="bar",
        description="ECharts series type: 'bar', 'line', or 'scatter'.",
    )


# 1. The Alias DTO
class CatalogItemAliasCreateDTO(BaseModel):
    value: str
    value_type: ENUMS.CatalogItemValueType
    description: Optional[str] = Field(default="", description="Description of the alias")

# 2. The Item DTO (Notice it contains lists of Aliases AND Children)
class CatalogItemCreateDTO(BaseModel):
    name: str
    value: str # Will be validated to UpperSnakeStr in your actual model
    code: int
    value_type: ENUMS.CatalogItemValueType
    temporal_value: Optional[DT.datetime] = None
    description: Optional[str] = Field(default="", description="Description of the catalog item")
    
    # Nested Relationships!
    aliases: List[CatalogItemAliasCreateDTO] = Field(default_factory=list)
    
    # Recursive typing for hierarchy (e.g., MX -> TAMPS -> Victoria)
    children: List['CatalogItemCreateDTO'] = Field(default_factory=list)

# 3. The Root Catalog DTO
class CatalogCreateDTO(BaseModel):
    name: str
    value: str 
    catalog_type: ENUMS.CatalogType
    description: Optional[str] = Field(default="", description="Description of the catalog")
    
    # All items belonging to this catalog
    items: List[CatalogItemCreateDTO] = Field(default_factory=list)

# Resolve the forward reference for the recursive 'children' field
CatalogItemCreateDTO.model_rebuild()

class CatalogCreatedResponseDTO(BaseModel):
    catalog_id: str

class CatalogCreatedBulkResponseDTO(BaseModel):
    catalog_ids: List[str]

class CatalogItemAliasResponseDTO(BaseModel):
    catalog_item_alias_id: Optional[str]= Field(default=None, description="Unique ID for this alias; may be None if not stored as a separate entity")
    value: str
    value_type: ENUMS.CatalogItemValueType
    description: Optional[str] = Field(default="", description="Description of the alias")

class CatalogItemResponseDTO(BaseModel):
    catalog_item_id: str
    name: str
    value: str
    code: int
    value_type: ENUMS.CatalogItemValueType
    temporal_value: Optional[DT.datetime] = Field(default=None, description="Optional temporal value for the catalog item, if applicable")
    description: Optional[str] = Field(default="", description="Description of the catalog item")
    
    aliases: List[CatalogItemAliasResponseDTO] = Field(default_factory=list, description="List of aliases associated with this catalog item")
    children: List['CatalogItemResponseDTO'] = Field(default_factory=list, description="List of child catalog items (for hierarchical catalogs)")

class CatalogResponseDTO(BaseModel):
    catalog_id: str
    name: str
    value: str
    catalog_type: ENUMS.CatalogType
    description: Optional[str] = Field(default="", description="Description of the catalog")
    
    # All items belonging to this catalog
    items: List[CatalogItemResponseDTO] = Field(default_factory=list, description="List of items in this catalog, each with their aliases and hierarchical children fully populated")

# Resolve the forward reference for the recursive 'children' field
CatalogItemResponseDTO.model_rebuild()

# Optional: A lightweight DTO just for listing catalogs without downloading all items
class CatalogSummaryDTO(BaseModel):
    catalog_id: str
    name: str
    value: str
    catalog_type: ENUMS.CatalogType


# ==========================================
# DATA INGESTION DTOs
# ==========================================

class DataSourceCreateDTO(BaseModel):
    name: str = Field(..., description="Name of the dataset.")
    description: Optional[str] = Field(default="", description="Human-readable description.")
    format: ENUMS.DataSourceFormatEnum = Field(default=ENUMS.DataSourceFormatEnum.CSV)
    bucket_id: Optional[str] = Field(default=None, description="Path or URL of the static file.")
    connection_uri: Optional[str] = Field(default=None, description="Connection string for databases.")

class DataSourceDTO(BaseModel):
    source_id: str
    name: str
    description: str = Field(default="", description="Human-readable description.")
    format: ENUMS.DataSourceFormatEnum
    bucket_id: Optional[str] = Field(default=None, description="MictlanX bucket id")
    connection_uri: Optional[str] = Field(default=None, description="Connection string for databases.")

    @staticmethod
    def from_model(model: M.DataSource) -> 'DataSourceDTO':
        return DataSourceDTO(
            source_id      = model.source_id,
            name           = model.name,
            description    = model.description or "",
            format         = model.format,
            bucket_id      = model.bucket_id,
            connection_uri = model.connection_uri,
        )

class DataRecordCreateDTO(BaseModel):
    """
    A single aggregated data row.  `spatial_id`, `temporal_id`, and each element of
    `interest_ids` must be valid `catalog_item_id` values from the associated catalogs.
    """
    record_id: str = Field(..., description="Unique identifier for this row. Use a deterministic ID so re-ingestion is idempotent.")
    spatial_id: str = Field(..., description="catalog_item_id from a SPATIAL catalog (e.g. the state or municipality).")
    temporal_id: DT.datetime = Field(..., description="Point in time this record represents (UTC datetime).")
    interest_ids: List[str] = Field(
        default_factory=list,
        description="catalog_item_ids from INTEREST catalogs (e.g. disease type, sex). Used for DSL VI() filtering and BY() grouping.",
    )
    numerical_interest_ids: dict = Field(
        default_factory=dict,
        description="Numeric variables keyed by a short name (e.g. {'TASA_100K': 45.3}). Referenced by VO(AVG(TASA_100K)).",
    )
    raw_payload: dict = Field(default_factory=dict, description="Original source row kept for debugging. Not used in queries.")

class DataSourceQueryDTO(BaseModel):
    query: str = Field(
        ...,
        description=(
            "JUB DSL query string. Examples: "
            "`jub.v1.VS(MX)` — all records from Mexico; "
            "`jub.v1.VS(TAM).VT(>= 2020).VI(SEX_FEMALE)` — filtered by state, year range, and sex."
        ),
    )
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Maximum records to return.")
    skip: Optional[int] = Field(default=0, ge=0, description="Records to skip (pagination offset).")

class DataSourceDeleteResponseDTO(BaseModel):
    deleted: bool
    records_removed: int


# ==========================================
# OBSERVATORY DTOs
# ==========================================

class ObservatoryCreateDTO(BaseModel):
    """Creates an immediately-enabled observatory. For the full provisioning workflow use ObservatorySetupDTO."""
    observatory_id: Optional[str] = Field(default=None, description="Custom string ID. A nanoid is auto-generated when omitted.")
    title: str = Field(..., description="Human-readable title shown in the UI.")
    description: Optional[str] = Field(default="", description="Short description of what this observatory covers.")
    image_url: Optional[str] = Field(default=None, description="URL of a representative image or icon.")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict, description="Arbitrary key-value pairs for client use.")


class ObservatoryUpdateDTO(BaseModel):
    title: Optional[str] = Field(default=None, description="Updated title of the observatory")
    description: Optional[str] = Field(default=None, description="Updated description of the observatory")
    image_url: Optional[str] = Field(default=None, description="Updated URL for the observatory's image or icon")
    metadata: Optional[Dict[str, str]] = Field(default=None, description="Updated metadata for the observatory as key-value pairs")


class LinkCatalogDTO(BaseModel):
    catalog_id: str
    level: int = Field(default=0, ge=0, description="Priority/display order for this catalog in the observatory.")


class LinkProductDTO(BaseModel):
    product_id: str


class ObservatoryDeleteResponseDTO(BaseModel):
    deleted: bool


# ==========================================
# PRODUCT DTOs
# ==========================================

class ProductCreateDTO(BaseModel):
    """Creates a single product and links it to an observatory with optional catalog-item tags."""
    product_id: Optional[str] = Field(default=None, description="Custom string ID. A nanoid is auto-generated when omitted.")
    name: str = Field(..., description="Human-readable product name.")
    description: Optional[str] = Field(default="", description="Short description of what data this product contains.")
    observatory_id: str = Field(..., description="ID of the observatory this product belongs to.")
    catalog_item_ids: List[str] = Field(
        default_factory=list,
        description="catalog_item_ids to tag this product with. These drive DSL-based product discovery.",
    )


class ProductUpdateDTO(BaseModel):
    name: Optional[str] = Field(default=None, description="Updated name of the product")
    description: Optional[str] = Field(default=None, description="Updated description of the product")


class ProductSimpleDTO(BaseModel):
    product_id: str
    name: str
    description: str = Field(default="", description="Description of the product")
    created_at: str
    updated_at: str

    @staticmethod
    def from_model(model: M.ProductX) -> 'ProductSimpleDTO':
        return ProductSimpleDTO(
            product_id  = model.product_id,
            name        = model.name,
            description = model.description or "",
            created_at  = model.created_at.isoformat(),
            updated_at  = model.updated_at.isoformat(),
        )


class TagProductDTO(BaseModel):
    catalog_item_ids: List[str] = Field(..., min_length=1)


class ProductDeleteResponseDTO(BaseModel):
    deleted: bool


# ==========================================
# CATALOG ITEM DTOs
# ==========================================

class CatalogItemStandaloneCreateDTO(BaseModel):
    catalog_item_id: Optional[str] = Field(default=None, description="Custom ID; auto-generated if omitted.")
    name: str
    value: str
    code: int
    value_type: ENUMS.CatalogItemValueType
    temporal_value: Optional[DT.datetime] = Field(default=None)
    description: Optional[str] = Field(default="")
    catalog_id: str = Field(..., description="The catalog this item belongs to.")
    parent_item_id: Optional[str] = Field(default=None, description="Optional parent item ID for hierarchical relationships.")


class CatalogItemUpdateDTO(BaseModel):
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    temporal_value: Optional[DT.datetime] = Field(default=None)


class CatalogItemXResponseDTO(BaseModel):
    catalog_item_id: str
    name: str
    value: str
    code: int
    value_type: ENUMS.CatalogItemValueType
    catalog_type: Optional[ENUMS.CatalogType] = Field(default=None)
    temporal_value: Optional[DT.datetime] = Field(default=None)
    description: str = Field(default="")
    created_at: str
    updated_at: str

    @staticmethod
    def from_model(model: M.CatalogItemX) -> 'CatalogItemXResponseDTO':
        return CatalogItemXResponseDTO(
            catalog_item_id = model.catalog_item_id,
            name            = model.name,
            value           = model.value,
            code            = model.code,
            value_type      = model.value_type,
            catalog_type    = model.catalog_type,
            temporal_value  = model.temporal_value,
            description     = model.description or "",
            created_at      = model.created_at.isoformat(),
            updated_at      = model.updated_at.isoformat(),
        )


class CatalogItemDeleteResponseDTO(BaseModel):
    deleted: bool


class CatalogItemAliasXResponseDTO(BaseModel):
    catalog_item_alias_id: str
    value: str
    value_type: ENUMS.CatalogItemValueType
    catalog_type: Optional[ENUMS.CatalogType] = Field(default=None)
    description: str = Field(default="")
    created_at: str
    updated_at: str

    @staticmethod
    def from_model(model: M.CatalogItemAlias) -> 'CatalogItemAliasXResponseDTO':
        return CatalogItemAliasXResponseDTO(
            catalog_item_alias_id = model.catalog_item_alias_id,
            value                 = model.value,
            value_type            = model.value_type,
            catalog_type          = model.catalog_type,
            description           = model.description or "",
            created_at            = model.created_at.isoformat(),
            updated_at            = model.updated_at.isoformat(),
        )


class LinkItemToCatalogDTO(BaseModel):
    catalog_id: str


class LinkItemRelationshipDTO(BaseModel):
    child_item_id: str = Field(..., description="ID of the child catalog item to link as a child of the parent.")


# ==========================================
# OBSERVATORY SETUP / PROVISIONING DTOs
# ==========================================

class ObservatorySetupDTO(BaseModel):
    """One-shot request that creates a disabled observatory and queues a SETUP task."""
    title: str
    user_id: str = Field(..., description="User responsible for this observatory (used for task ownership).")
    description: Optional[str] = Field(default="")
    image_url: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    observatory_id: Optional[str] = Field(default=None, description="Custom ID; auto-generated if omitted.")


class ObservatorySetupResponseDTO(BaseModel):
    observatory_id: str
    task_id: str
    status: str = "pending"
    message: str = (
        "Observatory created (disabled). Assign catalogs and products, "
        "then POST /tasks/{task_id}/complete to enable it."
    )


# ==========================================
# BULK CATALOG ASSIGNMENT DTOs
# ==========================================

class BulkCatalogsDTO(BaseModel):
    """Assign N fully-nested catalogs (items + aliases + hierarchy) to an observatory."""
    catalogs: List[CatalogCreateDTO]
    level: int = Field(default=0, ge=0, description="Link level applied to every catalog in this batch.")


class BulkCatalogsResponseDTO(BaseModel):
    observatory_id: str
    catalog_ids: List[str]


# ==========================================
# BULK PRODUCT ASSIGNMENT DTOs
# ==========================================

class BulkProductItemDTO(BaseModel):
    """A single product definition inside a bulk assignment request."""
    product_id: Optional[str] = Field(default=None, description="Custom ID; auto-generated if omitted.")
    name: str
    description: Optional[str] = Field(default="")
    catalog_item_ids: List[str] = Field(default_factory=list, description="Catalog-item tags to link to this product.")


class BulkProductsDTO(BaseModel):
    products: List[BulkProductItemDTO] = Field(..., min_length=1)


class BulkProductCreatedDTO(BaseModel):
    product_id: str
    name: str


class BulkProductsResponseDTO(BaseModel):
    observatory_id: str
    products: List[BulkProductCreatedDTO]


# ==========================================
# FILE UPLOAD / INGESTION DTOs
# ==========================================

class ProductUploadResponseDTO(BaseModel):
    """Returned immediately after a file is queued for background ingestion."""
    job_id: str
    product_id: str
    status: str = "queued"


# ==========================================
# TASK COMPLETION DTOs  (called by external systems)
# ==========================================

class TaskCompleteDTO(BaseModel):
    success: bool
    message: Optional[str] = Field(default=None, description="Human-readable result or error detail.")


class TaskCompleteResponseDTO(BaseModel):
    task_id: str
    status: str
    observatory_id: str
    observatory_enabled: bool