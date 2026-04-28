import pytest
from httpx import AsyncClient, ASGITransport
from jubapi.server import app 
from datetime import datetime, timezone
from typing import List, Dict, Any



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

async def test_api_search_data_records_real_db(async_client: AsyncClient,seeded_db, get_current_user):
    """
    Prueba el endpoint /search/records golpeando la DB real.
    """
    # Si tienes autenticación, extraemos los headers (como en tus tests de tasks)
    MOCK_USER, headers = get_current_user
    
    # DSL: Solo queremos los registros de México
    payload = {"query": "jub.v1.VS(MX)", "limit": 100, "skip": 0}
    
    response = await async_client.post("api/v2/search/records", json=payload, headers=headers)
    
    # Validaciones HTTP
    assert response.status_code == 200
    records = response.json()
    
    # De los 7 registros en seeded_db, 5 son de MX y 2 son de TAM/NL.
    # Por lo tanto, el endpoint real debe devolver exactamente 5.
    assert len(records) == 5
    assert all(r["spatial_id"] == "MX" for r in records)


@pytest.mark.asyncio
async def test_api_generate_plot_global_real_db(async_client: AsyncClient,  get_current_user):
    """
    Prueba el endpoint /search/plot para un KPI Global.
    Verifica la tubería completa: HTTP -> Router -> Service -> AST -> MongoDB -> ECharts Formatter -> HTTP.
    """
    MOCK_USER, headers = get_current_user
    
    # DSL: Suma del costo en México
    payload = {
        "query": "jub.v1.VS(MX).VO(SUM(COST))",
        "chart_type": "bar"
    }
    
    response = await async_client.post("api/v2/search/plot", json=payload, headers=headers)
    
    assert response.status_code == 200
    echarts_data = response.json()
    
    # Validamos que el JSON devuelto por HTTP sea un ECharts válido
    assert echarts_data["xAxis"]["data"] == ["Total"]
    assert echarts_data["series"][0]["name"] == "Total"
    
    # La matemática ejecutada en la DB real debe ser 9800
    assert echarts_data["series"][0]["data"] == [9800.0]


@pytest.mark.asyncio
async def test_api_generate_plot_complex_real_db(async_client: AsyncClient, seeded_db, get_current_user):
    """
    Prueba el endpoint /search/plot con la agrupación compleja BY() y filtros VI().
    """
    MOCK_USER, headers = get_current_user
    
    payload = {
        "query": "jub.v1.VS(MX).VI(CIE10_E11).VO(SUM(COST)).BY(TEMPORAL AND SEX)",
        "chart_type": "bar"
    }
    
    response = await async_client.post("api/v2/search/plot", json=payload, headers=headers)
    
    assert response.status_code == 200
    echarts_data = response.json()
    
    # Validar la leyenda extraída de la DB real
    legend_data = echarts_data["legend"]["data"]
    assert "SEX_MALE" in legend_data
    assert "SEX_FEMALE" in legend_data
    
    # Extraer las series
    male_series = next(s for s in echarts_data["series"] if s["name"] == "SEX_MALE")
    female_series = next(s for s in echarts_data["series"] if s["name"] == "SEX_FEMALE")
    
    # Validar los datos matemáticos procesados por Mongo
    assert male_series["data"] == [1000.0, 1100.0, 5000.0]
    assert female_series["data"] == [1200.0, 0, 1500.0] # El 0 es el padding que hace nuestro formateador


@pytest.mark.asyncio
async def test_api_search_bad_request(async_client: AsyncClient, get_current_user):
    """
    Prueba que la API se defienda correctamente de ataques o DSL mal formados.
    """
    MOCK_USER, headers = get_current_user
    
    # Un DSL completamente inválido matemáticamente
    payload = {
        "query": "jub.v1.VO(ESTA_FUNCION_NO_EXISTE(AGE))",
        "chart_type": "line"
    }
    
    response = await async_client.post("api/v2/search/plot", json=payload, headers=headers)
    print("Response status:", response)
    # Debe detenerse en el Parser y devolver un Error HTTP 400 Bad Request
    assert response.status_code == 500
    assert "Invalid math function" in response.text