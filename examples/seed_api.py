#!/usr/bin/env python3
"""
seed_api.py — Seeds JUB via the HTTP API (the right path for all users).

Unlike seed_db.py (which writes directly to MongoDB), this script goes through
the same endpoints that frontends and integrators use:

  1.  POST /api/v2/observatories/setup              → disabled observatory + PENDING task
  2.  POST /api/v2/observatories/{id}/catalogs/bulk → create & link all catalogs
  3.  GET  /api/v2/catalogs/{id}                    → fetch item IDs/values for tagging & records
  4.  POST /api/v2/observatories/{id}/products/bulk → create & link products with tags
  5.  POST /api/v2/products/{id}/upload             → upload chart file (requires auth)
  6.  POST /api/v2/datasources                      → register a data source per observatory
  7.  POST /api/v2/datasources/{id}/records         → ingest synthetic health records in chunks
  8.  POST /api/v2/tasks/{task_id}/complete         → enable the observatory

Clean modes remove all entities (datasources + records, observatories, products) via the
API's DELETE endpoints without touching user accounts.
Note: catalogs and catalog items have no DELETE endpoint and cannot be removed via the API.

  --clean       Delete existing entities then re-seed.
  --clean-only  Delete existing entities and exit (no seeding).

Chart files come from source/:
  · source/heatmap.html  (geographic / spatial products)
  · source/radar.html    (multi-dimensional / temporal products)

Usage:
    python examples/seed_api.py
    python examples/seed_api.py --api-url http://localhost:5000
    python examples/seed_api.py --clean-only
    python examples/seed_api.py --clean
    python examples/seed_api.py --username admin --password secret
    python examples/seed_api.py --signup --username newuser --password pass \\
                                 --email me@example.com --first-name Ada --last-name Lovelace
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as DT
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR   = Path(__file__).parent.parent
SOURCE_DIR = ROOT_DIR / "source"

HEATMAP_FILE = SOURCE_DIR / "heatmap.html"
RADAR_FILE   = SOURCE_DIR / "radar.html"


# ---------------------------------------------------------------------------
# Domain data  (inegi_code, full_name, abbr, pop_M)
# ---------------------------------------------------------------------------

MEXICO_STATES: List[Tuple[int, str, str, float]] = [
    (1,  "Aguascalientes",                   "AGS",  1.43),
    (2,  "Baja California",                  "BC",   3.77),
    (3,  "Baja California Sur",              "BCS",  0.80),
    (4,  "Campeche",                         "CAM",  1.00),
    (5,  "Coahuila de Zaragoza",             "COAH", 3.15),
    (6,  "Colima",                           "COL",  0.73),
    (7,  "Chiapas",                          "CHIS", 5.54),
    (8,  "Chihuahua",                        "CHIH", 3.74),
    (9,  "Ciudad de Mexico",                 "CDMX", 9.21),
    (10, "Durango",                          "DGO",  1.83),
    (11, "Guanajuato",                       "GTO",  6.17),
    (12, "Guerrero",                         "GRO",  3.54),
    (13, "Hidalgo",                          "HGO",  3.08),
    (14, "Jalisco",                          "JAL",  8.35),
    (15, "Estado de Mexico",                 "MEX",  16.99),
    (16, "Michoacan de Ocampo",              "MICH", 4.75),
    (17, "Morelos",                          "MOR",  1.97),
    (18, "Nayarit",                          "NAY",  1.24),
    (19, "Nuevo Leon",                       "NL",   5.78),
    (20, "Oaxaca",                           "OAX",  4.13),
    (21, "Puebla",                           "PUE",  6.58),
    (22, "Queretaro",                        "QRO",  2.37),
    (23, "Quintana Roo",                     "QROO", 1.86),
    (24, "San Luis Potosi",                  "SLP",  2.82),
    (25, "Sinaloa",                          "SIN",  3.03),
    (26, "Sonora",                           "SON",  2.94),
    (27, "Tabasco",                          "TAB",  2.40),
    (28, "Tamaulipas",                       "TAMS", 3.64),
    (29, "Tlaxcala",                         "TLAX", 1.34),
    (30, "Veracruz de Ignacio de la Llave",  "VER",  8.06),
    (31, "Yucatan",                          "YUC",  2.32),
    (32, "Zacatecas",                        "ZAC",  1.62),
]

YEARS = list(range(2015, 2024))

SEX_DATA = [
    (1, "Hombre",          "HOMBRE"),
    (2, "Mujer",           "MUJER"),
    (9, "No especificado", "NO_ESPECIFICADO"),
]

AGE_GROUP_DATA = [
    (1, "0-4 años",       "G0_4",    "Infancia temprana"),
    (2, "5-14 años",      "G5_14",   "Infancia y preadolescencia"),
    (3, "15-24 años",     "G15_24",  "Adolescencia y juventud"),
    (4, "25-34 años",     "G25_34",  "Adultos jovenes"),
    (5, "35-44 años",     "G35_44",  "Adultos en edad media"),
    (6, "45-54 años",     "G45_54",  "Adultos maduros"),
    (7, "55-64 años",     "G55_64",  "Adultos mayores tempranos"),
    (8, "65-74 años",     "G65_74",  "Adultos mayores"),
    (9, "75 años y más",  "G75_MAS", "Adultos mayores avanzados"),
]

CAUSE_DEATH_DATA = [
    (1,  "Enfermedades isquemicas del corazon", "ISQUEMICA_CORAZON",   "I20-I25"),
    (2,  "Diabetes mellitus",                   "DIABETES_MELLITUS",   "E10-E14"),
    (3,  "Tumores malignos",                    "TUMOR_MALIGNO",       "C00-D48"),
    (4,  "Enfermedades cerebrovasculares",       "CEREBROVASCULAR",     "I60-I69"),
    (5,  "Neumonia e influenza",                 "NEUMONIA_INFLUENZA",  "J09-J18"),
    (6,  "Enfermedades del higado",              "ENFERMEDAD_HIGADO",   "K70-K76"),
    (7,  "Accidentes de transito",               "ACCIDENTE_TRANSITO",  "V01-V99"),
    (8,  "Insuficiencia renal cronica",          "INSUFICIENCIA_RENAL", "N17-N19"),
    (9,  "Hipertension arterial sistemica",      "HIPERTENSION",        "I10-I15"),
    (10, "COVID-19",                             "COVID_19",            "U07"),
]

CANCER_CIE10_DATA = [
    (1,  "Labio, cavidad oral y faringe",       "C_ORAL_FARINGE",        "C00-C14"),
    (2,  "Esofago, estomago e intestinos",      "C_DIGESTIVO",           "C15-C26"),
    (3,  "Higado y vias biliares",              "C_HIGADO",              "C22-C24"),
    (4,  "Pancreas",                            "C_PANCREAS",            "C25"),
    (5,  "Organos respiratorios (pulmon)",      "C_RESPIRATORIO",        "C30-C39"),
    (6,  "Mama",                                "C_MAMA",                "C50"),
    (7,  "Cervix uterino",                      "C_CERVIX",              "C53"),
    (8,  "Cuerpo del utero",                    "C_UTERO",               "C54"),
    (9,  "Ovario",                              "C_OVARIO",              "C56"),
    (10, "Prostata",                            "C_PROSTATA",            "C61"),
    (11, "Vias urinarias (vejiga y rinon)",     "C_URINARIO",            "C64-C68"),
    (12, "Cerebro y sistema nervioso central",  "C_SNC",                 "C70-C72"),
    (13, "Tiroides",                            "C_TIROIDES",            "C73"),
    (14, "Tejido linfoide y hematopoyetico",    "C_LINFOHEMATOPOYETICO", "C81-C96"),
]

DERECHOHABIENCIA_DATA = [
    (1, "IMSS",                    "IMSS"),
    (2, "ISSSTE",                  "ISSSTE"),
    (3, "PEMEX / SEDENA / MARINA", "PEMEX_SEDENA_MARINA"),
    (4, "Seguro Popular / INSABI", "SEGURO_POPULAR_INSABI"),
    (5, "Seguro privado",          "PRIVADO"),
    (6, "Sin derechohabiencia",    "NINGUNA"),
]

# Mortality realism parameters (same as seed_db.py)
CAUSE_BASE_RATE: Dict[str, float] = {
    "ISQUEMICA_CORAZON":   85.0,
    "DIABETES_MELLITUS":   75.0,
    "TUMOR_MALIGNO":       60.0,
    "CEREBROVASCULAR":     32.0,
    "NEUMONIA_INFLUENZA":  18.0,
    "ENFERMEDAD_HIGADO":   26.0,
    "ACCIDENTE_TRANSITO":  14.0,
    "INSUFICIENCIA_RENAL": 22.0,
    "HIPERTENSION":        12.0,
    "COVID_19":             0.0,
}

AGE_MULTIPLIER: Dict[str, float] = {
    "G0_4":    0.05,
    "G5_14":   0.02,
    "G15_24":  0.08,
    "G25_34":  0.15,
    "G35_44":  0.30,
    "G45_54":  0.65,
    "G55_64":  1.40,
    "G65_74":  2.80,
    "G75_MAS": 5.50,
}

SEX_CAUSE_MULTIPLIER: Dict[str, Dict[str, float]] = {
    "ISQUEMICA_CORAZON":  {"HOMBRE": 1.6, "MUJER": 0.8, "NO_ESPECIFICADO": 1.0},
    "DIABETES_MELLITUS":  {"HOMBRE": 0.9, "MUJER": 1.1, "NO_ESPECIFICADO": 1.0},
    "TUMOR_MALIGNO":      {"HOMBRE": 1.1, "MUJER": 1.0, "NO_ESPECIFICADO": 1.0},
    "ENFERMEDAD_HIGADO":  {"HOMBRE": 2.0, "MUJER": 0.7, "NO_ESPECIFICADO": 1.0},
    "ACCIDENTE_TRANSITO": {"HOMBRE": 2.5, "MUJER": 0.5, "NO_ESPECIFICADO": 1.0},
    "COVID_19":            {"HOMBRE": 1.4, "MUJER": 0.8, "NO_ESPECIFICADO": 1.0},
}

CANCER_BASE_RATE: Dict[str, Dict[str, float]] = {
    "C_MAMA":                {"HOMBRE": 1.0,  "MUJER": 38.0},
    "C_CERVIX":              {"HOMBRE": 0.0,  "MUJER": 22.0},
    "C_UTERO":               {"HOMBRE": 0.0,  "MUJER": 12.0},
    "C_OVARIO":              {"HOMBRE": 0.0,  "MUJER":  8.0},
    "C_PROSTATA":            {"HOMBRE": 25.0, "MUJER":  0.0},
    "C_DIGESTIVO":           {"HOMBRE": 18.0, "MUJER": 14.0},
    "C_RESPIRATORIO":        {"HOMBRE": 14.0, "MUJER":  7.0},
    "C_HIGADO":              {"HOMBRE": 12.0, "MUJER":  6.0},
    "C_LINFOHEMATOPOYETICO": {"HOMBRE":  8.0, "MUJER":  6.5},
    "C_ORAL_FARINGE":        {"HOMBRE":  5.0, "MUJER":  2.5},
    "C_URINARIO":            {"HOMBRE":  7.0, "MUJER":  3.0},
    "C_TIROIDES":            {"HOMBRE":  2.5, "MUJER":  7.0},
    "C_SNC":                 {"HOMBRE":  4.5, "MUJER":  3.5},
    "C_PANCREAS":            {"HOMBRE":  5.0, "MUJER":  4.5},
}


# ---------------------------------------------------------------------------
# Observatory & product definitions
# ---------------------------------------------------------------------------

OBSERVATORIES = [
    {
        "observatory_id": "obs_mortalidad_mx",
        "title":          "Observatorio de Mortalidad — Mexico",
        "description": (
            "Monitorea las principales causas de muerte en Mexico, su distribucion "
            "geografica y temporal, y las tendencias de mortalidad prematura por grupos "
            "de poblacion. Fuente principal: Certificados de Defuncion SINAVE-DGIS."
        ),
        "image_url": None,
        "metadata":  {"fuente": "SINAVE-DGIS", "pais": "MX", "version": "2023"},
    },
    {
        "observatory_id": "obs_cancer_mx",
        "title":          "Observatorio de Cancer — Mexico",
        "description": (
            "Seguimiento epidemiologico de la incidencia y mortalidad por cancer en Mexico, "
            "con base en la clasificacion CIE-10 y los grupos de riesgo IARC. "
            "Fuente: Registro Nacional de Cancer / INCAN."
        ),
        "image_url": None,
        "metadata":  {"fuente": "INCAN / RNEC", "pais": "MX", "version": "2022"},
    },
    {
        "observatory_id": "obs_cronicas_mx",
        "title":          "Observatorio de Enfermedades Cronicas No Transmisibles",
        "description": (
            "Analiza la prevalencia y mortalidad por diabetes mellitus, enfermedades "
            "cardiovasculares e hipertension arterial en la poblacion mexicana, "
            "desagregado por derechohabiencia, sexo y region. Fuente: ENSANUT / SINAVE."
        ),
        "image_url": None,
        "metadata":  {"fuente": "ENSANUT / SINAVE", "pais": "MX", "version": "2022"},
    },
]

# catalog labels must match keys in CATALOG_BUILDERS (defined below)
OBS_CATALOG_SETS: Dict[str, List[str]] = {
    "obs_mortalidad_mx": ["spatial", "temporal", "sex", "age_group", "causa_defuncion"],
    "obs_cancer_mx":     ["spatial", "temporal", "sex", "age_group", "cie10_cancer"],
    "obs_cronicas_mx":   ["spatial", "temporal", "sex", "causa_defuncion", "derechohabiencia"],
}

PRODUCTS_BY_OBS: Dict[str, List[Dict]] = {
    "obs_mortalidad_mx": [
        {
            "product_id":  "prod_mort_causa_estado",
            "name":        "Mortalidad por Causa y Estado",
            "description": "Distribucion de defunciones por causa de muerte (top 10) y entidad federativa.",
            "tag_catalogs": ["causa_defuncion", "spatial"],
            "chart":        "heatmap",
        },
        {
            "product_id":  "prod_mort_edad_sexo",
            "name":        "Mortalidad por Grupo de Edad y Sexo",
            "description": "Mortalidad segun grupo etario y sexo. Identifica grupos vulnerables.",
            "tag_catalogs": ["sex", "age_group"],
            "chart":        "radar",
        },
        {
            "product_id":  "prod_mort_tendencia",
            "name":        "Tendencia de Mortalidad 2015-2023",
            "description": "Serie temporal de mortalidad. Incluye el impacto del COVID-19 en 2020-2021.",
            "tag_catalogs": ["temporal", "causa_defuncion"],
            "chart":        "radar",
        },
    ],
    "obs_cancer_mx": [
        {
            "product_id":  "prod_cancer_tipo_cie10",
            "name":        "Cancer por Tipo CIE-10 / IARC",
            "description": "Casos de cancer agrupados por CIE-10 y categorias IARC.",
            "tag_catalogs": ["cie10_cancer"],
            "chart":        "radar",
        },
        {
            "product_id":  "prod_cancer_mortalidad_estado",
            "name":        "Mortalidad por Cancer por Entidad",
            "description": "Tasas de mortalidad oncologica por estado. Identifica estados con mayor carga.",
            "tag_catalogs": ["cie10_cancer", "spatial"],
            "chart":        "heatmap",
        },
        {
            "product_id":  "prod_cancer_sexo_edad",
            "name":        "Cancer por Sexo y Grupo de Edad",
            "description": "Distribucion del cancer por sexo y grupo etario.",
            "tag_catalogs": ["sex", "age_group", "cie10_cancer"],
            "chart":        "radar",
        },
    ],
    "obs_cronicas_mx": [
        {
            "product_id":  "prod_diabetes_estado",
            "name":        "Mortalidad por Diabetes Mellitus por Estado",
            "description": "Tasa de mortalidad por diabetes por cada 100k hab. por entidad federativa.",
            "tag_catalogs": ["causa_defuncion", "spatial"],
            "chart":        "heatmap",
        },
        {
            "product_id":  "prod_cardio_tendencia",
            "name":        "Tendencia de Mortalidad Cardiovascular",
            "description": "Evolucion de la mortalidad por enfermedades isquemicas y cerebrovasculares.",
            "tag_catalogs": ["temporal", "causa_defuncion"],
            "chart":        "radar",
        },
        {
            "product_id":  "prod_cronica_derecho",
            "name":        "Enfermedades Cronicas por Derechohabiencia",
            "description": "Mortalidad cronica segun afiliacion al sistema de salud.",
            "tag_catalogs": ["derechohabiencia", "causa_defuncion"],
            "chart":        "radar",
        },
    ],
}


# ---------------------------------------------------------------------------
# Data source definitions  (one per observatory)
# ---------------------------------------------------------------------------

DATA_SOURCE_DEFS: Dict[str, Dict[str, str]] = {
    "obs_mortalidad_mx": {
        "name":        "SINAVE — Certificados de Defuncion 2015-2023",
        "description": (
            "Certificados de defuncion con causa de muerte CIE-10 capturados por "
            "el SINAVE/DGIS para todas las entidades federativas."
        ),
    },
    "obs_cancer_mx": {
        "name":        "Registro Nacional de Cancer INCAN 2015-2022",
        "description": (
            "Casos de cancer registrados por el INCAN y la Red del Registro "
            "Histopatologico de Neoplasias en Mexico."
        ),
    },
    "obs_cronicas_mx": {
        "name":        "ENSANUT — Enfermedades Cronicas 2016-2022",
        "description": (
            "Encuesta Nacional de Salud y Nutricion, modulo de enfermedades "
            "cronicas no transmisibles por derechohabiencia."
        ),
    },
}


# ---------------------------------------------------------------------------
# Catalog DTO builders — produce the JSON payload for POST /catalogs/bulk
# ---------------------------------------------------------------------------

def _alias(value: str, value_type: str = "STRING", description: str = "") -> Dict:
    return {"value": value, "value_type": value_type, "description": description}


def _item(name: str, value: str, code: int, value_type: str = "STRING",
          description: str = "", aliases: Optional[List[Dict]] = None,
          children: Optional[List[Dict]] = None,
          temporal_value: Optional[str] = None) -> Dict:
    d: Dict[str, Any] = {
        "name":        name,
        "value":       value,
        "code":        code,
        "value_type":  value_type,
        "description": description,
        "aliases":     aliases or [],
        "children":    children or [],
    }
    if temporal_value is not None:
        d["temporal_value"] = temporal_value
    return d


def build_spatial_dto() -> Dict:
    state_items = [
        _item(
            name        = name,
            value       = abbr,
            code        = code,
            description = f"Estado de {name}, Mexico (INEGI {code:02d})",
            aliases     = [
                _alias(str(code),    "NUMBER", "Clave INEGI del estado"),
                _alias(abbr,         "STRING", "Abreviatura oficial"),
                _alias(name,         "STRING", "Nombre completo"),
                _alias(f"{code:02d}","STRING", "Clave INEGI con cero"),
            ],
        )
        for code, name, abbr, _ in MEXICO_STATES
    ]
    mx_root = _item(
        name        = "Mexico",
        value       = "MX",
        code        = 0,
        description = "Republica Mexicana",
        aliases     = [
            _alias("MEX",    "STRING", "ISO 3166-1 alpha-3"),
            _alias("484",    "NUMBER", "ISO 3166-1 numerico"),
            _alias("Mexico", "STRING", "Nombre en ingles"),
        ],
        children    = state_items,
    )
    return {
        "name":         "Dimension Espacial — Mexico",
        "value":        "SPATIAL_MX",
        "catalog_type": "SPATIAL",
        "description":  "Jerarquia geografica de Mexico: Pais → Estado. Codigos INEGI 2020.",
        "items":        [mx_root],
    }


def build_temporal_dto() -> Dict:
    items = [
        _item(
            name           = str(year),
            value          = f"Y{year}",
            code           = year,
            value_type     = "DATETIME",
            description    = f"Año de reporte {year}",
            temporal_value = f"{year}-01-01T00:00:00Z",
            aliases        = [
                _alias(str(year),       "NUMBER", "Año como entero"),
                _alias(f"AÑO_{year}",   "STRING", "Etiqueta en espanol"),
                _alias(f"YEAR_{year}",  "STRING", "Etiqueta en ingles"),
            ],
        )
        for year in YEARS
    ]
    return {
        "name":         "Dimension Temporal — Años de Reporte",
        "value":        "TEMPORAL_ANIOS",
        "catalog_type": "TEMPORAL",
        "description":  "Años calendario 2015-2023 presentes en los registros de salud publica.",
        "items":        items,
    }


def build_sex_dto() -> Dict:
    items = [
        _item(
            name     = name,
            value    = val,
            code     = code,
            aliases  = [_alias(str(code), "NUMBER", "Codigo numerico SINAVE")],
        )
        for code, name, val in SEX_DATA
    ]
    return {
        "name":         "Sexo Biologico",
        "value":        "SEX",
        "catalog_type": "INTEREST",
        "description":  "Clasificacion por sexo biologico al nacimiento segun registros administrativos de salud.",
        "items":        items,
    }


def build_age_group_dto() -> Dict:
    items = [
        _item(
            name        = name,
            value       = val,
            code        = code,
            description = desc,
            aliases     = [_alias(str(code), "NUMBER", "Codigo numerico")],
        )
        for code, name, val, desc in AGE_GROUP_DATA
    ]
    return {
        "name":         "Grupos de Edad",
        "value":        "AGE_GROUP",
        "catalog_type": "INTEREST",
        "description":  "Clasificacion por grupos quinquenales de edad para analisis epidemiologico.",
        "items":        items,
    }


def build_causa_defuncion_dto() -> Dict:
    items = [
        _item(
            name        = name,
            value       = val,
            code        = code,
            description = f"Rango CIE-10: {cie}",
            aliases     = [
                _alias(cie,      "STRING", "Rango CIE-10"),
                _alias(str(code),"NUMBER", "Codigo secuencial"),
            ],
        )
        for code, name, val, cie in CAUSE_DEATH_DATA
    ]
    return {
        "name":         "Causa de Defuncion (Top 10)",
        "value":        "CAUSA_DEFUNCION",
        "catalog_type": "INTEREST",
        "description":  "Principales causas de muerte en Mexico segun CIE-10. Fuente: SINAVE-DGIS.",
        "items":        items,
    }


def build_cie10_cancer_dto() -> Dict:
    items = [
        _item(
            name        = name,
            value       = val,
            code        = code,
            description = f"CIE-10 {cie}",
            aliases     = [
                _alias(cie,      "STRING", "Rango CIE-10"),
                _alias(str(code),"NUMBER", "Codigo secuencial"),
            ],
        )
        for code, name, val, cie in CANCER_CIE10_DATA
    ]
    return {
        "name":         "Grupos de Cancer CIE-10 / IARC",
        "value":        "CIE10_CANCER",
        "catalog_type": "INTEREST",
        "description":  "Agrupacion de neoplasias malignas segun CIE-10. Fuente: OPS / IARC / INCAN.",
        "items":        items,
    }


def build_derechohabiencia_dto() -> Dict:
    items = [
        _item(
            name    = name,
            value   = val,
            code    = code,
            aliases = [_alias(str(code), "NUMBER", "Codigo numerico")],
        )
        for code, name, val in DERECHOHABIENCIA_DATA
    ]
    return {
        "name":         "Derechohabiencia / Afiliacion al Sistema de Salud",
        "value":        "DERECHOHABIENCIA",
        "catalog_type": "INTEREST",
        "description":  "Tipo de afiliacion al sistema de salud en Mexico. Fuente: Certificados de Defuncion / ENSANUT.",
        "items":        items,
    }


CATALOG_BUILDERS = {
    "spatial":          build_spatial_dto,
    "temporal":         build_temporal_dto,
    "sex":              build_sex_dto,
    "age_group":        build_age_group_dto,
    "causa_defuncion":  build_causa_defuncion_dto,
    "cie10_cancer":     build_cie10_cancer_dto,
    "derechohabiencia": build_derechohabiencia_dto,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(resp: httpx.Response, label: str) -> Any:
    """Raise with detail on non-2xx responses."""
    if resp.status_code >= 300:
        print(f"\n  ✗ {label} failed [{resp.status_code}]: {resp.text[:400]}")
        sys.exit(1)
    return resp.json()


def extract_item_ids(items: List[Dict]) -> List[str]:
    """Flatten a (possibly nested) catalog item tree into a list of item IDs."""
    ids: List[str] = []
    for item in items:
        ids.append(item["catalog_item_id"])
        if item.get("children"):
            ids.extend(extract_item_ids(item["children"]))
    return ids


def extract_item_map(items: List[Dict]) -> Dict[str, str]:
    """Build {value: catalog_item_id} recursively from an item tree."""
    result: Dict[str, str] = {}
    for item in items:
        result[item["value"]] = item["catalog_item_id"]
        if item.get("children"):
            result.update(extract_item_map(item["children"]))
    return result


def _uid(n: int = 10) -> str:
    return uuid.uuid4().hex[:n]


def _rnd_deaths(base: float, pop_m: float, noise: float = 0.25) -> int:
    raw = (base / 100_000) * pop_m * 1_000_000
    return max(1, round(raw * random.uniform(1 - noise, 1 + noise)))


# ---------------------------------------------------------------------------
# Record generators
# ---------------------------------------------------------------------------

def gen_mortality_records(
    source_id: str,
    state_map: Dict[str, str],
    year_map:  Dict[int, str],
    sex_map:   Dict[str, str],
    age_map:   Dict[str, str],
    cause_map: Dict[str, str],
) -> List[Dict]:
    """32 states × 9 years × 2 sexes × 5 causes × 9 age groups (~25 k records)."""
    records: List[Dict] = []
    top_causes = ["ISQUEMICA_CORAZON", "DIABETES_MELLITUS", "TUMOR_MALIGNO",
                  "CEREBROVASCULAR", "COVID_19"]
    sexes = ["HOMBRE", "MUJER"]
    for _, state_name, abbr, pop_m in MEXICO_STATES:
        state_id = state_map.get(abbr)
        if not state_id:
            continue
        for year in YEARS:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_id = sex_map.get(sex_val)
                if not sex_id:
                    continue
                for cause_val in top_causes:
                    if cause_val == "COVID_19" and year < 2020:
                        continue
                    cause_id = cause_map.get(cause_val)
                    if not cause_id:
                        continue
                    base = CAUSE_BASE_RATE.get(cause_val, 10.0)
                    if cause_val == "COVID_19":
                        base = 90.0 if year == 2021 else 40.0
                    sex_mult = SEX_CAUSE_MULTIPLIER.get(cause_val, {}).get(sex_val, 1.0)
                    for age_val, age_mult in AGE_MULTIPLIER.items():
                        age_id = age_map.get(age_val)
                        if not age_id:
                            continue
                        eff = base * sex_mult * age_mult
                        records.append({
                            "record_id":              _uid(),
                            "spatial_id":             state_id,
                            "temporal_id":            year_dt.isoformat(),
                            "interest_ids":           [sex_id, age_id, cause_id],
                            "numerical_interest_ids": {
                                "COUNT":    float(_rnd_deaths(eff, pop_m)),
                                "TASA_100K": round(eff, 2),
                            },
                            "raw_payload": {
                                "estado": state_name, "year": year,
                                "sexo": sex_val, "edad": age_val, "causa": cause_val,
                            },
                        })
    return records


def gen_cancer_records(
    source_id:  str,
    state_map:  Dict[str, str],
    year_map:   Dict[int, str],
    sex_map:    Dict[str, str],
    cancer_map: Dict[str, str],
) -> List[Dict]:
    """32 states × 5 years × 2 sexes × up to 8 cancer types (~2 500 records)."""
    records: List[Dict] = []
    cancer_years = [2015, 2017, 2019, 2020, 2022]
    sexes = ["HOMBRE", "MUJER"]
    top_cancers = [
        "C_MAMA", "C_PROSTATA", "C_DIGESTIVO", "C_RESPIRATORIO",
        "C_LINFOHEMATOPOYETICO", "C_CERVIX", "C_HIGADO", "C_TIROIDES",
    ]
    for _, state_name, abbr, pop_m in MEXICO_STATES:
        state_id = state_map.get(abbr)
        if not state_id:
            continue
        for year in cancer_years:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_id = sex_map.get(sex_val)
                if not sex_id:
                    continue
                for cancer_val in top_cancers:
                    cancer_id = cancer_map.get(cancer_val)
                    if not cancer_id:
                        continue
                    base = CANCER_BASE_RATE.get(cancer_val, {}).get(sex_val, 0.0)
                    if base == 0.0:
                        continue
                    records.append({
                        "record_id":              _uid(),
                        "spatial_id":             state_id,
                        "temporal_id":            year_dt.isoformat(),
                        "interest_ids":           [sex_id, cancer_id],
                        "numerical_interest_ids": {
                            "COUNT":    float(_rnd_deaths(base, pop_m, noise=0.30)),
                            "TASA_100K": round(base, 2),
                        },
                        "raw_payload": {
                            "estado": state_name, "year": year,
                            "sexo": sex_val, "cancer": cancer_val,
                        },
                    })
    return records


def gen_chronic_records(
    source_id:   str,
    state_map:   Dict[str, str],
    year_map:    Dict[int, str],
    sex_map:     Dict[str, str],
    cause_map:   Dict[str, str],
    derecho_map: Dict[str, str],
) -> List[Dict]:
    """32 states × 4 years × 2 sexes × 3 causes × 6 derechohabiencia (~4 600 records)."""
    records: List[Dict] = []
    chronic_years = [2016, 2018, 2020, 2022]
    sexes = ["HOMBRE", "MUJER"]
    chronic_causes = ["DIABETES_MELLITUS", "ISQUEMICA_CORAZON", "HIPERTENSION"]
    derecho_splits = {
        "IMSS": 0.35, "ISSSTE": 0.08, "PEMEX_SEDENA_MARINA": 0.03,
        "SEGURO_POPULAR_INSABI": 0.30, "PRIVADO": 0.05, "NINGUNA": 0.19,
    }
    for _, state_name, abbr, pop_m in MEXICO_STATES:
        state_id = state_map.get(abbr)
        if not state_id:
            continue
        for year in chronic_years:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_id = sex_map.get(sex_val)
                if not sex_id:
                    continue
                for cause_val in chronic_causes:
                    cause_id = cause_map.get(cause_val)
                    if not cause_id:
                        continue
                    base = CAUSE_BASE_RATE.get(cause_val, 10.0)
                    sex_mult = SEX_CAUSE_MULTIPLIER.get(cause_val, {}).get(sex_val, 1.0)
                    count = _rnd_deaths(base * sex_mult, pop_m)
                    for d_val, d_id in derecho_map.items():
                        split = derecho_splits.get(d_val, 0.1)
                        d_count = max(1, round(count * split * random.uniform(0.85, 1.15)))
                        records.append({
                            "record_id":              _uid(),
                            "spatial_id":             state_id,
                            "temporal_id":            year_dt.isoformat(),
                            "interest_ids":           [sex_id, cause_id, d_id],
                            "numerical_interest_ids": {
                                "COUNT":           float(d_count),
                                "PREVALENCIA_100K": round(base * sex_mult, 2),
                            },
                            "raw_payload": {
                                "estado": state_name, "year": year, "sexo": sex_val,
                                "causa": cause_val, "derechohabiencia": d_val,
                            },
                        })
    return records


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def do_login(
    client: httpx.AsyncClient,
    username: str,
    password: str,
    scope: str,
) -> Tuple[str, str, str]:
    resp = await client.post("/users/auth", json={
        "username":   username,
        "password":   password,
        "scope":      scope,
        "expiration": "1h",
    })
    data = _check(resp, f"login as '{username}'")
    token           = data["access_token"]
    temporal_secret = data.get("temporal_secret_key") or ""
    user_id         = data["user_profile"]["user_id"]
    print(f"  ✓ Authenticated as '{username}' (user_id={user_id})")
    return token, temporal_secret, user_id


# ---------------------------------------------------------------------------
# Clean  (API-only: datasources, observatories, products)
# ---------------------------------------------------------------------------

async def clean_all(client: httpx.AsyncClient) -> None:
    """
    Deletes all entities reachable via DELETE endpoints:
      1. Data sources (also removes all ingested records)
      2. Observatories (also removes observatory→catalog and observatory→product links)
      3. Products (also removes product→catalog-item tag links)

    Catalogs and catalog items have no DELETE endpoint and are left untouched.
    """
    print("\n─── Cleaning all entities via API ────────────────────────────────")

    # 1. Data sources + their records
    print("  · Deleting data sources (+ records)…")
    ds_list = _check(await client.get("/datasources"), "list datasources")
    for ds in ds_list:
        sid  = ds["source_id"]
        resp = await client.delete(f"/datasources/{sid}")
        if resp.status_code in (200, 204):
            data = resp.json() if resp.status_code == 200 else {}
            removed = data.get("records_removed", "?")
            print(f"    ✓ Deleted source {sid}  ({removed} records removed)")
        elif resp.status_code == 404:
            print(f"    · Not found (skip): {sid}")
        else:
            print(f"    ✗ [{resp.status_code}] {sid}: {resp.text[:200]}")

    # 2. Observatories (removes obs→catalog and obs→product links)
    print("  · Deleting observatories…")
    page = 0
    while True:
        obs_page = _check(
            await client.get("/observatories", params={"limit": 100, "page_index": page}),
            f"list observatories (page {page})",
        )
        if not obs_page:
            break
        for obs in obs_page:
            oid  = obs["observatory_id"]
            resp = await client.delete(f"/observatories/{oid}")
            if resp.status_code in (200, 204):
                print(f"    ✓ Deleted observatory {oid}")
            elif resp.status_code == 404:
                print(f"    · Not found (skip): {oid}")
            else:
                print(f"    ✗ [{resp.status_code}] {oid}: {resp.text[:200]}")
        if len(obs_page) < 100:
            break
        page += 1

    # 3. Products (removes product→catalog-item tag links)
    print("  · Deleting products…")
    prod_list = _check(
        await client.get("/products", params={"limit": 500}),
        "list products",
    )
    for prod in prod_list:
        pid  = prod["product_id"]
        resp = await client.delete(f"/products/{pid}")
        if resp.status_code in (200, 204):
            print(f"    ✓ Deleted product {pid}")
        elif resp.status_code == 404:
            print(f"    · Not found (skip): {pid}")
        else:
            print(f"    ✗ [{resp.status_code}] {pid}: {resp.text[:200]}")

    print("  ⚠  Catalogs and catalog items have no DELETE endpoint — they remain in the database.")
    print("  ✓ Clean complete.\n")


# ---------------------------------------------------------------------------
# Main seed coroutine
# ---------------------------------------------------------------------------

async def seed(
    api_url:    str,
    username:   str,
    password:   str,
    scope:      str,
    signup:     bool,
    email:      str,
    first_name: str,
    last_name:  str,
    clean:      bool = False,
    clean_only: bool = False,
) -> None:
    random.seed(42)

    async with httpx.AsyncClient(base_url=api_url, timeout=120.0) as client:

        # ── Auth ────────────────────────────────────────────────────────────
        print("\n─── Auth ─────────────────────────────────────────────────────────")
        if signup:
            resp = await client.post("/users/signup", json={
                "username":   username,
                "first_name": first_name,
                "last_name":  last_name,
                "email":      email,
                "password":   password,
                "scope":      scope,
                "expiration": "1y",
            })
            if resp.status_code not in (200, 201):
                print(f"  ✗ Signup failed [{resp.status_code}]: {resp.text[:300]}")
                sys.exit(1)
            print(f"  ✓ User '{username}' created")

        token, temporal_secret, user_id = await do_login(client, username, password, scope)
        client.headers["Authorization"]       = f"Bearer {token}"
        client.headers["Temporal-Secret-Key"] = temporal_secret

        # ── Optional clean ───────────────────────────────────────────────────
        if clean or clean_only:
            await clean_all(client)
            if clean_only:
                print("─── Done (clean only) ────────────────────────────────────────────")
                return

        # ── Validate source files (only needed for seeding) ──────────────────
        for f in (HEATMAP_FILE, RADAR_FILE):
            if not f.exists():
                print(f"  ✗ Source file not found: {f}")
                sys.exit(1)

        # ── Observatories ────────────────────────────────────────────────────
        for obs_def in OBSERVATORIES:
            obs_key = obs_def["observatory_id"]
            print(f"\n─── Observatory: {obs_def['title']} ─────────────────────────")

            # 1. Setup (creates disabled observatory + PENDING task)
            setup_data = _check(
                await client.post("/observatories/setup", json={
                    "observatory_id": obs_key,
                    "title":          obs_def["title"],
                    "description":    obs_def["description"],
                    "image_url":      obs_def["image_url"],
                    "metadata":       obs_def["metadata"],
                    "user_id":        user_id,
                }),
                "observatory setup",
            )
            obs_id  = setup_data["observatory_id"]
            task_id = setup_data["task_id"]
            print(f"  ✓ Observatory created (disabled) — id={obs_id}")
            print(f"  ✓ Setup task queued                — task_id={task_id}")

            # 2. Build and bulk-assign catalogs
            catalog_labels = OBS_CATALOG_SETS[obs_key]
            catalog_dtos   = [CATALOG_BUILDERS[lbl]() for lbl in catalog_labels]

            bulk_cats = _check(
                await client.post(f"/observatories/{obs_id}/catalogs/bulk",
                                  json={"catalogs": catalog_dtos}),
                "bulk catalogs",
            )
            catalog_ids     = bulk_cats["catalog_ids"]
            label_to_cat_id = dict(zip(catalog_labels, catalog_ids))
            print(f"  ✓ {len(catalog_ids)} catalogs created and linked")

            # 3. Fetch each catalog — build item ID lists (for product tagging)
            #    and value→id maps (for record generation)
            label_to_item_ids:   Dict[str, List[str]]       = {}
            label_to_value_map:  Dict[str, Dict[str, str]]  = {}
            for label, cat_id in label_to_cat_id.items():
                cat_data = _check(
                    await client.get(f"/catalogs/{cat_id}"),
                    f"fetch catalog {label}",
                )
                label_to_item_ids[label]  = extract_item_ids(cat_data["items"])
                label_to_value_map[label] = extract_item_map(cat_data["items"])
            print(f"  ✓ Catalog item IDs fetched")

            # 4. Build and bulk-assign products
            products_in_obs   = PRODUCTS_BY_OBS[obs_key]
            products_payload: List[Dict] = []
            for prod in products_in_obs:
                item_ids: List[str] = []
                for cat_label in prod["tag_catalogs"]:
                    item_ids.extend(label_to_item_ids.get(cat_label, [])[:5])
                products_payload.append({
                    "product_id":       prod["product_id"],
                    "name":             prod["name"],
                    "description":      prod["description"],
                    "catalog_item_ids": item_ids,
                })

            bulk_prods = _check(
                await client.post(f"/observatories/{obs_id}/products/bulk",
                                  json={"products": products_payload}),
                "bulk products",
            )
            created_products = bulk_prods["products"]
            print(f"  ✓ {len(created_products)} products created and linked")

            # 5. Upload chart files (one per product, requires auth)
            print(f"  ─ Uploading chart files…")
            for prod_def, created in zip(products_in_obs, created_products):
                pid      = created["product_id"]
                src_file = HEATMAP_FILE if prod_def["chart"] == "heatmap" else RADAR_FILE

                with open(src_file, "rb") as fh:
                    upload_resp = await client.post(
                        f"/products/{pid}/upload",
                        files={"file": (src_file.name, fh, "text/html")},
                    )
                upload_data = _check(upload_resp, f"upload for {pid}")
                job_id = upload_data["job_id"]
                print(f"    → {prod_def['name'][:40]:<40} [{src_file.name}] job_id={job_id}")

            # 6. Register data source
            src_def = DATA_SOURCE_DEFS.get(obs_key)
            if src_def:
                src_data  = _check(
                    await client.post("/datasources", json=src_def),
                    "create data source",
                )
                source_id = src_data["source_id"]
                print(f"  ✓ Data source created — source_id={source_id}")

                # 7. Generate and ingest synthetic records
                vmap = label_to_value_map
                year_map: Dict[int, str] = {
                    int(v[1:]): iid
                    for v, iid in vmap.get("temporal", {}).items()
                    if v.startswith("Y") and v[1:].isdigit()
                }

                if obs_key == "obs_mortalidad_mx":
                    records = gen_mortality_records(
                        source_id,
                        state_map  = vmap["spatial"],
                        year_map   = year_map,
                        sex_map    = vmap["sex"],
                        age_map    = vmap["age_group"],
                        cause_map  = vmap["causa_defuncion"],
                    )
                elif obs_key == "obs_cancer_mx":
                    records = gen_cancer_records(
                        source_id,
                        state_map  = vmap["spatial"],
                        year_map   = year_map,
                        sex_map    = vmap["sex"],
                        cancer_map = vmap["cie10_cancer"],
                    )
                elif obs_key == "obs_cronicas_mx":
                    records = gen_chronic_records(
                        source_id,
                        state_map   = vmap["spatial"],
                        year_map    = year_map,
                        sex_map     = vmap["sex"],
                        cause_map   = vmap["causa_defuncion"],
                        derecho_map = vmap["derechohabiencia"],
                    )
                else:
                    records = []

                print(f"  ─ Ingesting {len(records):,} records in chunks of 300…")
                CHUNK = 300
                inserted_total = 0
                for i in range(0, len(records), CHUNK):
                    chunk = records[i : i + CHUNK]
                    ingest_data = _check(
                        await client.post(f"/datasources/{source_id}/records", json=chunk),
                        f"ingest records chunk {i // CHUNK + 1}",
                    )
                    inserted_total += ingest_data.get("inserted", len(chunk))
                print(f"  ✓ {inserted_total:,} records ingested")

            # 8. Complete setup task — enables the observatory
            complete_data = _check(
                await client.post(f"/tasks/{task_id}/complete", json={
                    "success": True,
                    "message": "Observatory seeded via seed_api.py.",
                }),
                "complete task",
            )
            enabled = complete_data.get("observatory_enabled", False)
            print(f"  ✓ Setup task completed — observatory enabled: {enabled}")

    print("\n─── Done ─────────────────────────────────────────────────────────")
    print("  All observatories, catalogs, products, data sources, and records created via API.")
    print(f"  API: {api_url}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed JUB via the HTTP API (mirrors the real user workflow).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api-url",    default="http://localhost:5000/api/v2",
                        help="Base URL of the JUB v2 API.")
    parser.add_argument("--username",   default="invitado",  help="Auth username.")
    parser.add_argument("--password",   default="invitado",  help="Auth password.")
    parser.add_argument("--scope",      default="jub",       help="Auth scope.")
    parser.add_argument("--clean",      action="store_true",
                        help="Delete existing entities via API before seeding.")
    parser.add_argument("--clean-only", action="store_true",
                        help="Delete existing entities via API then exit (no seeding).")
    parser.add_argument("--signup",     action="store_true",
                        help="Create the user before logging in.")
    parser.add_argument("--email",      default="invitado@example.com",
                        help="Email (only used with --signup).")
    parser.add_argument("--first-name", default="Invitado",
                        help="First name (only used with --signup).")
    parser.add_argument("--last-name",  default="JUB",
                        help="Last name (only used with --signup).")
    args = parser.parse_args()

    print("JUB API Seed Script")
    print(f"  api-url    : {args.api_url}")
    print(f"  username   : {args.username}")
    print(f"  signup     : {args.signup}")
    print(f"  clean      : {args.clean}")
    print(f"  clean-only : {args.clean_only}")
    print()

    asyncio.run(seed(
        api_url    = args.api_url,
        username   = args.username,
        password   = args.password,
        scope      = args.scope,
        signup     = args.signup,
        email      = args.email,
        first_name = args.first_name,
        last_name  = args.last_name,
        clean      = args.clean,
        clean_only = args.clean_only,
    ))


if __name__ == "__main__":
    main()
