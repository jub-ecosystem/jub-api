from enum import Enum
class CollectionNames(Enum):
    """Centralized collection names for MongoDB."""
    OBSERVATORIES                    = "observatories"
    PRODUCTS                         = "products"
    CATALOGS                         = "catalogs"
    CATALOG_ITEMS                    = "catalog_items"
    CATALOG_ITEM_VALUES              = "catalog_item_values"
    CATALOG_ITEM_ALIASES             = "catalog_item_aliases"
    
    OBSERVATORY_PRODUCT_LINKS        = "observatory_product_links"
    PRODUCT_CATALOGS_ITEM_LINKS      = "product_catalogs_item_links"
    CATALOG_ITEM_RELATIONSHIPS       = "catalog_item_relationships"
    CATALOG_CATALOG_ITEM_LINKS       = "catalog_catalog_item_links"
    CATALOG_ITEM_CATALOG_ALIAS_LINKS = "catalog_item_catalog_alias_links"
    OBSERVATORY_CATALOG_LINKS        = "observatory_catalog_links"

    NOTIFICATIONS                   = "notifications"
    TASKS                           = 'tasks'
    DATA_SOURCES                    = "data_sources"
    DATA_RECORDS                    = "data_records"

    USER_PROFILES                   = "user_profiles"    
    OBSERVATORIES_V1                = "observatories_v1"
    PRODUCTS_V1                     = "products_v1"
    CATALOGS_V1                     = "catalogs_v1"
    CATALOG_ITEMS_V1                = "catalog_items_v1"
    CATALOG_ITEM_VALUES_V1          = "catalog_item_values_v1"

    # ── Service / Workflow domain ──────────────────────────────────────────
    BUILDING_BLOCKS                 = "building_blocks"
    PATTERNS                        = "patterns"
    STAGES                          = "stages"
    WORKFLOWS                       = "workflows"
    SERVICES                        = "services"

