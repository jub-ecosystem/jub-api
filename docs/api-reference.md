# API Reference

Base URL: `/api/v2`

Interactive documentation: `/docs` (Swagger UI when server is running)

---

## Authentication

Most endpoints require a Bearer token obtained via `POST /users/auth`.
Machine-to-machine endpoints (marked **no auth**) do not require a token.

```http
Authorization: Bearer <access_token>
Temporal-Secret-Key: <temporal_secret_key>
```

---

## Error responses

All errors use the same envelope:

```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|---|---|
| `400` | Request payload validation failed |
| `401` | Missing or invalid token |
| `403` | Authenticated but not permitted |
| `404` | Resource not found |
| `409` | Resource already exists |
| `500` | Unexpected server error |

---

## Observatories — `/observatories`

### `POST /observatories/setup` — **no auth** — Create disabled observatory + pending task

Creates an observatory with `is_disabled: true` and a `SETUP` task in `PENDING` state.
Call `POST /tasks/{task_id}/complete` to enable the observatory after provisioning.

**Request body**
```json
{
  "title": "Cancer Observatory 2024",
  "user_id": "usr_system",
  "description": "National cancer incidence data for Mexico.",
  "observatory_id": "obs_cancer_2024",
  "metadata": { "edition": "2024" }
}
```

**Response `201`**
```json
{
  "observatory_id": "obs_cancer_2024",
  "task_id": "tsk_abc123",
  "status": "pending",
  "message": "Observatory created (disabled). ..."
}
```

---

### `POST /observatories/{id}/catalogs/bulk` — Assign N nested catalogs

Creates all catalogs (with items, aliases, and hierarchy) and links them to the observatory.
See [Use Cases — Step 2](use-cases.md#step-2-assign-catalogs) for the full JSON shape.

**Response `201`**
```json
{ "observatory_id": "obs_cancer_2024", "catalog_ids": ["cat_001", "cat_002"] }
```

---

### `POST /observatories/{id}/products/bulk` — Assign N products

Creates products and links them to the observatory and catalog-item tags.

**Request body**
```json
{
  "products": [
    {
      "name": "Breast Cancer Incidence 2024",
      "description": "Annual rates by state",
      "catalog_item_ids": ["itm_abc", "itm_def"]
    }
  ]
}
```

**Response `201`**
```json
{
  "observatory_id": "obs_cancer_2024",
  "products": [{ "product_id": "p_001", "name": "Breast Cancer Incidence 2024" }]
}
```

---

### `POST /observatories` — Create enabled observatory

Creates an immediately active observatory. Use `/setup` for the full provisioning workflow.

### `GET /observatories` — List observatories

### `GET /observatories/{id}` — Get observatory

### `PUT /observatories/{id}` — Update observatory

Partial update: `title`, `description`, `image_url`, `metadata`.

### `DELETE /observatories/{id}` — Delete observatory

Deletes the observatory and all its catalog/product links (cascade).

### `GET /observatories/{id}/catalogs` — List linked catalogs

### `POST /observatories/{id}/catalogs` — Link an existing catalog

```json
{ "catalog_id": "cat_001", "level": 0 }
```

### `DELETE /observatories/{id}/catalogs/{catalog_id}` — Unlink catalog

### `GET /observatories/{id}/products` — List linked products

---

## Products — `/products`

### `POST /products/{id}/upload` — **no auth** — Queue file for background ingestion

**Content-Type:** `multipart/form-data`

| Form field | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | ✓ | User requesting the upload |
| `file` | binary | ✓ | Data file to ingest |

**Response `202`**
```json
{ "job_id": "tsk_upload_001", "product_id": "p_001", "status": "queued" }
```

The file is persisted via the `StorageBackend` in a background task.
Key format: `products/{product_id}/{job_id}/{filename}`.
Poll `GET /tasks/{job_id}` for status.

---

### `POST /products` — Create one product

### `GET /products` — List products

### `GET /products/{id}` — Get product

### `PUT /products/{id}` — Update name / description

### `DELETE /products/{id}` — Delete product

### `GET /products/{id}/tags` — List catalog-item tags

### `POST /products/{id}/tags` — Add tags

```json
{ "catalog_item_ids": ["itm_abc", "itm_def"] }
```

### `DELETE /products/{id}/tags/{catalog_item_id}` — Remove tag

---

## Catalogs — `/catalogs`

### `POST /catalogs/bulk` — Create one catalog with full item tree

Accepts `CatalogCreateDTO` with nested items, aliases, and children.

### `GET /catalogs` — List all catalogs (summary)

### `GET /catalogs/{id}` — Get full catalog tree

Returns catalog with all items, aliases, and hierarchical children fully hydrated.

### `DELETE /catalogs/{id}` — Delete catalog

---

## Catalog Items — `/catalog-items`

### `POST /catalog-items` — Create standalone catalog item

### `GET /catalog-items/{id}` — Get catalog item

### `PUT /catalog-items/{id}` — Update catalog item

### `DELETE /catalog-items/{id}` — Delete catalog item

### `POST /catalog-items/{id}/aliases` — Add alias

### `DELETE /catalog-items/{id}/aliases/{alias_id}` — Remove alias

### `POST /catalog-items/{id}/link` — Link item to a catalog

### `POST /catalog-items/{id}/children` — Add child item (hierarchy)

---

## Search — `/search`

### `POST /search` — Search products by DSL

Returns hydrated `ProductXDTO` list with spatial/temporal/interest variable metadata.

```json
{
  "query": "jub.v1.VS(MX).VT(>= 2020).VI(SEX_FEMALE AND C_MAMA)",
  "observatory_id": "obs_cancer_2024",
  "limit": 20,
  "skip": 0
}
```

---

### `POST /search/records` — Fetch raw data records by DSL

Resolves VS/VI identifiers to `catalog_item_id` values and returns matching `DataRecord`
documents.

```json
{
  "query": "jub.v1.VS(TAM).VT(2023).VI(C_MAMA)",
  "source_id": "src_cancer_2024",
  "limit": 100
}
```

---

### `POST /search/plot` — Generate ECharts plot data

Runs a full DSL aggregation and returns an ECharts-ready JSON object. Axis labels show
catalog item `name` values, not raw IDs.

```json
{
  "query": "jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO).VO(AVG(TASA_100K)).BY(CIE10_CANCER)",
  "source_id": "src_cancer_2024",
  "chart_type": "bar"
}
```

**Response**
```json
{
  "xAxis":  { "type": "category", "data": ["Breast Cancer", "Ovarian Cancer"] },
  "yAxis":  { "type": "value" },
  "legend": { "data": ["Total"] },
  "series": [{ "name": "Total", "type": "bar", "data": [42.3, 18.7], "smooth": false }],
  "tooltip": { "trigger": "axis" }
}
```

### `POST /search/observatories` — Search observatories by DSL

---

## Data Sources — `/datasources`

### `POST /datasources` — Register data source

```json
{
  "name": "Cancer Registry 2024",
  "description": "CSV export from national registry",
  "format": "csv"
}
```

### `GET /datasources` — List data sources

### `GET /datasources/{id}` — Get data source

### `DELETE /datasources/{id}` — Delete source and all its records

### `POST /datasources/{id}/records` — Bulk-insert data records

Array of `DataRecordCreateDTO`. Each record's `spatial_id` and `interest_ids` must be
valid `catalog_item_id` values already present in the catalogs.

### `POST /datasources/{id}/query` — DSL query scoped to this source

---

## Tasks — `/tasks`

### `POST /tasks/{id}/complete` — **no auth** — Mark task complete or failed

Called by external systems (indexers, provisioners) when their job is done.
If `success: true`, the associated observatory is automatically enabled.

```json
{ "success": true, "message": "Indexed 42,000 records." }
```

**Response `200`**
```json
{
  "task_id": "tsk_abc123",
  "status": "success",
  "observatory_id": "obs_cancer_2024",
  "observatory_enabled": true
}
```

---

### `GET /tasks` — List my tasks (auth required)

### `GET /tasks/{id}` — Task detail with attempt history (auth required)

### `GET /tasks/stats` — Task counts by status (auth required)

### `PUT /tasks/{id}/retry` — Retry a failed task (auth required)

---

## Users — `/users`

### `POST /users/signup` — Register a new user

### `POST /users/auth` — Login (returns `access_token`)

### `GET /users/me` — Get current user profile (auth required)

### `PUT /users/me/settings` — Update user preferences (auth required)
