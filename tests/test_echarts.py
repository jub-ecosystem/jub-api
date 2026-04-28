import pytest
from jubapi.querylang.v2.parser import QueryAST
from jubapi.querylang.v2.translator import ASTToMongoTranslator
from jubapi.utils import Utils
from typing import List, Dict, Any
from datetime import datetime, timezone


def make_date(year: int, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)

@pytest.fixture
async def seeded_db(test_db):
    """
    Inyecta una base de datos de prueba realista para validar el motor analítico.
    Contiene variaciones de espacio (VS), tiempo (VT), intereses (VI) y variables continuas (VO).
    """
    records: List[Dict[str, Any]] = [
        # --- AÑO 2020 ---
        {
            "record_id": "rec_001", "source_id": "src_health",
            "spatial_id": "MX", "temporal_id": make_date(2020),
            "interest_ids": ["SEX_MALE", "CIE10_E11"], # E11 = Diabetes
            "numerical_interest_ids": {"AGE": 40.0, "COST": 1000.0},
            "raw_payload": {}
        },
        {
            "record_id": "rec_002", "source_id": "src_health",
            "spatial_id": "MX", "temporal_id": make_date(2020),
            "interest_ids": ["SEX_FEMALE", "CIE10_E11"],
            "numerical_interest_ids": {"AGE": 45.0, "COST": 1200.0},
            "raw_payload": {}
        },
        
        # --- AÑO 2021 ---
        {
            "record_id": "rec_003", "source_id": "src_health",
            "spatial_id": "MX", "temporal_id": make_date(2021),
            "interest_ids": ["SEX_MALE", "CIE10_E11"],
            "numerical_interest_ids": {"AGE": 42.0, "COST": 1100.0},
            "raw_payload": {}
        },
        {
            "record_id": "rec_004", "source_id": "src_health",
            "spatial_id": "TAM", "temporal_id": make_date(2021), # Ojo: Tamaulipas
            "interest_ids": ["SEX_MALE", "CIE10_I10"], # I10 = Hipertensión
            "numerical_interest_ids": {"AGE": 60.0, "COST": 500.0},
            "raw_payload": {}
        },
        
        # --- AÑO 2022 ---
        {
            "record_id": "rec_005", "source_id": "src_health",
            "spatial_id": "MX", "temporal_id": make_date(2022),
            "interest_ids": ["SEX_FEMALE", "CIE10_E11"],
            "numerical_interest_ids": {"AGE": 50.0, "COST": 1500.0},
            "raw_payload": {}
        },
        {
            "record_id": "rec_006", "source_id": "src_health",
            "spatial_id": "NL", "temporal_id": make_date(2022), # Ojo: Nuevo León
            "interest_ids": ["SEX_FEMALE", "CIE10_I10"],
            "numerical_interest_ids": {"AGE": 35.0, "COST": 800.0},
            "raw_payload": {}
        },
        {
            # Registro con un costo extremo para probar sumas
            "record_id": "rec_007", "source_id": "src_health",
            "spatial_id": "MX", "temporal_id": make_date(2022),
            "interest_ids": ["SEX_MALE", "CIE10_E11"],
            "numerical_interest_ids": {"AGE": 41.0, "COST": 5000.0}, 
            "raw_payload": {}
        }
    ]
    
    # Insertar directamente usando Motor
    await test_db.data_records.insert_many(records)
    return test_db


@pytest.mark.asyncio
async def test_echarts_global_kpi(seeded_db):
    """
    Scenario 1: A Global KPI (No BY clause).
    The user wants to know the Historical Total Cost in Mexico.
    """
    # 1. Parse and Translate
    query = "jub.v1.VS(MX).VO(SUM(COST))"
    ast = QueryAST.parse(query)
    pipeline = ASTToMongoTranslator.translate(ast)
    
    # 2. Execute directly in MongoDB
    raw_results = await seeded_db.data_records.aggregate(pipeline).to_list(length=None)
    
    # 3. Format for ECharts
    echarts_data = Utils.format_for_echarts(raw_results, chart_type="bar")
    
    # --- ECHARTS VALIDATIONS ---
    assert echarts_data["xAxis"]["data"] == ["Total"]
    assert len(echarts_data["series"]) == 1
    
    series = echarts_data["series"][0]
    assert series["name"] == "Total"
    
    # Math Verification: 
    # MX in 2020 (1000 + 1200) + 2021 (1100) + 2022 (1500 + 5000) = 9800
    # (TAM and NL are ignored due to the VS filter)
    assert series["data"] == [9800.0]


@pytest.mark.asyncio
async def test_echarts_line_single_dimension(seeded_db):
    """
    Scenario 2: Simple Grouping (One X-Axis).
    The user wants to see how the Average Age in Mexico has evolved over time.
    """
    query = "jub.v1.VS(MX).VO(AVG(AGE)).BY(TEMPORAL)"
    ast = QueryAST.parse(query)
    pipeline = ASTToMongoTranslator.translate(ast)
    
    raw_results = await seeded_db.data_records.aggregate(pipeline).to_list(length=None)
    echarts_data = Utils.format_for_echarts(raw_results, chart_type="line")
    
    # --- ECHARTS VALIDATIONS ---
    # The formatter converts datetime to string. 
    # The X-Axis should have the 3 years where MX has data.
    x_axis = echarts_data["xAxis"]["data"]
    assert len(x_axis) == 3 
    
    series = echarts_data["series"][0]
    assert series["type"] == "line"
    assert series["name"] == "Total" # No Hue provided, defaults to Total
    
    # Math Verification (Averages per year in MX):
    # 2020: (40 + 45) / 2 = 42.5
    # 2021: Only one record = 42.0
    # 2022: (50 + 41) / 2 = 45.5
    assert series["data"] == [42.5, 42.0, 45.5]


@pytest.mark.asyncio
async def test_echarts_bar_multi_dimension(seeded_db):
    """
    Scenario 3: Complex Breakdown (X-Axis + Hue/Colors).
    Total Cost in Mexico for patients with Diabetes (E11), grouped by Year and Sex.
    THIS TEST VALIDATES THE REGEX MAGIC ON MONGODB ARRAYS.
    """
    # VI(CIE10_E11) = Filter only Diabetes
    # BY(TEMPORAL AND SEX) = X-Axis is Year, Colors/Hue by Sex.
    query = "jub.v1.VS(MX).VI(CIE10_E11).VO(SUM(COST)).BY(TEMPORAL AND SEX)"
    ast = QueryAST.parse(query)
    pipeline = ASTToMongoTranslator.translate(ast)
    
    raw_results = await seeded_db.data_records.aggregate(pipeline).to_list(length=None)
    echarts_data = Utils.format_for_echarts(raw_results, chart_type="bar")
    print(echarts_data)  # Debug: Ver la estructura exacta que llega a ECharts
    # --- ECHARTS VALIDATIONS ---
    # Validate that the Regex successfully extracted the exact labels for the legend
    legend_data = echarts_data["legend"]["data"]
    assert "SEX_MALE" in legend_data
    assert "SEX_FEMALE" in legend_data
    
    # Locate the individual series
    male_series = next(s for s in echarts_data["series"] if s["name"] == "SEX_MALE")
    female_series = next(s for s in echarts_data["series"] if s["name"] == "SEX_FEMALE")
    
    # Math Verification MALE (Sum of costs in MX per year):
    # 2020 = 1000, 2021 = 1100, 2022 = 5000
    assert male_series["data"] == [1000.0, 1100.0, 5000.0]
    
    # Math Verification FEMALE:
    # 2020 = 1200
    # 2021 = 0 (No females registered in MX this year, formatter must pad with 0)
    # 2022 = 1500
    assert female_series["data"] == [1200.0, 0, 1500.0]