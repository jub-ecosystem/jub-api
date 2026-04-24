from pydantic import BaseModel, Field,StringConstraints,AfterValidator
from typing import Optional, Dict, Annotated,Any,List
import jubapi.enums.v2 as ENUMS
# from enum import Enum
import datetime
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
  is_disabled: bool = Field(default=False)
  @staticmethod
  def from_doc(doc: Dict) -> 'ObservatoryX':
    return ObservatoryX(
        observatory_id = str(doc.get("observatory_id")),
        title          = doc['title'],
        description    = doc.get('description', ''),
        metadata       = doc.get('metadata', {}),
        is_disabled    = doc.get('is_disabled', False),
        created_at     = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
        updated_at     = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
    )

 
class ProductX(Descriptable):
    product_id: str
    name: str




class CatalogX(Descriptable):
    catalog_id: str
    root_group_id: Optional[str ] = Field(default=None)
    name: str
    value: UpperSnakeStr 
    catalog_type: ENUMS.CatalogType
    parent_catalog_id: Optional[str] = None
    level: int = 0



class CatalogItemX(Descriptable):
  catalog_item_id: str
  name: str
  value: UpperSnakeStr
  code: int
  value_type: ENUMS.CatalogItemValueType
  catalog_type: Optional[ENUMS.CatalogType] = Field(default=None)
  temporal_value: Optional[DT.datetime] = Field(default=None)

  @staticmethod
  def from_doc(doc: Dict) -> 'CatalogItemX':
    return CatalogItemX(
        catalog_item_id = str(doc.get("catalog_item_id")),
        name            = doc['name'],
        value           = doc['value'],
        code            = doc['code'],
        value_type      = ENUMS.CatalogItemValueType(doc['value_type']),
        catalog_type    = ENUMS.CatalogType(doc['catalog_type']) if 'catalog_type' in doc else None,
        temporal_value  = doc.get('temporal_value'),
        description     = doc.get('description', ''),
        metadata        = doc.get('metadata', {}),
        created_at      = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
        updated_at      = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
    )

class CatalogItemAlias(Descriptable):
    catalog_item_alias_id: str
    value: str
    value_type: ENUMS.CatalogItemValueType
    catalog_type: Optional[ENUMS.CatalogType] = Field(default=None)

    @staticmethod
    def from_doc(doc: Dict) -> 'CatalogItemAlias':
        return CatalogItemAlias(
            catalog_item_alias_id = str(doc.get("catalog_item_alias_id")),
            value                 = doc.get("value",None),
            value_type            = ENUMS.CatalogItemValueType(doc['value_type']),
            catalog_type          = ENUMS.CatalogType(doc['catalog_type']) if 'catalog_type' in doc else None,
            description           = doc.get('description', ''),
            metadata              = doc.get('metadata', {}),
            created_at            = doc.get('created_at', DT.datetime.now(DT.timezone.utc)),
            updated_at            = doc.get('updated_at', DT.datetime.now(DT.timezone.utc))
        )



class ProductServiceLink(TimestampedModel):
    product_id: str
    service_id: str

class CatalogServiceLink(TimestampedModel):
    catalog_id: str
    service_id: str

# Links
class ObservatoryToCatalogLink(TimestampedModel):
  observatory_id:str
  catalog_id:str 
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
# 2. CONFIGURATION SUB-MODELS
# ==========================================
class AppearanceSettings(BaseModel):
    theme: ENUMS.ThemeEnum = Field(
        default=ENUMS.ThemeEnum.SYSTEM, 
        description="User interface theme preference (Light, Dark, or System default)"
    )
    reduce_animations: bool = Field(
        default=False, 
        description="Improves performance on lower-end devices"
    )
    font_size: int = Field(
        default=14, 
        ge=8, le=24, # Added min/max limits for safety
        description="Base font size for the application"
    )

class ExplorationSettings(BaseModel):
    items_per_page: int = Field(
        default=24, 
        ge=1, le=100, # Added min/max limits for safety
        description="Number of results to display per page"
    )
    default_view: ENUMS.ViewModeEnum = Field(
        default=ENUMS.ViewModeEnum.GRID, 
        description="Default view mode (Grid or List)"
    )
    enable_tutorial: bool = Field(
        default=True,
        description="Show onboarding tutorial for new users"
    )

class ExportSettings(BaseModel):
    default_format: ENUMS.ExportFormatEnum = Field(
        default=ENUMS.ExportFormatEnum.YML, 
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




# ==========================================
# DATA INGESTION ENTITIES
# ==========================================
class DataSource(BaseModel):
    source_id: str = Field(..., description="Unique ID for the data source.")
    name: str = Field(..., description="Name of the dataset or database.")
    description: Optional[str] = Field(default="", description="Human-readable description of this data source.")
    format: ENUMS.DataSourceFormatEnum = Field(default=ENUMS.DataSourceFormatEnum.CSV, description="Format or database engine.")
    connection_uri: Optional[str] = Field(default=None, description="Connection string for databases.")
    bucket_id: Optional[str] = Field(default="jub", description="Path or URL if the source is a static file.")
    ball_id: Optional[str] = Field(default="", description="ID of the BALL this source belongs to, if any.")

class DataRecord(BaseModel):
    record_id: str = Field(..., description="Unique ID for this specific row/record.")
    source_id: str = Field(..., description="ID of the DataSource (e.g., the CSV file) this belongs to.")
    
    # --- The Dimensions (Strictly Catalog Item IDs) ---
    spatial_id: str = Field(..., description="Must be a valid ID from cat_spatial (e.g., 'MX', 'TAM').")
    temporal_id: DT.datetime  = Field(..., description="Must be a valid ID from cat_time (e.g., 'Y2026').")
    interest_ids: List[str] = Field(
        default_factory=list, 
        description="List of valid IDs from interest catalogs (e.g., ['C50_1', 'FEMALE'])."
    )
    numerical_interest_ids: Dict[str, float] = Field(
        default_factory=dict, 
        description="For any numerical variables, store the catalog item ID and its corresponding value (e.g., {'AGE': 45})."
    )
    
    # --- The Metric ---
    # This is the actual value you use to draw the height of the bar chart or the point on the line graph.
    # value: float = Field(..., description="The actual numeric value/count for this specific combination.")
    
    # Optional: Keep the raw row just in case you need to debug why it mapped a certain way
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="The original flat CSV row.")



class DataMetricX(BaseModel):
    metric_id: str = Field(..., description="Unique ID for this pre-calculated metric.")
    source_id: str = Field(..., description="The DataSource this was calculated from.")
    
    # What are we measuring?
    target_variable: str = Field(..., description="The original column name (e.g., 'age').")
    metric_type: ENUMS.MetricTypeEnum = Field(..., description="The mathematical operation applied.")
    value: float = Field(..., description="The final calculated number.")

    # Context: How was this filtered/grouped?
    # This allows the search engine to find this exact metric later!
    dsl_query: str = Field(..., description="The query used to filter this data (e.g., 'jub.v1.VS(MX)')")
    
    # Optional: Breakdown of the specific dimensions for quick DB indexing
    dimensions: Dict[str, str] = Field(
        default_factory=dict, 
        description="e.g., {'spatial': 'MX', 'sex': 'M'}"
    )

# ==========================================
# USER & INTERACTION ENTITIES
# ==========================================
class Notification(BaseModel):
    notification_id: str = Field(description="Unique ID for the notification.")
    user_id: str = Field(description="The user receiving the notification.")
    status: ENUMS.NotificationStatusEnum = Field(description="Type of notification (info, warning, error, success).")
    operation: ENUMS.NotificationOperationEnum = Field(description="The CRUD operation that triggered this notification.")
    entity: ENUMS.NotificationEntityEnum = Field(description="The type of entity this notification is about (e.g., product, observatory, user_profile).")
    entity_id: Optional[str] = Field(default=None, description="The specific ID of the entity involved (e.g., product_id or observatory_id).")
    title: str = Field(description="Short title for the notification.")
    message: str = Field(description="Notification content.")
    is_read: bool = Field(default=False, description="Read status.")
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc), description="Timestamp when the notification was created.")

class Task(BaseModel):
    task_id: str = Field(..., description="Unique ID for the background or processing task.")
    user_id: str = Field(..., description="The user who created the task.")
    observatory_id: str = Field(..., description="The observatory this task is associated with.")
    status: ENUMS.TaskStatus = Field(default=ENUMS.TaskStatus.PENDING, description="Current status of the task.")
    logs: List[str] = Field(default_factory=list, description="Execution logs or error messages.")

# ==========================================
# OBSERVATORY ENTITIES
# ==========================================
class View(BaseModel):
    view_id: str = Field(..., description="Unique ID for the saved view.")
    observatory_id: str = Field(..., description="The observatory this view belongs to.")
    name: str = Field(..., description="Name of the saved view/configuration.")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="UI configuration or filter state.")

class Review(BaseModel):
    review_id: str = Field(..., description="Unique ID for the review.")
    observatory_id: str = Field(..., description="The observatory being reviewed.")
    user_id: str = Field(..., description="The user who wrote the review.")
    content: str = Field(..., description="Text content of the review.")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5.")


class TaskAttempt(BaseModel):
    attempt_number: int = Field(..., description="1 for the first run, 2 for the first retry, etc.")
    status: ENUMS.TaskStatusEnum = Field(default=ENUMS.TaskStatusEnum.PENDING)
    start_time: Optional[datetime.datetime] = Field(default=None, description="When this specific attempt started running.")
    end_time: Optional[datetime.datetime] = Field(default=None, description="When this attempt finished (success or fail).")
    error_message: Optional[str] = Field(default=None, description="If it failed, why did it fail?")
    
    @property
    def response_time_seconds(self) -> Optional[float]:
        """Calculates how long this specific attempt took."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
class TaskX(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task.")
    user_id: str = Field(..., description="The user who triggered the task.")
    observatory_id: str = Field(..., description="The observatory this task belongs to.")
    
    title: str = Field(..., description="Generated title including the operation and observatory name.")
    description: str = Field(..., description="Brief explanation of what the task is doing.")
    operation: ENUMS.TaskOperationEnum = Field(..., description="What operation triggered this task.")
    current_status: ENUMS.TaskStatusEnum = Field(default=ENUMS.TaskStatusEnum.PENDING, description="The overall current status.")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="For the progress bar (0 to 100).")
    progress_message: Optional[str] = Field(default=None, description="e.g., 'Generando productos...' or 'En cola...'")
    attempts: List[TaskAttempt] = Field(
        default_factory=list, 
        description="History of execution attempts. A new item is added on 'Retry'."
    )
    
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE / WORKFLOW DOMAIN
# These models are independent of the observatory/catalog domain.
# ══════════════════════════════════════════════════════════════════════════════

class BuildingBlock(TimestampedModel):
    """The smallest execution unit — a container image + entrypoint command."""
    building_block_id: str = Field(..., description="Primary key (nanoid).")
    name: str              = Field(..., description="Human-readable identifier.")
    command: str           = Field(..., description="Entrypoint command executed inside the container.")
    image: str             = Field(..., description="Docker image reference (e.g. 'python:3.11-slim').")
    description: Optional[str] = Field(default="", description="Optional longer description.")


class PatternX(TimestampedModel):
    """
    A reusable processing pattern that declares how a building block is deployed:
    how many workers, what load-balancer strategy, and which task type it handles.
    """
    pattern_id: str             = Field(..., description="Primary key (nanoid).")
    name: str                   = Field(..., description="Human-readable pattern name.")
    description: Optional[str]  = Field(default="")
    task: str                   = Field(..., description="Task category this pattern handles (e.g. 'transform', 'ingest').")
    pattern: str                = Field(..., description="Pattern type (e.g. 'map-reduce', 'pipeline', 'fanout').")
    workers: int                = Field(default=1, ge=1, description="Number of parallel worker replicas.")
    loadbalancer: str           = Field(default="round-robin", description="Load-balancer strategy (e.g. 'round-robin', 'least-connections').")
    building_block_id: Optional[str] = Field(default=None, description="Reference to BuildingBlock that implements this pattern.")


class StageX(TimestampedModel):
    """
    One step in a workflow.  Declares where data comes from (source), where it goes
    (sink), how it is transformed (transformation), and which HTTP endpoint it exposes.
    """
    stage_id: str               = Field(..., description="Primary key (nanoid).")
    name: str                   = Field(..., description="Human-readable stage name.")
    source: str                 = Field(..., description="Input source identifier or URI.")
    sink: str                   = Field(..., description="Output sink identifier or URI.")
    transformation_id: Optional[str] = Field(default=None, description="Reference to PatternX applied in this stage.")
    endpoint: str               = Field(..., description="HTTP or messaging endpoint exposed by this stage.")


class WorkflowX(TimestampedModel):
    """An ordered sequence of stages forming a complete processing pipeline."""
    workflow_id: str       = Field(..., description="Primary key (nanoid).")
    name: str              = Field(..., description="Human-readable workflow name.")
    stage_ids: List[str]   = Field(default_factory=list, description="Ordered list of StageX IDs.")


class ServiceX(TimestampedModel):
    """
    Top-level entity that groups a workflow under a named, ownable service.
    The `public` flag controls discoverability via the Services DSL.
    """
    service_id: str            = Field(..., description="Primary key (nanoid).")
    name: str                  = Field(..., description="Service name — searchable via DSL.")
    description: Optional[str] = Field(default="", description="What this service does.")
    owner_id: str              = Field(..., description="User ID of the service owner.")
    public: bool               = Field(default=False, description="Whether the service is publicly discoverable.")
    workflow_id: Optional[str] = Field(default=None, description="Reference to the WorkflowX this service executes.")
