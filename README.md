# jub-api

REST API for managing observatories, catalogs, products, and data records. Built with FastAPI and MongoDB. Provides a custom query language (DSL) for filtering and aggregating data records, and delegates authentication to an external Xolo service.

Version: `0.0.1a2`


## Requirements

- Python 3.10 or higher
- Poetry
- Docker and Docker Compose (for MongoDB and Xolo)


## Architecture

The codebase follows a strict four-layer architecture. Each request travels down the stack and the result travels back up.

```
Controller  ->  Service  ->  Repository  ->  MongoDB
```

**Controller** receives the HTTP request, validates the input DTO, calls the service via FastAPI `Depends()` injection, and raises an `HTTPException` if the result is an error.

**Service** contains all business logic. It coordinates operations across multiple repositories and returns a `Result[T, JubError]` from the `option` library. Either `Ok(value)` or `Err(JubError)`.

**Repository** is the only layer that talks to MongoDB. Every repository extends `BaseRepository[T]` which provides `find`, `insert`, `get_by_id`, `update`, `delete`, and `count`. Repositories are typed with their Pydantic model.

**Middlewares** (`jubapi/middlewares/__init__.py`) are FastAPI dependency factories. This is the single place where repositories are instantiated and injected into services.


## Project structure

```
jubapi/
├── server.py                    FastAPI app entry point, router registration, CORS, lifespan
├── config/                      Loads all environment variables from the .env file
├── db/
│   ├── constants.py             CollectionNames enum with every MongoDB collection name
│   └── __init__.py              connect_to_mongo / close_mongo_connection
├── controllers/
│   ├── v1/                      Legacy routers, no /api/v2 prefix
│   └── v2/                      Active routers, all prefixed /api/v2
├── services/
│   └── v2/__init__.py           All business logic classes
├── repositories/
│   └── v2/
│       ├── base.py              BaseRepository[T] with generic CRUD methods
│       └── __init__.py          All repository classes
├── models/
│   └── v2/__init__.py           Internal Pydantic domain models
├── dto/
│   └── v2/__init__.py           Request and response DTOs
├── middlewares/__init__.py      Dependency factories, wires repos into services
├── errors/__init__.py           JubError hierarchy, each maps to an HTTP status code
├── enums/
│   └── v2/__init__.py           All enums used across the project
├── querylang/
│   └── v2/
│       ├── parser.py            Parses the data DSL into a QueryAST
│       ├── translator.py        Translates QueryAST into a MongoDB aggregation pipeline
│       └── service_parser.py    Parses jub.v1.SVC() queries into Mongo filter dicts
├── storage/                     StorageBackend abstraction for file uploads
└── log/                         Logger setup
```


## Environment variables

All variables are loaded from the file pointed to by `JUB_ENV_FILE_PATH` (defaults to `.env`).

| Variable | Default | Description |
|---|---|---|
| `JUB_ENV_FILE_PATH` | `.env` | Path to the env file to load |
| `JUB_MONGODB_URI` | `mongodb://localhost:27017/jub` | MongoDB connection string |
| `JUB_MONGODB_DATABASE_NAME` | `jub` | Database name |
| `JUB_XOLO_API_URL` | `http://localhost:10000/api/v4` | Xolo auth service base URL |
| `JUB_XOLO_SECRET` | `secret` | Shared secret for Xolo token validation |
| `JUB_ROOT_PATH` | `` | FastAPI root path, used when running behind a reverse proxy |
| `JUB_HOST` | `0.0.0.0` | Uvicorn bind host |
| `JUB_PORT` | `5000` | Uvicorn bind port |
| `JUB_LOG_DEBUG` | `1` | Set to `0` to disable console logging |
| `JUB_LOG_NAME` | `jubapi` | Logger name |
| `JUB_LOG_PATH` | `/log` | Directory where log files are written |
| `JUB_CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins |
| `JUB_CORS_METHODS` | `*` | Comma-separated list of allowed HTTP methods |
| `JUB_CORS_HEADERS` | `*` | Comma-separated list of allowed headers |
| `JUB_CORS_CREDENTIALS` | `True` | Whether to allow credentials in CORS |
| `JUB_OPENAPI_TITLE` | `OCA - API` | Title shown in the OpenAPI docs |
| `JUB_OPENAPI_VERSION` | `0.0.1` | Version shown in the OpenAPI docs |


## Local development

Install dependencies and activate the virtual environment.

```sh
poetry install && poetry lock
poetry self add poetry-plugin-shell
poetry shell
```

Start MongoDB and the Xolo auth service, then run the API.

```sh
./run_local.sh
```

This script brings up the MongoDB container (`docker-compose.yml`), the Xolo stack (`xolo.yml`), and starts uvicorn on port 5000 with hot reload.

Run the test suite.

```sh
# All tests
pytest tests/ -s -vvvv

# Single file
pytest tests/test_search_service.py -s -vvvv

# With coverage
coverage run -m pytest tests/ -s -vvvv && coverage report -m
```

Tests require MongoDB running at `mongodb://localhost:27027/jub_test`. The `JUB_ENV_FILE_PATH` variable controls which `.env` file is loaded. It defaults to `.env.test`.


## Docker deployment

The full stack (API, MongoDB, Xolo auth service, Redis cache) runs via a single compose file.

```sh
# Build the image
docker compose -f docker-compose.yml build

# Start everything
docker compose -f docker-compose.yml up -d
```

The API reads its configuration from `.env.dev` by default when running inside Docker. The Xolo service and its MongoDB instance are declared in the same compose file.

For a standalone deployment of only the Xolo auth service:

```sh
docker compose -f xolo.yml up -d
```

The `cluster.yml` file is an optional configuration for multi-node production deployments and is not required for local or single-host setups.


## API versions

**v1** is the legacy API. Its routers live under `jubapi/controllers/v1/` and have no version prefix. It covers observatories, catalogs, and products with a simpler data model. It is not under active development.

**v2** is the active API. All routes are prefixed `/api/v2`. It introduces the full entity graph, the DSL, tasks, notifications, file uploads, and the service and workflow domain.

The OpenAPI documentation is available at `/docs` when the server is running.


## Query DSL

The DSL is the primary way to filter and aggregate data records. A query is a string that starts with `jub.v1.` followed by one or more variable clauses chained together.

### Data query

Used by the `POST /api/v2/search` endpoint via the `query` field of `SearchQueryDTO`.

**Syntax**

```
jub.v1.<clause1>(<expression>).<clause2>(<expression>)...
```

**Variable prefixes**

| Prefix | Name | Description |
|---|---|---|
| `VS` | Spatial variable | Filters by the `spatial_id` field of a data record |
| `VT` | Temporal variable | Filters by the `temporal_id` field (datetime) |
| `VI` | Interest variable | Filters by values in the `interest_ids` array |
| `VO` | Observable variable | Defines the aggregation metric: AVG, SUM, or COUNT |
| `BY` | Grouping variable | Groups the result set, maps to the `$group` stage |

**Logical operators inside a clause**

| Operator | Behavior |
|---|---|
| `AND` | Record must match all conditions in the clause |
| `OR` | Record must match at least one condition |
| (none) | Single condition, no logic operator needed |

**Spatial — VS**

Filters on the `spatial_id` field. AND is not allowed because a record can only have one location.

```
# Exact location
jub.v1.VS(MX_JAL_GDL)

# Wildcard: all children of MX
jub.v1.VS(MX.*)

# Global wildcard: no spatial filter
jub.v1.VS(*)

# Multiple locations with OR
jub.v1.VS(MX OR US)

# Mix exact and wildcard
jub.v1.VS(MX_JAL_GDL OR US.*)
```

**Temporal — VT**

Filters on the `temporal_id` field. Partial dates are automatically padded: `2020` becomes `2020-01-01T00:00:00Z`, `2020-05` becomes `2020-05-01T00:00:00Z`.

```
# Exact year
jub.v1.VT(2020)

# Exact month
jub.v1.VT(2020-06)

# Exact date
jub.v1.VT(2020-06-15)

# Range with AND
jub.v1.VT(>= 2018 AND <= 2022)

# Open-ended range
jub.v1.VT(>= 2020)

# Multiple exact years with OR
jub.v1.VT(2020 OR 2021 OR 2022)
```

Supported comparison operators: `=`, `!=`, `>`, `<`, `>=`, `<=`.

**Interest — VI**

Filters on the `interest_ids` array field. Interest IDs are stored as `CATALOG_PATH` strings (e.g. `SEX_MALE`, `CIE10_II_C_50`). The DSL uses dot notation which is translated to underscores internally.

```
# Exact catalog item
jub.v1.VI(SEX.MALE)

# Nested path
jub.v1.VI(CIE10.II.C.50)

# All items under a catalog (wildcard)
jub.v1.VI(SEX.*)

# All records regardless of interest (global wildcard)
jub.v1.VI(*)

# Must have BOTH tags (AND)
jub.v1.VI(SEX.MALE AND CIE10.C50)

# Must have EITHER tag (OR)
jub.v1.VI(SEX.MALE OR SEX.FEMALE)

# Filter by catalog root only (any item inside SEX)
jub.v1.VI(SEX)
```

**Observable — VO**

Defines the aggregation metric. If omitted, defaults to `COUNT`.

```
# Count records
jub.v1.VO(COUNT)

# Average a numerical interest field
jub.v1.VO(AVG(AGE))

# Sum a numerical interest field
jub.v1.VO(SUM(INCOME))
```

The target field in `AVG` and `SUM` maps to keys in the `numerical_interest_ids` dictionary of `DataRecord`.

**Grouping — BY**

Groups the aggregated result. The first value becomes the `x_axis` key in the output, the second becomes `hue`. Maps to the `_id` of the MongoDB `$group` stage.

```
# Group by year
jub.v1.BY(TEMPORAL)

# Group by location
jub.v1.BY(SPATIAL)

# Group by an interest catalog
jub.v1.BY(SEX)

# Two-dimensional grouping (x_axis + hue)
jub.v1.BY(TEMPORAL, SEX)
```

**Complete query examples**

```
# Count of all records in Mexico between 2018 and 2022, grouped by year
jub.v1.VS(MX).VT(>= 2018 AND <= 2022).VO(COUNT).BY(TEMPORAL)

# Average age of males in Mexico, grouped by state
jub.v1.VS(MX.*).VI(SEX.MALE).VO(AVG(AGE)).BY(SPATIAL)

# Count of ICD-10 chapter II records, broken down by sex per year
jub.v1.VI(CIE10.II.*).VO(COUNT).BY(TEMPORAL, SEX)

# Total income for a specific location and interest group
jub.v1.VS(MX_JAL_GDL).VI(INCOME_HIGH).VO(SUM(INCOME)).BY(TEMPORAL)
```

**Internal pipeline**

`QueryAST.parse(query_str)` tokenizes the string into a list of `CatalogQuery` nodes. Each node holds a `catalog_prefix` and a `ConditionGroup` with `AND`, `OR`, or `SINGLE` logic. `ASTToMongoTranslator.translate(ast)` then converts the AST into a three-stage MongoDB aggregation pipeline:

1. `$match` — applies the spatial, temporal, and interest filters
2. `$group` — aggregates with the chosen metric and grouping key
3. `$sort` — orders the result by `x_axis` for clean chart output


### Service query — jub.v1.SVC

Used by endpoints that search or filter services. The parser lives in `jubapi/querylang/v2/service_parser.py` and produces a MongoDB filter dict directly (no aggregation pipeline).

**Syntax**

```
jub.v1.SVC(key=value,key=value,...)
```

**Allowed filter keys**

| Key | Type | Description |
|---|---|---|
| `*` | — | Return all services, no filter applied |
| `name` | string | Case-insensitive substring match on the service name |
| `public` | `true` / `false` | Filter by public visibility flag |
| `owner` | string | Exact match on `owner_id` |
| `id` | string | Exact match on `service_id` |
| `provider` | string | Exact match on provider: `XELHUA`, `NEZ`, `EXTERNAL`, `OTHER` |

Multiple keys are combined with a comma and all must match (implicit AND).

**Examples**

```
# All services
jub.v1.SVC(*)

# Services whose name contains "imaging"
jub.v1.SVC(name=imaging)

# Only public services
jub.v1.SVC(public=true)

# Services from the NEZ provider
jub.v1.SVC(provider=NEZ)

# Public services from XELHUA whose name contains "cancer"
jub.v1.SVC(name=cancer,provider=XELHUA,public=true)

# Service owned by a specific user
jub.v1.SVC(owner=usr_abc123)

# Lookup by exact ID
jub.v1.SVC(id=svc_xyz789)
```

Provider values are case-insensitive in the query string and are uppercased before matching.


## Controllers

All v2 controllers live under `jubapi/controllers/v2/`. Every router is registered in `jubapi/server.py` with the `/api/v2` prefix.

| File | Prefix | Responsibility |
|---|---|---|
| `observatories.py` | `/api/v2/observatories` | Observatory CRUD, setup flow with task, catalog and product links, view counter, reviews |
| `products.py` | `/api/v2/products` | Product CRUD, tag management, file upload with background task tracking |
| `catalogs.py` | `/api/v2/catalogs` | Catalog CRUD |
| `catalogs_items.py` | `/api/v2/catalog-items` | Catalog item CRUD and alias management |
| `search.py` | `/api/v2/search` | DSL-powered data record queries |
| `datasources.py` | `/api/v2/datasources` | Data source and data record ingestion |
| `users.py` | `/api/v2/users` | User profile CRUD |
| `notifications.py` | `/api/v2/notifications` | Notification list, mark-as-read, clear |
| `tasks.py` | `/api/v2/tasks` | Background task tracking, retry, external completion callback |
| `jub.py` | `/api/v2/jub` | Bulk import via a JubFile payload |
| `services.py` | `/api/v2/services` | External service registry with SVC() DSL search |
| `workflows.py` | `/api/v2/workflows` | Workflow definitions |
| `stages.py` | `/api/v2/stages` | Workflow stage definitions |
| `patterns.py` | `/api/v2/patterns` | Workflow pattern definitions |


## Services

All v2 services live in `jubapi/services/v2/__init__.py`.

| Class | Responsibility |
|---|---|
| `ObservatoriesService` | Observatory lifecycle, catalog and product linking, view counter, reviews |
| `ProductService` | Product CRUD and catalog item tag linking |
| `CatalogService` | Catalog and catalog item management |
| `TasksService` | Task creation, completion (success or failure), progress updates, retry |
| `NotificationService` | Notification fan-out and status updates |
| `UsersProfileXService` | User profile creation and retrieval |
| `DataIngestionService` | Inserting data sources and their records |
| `DataQueryService` | Translating DSL queries into aggregation pipelines and running them |
| `GraphLinkManager` | Central manager for creating and severing all inter-entity graph edges |
| `BuildingBlockService` | Building block CRUD |
| `PatternService` | Pattern CRUD |
| `StageService` | Stage CRUD |
| `WorkflowService` | Workflow CRUD |
| `ExternalServiceService` | Service entity CRUD and SVC() DSL search |


## Repositories

All repositories live in `jubapi/repositories/v2/__init__.py` and extend `BaseRepository[T]`. The base class provides `find`, `insert`, `get_by_id`, `find_by_ids`, `find_many`, `update`, `delete`, and `count`.

| Class | Collection | Notes |
|---|---|---|
| `ObservatoriesRepository` | `observatories` | Adds `increment_views()` using MongoDB `$inc` |
| `ProductsRepository` | `products` | |
| `CatalogsRepository` | `catalogs` | |
| `CatalogItemsRepository` | `catalog_items` | |
| `CatalogItemAliasesRepository` | `catalog_item_aliases` | Adds `find_by_value()` |
| `ReviewRepository` | `observatory_reviews` | Adds `get_by_observatory()` and `get_by_user_and_observatory()` |
| `ObservatoryToProductLinkRepository` | `observatory_product_links` | Edge table between Observatory and Product |
| `ObservatoryToCatalogLinkRepository` | `observatory_catalog_links` | Edge table between Observatory and Catalog |
| `CatalogToCatalogItemLinkRepository` | `catalog_catalog_item_links` | Edge table between Catalog and CatalogItem |
| `ProductToCatalogItemLinkRepository` | `product_catalogs_item_links` | Edge table between Product and CatalogItem (tags) |
| `CatalogItemRelationshipRepository` | `catalog_item_relationships` | Peer relationship between CatalogItems |
| `CatalogItemToCatalogAliasLinkRepository` | `catalog_item_catalog_alias_links` | Edge table between CatalogItem and its aliases |
| `UserProfileXRepository` | `user_profiles` | |
| `NotificationsRepository` | `notifications` | |
| `TaskRepository` | `tasks` | Adds `get_tasks_by_user()`, `get_task_statistics()`, `update_progress()`, `add_retry_attempt()` |
| `DataSourceRepository` | `data_sources` | |
| `DataRecordsRepository` | `data_records` | |
| `BuildingBlockRepository` | `building_blocks` | |
| `PatternRepository` | `patterns` | |
| `StageRepository` | `stages` | |
| `WorkflowRepository` | `workflows` | |
| `ServiceRepository` | `services` | |


## Models

Internal domain models live in `jubapi/models/v2/__init__.py`. They are Pydantic models used inside the service and repository layers. Controllers never receive raw models directly.

All models that need timestamps extend `TimestampedModel` which adds `created_at` and `updated_at`. Models that also need a free-text description and a metadata dictionary extend `Descriptable`.

| Model | Key fields | Notes |
|---|---|---|
| `ObservatoryX` | `observatory_id`, `title`, `image_url`, `is_disabled`, `view_count` | Top-level entity that groups products and catalogs |
| `ProductX` | `product_id`, `name`, `description` | Belongs to one observatory via a link document |
| `CatalogX` | `catalog_id`, `name`, `value`, `catalog_type`, `level`, `parent_catalog_id` | Hierarchical classification tree |
| `CatalogItemX` | `catalog_item_id`, `name`, `value`, `code`, `value_type`, `parent_id` | Leaf node of a catalog, used as a tag on products and records |
| `CatalogItemAlias` | `catalog_item_alias_id`, `value` | Alternate name for a catalog item |
| `UserProfileX` | `user_id`, `username`, `email`, `role` | Local profile linked to a Xolo auth identity |
| `Notification` | `notification_id`, `user_id`, `title`, `status`, `operation`, `entity` | In-app notification |
| `TaskX` | `task_id`, `user_id`, `observatory_id`, `operation`, `current_status`, `progress_percentage`, `attempts` | Background job with full attempt history |
| `TaskAttempt` | `attempt_number`, `status`, `start_time`, `end_time`, `error_message` | Single attempt within a task, used as an audit trail |
| `Review` | `review_id`, `observatory_id`, `user_id`, `content`, `rating` | User review for an observatory, rating 1 to 5 |
| `DataSource` | `source_id`, `name`, `format` | Descriptor for an ingested data file |
| `DataRecord` | `record_id`, `source_id`, `spatial_id`, `temporal_id`, `interest_ids`, `numerical_interest_ids` | Single row of ingested data, the target of DSL queries |
| `BuildingBlock` | `building_block_id`, `name`, `command`, `image` | Reusable compute unit |
| `PatternX` | `pattern_id`, `name`, `task`, `pattern`, `workers`, `loadbalancer` | Orchestration pattern |
| `StageX` | `stage_id`, `name`, `building_block_id` | Step inside a workflow |
| `WorkflowX` | `workflow_id`, `name`, `stages` | Ordered list of stages |
| `ServiceX` | `service_id`, `name`, `owner_id`, `public`, `provider`, `workflow_id` | Named service that wraps a workflow. `provider` is one of `XELHUA`, `NEZ`, `EXTERNAL`, `OTHER` |


## DTOs

DTOs live in `jubapi/dto/v2/__init__.py`. They are the only types that cross the HTTP boundary. Services convert between internal models and DTOs. Controllers only see DTOs.

**Request DTOs**

| DTO | Used by |
|---|---|
| `SearchQueryDTO` | `POST /search` — wraps the DSL `query` string plus `limit` and `skip` |
| `ObservatorySetupDTO` | `POST /observatories/setup` |
| `CreateReviewDTO` | `POST /observatories/{id}/reviews` |
| `UpdateReviewDTO` | `PUT /observatories/{id}/reviews/{review_id}` |
| `CreateTaskDTO` | Internal — services create tasks programmatically, not exposed directly |
| `JubFile` | `POST /jub` — bulk import payload containing catalogs, observatories, and products |

**Response DTOs**

| DTO | Description |
|---|---|
| `ObservatoryXDTO` | Observatory with `view_count` |
| `ProductSimpleDTO` | Product summary |
| `ProductUploadResponseDTO` | Returns `job_id` and `product_id` after a file upload is queued |
| `CatalogXDTO` | Catalog with hierarchy metadata |
| `CatalogItemDTO` | Catalog item with its aliases |
| `ReviewDTO` | Observatory review with timestamps |
| `TaskXDTO` | Task state including current status and progress message |
| `TasksStatsDTO` | Aggregate counts: `pending`, `running`, `success`, `failed` |
| `UserProfileDTO` | User profile, returned by the `get_current_user` dependency |
| `ServiceDTO` | Service summary |
| `ServiceDetailDTO` | Service with hydrated workflow |
