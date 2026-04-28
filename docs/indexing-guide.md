# Indexing Guide

Guide for indexing observatories, products, catalogs, data sources, and services using the **JUB Python client**.

---

## Client setup

```python
import asyncio
from jub.client.v2 import JubClient, JubClientBuilder
import jub.dto.v2 as DTO

async def main():
    result = await JubClientBuilder(
        api_url  = "http://localhost:5000",
        username = "admin",
        password = "secret",
    ).build()

    if result.is_err:
        raise result.unwrap_err()

    client: JubClient = result.unwrap()
    # client.user_id is set automatically after authentication
```

Every method returns `Result[T, Exception]`. Check `.is_ok` / `.is_err` and call `.unwrap()` to get the value.

**What happens under the hood:**
`POST /api/v2/users/auth` — exchanges credentials for a JWT. The token and `Temporal-Secret-Key` are attached to every subsequent request automatically.

---

## Use Case 1 — Set up an observatory with catalogs and products

Observatories are created in **disabled** state. The setup flow is:
1. Create the observatory → get a `task_id`
2. Bulk-create and link catalogs
3. Bulk-create and link products
4. Complete the task → observatory becomes active

```python
async def setup_observatory(client: JubClient) -> str:

    # Step 1 — create the observatory (disabled until task is completed)
    # POST /api/v2/observatories/setup
    result = await client.setup_observatory(DTO.ObservatorySetupDTO(
        observatory_id = "obs_cancer_mx",
        title          = "Cancer Observatory — Mexico",
        description    = "Epidemiological surveillance of cancer incidence.",
        metadata       = {"source": "INCAN", "country": "MX"},
    ))
    setup = result.unwrap()
    obs_id  = setup.observatory_id  # "obs_cancer_mx"
    task_id = setup.task_id

    # Step 2 — bulk-create catalogs and link them to the observatory
    # POST /api/v2/observatories/{obs_id}/catalogs/bulk
    result = await client.bulk_assign_catalogs(obs_id, DTO.BulkCatalogsDTO(
        catalogs=[
            DTO.CatalogCreateDTO(
                name         = "Spatial — Mexico",
                value        = "SPATIAL_MX",
                catalog_type = "SPATIAL",
                items=[
                    DTO.CatalogItemCreateDTO(
                        name="Mexico", value="MX", code=0, value_type="STRING",
                        children=[
                            DTO.CatalogItemCreateDTO(
                                name="Ciudad de Mexico", value="CDMX", code=9, value_type="STRING",
                                aliases=[DTO.CatalogItemAliasCreateDTO(value="09", value_type="STRING")],
                            ),
                        ],
                    )
                ],
            ),
            DTO.CatalogCreateDTO(
                name         = "CIE-10 Cancer Groups",
                value        = "CIE10_CANCER",
                catalog_type = "INTEREST",
                items=[
                    DTO.CatalogItemCreateDTO(name="Breast", value="C_MAMA",   code=6, value_type="STRING"),
                    DTO.CatalogItemCreateDTO(name="Ovary",  value="C_OVARIO", code=9, value_type="STRING"),
                ],
            ),
        ]
    ))
    catalog_ids = result.unwrap().catalog_ids  # ["cat_abc", "cat_xyz"]

    # Fetch catalog items to use as product tags
    cat_detail = (await client.get_catalog(catalog_ids[1])).unwrap()
    item_ids   = [item.catalog_item_id for item in cat_detail.items]

    # Step 3 — bulk-create products and link them to the observatory
    # POST /api/v2/observatories/{obs_id}/products/bulk
    result = await client.bulk_assign_products(obs_id, DTO.BulkProductsDTO(
        products=[
            DTO.BulkProductItemDTO(
                product_id       = "prod_cancer_by_state",
                name             = "Cancer mortality by state",
                description      = "Oncological mortality rates per 100k by state.",
                catalog_item_ids = item_ids,
            ),
        ]
    ))
    print(f"Products created: {[p.product_id for p in result.unwrap().products]}")

    # Step 4 — complete the setup task → enables the observatory
    # POST /api/v2/tasks/{task_id}/complete
    done = (await client.complete_task(task_id, DTO.TaskCompleteDTO(
        success = True,
        message = "Initial setup done.",
    ))).unwrap()
    print(f"Observatory enabled: {done.observatory_enabled}")  # True

    return obs_id
```



---

## Use Case 2 — Create catalogs in bulk

Catalogs can be created independently (not tied to an observatory setup) and linked later.

```python
async def create_catalogs(client: JubClient) -> list[str]:

    # Create multiple catalogs in one call
    # POST /api/v2/catalogs/bulk
    result = await client.create_bulk_catalogs_from_json(data=[
        {
            "name": "Biological sex", "value": "SEX", "catalog_type": "INTEREST",
            "items": [
                {"name": "Female", "value": "MUJER",  "code": 2, "value_type": "STRING"},
                {"name": "Male",   "value": "HOMBRE", "code": 1, "value_type": "STRING"},
            ],
        },
        {
            "name": "Report years", "value": "TEMPORAL_ANIOS", "catalog_type": "TEMPORAL",
            "items": [
                {"name": "2022", "value": "Y2022", "code": 2022, "value_type": "DATETIME",
                 "temporal_value": "2022-01-01T00:00:00Z"},
                {"name": "2023", "value": "Y2023", "code": 2023, "value_type": "DATETIME",
                 "temporal_value": "2023-01-01T00:00:00Z"},
            ],
        },
    ])
    catalog_ids = result.unwrap().catalog_ids
    print(f"Created catalogs: {catalog_ids}")

    # Optionally link them to an existing observatory
    # POST /api/v2/observatories/{obs_id}/catalogs
    for cat_id in catalog_ids:
        await client.link_catalog_to_observatory("obs_cancer_mx", DTO.LinkCatalogDTO(catalog_id=cat_id))

    return catalog_ids
```

You can also load from a file:

```python
result = await client.create_bulk_catalogs_from_json(json_path="data/catalogs.json")
```
---

## Use Case 3 — Create a product and upload a file

Use this when adding products to an **existing** observatory, or when you need to attach a chart or report file to a product.

```python
async def create_product_with_upload(client: JubClient, obs_id: str, item_ids: list[str]) -> str:

    # Create a standalone product linked to the observatory
    # POST /api/v2/products
    result = await client.create_product(DTO.ProductCreateDTO(
        product_id       = "prod_cancer_sexo_edad",
        name             = "Cancer by sex and age group",
        description      = "Distribution by sex and age cohort.",
        observatory_id   = obs_id,
        catalog_item_ids = item_ids,
    ))
    product_id = result.unwrap().product_id

    # Add more tags later if needed
    # POST /api/v2/products/{product_id}/tags
    await client.add_product_tags(product_id, DTO.TagProductDTO(
        catalog_item_ids = item_ids[:3],
    ))

    # Upload a chart file for this product
    # POST /api/v2/products/{product_id}/upload  (multipart/form-data)
    upload = (await client.upload_product(product_id, "source/heatmap.html")).unwrap()
    print(f"Upload job: {upload['job_id']}")

    # Poll until the upload job finishes
    while True:
        task = (await client.get_task(upload["job_id"])).unwrap()
        if task.current_status in ("SUCCESS", "FAILED"):
            print(f"Upload {task.current_status}: {task.progress_message}")
            break
        await asyncio.sleep(2)

    return product_id
```
---

## Use Case 4 — Create services, workflows, stages, patterns, and building blocks

Use the one-shot `index_service` to create the full tree in one request, or build each layer individually.

### Option A — One-shot (recommended)

```python
async def index_service_oneshot(client: JubClient) -> str:

    # POST /api/v2/services/index
    # Creates BB → Pattern → Stage → Workflow → Service atomically
    result = await client.index_service(DTO.ServiceIndexDTO(
        name        = "cancer-ingest-svc",
        owner_id    = client.user_id,
        description = "Ingests cancer mortality records.",
        public      = True,
        workflow    = DTO.WorkflowInlineDTO(
            name   = "Cancer ingestion workflow",
            stages = [
                DTO.StageInlineDTO(
                    name     = "Ingest CSV",
                    source   = "s3://my-bucket/cancer.csv",
                    sink     = "jub://datasources/ds_cancer_mx",
                    endpoint = "http://ingestor-svc/run",
                    transformation = DTO.PatternInlineDTO(
                        name    = "CSV pipeline",
                        task    = "ingest",
                        pattern = "pipeline",
                        workers = 2,
                        building_block = DTO.BuildingBlockInlineDTO(
                            name    = "CSV ingestor",
                            command = "python ingest.py",
                            image   = "registry.example.com/ingestor:latest",
                        ),
                    ),
                ),
            ],
        ),
    ))
    resp = result.unwrap()
    print(f"service={resp.service_id}  workflow={resp.workflow_id}  stages={resp.stage_ids}")
    return resp.service_id
```

### Option B — Step by step

```python
async def index_service_stepbystep(client: JubClient) -> str:

    # POST /api/v2/building-blocks
    bb = (await client.create_building_block(DTO.BuildingBlockCreateDTO(
        name="CSV ingestor", command="python ingest.py",
        image="registry.example.com/ingestor:latest",
    ))).unwrap()

    # POST /api/v2/patterns
    pattern = (await client.create_pattern(DTO.PatternCreateDTO(
        name="CSV pipeline", task="ingest", pattern="pipeline",
        workers=2, building_block_id=bb["building_block_id"],
    ))).unwrap()

    # POST /api/v2/stages
    stage = (await client.create_stage(DTO.StageCreateDTO(
        name="Ingest CSV",
        source="s3://my-bucket/cancer.csv",
        sink="jub://datasources/ds_cancer_mx",
        endpoint="http://ingestor-svc/run",
        transformation_id=pattern["pattern_id"],
    ))).unwrap()

    # POST /api/v2/workflows
    workflow = (await client.create_workflow(DTO.WorkflowCreateDTO(
        name="Cancer ingestion workflow",
        stage_ids=[stage["stage_id"]],
    ))).unwrap()

    # POST /api/v2/services
    service = (await client.create_service(DTO.ServiceCreateDTO(
        name="cancer-ingest-svc", owner_id=client.user_id,
        description="Ingests cancer mortality records.",
        public=True, workflow_id=workflow["workflow_id"],
    ))).unwrap()

    return service["service_id"]
```

Query services with the DSL:

```python
# POST /api/v2/search/services
result = await client.search_service(DTO.SearchQueryDTO(query="jub.v1.SVC(name=cancer,public=true)"))
```

---

## Use Case 5 — Register a data source and ingest records

```python
async def datasource_and_records(client: JubClient) -> str:

    # Register the data source
    # POST /api/v2/datasources
    ds = (await client.register_data_source(DTO.DataSourceCreateDTO(
        name           = "Cancer mortality records",
        description    = "Row-level data by state, year, sex, and CIE-10.",
        format         = "csv",
        connection_uri = "s3://my-bucket/cancer/mortality.csv",
    ))).unwrap()
    source_id = ds.source_id

    # Ingest records (batch; repeat for large datasets)
    # POST /api/v2/datasources/{source_id}/records
    result = await client.ingest_records(source_id, [
        DTO.DataRecordCreateDTO(
            record_id               = "rec_cdmx_2022_mujer_mama",   # deterministic → idempotent
            spatial_id              = "<catalog_item_id:CDMX>",
            temporal_id             = "2022-01-01T00:00:00Z",
            interest_ids            = ["<item_id:MUJER>", "<item_id:C_MAMA>"],
            numerical_interest_ids  = {"TASA_100K": 18.4},
            raw_payload             = {"estado": "CDMX", "anio": 2022},
        ),
    ])
    print(f"Inserted: {result.unwrap()['inserted']} records")

    # Query records with the DSL
    # POST /api/v2/datasources/{source_id}/query
    records = (await client.query_records(source_id, DTO.DataSourceQueryDTO(
        query = "jub.v1.VS(CDMX).VT(>= 2020).VI(C_MAMA)",
        limit = 50,
    ))).unwrap()
    print(f"Records returned: {len(records)}")

    # Aggregated plot (ECharts JSON)
    # POST /api/v2/search/plot
    plot = (await client.generate_plot(DTO.PlotQueryDTO(
        query      = "jub.v1.VS(MX).VI(C_MAMA OR C_OVARIO).VO(AVG(TASA_100K)).BY(CIE10_CANCER)",
        chart_type = "bar",
    ))).unwrap()
    print("ECharts config keys:", list(plot.keys()))

    return source_id
```

---

## DSL quick reference

| Prefix | Purpose | Example |
|--------|---------|---------|
| `VS`   | Spatial filter  | `VS(CDMX)` |
| `VT`   | Temporal filter | `VT(>= 2020)` |
| `VI`   | Interest filter | `VI(C_MAMA AND MUJER)` |
| `VO`   | Metric / aggregation | `VO(AVG(TASA_100K))` |
| `BY`   | Group-by | `BY(CIE10_CANCER)` |
| `SVC`  | Service search  | `SVC(name=cancer,public=true)` |
