# Use Cases

This page covers the most common workflows from provisioning an observatory to generating charts.

---

## Use Case 1 — Full Observatory Provisioning (Primary Workflow)

This is the end-to-end lifecycle for creating a new observable data space.
The observatory starts disabled and becomes publicly searchable only after explicit completion.

```
POST /observatories/setup         → observatory created (disabled) + task created (pending)
     │
POST /{id}/catalogs/bulk          → spatial + temporal + interest vocabularies loaded
     │
POST /{id}/products/bulk          → products registered, product_ids returned
     │
POST /products/{id}/upload        → file queued per product, job_id returned
     │                              (background: file saved to storage)
POST /datasources                 → data source registered
POST /datasources/{id}/records    → aggregated rows inserted
     │
POST /tasks/{task_id}/complete    → observatory enabled (is_disabled → false)
```

---

### Step 1 — Create the observatory (disabled)

```http
POST /api/v2/observatories/setup
Content-Type: application/json

{
  "title": "National Cancer Observatory 2024",
  "user_id": "usr_system",
  "description": "Tracks cancer incidence and mortality across Mexico.",
  "metadata": {
    "edition": "2024",
    "country": "MX",
    "institution": "CINVESTAV"
  }
}
```

**Response `201`**
```json
{
  "observatory_id": "obs_cancer_2024",
  "task_id": "tsk_abc123",
  "status": "pending",
  "message": "Observatory created (disabled). Assign catalogs and products, then POST /tasks/{task_id}/complete to enable it."
}
```

Save both `observatory_id` and `task_id` — you will need them throughout this workflow.

---

### Step 2 — Assign catalogs

Send all catalogs in one request. Each catalog is created with its full item tree
(items → aliases → children) in a single JSON document.

```http
POST /api/v2/observatories/obs_cancer_2024/catalogs/bulk
Content-Type: application/json

{
  "level": 0,
  "catalogs": [
    {
      "name": "Spatial Mexico",
      "value": "SPATIAL",
      "catalog_type": "spatial",
      "description": "Geographic hierarchy for Mexico",
      "items": [
        {
          "name": "México",
          "value": "MX",
          "code": 9,
          "value_type": "string",
          "aliases": [
            { "value": "MEX", "value_type": "string" },
            { "value": "Mexico", "value_type": "string" }
          ],
          "children": [
            {
              "name": "Aguascalientes", "value": "AGS", "code": 1,
              "value_type": "string", "aliases": [], "children": []
            },
            {
              "name": "Tamaulipas", "value": "TAM", "code": 28,
              "value_type": "string",
              "aliases": [{ "value": "Tamaulipas", "value_type": "string" }],
              "children": []
            }
          ]
        }
      ]
    },
    {
      "name": "Temporal — Annual",
      "value": "TEMPORAL",
      "catalog_type": "temporal",
      "items": [
        {
          "name": "2022", "value": "Y2022", "code": 2022,
          "value_type": "datetime", "temporal_value": "2022-01-01T00:00:00Z",
          "aliases": [], "children": []
        },
        {
          "name": "2023", "value": "Y2023", "code": 2023,
          "value_type": "datetime", "temporal_value": "2023-01-01T00:00:00Z",
          "aliases": [], "children": []
        }
      ]
    },
    {
      "name": "Cancer Types — CIE-10",
      "value": "CIE10_CANCER",
      "catalog_type": "interest",
      "items": [
        {
          "name": "Breast Cancer",   "value": "C_MAMA",    "code": 101,
          "value_type": "string", "aliases": [], "children": []
        },
        {
          "name": "Ovarian Cancer",  "value": "C_OVARIO",  "code": 102,
          "value_type": "string", "aliases": [], "children": []
        },
        {
          "name": "Cervical Cancer", "value": "C_CERVIX",  "code": 103,
          "value_type": "string", "aliases": [], "children": []
        },
        {
          "name": "Prostate Cancer", "value": "C_PROSTATA","code": 104,
          "value_type": "string", "aliases": [], "children": []
        }
      ]
    },
    {
      "name": "Sex",
      "value": "SEX",
      "catalog_type": "interest",
      "items": [
        { "name": "Female", "value": "SEX_FEMALE", "code": 2, "value_type": "string", "aliases": [], "children": [] },
        { "name": "Male",   "value": "SEX_MALE",   "code": 1, "value_type": "string", "aliases": [], "children": [] }
      ]
    }
  ]
}
```

**Response `201`**
```json
{
  "observatory_id": "obs_cancer_2024",
  "catalog_ids": ["cat_spatial_001", "cat_temporal_001", "cat_cancer_001", "cat_sex_001"]
}
```

---

### Step 3 — Assign products

```http
POST /api/v2/observatories/obs_cancer_2024/products/bulk
Content-Type: application/json

{
  "products": [
    {
      "name": "Breast Cancer Incidence 2022-2023",
      "description": "Annual incidence rates per 100,000 women by state.",
      "catalog_item_ids": []
    },
    {
      "name": "Female Cancer Mortality 2022-2023",
      "description": "Mortality rates for all female cancer types.",
      "catalog_item_ids": []
    }
  ]
}
```

**Response `201`**
```json
{
  "observatory_id": "obs_cancer_2024",
  "products": [
    { "product_id": "p_001", "name": "Breast Cancer Incidence 2022-2023" },
    { "product_id": "p_002", "name": "Female Cancer Mortality 2022-2023" }
  ]
}
```

Save the `product_id` values — you need them for file uploads.

---

### Step 4 — Upload data files

Upload one file per product. Each upload is queued and processed in the background.

```http
POST /api/v2/products/p_001/upload
Content-Type: multipart/form-data

user_id=usr_system
file=@breast_cancer_incidence_2022_2023.csv
```

**Response `202`**
```json
{
  "job_id": "tsk_upload_001",
  "product_id": "p_001",
  "status": "queued"
}
```

The file is persisted by the configured `StorageBackend` in the background.
Track progress:

```http
GET /api/v2/tasks/tsk_upload_001
```

Repeat for each product file.

---

### Step 5 — Register data source and insert records

Register the data source:

```http
POST /api/v2/datasources
Content-Type: application/json

{
  "name": "Cancer Registry 2022-2023",
  "description": "Processed CSV export from national registry",
  "format": "csv"
}
```

**Response `201`**
```json
{ "source_id": "src_cancer_2024", ... }
```

Insert the aggregated records. Each record maps catalog items to a metric value:

```http
POST /api/v2/datasources/src_cancer_2024/records
Content-Type: application/json

[
  {
    "record_id": "rec_001",
    "spatial_id": "<catalog_item_id for AGS>",
    "temporal_id": "2022-01-01T00:00:00Z",
    "interest_ids": [
      "<catalog_item_id for C_MAMA>",
      "<catalog_item_id for SEX_FEMALE>"
    ],
    "numerical_interest_ids": { "TASA_100K": 42.3, "CASOS": 1250 },
    "raw_payload": {}
  },
  {
    "record_id": "rec_002",
    "spatial_id": "<catalog_item_id for TAM>",
    "temporal_id": "2022-01-01T00:00:00Z",
    "interest_ids": [
      "<catalog_item_id for C_OVARIO>",
      "<catalog_item_id for SEX_FEMALE>"
    ],
    "numerical_interest_ids": { "TASA_100K": 18.7, "CASOS": 540 },
    "raw_payload": {}
  }
]
```

!!! tip "Finding catalog_item_ids"
    After creating catalogs in Step 2, call `GET /api/v2/catalogs/{catalog_id}` to retrieve
    the full item tree with generated `catalog_item_id` values.

---

### Step 6 — Enable the observatory

Once all catalogs, products, files, and records are in place, signal completion:

```http
POST /api/v2/tasks/tsk_abc123/complete
Content-Type: application/json

{
  "success": true,
  "message": "Provisioning complete. 2 products, 50,000 records indexed."
}
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

The observatory is now live and searchable.

---

### Handling failures

If something goes wrong during provisioning:

```http
POST /api/v2/tasks/tsk_abc123/complete
{
  "success": false,
  "message": "Failed to parse records: column TASA_100K missing in rows 120-150."
}
```

The observatory stays disabled. Fix the issue and retry:

```http
PUT /api/v2/tasks/tsk_abc123/retry
```

---

## Use Case 2 — Query Raw Data Records

Fetch `DataRecord` documents matching a DSL filter.

```http
POST /api/v2/search/records
Content-Type: application/json

{
  "query": "jub.v1.VS(TAM).VT(>= 2022 AND <= 2023).VI(SEX_FEMALE AND C_MAMA)",
  "source_id": "src_cancer_2024",
  "limit": 500
}
```

The engine resolves `TAM`, `SEX_FEMALE`, and `C_MAMA` to their `catalog_item_id` values
before running the MongoDB `$match`.

---

## Use Case 3 — Generate a Chart

Run a DSL aggregation and get an ECharts-ready JSON object.

```http
POST /api/v2/search/plot
Content-Type: application/json

{
  "query": "jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO OR C_CERVIX OR C_PROSTATA).VO(AVG(TASA_100K)).BY(CIE10_CANCER)",
  "source_id": "src_cancer_2024",
  "chart_type": "bar"
}
```

**Response**
```json
{
  "xAxis":  { "type": "category", "data": ["Breast Cancer", "Cervical Cancer", "Ovarian Cancer", "Prostate Cancer"] },
  "yAxis":  { "type": "value" },
  "legend": { "data": ["Total"] },
  "series": [{
    "name": "Total",
    "type": "bar",
    "data": [42.3, 28.1, 18.7, 35.6],
    "smooth": false
  }],
  "tooltip": { "trigger": "axis" }
}
```

Drop this response directly into Vue-ECharts or Apache ECharts.

---

## Use Case 4 — Search Products by DSL

Discover which products match a combination of dimensions.

```http
POST /api/v2/search
Content-Type: application/json

{
  "query": "jub.v1.VS(MX.TAM).VT(>= 2022).VI(SEX_FEMALE AND C_MAMA)",
  "observatory_id": "obs_cancer_2024",
  "limit": 20
}
```

Returns a list of `ProductXDTO` objects with resolved spatial, temporal, and interest
variable metadata.

---

## Use Case 5 — Temporal trend (line chart)

```http
POST /api/v2/search/plot
{
  "query": "jub.v1.VS(MX).VI(C_MAMA).VO(AVG(TASA_100K)).BY(TEMPORAL)",
  "source_id": "src_cancer_2024",
  "chart_type": "line"
}
```

Groups results by year, producing one point per year on the x-axis.

---

## Use Case 6 — Spatial distribution

```http
POST /api/v2/search/plot
{
  "query": "jub.v1.VI(C_MAMA).VT(2023).VO(AVG(TASA_100K)).BY(SPATIAL)",
  "source_id": "src_cancer_2024",
  "chart_type": "bar"
}
```

Groups results by state, producing one bar per state.

---

## Use Case 7 — Retry a failed upload

```http
# 1. Check what failed
GET /api/v2/tasks/tsk_upload_001

# 2. Retry
PUT /api/v2/tasks/tsk_upload_001/retry
```

---

## Use Case 8 — Re-query a data source directly

```http
POST /api/v2/datasources/src_cancer_2024/query
{
  "query": "jub.v1.VS(AGS).VT(2023)",
  "limit": 100
}
```

Returns records scoped to `src_cancer_2024` matching the DSL filter.
