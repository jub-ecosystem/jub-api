"""
Unit tests for the Service/Workflow domain:
  BuildingBlockService, PatternService, StageService,
  WorkflowService, ServiceXService (CRUD + index + DSL search).
"""
import pytest
import jubapi.repositories.v2 as R
import jubapi.services.v2 as S
import jubapi.dto.v2 as DTO
from jubapi.db.constants import CollectionNames


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def svcs(test_db):
    bb_repo       = R.BuildingBlockRepository(test_db[CollectionNames.BUILDING_BLOCKS.value])
    pattern_repo  = R.PatternRepository(test_db[CollectionNames.PATTERNS.value])
    stage_repo    = R.StageRepository(test_db[CollectionNames.STAGES.value])
    workflow_repo = R.WorkflowRepository(test_db[CollectionNames.WORKFLOWS.value])
    service_repo  = R.ServiceRepository(test_db[CollectionNames.SERVICES.value])

    return {
        "bb":       S.BuildingBlockService(bb_repo),
        "pattern":  S.PatternService(pattern_repo),
        "stage":    S.StageService(stage_repo),
        "workflow": S.WorkflowService(workflow_repo, stage_repo),
        "service":  S.ServiceXService(service_repo, workflow_repo, stage_repo, pattern_repo, bb_repo),
    }


# ---------------------------------------------------------------------------
# BuildingBlockService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bb_create_and_get(svcs):
    svc:S.BuildingBlockService = svcs["bb"]
    dto = DTO.BuildingBlockCreateDTO(name="Ingestor", command="python ingest.py", image="python:3.11-slim")
    result = await svc.create(dto)
    assert result.is_ok, result.unwrap_err()

    bb = result.unwrap()
    assert bb.name == "Ingestor"
    assert bb.building_block_id.startswith("bb_")

    fetched = await svc.get(bb.building_block_id)
    assert fetched.is_ok
    assert fetched.unwrap().command == "python ingest.py"


@pytest.mark.asyncio
async def test_bb_list(svcs):
    svc:S.BuildingBlockService = svcs["bb"]
    await svc.create(DTO.BuildingBlockCreateDTO(name="A", command="a", image="img"))
    await svc.create(DTO.BuildingBlockCreateDTO(name="B", command="b", image="img"))

    result = await svc.list()
    assert result.is_ok
    assert len(result.unwrap()) == 2


@pytest.mark.asyncio
async def test_bb_update(svcs):
    svc:S.BuildingBlockService = svcs["bb"]
    bb = (await svc.create(DTO.BuildingBlockCreateDTO(name="Old", command="old", image="img"))).unwrap()

    upd = await svc.update(bb.building_block_id, DTO.BuildingBlockUpdateDTO(name="New", command="new"))
    assert upd.is_ok
    assert upd.unwrap().name == "New"
    assert upd.unwrap().command == "new"


@pytest.mark.asyncio
async def test_bb_delete(svcs):
    svc:S.BuildingBlockService = svcs["bb"]
    bb = (await svc.create(DTO.BuildingBlockCreateDTO(name="ToDelete", command="x", image="img"))).unwrap()

    del_result = await svc.delete(bb.building_block_id)
    assert del_result.is_ok

    get_result = await svc.get(bb.building_block_id)
    assert get_result.is_err


@pytest.mark.asyncio
async def test_bb_delete_not_found(svcs):
    svc:S.BuildingBlockService = svcs["bb"]
    result = await svc.delete("nonexistent")
    assert result.is_err


# ---------------------------------------------------------------------------
# PatternService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pattern_create_and_get(svcs):
    svc:S.PatternService = svcs["pattern"]
    dto = DTO.PatternCreateDTO(name="MapReduce", task="transform", pattern="map-reduce", workers=3)
    result = await svc.create(dto)
    assert result.is_ok, result.unwrap_err()

    p = result.unwrap()
    assert p.pattern_id.startswith("pat_")
    assert p.workers == 3

    fetched = await svc.get(p.pattern_id)
    assert fetched.is_ok
    assert fetched.unwrap().pattern == "map-reduce"


@pytest.mark.asyncio
async def test_pattern_with_building_block(svcs):
    bb = (await svcs["bb"].create(DTO.BuildingBlockCreateDTO(name="BB", command="run", image="img"))).unwrap()

    dto = DTO.PatternCreateDTO(
        name="Pipeline", task="ingest", pattern="pipeline",
        building_block_id=bb.building_block_id
    )
    result = await svcs["pattern"].create(dto)
    assert result.is_ok
    assert result.unwrap().building_block_id == bb.building_block_id


@pytest.mark.asyncio
async def test_pattern_update(svcs):
    svc:S.PatternService = svcs["pattern"]
    p = (await svc.create(DTO.PatternCreateDTO(name="P", task="t", pattern="fanout"))).unwrap()

    upd = await svc.update(p.pattern_id, DTO.PatternUpdateDTO(workers=5, loadbalancer="least-connections"))
    assert upd.is_ok
    assert upd.unwrap().workers == 5
    assert upd.unwrap().loadbalancer == "least-connections"


@pytest.mark.asyncio
async def test_pattern_delete(svcs):
    svc:S.PatternService = svcs["pattern"]
    p = (await svc.create(DTO.PatternCreateDTO(name="P", task="t", pattern="fanout"))).unwrap()

    assert (await svc.delete(p.pattern_id)).is_ok
    assert (await svc.get(p.pattern_id)).is_err


# ---------------------------------------------------------------------------
# StageService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stage_create_and_get(svcs):
    svc:S.StageService = svcs["stage"]
    dto = DTO.StageCreateDTO(name="Fetch", source="s3://bucket", sink="mongo://db", endpoint="/fetch")
    result = await svc.create(dto)
    assert result.is_ok, result.unwrap_err()

    stage = result.unwrap()
    assert stage.stage_id.startswith("stg_")
    assert stage.source == "s3://bucket"

    fetched = await svc.get(stage.stage_id)
    assert fetched.is_ok
    assert fetched.unwrap().sink == "mongo://db"


@pytest.mark.asyncio
async def test_stage_list(svcs):
    svc:S.StageService = svcs["stage"]
    await svc.create(DTO.StageCreateDTO(name="S1", source="a", sink="b", endpoint="/s1"))
    await svc.create(DTO.StageCreateDTO(name="S2", source="c", sink="d", endpoint="/s2"))

    result = await svc.list()
    assert result.is_ok
    assert len(result.unwrap()) == 2


@pytest.mark.asyncio
async def test_stage_update(svcs):
    svc:S.StageService = svcs["stage"]
    stage = (await svc.create(DTO.StageCreateDTO(name="Old", source="a", sink="b", endpoint="/old"))).unwrap()

    upd = await svc.update(stage.stage_id, DTO.StageUpdateDTO(name="New", endpoint="/new"))
    assert upd.is_ok
    assert upd.unwrap().name == "New"
    assert upd.unwrap().endpoint == "/new"


@pytest.mark.asyncio
async def test_stage_delete(svcs):
    svc:S.StageService = svcs["stage"]
    stage = (await svc.create(DTO.StageCreateDTO(name="ToDelete", source="a", sink="b", endpoint="/del"))).unwrap()

    assert (await svc.delete(stage.stage_id)).is_ok
    assert (await svc.get(stage.stage_id)).is_err


# ---------------------------------------------------------------------------
# WorkflowService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_create_and_get(svcs):
    stage = (await svcs["stage"].create(
        DTO.StageCreateDTO(name="S", source="a", sink="b", endpoint="/s")
    )).unwrap()

    svc:S.WorkflowService = svcs["workflow"]
    dto = DTO.WorkflowCreateDTO(name="ETL", stage_ids=[stage.stage_id])
    result = await svc.create(dto)
    assert result.is_ok, result.unwrap_err()

    wf = result.unwrap()
    assert wf.workflow_id.startswith("wf_")
    assert stage.stage_id in wf.stage_ids

    fetched = await svc.get(wf.workflow_id)
    assert fetched.is_ok
    assert fetched.unwrap().name == "ETL"


@pytest.mark.asyncio
async def test_workflow_update(svcs):
    svc:S.WorkflowService = svcs["workflow"]
    wf = (await svc.create(DTO.WorkflowCreateDTO(name="Old", stage_ids=[]))).unwrap()

    upd = await svc.update(wf.workflow_id, DTO.WorkflowUpdateDTO(name="New"))
    assert upd.is_ok
    assert upd.unwrap().name == "New"


@pytest.mark.asyncio
async def test_workflow_delete_no_cascade(svcs):
    svc:S.StageService =svcs["stage"]
    workflow_svc:S.WorkflowService = svcs["workflow"]
    stage = (await svc.create(
        DTO.StageCreateDTO(name="Keep", source="a", sink="b", endpoint="/k")
    )).unwrap()

    wf:S.WorkflowService = (await workflow_svc.create(DTO.WorkflowCreateDTO(name="WF", stage_ids=[stage.stage_id]))).unwrap()

    result = await workflow_svc.delete(wf.workflow_id, cascade=False)
    assert result.is_ok

    # Stage must still exist
    assert (await svc.get(stage.stage_id)).is_ok


@pytest.mark.asyncio
async def test_workflow_delete_cascade(svcs):
    svc:S.StageService = svcs["stage"]
    workflow_svc:S.WorkflowService = svcs["workflow"]
    s1 = (await svc.create(DTO.StageCreateDTO(name="S1", source="a", sink="b", endpoint="/s1"))).unwrap()
    s2 = (await svc.create(DTO.StageCreateDTO(name="S2", source="c", sink="d", endpoint="/s2"))).unwrap()

    wf = (await workflow_svc.create(
        DTO.WorkflowCreateDTO(name="WF", stage_ids=[s1.stage_id, s2.stage_id])
    )).unwrap()

    result = await workflow_svc.delete(wf.workflow_id, cascade=True)
    assert result.is_ok
    assert result.unwrap()["stages"] == 2

    assert (await svc.get(s1.stage_id)).is_err
    assert (await svc.get(s2.stage_id)).is_err


# ---------------------------------------------------------------------------
# ServiceXService — CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_create_and_get(svcs):
    svc:S.ServiceXService = svcs["service"]
    dto = DTO.ServiceCreateDTO(name="Cancer API", owner_id="user_01", public=True)
    result = await svc.create(dto)
    assert result.is_ok, result.unwrap_err()

    service = result.unwrap()
    assert service.service_id.startswith("svc_")
    assert service.public is True

    fetched = await svc.get(service.service_id)
    assert fetched.is_ok
    assert fetched.unwrap().name == "Cancer API"


@pytest.mark.asyncio
async def test_service_update(svcs):
    svc:S.ServiceXService = svcs["service"]
    service = (await svc.create(DTO.ServiceCreateDTO(name="Old", owner_id="u1"))).unwrap()

    upd = await svc.update(service.service_id, DTO.ServiceUpdateDTO(name="New", public=True))
    assert upd.is_ok
    assert upd.unwrap().name == "New"
    assert upd.unwrap().public is True


@pytest.mark.asyncio
async def test_service_delete(svcs):
    svc:S.ServiceXService = svcs["service"]
    service = (await svc.create(DTO.ServiceCreateDTO(name="ToDelete", owner_id="u1"))).unwrap()

    del_result = await svc.delete(service.service_id)
    assert del_result.is_ok
    assert del_result.unwrap().deleted is True

    assert (await svc.get(service.service_id)).is_err


# ---------------------------------------------------------------------------
# ServiceXService — index (one-shot full-tree creation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_index_full_tree(svcs):
    svc:S.ServiceXService = svcs["service"]
    dto = DTO.ServiceIndexDTO(
        name     = "Full Tree Service",
        owner_id = "user_42",
        public   = True,
        description= "A service with a full workflow, stages, patterns, and building blocks created in one call.",
        workflow = DTO.WorkflowInlineDTO(
            name   = "ETL Workflow",
            stages = [
                DTO.StageInlineDTO(
                    name           = "Ingest Stage",
                    source         = "s3://raw",
                    sink           = "mongo://processed",
                    endpoint       = "/ingest",
                    transformation = DTO.PatternInlineDTO(
                        name           = "Map Pattern",
                        task           = "transform",
                        pattern        = "map-reduce",
                        workers        = 2,
                        loadbalancer   = "round-robin",
                        building_block = DTO.BuildingBlockInlineDTO(
                            name    = "Python Worker",
                            command = "python worker.py",
                            image   = "python:3.11-slim",
                        ),
                    ),
                ),
                DTO.StageInlineDTO(
                    name     = "Export Stage",
                    source   = "mongo://processed",
                    sink     = "s3://output",
                    endpoint = "/export",
                ),
            ],
        ),
    )

    result = await svc.create_full(dto)
    assert result.is_ok, result.unwrap_err()

    resp = result.unwrap()
    assert resp.service_id.startswith("svc_")
    assert resp.workflow_id is not None and resp.workflow_id.startswith("wf_")
    assert len(resp.stage_ids) == 2
    assert len(resp.pattern_ids) == 1
    assert len(resp.building_block_ids) == 1

    # Verify every created entity persists
    assert (await svcs["bb"].get(resp.building_block_ids[0])).is_ok
    assert (await svcs["pattern"].get(resp.pattern_ids[0])).is_ok
    for sid in resp.stage_ids:
        assert (await svcs["stage"].get(sid)).is_ok
    assert (await svcs["workflow"].get(resp.workflow_id)).is_ok
    assert (await svc.get(resp.service_id)).is_ok


@pytest.mark.asyncio
async def test_service_index_existing_workflow(svcs):
    workflow_svc:S.WorkflowService = svcs["workflow"]
    wf = (await workflow_svc.create(DTO.WorkflowCreateDTO(name="Existing WF", stage_ids=[]))).unwrap()

    svc:S.ServiceXService = svcs["service"]
    result = await svc.create_full(DTO.ServiceIndexDTO(
        name="Service With Existing WF",
        owner_id="user_01",
        workflow_id=wf.workflow_id,
    ))
    assert result.is_ok
    assert result.unwrap().workflow_id == wf.workflow_id
    assert result.unwrap().stage_ids == []


# ---------------------------------------------------------------------------
# ServiceXService — DSL search (SVC queries)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def seeded_services(svcs):
    svc:S.ServiceXService = svcs["service"]
    await svc.create(DTO.ServiceCreateDTO(name="Cancer Registry API",    owner_id="user_01", public=True))
    await svc.create(DTO.ServiceCreateDTO(name="Mortality Dashboard",    owner_id="user_02", public=True))
    await svc.create(DTO.ServiceCreateDTO(name="Cancer Incidence Report",owner_id="user_01", public=False))
    await svc.create(DTO.ServiceCreateDTO(name="Internal ETL Pipeline",  owner_id="user_03", public=False))
    return svc


@pytest.mark.asyncio
async def test_dsl_wildcard_returns_all(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(*)")
    assert result.is_ok
    assert len(result.unwrap()) == 4


@pytest.mark.asyncio
async def test_dsl_filter_by_name(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(name=cancer)")
    assert result.is_ok
    names = [s.name for s in result.unwrap()]
    assert len(names) == 2
    assert all("cancer" in n.lower() for n in names)


@pytest.mark.asyncio
async def test_dsl_filter_public_only(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(public=true)")
    assert result.is_ok
    services = result.unwrap()
    assert len(services) == 2
    assert all(s.public for s in services)


@pytest.mark.asyncio
async def test_dsl_filter_private_only(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(public=false)")
    assert result.is_ok
    assert len(result.unwrap()) == 2
    assert all(not s.public for s in result.unwrap())


@pytest.mark.asyncio
async def test_dsl_filter_by_owner(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(owner=user_01)")
    assert result.is_ok
    services = result.unwrap()
    assert len(services) == 2
    assert all(s.owner_id == "user_01" for s in services)


@pytest.mark.asyncio
async def test_dsl_combined_name_and_public(seeded_services):
    result = await seeded_services.query_services("jub.v1.SVC(name=cancer,public=true)")
    assert result.is_ok
    services = result.unwrap()
    assert len(services) == 1
    assert "cancer" in services[0].name.lower()
    assert services[0].public is True


@pytest.mark.asyncio
async def test_dsl_invalid_query_returns_error(svcs):
    result = await svcs["service"].query_services("not_a_valid_query")
    assert result.is_err


@pytest.mark.asyncio
async def test_dsl_unknown_filter_key_returns_error(svcs):
    result = await svcs["service"].query_services("jub.v1.SVC(foo=bar)")
    assert result.is_err
