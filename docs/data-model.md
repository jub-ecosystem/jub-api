# Data Model

## Entity Relationship

JUB API uses a graph-like structure with dedicated link collections instead of embedded arrays.
This keeps documents small and supports many-to-many relationships without duplication.

```
Observatory
  │  observatory_catalog_links
  ├──────────────────────────────► Catalog
  │                                    │  catalog_catalog_item_links
  │                                    └──► CatalogItem ──► child CatalogItem
  │                                                   └──► CatalogItemAlias
  │  observatory_product_links
  └──────────────────────────────► Product
                                       │  product_catalogs_item_links
                                       └──► CatalogItem (tags)

DataSource ──► DataRecord
                   ├── spatial_id      → catalog_item_id
                   ├── temporal_id     → datetime
                   ├── interest_ids[]  → catalog_item_id[]
                   └── numerical_interest_ids → { field: float }
```

---

## Core Entities

### Observatory

The root context for a data platform instance.

| Field | Type | Description |
|---|---|---|
| `observatory_id` | string | Primary key |
| `title` | string | Human-readable name |
| `description` | string | Short description |
| `image_url` | string? | Optional cover image URL |
| `is_disabled` | bool | `true` while being provisioned; `false` when live |
| `metadata` | dict | Arbitrary key-value pairs |

!!! info "Disabled flag"
    Observatories are created with `is_disabled: true` via the setup endpoint and enabled
    automatically when `POST /tasks/{task_id}/complete` is called with `success: true`.

---

### Catalog

A typed vocabulary of items. `catalog_type` determines how items are interpreted by the DSL.

| Field | Type | Description |
|---|---|---|
| `catalog_id` | string | Primary key |
| `name` | string | Human-readable label |
| `value` | UpperSnakeStr | Normalised identifier used in DSL (e.g. `SPATIAL`, `CIE10_CANCER`) |
| `catalog_type` | enum | `spatial` · `temporal` · `interest` |
| `level` | int | Depth in hierarchy (0 = root) |
| `parent_catalog_id` | string? | Parent catalog for sub-catalogs |

---

### Catalog Item

A single vocabulary entry — a leaf node of a catalog.

| Field | Type | Description |
|---|---|---|
| `catalog_item_id` | string | Primary key. Stored verbatim in `DataRecord.spatial_id` and `interest_ids` |
| `name` | string | Human-readable label (e.g. "Breast Cancer") |
| `value` | UpperSnakeStr | Short normalised code (e.g. `C_MAMA`) |
| `code` | int | Numeric code (e.g. `101`) |
| `value_type` | enum | `string` · `datetime` |
| `temporal_value` | datetime? | Actual datetime for temporal items |

---

### Catalog Item Alias

Alternative names or codes for a catalog item. The DSL resolver checks aliases so users
can query by any of them.

| Field | Type | Description |
|---|---|---|
| `catalog_item_alias_id` | string | Primary key |
| `value` | string | Alternative name, code string, or abbreviation |

---

### Product

A dataset or analytical report. Tagged with catalog items across multiple dimensions.

| Field | Type | Description |
|---|---|---|
| `product_id` | string | Primary key |
| `name` | string | Human-readable product name |
| `description` | string | Short description |

Tags (links to catalog items) drive DSL-based product discovery.

---

### Data Source

Metadata about a raw data file or database.

| Field | Type | Description |
|---|---|---|
| `source_id` | string | Primary key |
| `name` | string | Dataset name |
| `format` | enum | `csv` · `json` · … |
| `bucket_id` | string? | Storage bucket or path |

---

### Data Record

A single aggregated row inside a data source.

| Field | Type | Description |
|---|---|---|
| `record_id` | string | Primary key |
| `source_id` | string | Parent data source |
| `spatial_id` | string | `catalog_item_id` from a SPATIAL catalog |
| `temporal_id` | datetime | UTC datetime this record represents |
| `interest_ids` | string[] | `catalog_item_id` values from INTEREST catalogs |
| `numerical_interest_ids` | dict | `{ "TASA_100K": 45.3 }` — numeric variables for `VO()` |
| `raw_payload` | dict | Original source row (debug only) |

!!! warning "ID contract"
    Every value in `spatial_id` and `interest_ids` must be a `catalog_item_id` that already
    exists in the catalog. The DSL resolver looks them up at query time to resolve user-provided
    values/codes/aliases.

---

### Task

Tracks the status of a background or external operation.

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Primary key |
| `user_id` | string | User who created the task |
| `observatory_id` | string | Associated observatory |
| `operation` | enum | `setup` · `index` · `create` · `sync` · … |
| `current_status` | enum | `pending` · `running` · `success` · `failed` |
| `attempts` | TaskAttempt[] | Full execution history |

---

## Link Collections

| Collection | Relationship |
|---|---|
| `observatory_product_links` | Observatory → Product |
| `observatory_catalog_links` | Observatory → Catalog (with `level`) |
| `catalog_catalog_item_links` | Catalog → CatalogItem |
| `product_catalogs_item_links` | Product → CatalogItem (tags) |
| `catalog_item_relationships` | CatalogItem → child CatalogItem (hierarchy) |
| `catalog_item_catalog_alias_links` | CatalogItem → CatalogItemAlias |

`GraphLinkManager` owns all operations on these collections and enforces cascading deletions.
