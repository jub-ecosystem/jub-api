import pytest
import datetime
from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

import jubapi.models.v2 as M
import jubapi.repositories.v2 as R
import jubapi.services.v2 as S
from jubapi.db.constants import CollectionNames
import jubapi.errors as EX

@pytest.fixture
def source_repo(test_db):
    return R.DataSourceRepository(test_db[CollectionNames.DATA_SOURCES.value])

@pytest.fixture
def record_repo(test_db):
    return R.DataRecordRepository(test_db[CollectionNames.DATA_RECORDS.value])

@pytest.fixture
def ingestion_service(source_repo, record_repo):
    return S.DataIngestionService(source_repo, record_repo)

# Helper for UTC dates
def make_utc_date(year, month=1, day=1):
    return datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)


# ==========================================
# 1. REPOSITORY INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_insert_many_records(record_repo: R.DataRecordRepository, test_db):
    """Verifies that insert_many actually writes multiple documents to Mongo."""
    records = [
        M.DataRecord(
            record_id="rec_1", source_id="src_1", spatial_id="MX", 
            temporal_id=make_utc_date(2025), interest_ids=["MALE"], 
            numerical_interest_ids={}, raw_payload={}
        ),
        M.DataRecord(
            record_id="rec_2", source_id="src_1", spatial_id="TAM", 
            temporal_id=make_utc_date(2026), interest_ids=["FEMALE"], 
            numerical_interest_ids={}, raw_payload={}
        )
    ]
    
    result = await record_repo.insert_many(records)
    
    assert result.is_ok
    assert result.unwrap() == 2
    
    # Directly query the database to verify they exist
    db_count = await test_db[CollectionNames.DATA_RECORDS.value].count_documents({"source_id": "src_1"})
    assert db_count == 2

@pytest.mark.asyncio
async def test_delete_by_source(record_repo: R.DataRecordRepository):
    """Verifies that records are wiped cleanly based on source_id."""
    await record_repo.insert_many([
        M.DataRecord(record_id="rec_1", source_id="src_target", spatial_id="MX", temporal_id=make_utc_date(2020), interest_ids=[], numerical_interest_ids={}),
        M.DataRecord(record_id="rec_2", source_id="src_target", spatial_id="NL", temporal_id=make_utc_date(2020), interest_ids=[], numerical_interest_ids={}),
        M.DataRecord(record_id="rec_3", source_id="src_other", spatial_id="TAM", temporal_id=make_utc_date(2020), interest_ids=[], numerical_interest_ids={})
    ])
    
    result = await record_repo.delete_by_source("src_target")
    
    assert result.is_ok
    assert result.unwrap() == 2  # Should only delete the two target records
    
    # Verify the remaining record is untouched
    remaining_count = await record_repo.count({})
    assert remaining_count.is_ok
    assert remaining_count.unwrap() == 1
    
    remaining_doc = await record_repo.find_many({}) 
    assert remaining_doc.is_ok
    assert remaining_doc.unwrap()[0].source_id == "src_other"


# ==========================================
# 2. SERVICE INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_register_data_source(ingestion_service: S.DataIngestionService, test_db):
    """Tests the full flow of registering a new data source."""
    result = await ingestion_service.register_data_source(
        name="Integration Test DB",
        description="Testing live db",
        bucket_id="/data/test.csv"
    )

    assert result.is_ok
    source = result.unwrap()
    
    # Check that it actually lives in the database
    db_source = await test_db[CollectionNames.DATA_SOURCES.value].find_one({"source_id": source.source_id})
    assert db_source is not None
    assert db_source["name"] == "Integration Test DB"

@pytest.mark.asyncio
async def test_ingest_parsed_records_success(ingestion_service: S.DataIngestionService, test_db):
    """Tests ingesting records for a valid source."""
    source_result = await ingestion_service.register_data_source("Valid DB", "Desc", "/path")
    source_id = source_result.unwrap().source_id
    
    records = [
        M.DataRecord(record_id="rec_A", source_id=source_id, spatial_id="MX", temporal_id=make_utc_date(2025), interest_ids=[], numerical_interest_ids={}),
        M.DataRecord(record_id="rec_B", source_id=source_id, spatial_id="TAM", temporal_id=make_utc_date(2025), interest_ids=[], numerical_interest_ids={})
    ]
    
    ingest_result = await ingestion_service.ingest_parsed_records(source_id, records)
    
    assert ingest_result.is_ok
    assert ingest_result.unwrap() == 2
    
    # Verify database state
    db_records = await test_db[CollectionNames.DATA_RECORDS.value].count_documents({"source_id": source_id})
    assert db_records == 2

@pytest.mark.asyncio
async def test_ingest_parsed_records_source_not_found(ingestion_service: S.DataIngestionService, test_db):
    """Ensures ingestion is blocked if the source doesn't exist in the database."""
    records = [
        M.DataRecord(record_id="rec_A", source_id="fake_source", spatial_id="MX", temporal_id=make_utc_date(2025), interest_ids=[], numerical_interest_ids={})
    ]
    
    result = await ingestion_service.ingest_parsed_records("fake_source", records)
    
    assert result.is_err
    assert isinstance(result.unwrap_err(), EX.NotFound)
    
    # Ensure nothing was accidentally written
    db_records = await test_db[CollectionNames.DATA_RECORDS.value].count_documents({})
    assert db_records == 0

@pytest.mark.asyncio
async def test_delete_data_source_cascades(ingestion_service: S.DataIngestionService, test_db):
    """Tests that deleting a source perfectly cleans up both tables."""
    source_result = await ingestion_service.register_data_source("To Delete", "Desc", "/path")
    source_id = source_result.unwrap().source_id
    
    records = [M.DataRecord(record_id="rec_del", source_id=source_id, spatial_id="MX", temporal_id=make_utc_date(2025), interest_ids=[], numerical_interest_ids={})]
    await ingestion_service.ingest_parsed_records(source_id, records)
    
    assert await test_db[CollectionNames.DATA_SOURCES.value].count_documents({}) == 1
    assert await test_db[CollectionNames.DATA_RECORDS.value].count_documents({}) == 1
    
    delete_result = await ingestion_service.delete_data_source(source_id)
    assert delete_result.is_ok
    
    assert await test_db[CollectionNames.DATA_SOURCES.value].count_documents({}) == 0
    assert await test_db[CollectionNames.DATA_RECORDS.value].count_documents({}) == 0