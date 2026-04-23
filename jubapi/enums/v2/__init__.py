from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class TaskOperationEnum(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC   = "sync"
    SETUP  = "setup"   # observatory provisioning
    INDEX  = "index"   # file ingestion / data indexing
    

class NotificationStatusEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
class NotificationOperationEnum(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ  = "read"
    OTHER = "other"

class NotificationEntityEnum(str, Enum):
    PRODUCT = "product"
    OBSERVATORY = "observatory"
    CATALOG = "catalog"
    USER_PROFILE = "user_profile"
    USER = "user"
    DATA_SOURCE = "data_source"
    TASK = "task"
    OTHER = "other"
    SETTINGS = "settings"
    NONE = "none"

# class Notification

class MetricTypeEnum(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    STD_DEV = "std_dev"
    COUNT = "count"
    SUM = "sum"

class DataSourceFormatEnum(str, Enum):
    CSV      = "csv"
    JSON     = "json"
    POSTGRES = "postgres"
    MYSQL    = "mysql"
    MONGODB  = "mongodb"

class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"

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


class CatalogItemValueType(str, Enum):
    STRING   = "STRING"
    NUMBER   = "NUMBER"
    BOOLEAN  = "BOOLEAN"
    DATETIME = "DATETIME"

class CatalogType(str, Enum):
    INTEREST   = "INTEREST"
    TEMPORAL   = "TEMPORAL"
    SPATIAL    = "SPATIAL"
    OBSERVABLE = "OBSERVABLE"
    REFERENCE  = "REFERENCE"