# Configuration

JUB API is configured entirely with environment variables. On startup,
`jubapi/config/__init__.py` loads the file pointed to by `JUB_ENV_FILE_PATH`
(default `.env`) and then reads the variables below. Values in that file override
variables already set in the shell.

The repository ships three env files:

| File | Used by |
|---|---|
| `.env` | `./run_local.sh` (local uvicorn) |
| `.env.dev` | `docker-compose.yml` |
| `.env.test` | The test suite (`tests/conftest.py` sets `JUB_ENV_FILE_PATH=.env.test` unless it is already set) |

---

## Application variables

These are read by the API process itself.

### Core

| Variable | Default | Description |
|---|---|---|
| `JUB_ENV_FILE_PATH` | `.env` | Path to the env file to load |
| `JUB_MONGODB_URI` | `mongodb://localhost:27017/jub` | MongoDB connection string |
| `JUB_MONGODB_DATABASE_NAME` | `jub` | Database name |
| `JUB_ROOT_PATH` | `""` | FastAPI root path, used when running behind a reverse proxy |

### Authentication (Xolo)

| Variable | Default | Description |
|---|---|---|
| `JUB_XOLO_API_URL` | `http://localhost:10000/api/v4` | Xolo auth service base URL |
| `JUB_XOLO_SECRET` | `secret` | Shared secret for Xolo token validation. Always override it outside local development |

### Logging

| Variable | Default | Description |
|---|---|---|
| `JUB_LOG_DEBUG` | `1` | `1` enables console logging, `0` disables it |
| `JUB_LOG_NAME` | `jubapi` | Logger name |
| `JUB_LOG_PATH` | `/log` | Directory where log files are written |

### CORS

All list values are comma-separated.

| Variable | Default | Description |
|---|---|---|
| `JUB_CORS_ORIGINS` | `http://localhost:3100,https://jub.tamps.cinvestav.mx` | Allowed origins |
| `JUB_CORS_METHODS` | `*` | Allowed HTTP methods |
| `JUB_CORS_HEADERS` | `*` | Allowed headers |
| `JUB_CORS_CREDENTIALS` | `True` | Allow credentials (`true`/`1` enable it, anything else disables it) |

### OpenAPI

| Variable | Default | Description |
|---|---|---|
| `JUB_OPENAPI_TITLE` | `OCA - API` | Title shown in the OpenAPI docs |
| `JUB_OPENAPI_VERSION` | `0.0.1` | Version shown in the OpenAPI docs |
| `JUB_OPENAPI_SUMMARY` | `This API enable the manipulation of observatories and catalogs` | Summary shown in the OpenAPI docs |
| `JUB_OPENAPI_DESCRIPTION` | `""` | Description shown in the OpenAPI docs |
| `JUB_OPENAPI_LOGO` | `https://i.ibb.co/9vSnz09/android-chrome-192x192.png` | Logo URL shown in the OpenAPI docs |

### Storage

See [Storage](storage.md) for how each backend behaves.

| Variable | Default | Description |
|---|---|---|
| `JUB_STORAGE_BACKEND` | `FS` | `FS`, `MEMORY` or `MICTLANX` (case-insensitive) |
| `JUB_STORAGE_PATH` | `/jub` | Base directory for the `FS` backend; files go to `<path>/products/...` |
| `JUB_STORAGE_CACHE_MAX_BYTES` | `4294967296` (4 GB) | Read cache size for the `FS` and `MICTLANX` backends |
| `JUB_STORAGE_CACHE_TTL` | `300` | Read cache TTL in seconds |
| `JUB_MICTLANX_URI` | `""` | MictlanX router URI. Required when `JUB_STORAGE_BACKEND=MICTLANX` |
| `JUB_MICTLANX_BUCKET_ID` | `jub` | MictlanX bucket where files are stored |
| `JUB_MICTLANX_CLIENT_ID` | `jubapi` | Client id used in MictlanX logs |

### Search cache

| Variable | Default | Description |
|---|---|---|
| `JUB_SEARCH_PRODUCT_CACHE_TTL` | `60` | TTL in seconds of the product search cache |
| `JUB_SEARCH_OBSERVATORY_CACHE_TTL` | `120` | TTL in seconds of the observatory search cache |

### Orphan check

A background job that looks for stored product files whose product no longer exists.

| Variable | Default | Description |
|---|---|---|
| `JUB_ORPHAN_CHECK_ENABLED` | `0` | `1` runs the job periodically |
| `JUB_ORPHAN_CHECK_INTERVAL_SECONDS` | `3600` | Seconds between runs |
| `JUB_ORPHAN_CHECK_DELETE` | `0` | `1` deletes orphaned files, `0` only reports them |

---

## Deployment variables

These are read by `run_local.sh` and the compose files, not by the Python code.

| Variable | Default | Used in | Description |
|---|---|---|---|
| `JUB_HOST` | `0.0.0.0` | `run_local.sh`, `docker-compose.yml`, `jub.prod.yml` | Uvicorn bind host |
| `JUB_PORT` | `5000` | `run_local.sh`, `docker-compose.yml`, `jub.prod.yml` | Uvicorn bind port (also the published container port) |
| `JUB_RELOAD` | unset | `docker-compose.yml` | When set (even empty), uvicorn runs with `--reload` |
| `JUB_MONGODB_HOST_PORT` | `27027` | `docker-compose.yml` | Host port mapped to the MongoDB container |
| `JUB_DOCKERFILE` | `Dockerfile` | `docker-compose.yml` | Dockerfile used to build the API image |
| `JUB_IMAGE_NAME` | `jub:api-0.0.1a0` | `docker-compose.yml` | API image name (`build.sh` takes it as its first argument, default `jubapi:latest`) |
| `JUB_UI_IMAGE` | `nachocode/jub:ui-0.1.0a5` | `docker-compose.yml` | Jub UI image |
| `JUB_UI_LOCAL_PORT` | `3000` | `docker-compose.yml` | Host port for the Jub UI |
