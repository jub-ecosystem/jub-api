# Getting Started

This guide walks you through running JUB API locally from scratch.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| Poetry | ≥ 1.6 |
| Docker & Docker Compose | Any recent version |
| MongoDB | Provided via Docker |

---

## Step 1 — Start the dependencies

JUB API relies on **MongoDB** for persistence and **Xolo** for authentication.
Both are started with a single command from the project root:

```bash
# Starts MongoDB (docker-compose.yml) + Xolo auth service (xolo.yml)
./run_local.sh
```

If you prefer to start them separately:

```bash
# MongoDB only
docker compose -f docker-compose.yml up -d

# Xolo auth service
docker compose -f xolo.yml up -d
```

MongoDB will be available at `mongodb://localhost:27027/`.

---

## Step 2 — Install Python dependencies

```bash
pip install poetry
poetry self add poetry-plugin-shell   # enables ‘poetry shell’

poetry install     # install all project dependencies
poetry lock        # update the lock file if needed
poetry shell       # activate the virtual environment
```

---

## Step 3 — Configure environment

The server loads its configuration from the file pointed to by `JUB_ENV_FILE_PATH`
(defaults to `.env`).  Copy the provided template and fill in the values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Description | Default |
|---|---|---|
| `JUB_MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27027/jub` |
| `JUB_MONGODB_DATABASE_NAME` | Database name | `jub` |
| `JUB_XOLO_API_URL` | Xolo auth service URL | `http://localhost:3000` |
| `JUB_XOLO_SECRET` | Shared secret for Xolo | — |
| `JUB_LOG_DEBUG` | Enable verbose logging (`1` / `0`) | `0` |
| `JUB_ROOT_PATH` | FastAPI root path for reverse proxies | `""` |

For tests a separate `.env.test` file is used, which points to `jub_test` database
on port `27027`.

---

## Step 4 — Run the development server

```bash
./run_local.sh
```

Or directly with uvicorn:

```bash
uvicorn jubapi.server:app --host 0.0.0.0 --port 5000 --reload
```

The API will be available at `http://localhost:5000`.
Interactive Swagger documentation is at `http://localhost:5000/docs`.

---

## Step 5 — Run tests

```bash
# All tests
pytest tests/ -s -vvvv

# Single test file
pytest tests/test_search_service.py -s -vvvv

# With coverage report
coverage run -m pytest tests/ -s -vvvv && coverage report -m
```

!!! note
    Tests require MongoDB running at `mongodb://localhost:27027/jub_test`.
    The `./run_local.sh` script starts it automatically.

---

## Step 6 — Browse the docs locally

```bash
mkdocs serve
```

Documentation will be served at `http://localhost:8000`.

---

## First request

Once the server is running, verify it is healthy:

```bash
curl http://localhost:5000/api/v2/observatories
# → []
```

Then follow the [Use Cases guide](use-cases.md) to create your first observatory.
