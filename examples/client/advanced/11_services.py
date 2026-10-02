"""
11 — Services
=============

A service describes a processing pipeline that feeds an observatory:

    Service → Workflow → Stage(s) → Pattern → Building block
                          source → transformation → sink    (container image + command)

Two ways to create one:

    A. index_service()   the whole tree in one request. Each level can be defined
                         inline (created) or referenced by id (reused).
    B. step by step      create_building_block → create_pattern → create_stage
                         → create_workflow → create_service. Use it to reuse
                         existing pieces or inspect each result.

Then:

    link_service_to_observatory()   show it on an observatory
    list_observatory_services()
    search_services()               SVC() DSL: SVC(*), SVC(name=x), SVC(public=true),
                                    SVC(owner=<user_id>), combined with commas

Run:
    python examples/client/advanced/11_services.py
"""

import asyncio

import jub.dto.v2 as DTO
import jub.enums as ENUM

from _common import SUFFIX, build_client, require, save_state, unwrap


async def index_service_oneshot(client, suffix: str) -> str:
    """A. Two-stage ingestion pipeline created in a single call."""
    resp = unwrap(
        await client.index_service(DTO.ServiceIndexDTO(
            name        = f"sinave-ingest-{suffix}",
            owner_id    = client.user_id,
            description = "Descarga, valida e ingesta los certificados de defuncion del SINAVE.",
            public      = True,
            provider    = ENUM.ServiceProviderEnum.NEZ,
            workflow    = DTO.WorkflowInlineDTO(
                name   = f"SINAVE Ingestion Workflow {suffix}",
                stages = [
                    DTO.StageInlineDTO(
                        name     = f"Fetch and Validate {suffix}",
                        source   = "s3://sinave/defunciones/latest.csv",
                        sink     = "jub://staging/defunciones_validadas",
                        endpoint = "http://validator-svc/run",
                        transformation = DTO.PatternInlineDTO(
                            name    = f"CSV Validator Pattern {suffix}",
                            task    = "validate",
                            pattern = "pipeline",
                            workers = 1,
                            building_block = DTO.BuildingBlockInlineDTO(
                                name        = f"CSV Validator {suffix}",
                                command     = "python validate.py --strict",
                                image       = "registry.example.com/csv-validator:latest",
                                description = "Valida el esquema del CSV y descarta filas invalidas.",
                            ),
                        ),
                    ),
                    DTO.StageInlineDTO(
                        name     = f"Ingest Records {suffix}",
                        source   = "jub://staging/defunciones_validadas",
                        sink     = f"jub://datasources/{require('source_id', '10_datasource.py')}",
                        endpoint = "http://ingestor-svc/run",
                        transformation = DTO.PatternInlineDTO(
                            name         = f"Record Ingest Pattern {suffix}",
                            task         = "ingest",
                            pattern      = "pipeline",
                            workers      = 2,
                            loadbalancer = "round-robin",
                            building_block = DTO.BuildingBlockInlineDTO(
                                name        = f"Record Ingestor {suffix}",
                                command     = "python ingest.py --source defunciones_validadas",
                                image       = "registry.example.com/ingestor:latest",
                                description = "Convierte filas en DataRecordCreateDTO y las envia a la API.",
                            ),
                        ),
                    ),
                ],
            ),
        )),
        "index service",
    )
    print("✓ [index_service] one request")
    print(f"  service         {resp.service_id}")
    print(f"  workflow        {resp.workflow_id}")
    print(f"  stages          {resp.stage_ids}")
    print(f"  patterns        {resp.pattern_ids}")
    print(f"  building blocks {resp.building_block_ids}")
    return resp.service_id


async def create_service_step_by_step(client, suffix: str) -> str:
    """B. A one-stage chart renderer, built layer by layer."""
    bb = unwrap(await client.create_building_block(DTO.BuildingBlockCreateDTO(
        name        = f"Chart Renderer {suffix}",
        command     = "python render.py --format html",
        image       = "registry.example.com/chart-renderer:latest",
        description = "Genera los mapas de calor y radares de los productos.",
    )), "create building block")

    pattern = unwrap(await client.create_pattern(DTO.PatternCreateDTO(
        name              = f"Chart Render Pattern {suffix}",
        task              = "render",
        pattern           = "pipeline",
        workers           = 1,
        building_block_id = bb.building_block_id,
        description       = "Un worker por grafica.",
    )), "create pattern")

    stage = unwrap(await client.create_stage(DTO.StageCreateDTO(
        name              = f"Render Charts {suffix}",
        source            = f"jub://datasources/{require('source_id', '10_datasource.py')}",
        sink              = "jub://products",
        endpoint          = "http://renderer-svc/run",
        transformation_id = pattern.pattern_id,
    )), "create stage")

    workflow = unwrap(await client.create_workflow(DTO.WorkflowCreateDTO(
        name      = f"Chart Rendering Workflow {suffix}",
        stage_ids = [stage.stage_id],
    )), "create workflow")

    service = unwrap(await client.create_service(DTO.ServiceCreateDTO(
        name        = f"chart-renderer-{suffix}",
        owner_id    = client.user_id,
        description = "Regenera las graficas de los productos a partir de los registros.",
        public      = False,
        workflow_id = workflow.workflow_id,
        provider    = ENUM.ServiceProviderEnum.XELHUA,
    )), "create service")

    print("✓ [step by step]")
    print(f"  building block  {bb.building_block_id}")
    print(f"  pattern         {pattern.pattern_id}")
    print(f"  stage           {stage.stage_id}")
    print(f"  workflow        {workflow.workflow_id}")
    print(f"  service         {service.service_id}")
    return service.service_id


async def main() -> None:
    client = await build_client()
    obs_id = require("observatory_id", "04_observatories.py")
    suffix = SUFFIX

    ingest_id   = await index_service_oneshot(client, suffix)
    renderer_id = await create_service_step_by_step(client, suffix)

    # ── Link both to the observatory ─────────────────────────────────────
    for service_id in (ingest_id, renderer_id):
        unwrap(await client.link_service_to_observatory(obs_id, service_id), f"link service {service_id}")
    save_state(services=[ingest_id, renderer_id])

    linked = unwrap(await client.list_observatory_services(obs_id), "list observatory services")
    print(f"\n[list_observatory_services] {obs_id}")
    for s in linked:
        print(f"  {s.service_id}  {s.name:<28} provider={s.provider}  public={s.public}")

    # ── Search ───────────────────────────────────────────────────────────
    print("\n[search_services]")
    for query in (
        f"jub.v1.SVC(name={suffix})",
        f"jub.v1.SVC(owner={client.user_id})",
        f"jub.v1.SVC(name={suffix},public=true)",
    ):
        found = unwrap(await client.search_services(DTO.ServiceQueryDTO(query=query, limit=10)), f"search {query}")
        print(f"  {query:<50} {len(found)} → {', '.join(s.name for s in found) or '—'}")


if __name__ == "__main__":
    asyncio.run(main())
