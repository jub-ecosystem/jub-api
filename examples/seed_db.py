#!/usr/bin/env python3
"""
seed_db.py — Populates JUB with a realistic Mexican public-health dataset.

Domain : Mexican epidemiology — mortality, cancer, chronic diseases
Catalogs: SPATIAL (MX states), TEMPORAL (2015-2023), SEX, AGE_GROUP,
          CAUSA_DEFUNCION, CIE10_CANCER, DERECHOHABIENCIA
Entities: 3 observatories, 9 products, 3 data sources, ~2 500 synthetic records

Usage:
    python seed_db.py                       # default: mongodb://localhost:27027  db: jub
    python seed_db.py --clean               # drops + recreates
    python seed_db.py --mongo-uri URI --db-name NAME
"""

from __future__ import annotations
import argparse
import asyncio
import datetime as DT
import random
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


# ─────────────────────────────────────────────────────────────────────────────
# Tiny helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uid(prefix: str, n: int = 8) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:n]}"


def _now() -> DT.datetime:
    return DT.datetime.now(DT.timezone.utc)


def _usk(v: str) -> str:
    """Mirror of jubapi.models.v2.to_upper_snake."""
    v = re.sub(r"([a-z])([A-Z])", r"\1_\2", v)
    v = re.sub(r"[^A-Za-z0-9]+", "_", v)
    return v.upper().strip("_")


# ─────────────────────────────────────────────────────────────────────────────
# Domain data
# ─────────────────────────────────────────────────────────────────────────────

# (inegi_code, full_name, abbr, pop_M)   pop_M = approx 2020 population in millions
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

YEARS: List[int] = list(range(2015, 2024))   # 9 years

# (code, display_name, UPPER_SNAKE_value, description)
SEX_DATA = [
    (1, "Hombre",          "HOMBRE",           "Sexo biológico masculino"),
    (2, "Mujer",           "MUJER",            "Sexo biológico femenino"),
    (9, "No especificado", "NO_ESPECIFICADO",  "Sexo no registrado o indeterminado"),
]

AGE_GROUP_DATA = [
    (1, "0-4 años",       "G0_4",    "Infancia temprana"),
    (2, "5-14 años",      "G5_14",   "Infancia y preadolescencia"),
    (3, "15-24 años",     "G15_24",  "Adolescencia y juventud"),
    (4, "25-34 años",     "G25_34",  "Adultos jóvenes"),
    (5, "35-44 años",     "G35_44",  "Adultos en edad media"),
    (6, "45-54 años",     "G45_54",  "Adultos maduros"),
    (7, "55-64 años",     "G55_64",  "Adultos mayores tempranos"),
    (8, "65-74 años",     "G65_74",  "Adultos mayores"),
    (9, "75 años y más",  "G75_MAS", "Adultos mayores avanzados"),
]

# (code, name, value, cie10_range, cie10_description)
CAUSE_DEATH_DATA = [
    (1,  "Enfermedades isquemicas del corazon", "ISQUEMICA_CORAZON",   "I20-I25", "Infarto agudo de miocardio y cardiopatía isquémica"),
    (2,  "Diabetes mellitus",                   "DIABETES_MELLITUS",   "E10-E14", "Diabetes tipo 1, tipo 2 y otras formas"),
    (3,  "Tumores malignos",                    "TUMOR_MALIGNO",       "C00-D48", "Neoplasias malignas (todos los tipos)"),
    (4,  "Enfermedades cerebrovasculares",       "CEREBROVASCULAR",     "I60-I69", "Accidentes cerebrovasculares, hemorragia e infarto cerebral"),
    (5,  "Neumonia e influenza",                 "NEUMONIA_INFLUENZA",  "J09-J18", "Infecciones respiratorias agudas graves"),
    (6,  "Enfermedades del higado",              "ENFERMEDAD_HIGADO",   "K70-K76", "Cirrosis y enfermedad hepática"),
    (7,  "Accidentes de transito",               "ACCIDENTE_TRANSITO",  "V01-V99", "Lesiones por accidentes viales"),
    (8,  "Insuficiencia renal cronica",          "INSUFICIENCIA_RENAL", "N17-N19", "Enfermedad renal crónica y aguda"),
    (9,  "Hipertension arterial sistemica",      "HIPERTENSION",        "I10-I15", "Hipertensión esencial y secundaria"),
    (10, "COVID-19",                             "COVID_19",            "U07",     "Enfermedad por coronavirus 2019"),
]

# (code, name, value, cie10_range, iarc_group)
CANCER_CIE10_DATA = [
    (1,  "Labio, cavidad oral y faringe",          "C_ORAL_FARINGE",        "C00-C14", "Grupo 1"),
    (2,  "Esofago, estomago e intestinos",         "C_DIGESTIVO",           "C15-C26", "Grupo 1"),
    (3,  "Higado y vias biliares",                 "C_HIGADO",              "C22-C24", "Grupo 1"),
    (4,  "Pancreas",                               "C_PANCREAS",            "C25",     "Grupo 2A"),
    (5,  "Organos respiratorios (pulmon)",         "C_RESPIRATORIO",        "C30-C39", "Grupo 1"),
    (6,  "Mama",                                   "C_MAMA",                "C50",     "Grupo 1"),
    (7,  "Cervix uterino",                         "C_CERVIX",              "C53",     "Grupo 1"),
    (8,  "Cuerpo del utero",                       "C_UTERO",               "C54",     "Grupo 2A"),
    (9,  "Ovario",                                 "C_OVARIO",              "C56",     "Grupo 2A"),
    (10, "Prostata",                               "C_PROSTATA",            "C61",     "Grupo 2A"),
    (11, "Vias urinarias (vejiga y rinon)",        "C_URINARIO",            "C64-C68", "Grupo 1"),
    (12, "Cerebro y sistema nervioso central",     "C_SNC",                 "C70-C72", "Grupo 2B"),
    (13, "Tiroides",                               "C_TIROIDES",            "C73",     "Grupo 2A"),
    (14, "Tejido linfoide y hematopoyetico",       "C_LINFOHEMATOPOYETICO", "C81-C96", "Grupo 1"),
]

DERECHOHABIENCIA_DATA = [
    (1, "IMSS",                    "IMSS",                  "Instituto Mexicano del Seguro Social"),
    (2, "ISSSTE",                  "ISSSTE",                "Instituto de Seguridad y Servicios Sociales de los Trabajadores del Estado"),
    (3, "PEMEX / SEDENA / MARINA", "PEMEX_SEDENA_MARINA",   "Servicios medicos de PEMEX y fuerzas armadas"),
    (4, "Seguro Popular / INSABI", "SEGURO_POPULAR_INSABI", "Seguro Popular (hasta 2019) e INSABI (2020 en adelante)"),
    (5, "Seguro privado",          "PRIVADO",               "Seguro medico de contratacion privada"),
    (6, "Sin derechohabiencia",    "NINGUNA",               "Sin afiliacion a ningun servicio de salud"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Observatories, Products, catalog-link config
# ─────────────────────────────────────────────────────────────────────────────

OBSERVATORIES = [
    {
        "observatory_id": "obs_mortalidad_mx",
        "title":          "Observatorio de Mortalidad — Mexico",
        "description":    (
            "Monitorea las principales causas de muerte en México, su distribución "
            "geográfica y temporal, y las tendencias de mortalidad prematura por grupos "
            "de población. Fuente principal: Certificados de Defunción SINAVE-DGIS."
        ),
        "image_url": None,
        "metadata":  {"fuente": "SINAVE-DGIS", "pais": "MX", "version": "2023"},
    },
    {
        "observatory_id": "obs_cancer_mx",
        "title":          "Observatorio de Cancer — Mexico",
        "description":    (
            "Seguimiento epidemiológico de la incidencia y mortalidad por cáncer en México, "
            "con base en la clasificación CIE-10 y los grupos de riesgo IARC. "
            "Fuente: Registro Nacional de Cáncer / INCAN."
        ),
        "image_url": None,
        "metadata":  {"fuente": "INCAN / RNEC", "pais": "MX", "version": "2022"},
    },
    {
        "observatory_id": "obs_cronicas_mx",
        "title":          "Observatorio de Enfermedades Cronicas No Transmisibles",
        "description":    (
            "Analiza la prevalencia y mortalidad por diabetes mellitus, enfermedades "
            "cardiovasculares e hipertensión arterial en la población mexicana, "
            "desagregado por derechohabiencia, sexo y región. Fuente: ENSANUT / SINAVE."
        ),
        "image_url": None,
        "metadata":  {"fuente": "ENSANUT / SINAVE", "pais": "MX", "version": "2022"},
    },
]

PRODUCTS_BY_OBS: Dict[str, List[Dict]] = {
    "obs_mortalidad_mx": [
        {
            "product_id":  "prod_mort_causa_estado",
            "name":        "Mortalidad por Causa y Estado",
            "description": "Distribucion de defunciones por causa de muerte (top 10) y entidad federativa.",
            "tag_catalogs": ["CAUSA_DEFUNCION", "SPATIAL_MX"],
        },
        {
            "product_id":  "prod_mort_edad_sexo",
            "name":        "Mortalidad por Grupo de Edad y Sexo",
            "description": "Mortalidad según grupo etario y sexo. Identifica grupos vulnerables.",
            "tag_catalogs": ["SEX", "AGE_GROUP"],
        },
        {
            "product_id":  "prod_mort_tendencia",
            "name":        "Tendencia de Mortalidad 2015-2023",
            "description": "Serie temporal de mortalidad. Incluye el impacto del COVID-19 en 2020-2021.",
            "tag_catalogs": ["TEMPORAL_ANIOS", "CAUSA_DEFUNCION"],
        },
    ],
    "obs_cancer_mx": [
        {
            "product_id":  "prod_cancer_tipo_cie10",
            "name":        "Cancer por Tipo CIE-10 / IARC",
            "description": "Casos de cancer agrupados por CIE-10 y categorias IARC.",
            "tag_catalogs": ["CIE10_CANCER"],
        },
        {
            "product_id":  "prod_cancer_mortalidad_estado",
            "name":        "Mortalidad por Cancer por Entidad",
            "description": "Tasas de mortalidad oncologica por estado. Identifica estados con mayor carga.",
            "tag_catalogs": ["CIE10_CANCER", "SPATIAL_MX"],
        },
        {
            "product_id":  "prod_cancer_sexo_edad",
            "name":        "Cancer por Sexo y Grupo de Edad",
            "description": "Distribucion del cancer por sexo y grupo etario.",
            "tag_catalogs": ["SEX", "AGE_GROUP", "CIE10_CANCER"],
        },
    ],
    "obs_cronicas_mx": [
        {
            "product_id":  "prod_diabetes_estado",
            "name":        "Mortalidad por Diabetes Mellitus por Estado",
            "description": "Tasa de mortalidad por diabetes por cada 100k hab. por entidad federativa.",
            "tag_catalogs": ["CAUSA_DEFUNCION", "SPATIAL_MX"],
        },
        {
            "product_id":  "prod_cardio_tendencia",
            "name":        "Tendencia de Mortalidad Cardiovascular",
            "description": "Evolucion de la mortalidad por enfermedades isquemicas y cerebrovasculares.",
            "tag_catalogs": ["TEMPORAL_ANIOS", "CAUSA_DEFUNCION"],
        },
        {
            "product_id":  "prod_cronica_derecho",
            "name":        "Enfermedades Cronicas por Derechohabiencia",
            "description": "Mortalidad cronica segun afiliacion al sistema de salud.",
            "tag_catalogs": ["DERECHOHABIENCIA", "CAUSA_DEFUNCION"],
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Mortality realism: base deaths-per-100k by cause, age multipliers
# ─────────────────────────────────────────────────────────────────────────────

# Rough base deaths per 100k/year for each cause (adult average)
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
    "COVID_19":             0.0,   # added separately below for 2020-2021
}

# Multiplier by age group (younger → much lower)
AGE_MULTIPLIER: Dict[str, float] = {
    "G0_4":   0.05,
    "G5_14":  0.02,
    "G15_24": 0.08,
    "G25_34": 0.15,
    "G35_44": 0.30,
    "G45_54": 0.65,
    "G55_64": 1.40,
    "G65_74": 2.80,
    "G75_MAS":5.50,
}

# Sex multiplier for certain causes
SEX_CAUSE_MULTIPLIER: Dict[str, Dict[str, float]] = {
    "ISQUEMICA_CORAZON":   {"HOMBRE": 1.6,  "MUJER": 0.8,  "NO_ESPECIFICADO": 1.0},
    "DIABETES_MELLITUS":   {"HOMBRE": 0.9,  "MUJER": 1.1,  "NO_ESPECIFICADO": 1.0},
    "TUMOR_MALIGNO":       {"HOMBRE": 1.1,  "MUJER": 1.0,  "NO_ESPECIFICADO": 1.0},
    "ENFERMEDAD_HIGADO":   {"HOMBRE": 2.0,  "MUJER": 0.7,  "NO_ESPECIFICADO": 1.0},
    "ACCIDENTE_TRANSITO":  {"HOMBRE": 2.5,  "MUJER": 0.5,  "NO_ESPECIFICADO": 1.0},
    "COVID_19":             {"HOMBRE": 1.4,  "MUJER": 0.8,  "NO_ESPECIFICADO": 1.0},
}

# Cancer incidence per 100k (by sex, cancer type)
CANCER_BASE_RATE: Dict[str, Dict[str, float]] = {
    "C_MAMA":               {"HOMBRE": 1.0,   "MUJER": 38.0},
    "C_CERVIX":             {"HOMBRE": 0.0,   "MUJER": 22.0},
    "C_UTERO":              {"HOMBRE": 0.0,   "MUJER": 12.0},
    "C_OVARIO":             {"HOMBRE": 0.0,   "MUJER": 8.0},
    "C_PROSTATA":           {"HOMBRE": 25.0,  "MUJER": 0.0},
    "C_DIGESTIVO":          {"HOMBRE": 18.0,  "MUJER": 14.0},
    "C_RESPIRATORIO":       {"HOMBRE": 14.0,  "MUJER": 7.0},
    "C_HIGADO":             {"HOMBRE": 12.0,  "MUJER": 6.0},
    "C_LINFOHEMATOPOYETICO":{"HOMBRE": 8.0,   "MUJER": 6.5},
    "C_ORAL_FARINGE":       {"HOMBRE": 5.0,   "MUJER": 2.5},
    "C_URINARIO":           {"HOMBRE": 7.0,   "MUJER": 3.0},
    "C_TIROIDES":           {"HOMBRE": 2.5,   "MUJER": 7.0},
    "C_SNC":                {"HOMBRE": 4.5,   "MUJER": 3.5},
    "C_PANCREAS":           {"HOMBRE": 5.0,   "MUJER": 4.5},
}


# ─────────────────────────────────────────────────────────────────────────────
# Catalog builder
# ─────────────────────────────────────────────────────────────────────────────

class CatalogAccumulator:
    """Collects documents before bulk-inserting into MongoDB."""

    def __init__(self):
        self.catalogs:           List[Dict] = []
        self.items:              List[Dict] = []
        self.aliases:            List[Dict] = []
        self.cat_item_links:     List[Dict] = []   # catalog → item
        self.item_alias_links:   List[Dict] = []   # item → alias
        self.relationships:      List[Dict] = []   # parent_item → child_item

    # ── Catalog ──────────────────────────────────────────────────────────────

    def add_catalog(
        self,
        *,
        catalog_id: str,
        name: str,
        value: str,
        catalog_type: str,
        description: str = "",
    ) -> str:
        ts = _now()
        self.catalogs.append({
            "catalog_id":        catalog_id,
            "name":              name,
            "value":             _usk(value),
            "catalog_type":      catalog_type,
            "description":       description,
            "metadata":          {},
            "root_group_id":     None,
            "parent_catalog_id": None,
            "level":             0,
            "created_at":        ts,
            "updated_at":        ts,
        })
        return catalog_id

    # ── Item ─────────────────────────────────────────────────────────────────

    def add_item(
        self,
        *,
        catalog_id: str,
        name: str,
        value: str,
        code: int,
        catalog_type: str,
        value_type: str = "STRING",
        description: str = "",
        temporal_value: Optional[DT.datetime] = None,
        item_id: Optional[str] = None,
    ) -> str:
        item_id = item_id or _uid("itm")
        ts = _now()
        self.items.append({
            "catalog_item_id": item_id,
            "name":            name,
            "value":           _usk(value),
            "code":            code,
            "value_type":      value_type,
            "catalog_type":    catalog_type,
            "temporal_value":  temporal_value,
            "description":     description,
            "metadata":        {},
            "created_at":      ts,
            "updated_at":      ts,
        })
        ts2 = _now()
        self.cat_item_links.append({
            "catalog_id":      catalog_id,
            "catalog_item_id": item_id,
            "created_at":      ts2,
            "updated_at":      ts2,
        })
        return item_id

    # ── Alias ────────────────────────────────────────────────────────────────

    def add_alias(
        self,
        *,
        item_id: str,
        value: str,
        value_type: str = "STRING",
        description: str = "",
    ) -> str:
        alias_id = _uid("alias")
        ts = _now()
        self.aliases.append({
            "catalog_item_alias_id": alias_id,
            "value":                 value,
            "value_type":            value_type,
            "catalog_type":          None,
            "description":           description,
            "metadata":              {},
            "created_at":            ts,
            "updated_at":            ts,
        })
        ts2 = _now()
        self.item_alias_links.append({
            "catalog_item_id":       item_id,
            "catalog_item_alias_id": alias_id,
            "created_at":            ts2,
            "updated_at":            ts2,
        })
        return alias_id

    # ── Hierarchy ────────────────────────────────────────────────────────────

    def add_relationship(self, parent_id: str, child_id: str):
        ts = _now()
        self.relationships.append({
            "parent_id":  parent_id,
            "child_id":   child_id,
            "created_at": ts,
            "updated_at": ts,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Build catalogs
# ─────────────────────────────────────────────────────────────────────────────

def build_spatial(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    """Returns (catalog_id, {abbr -> item_id})."""
    cat_id = "cat_spatial_mx"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Dimension Espacial — Mexico",
        value="SPATIAL_MX",
        catalog_type="SPATIAL",
        description=(
            "Jerarquía geográfica de México: País → Estado. "
            "Códigos INEGI 2020. Fuente: INEGI."
        ),
    )

    # Root: Mexico
    mx_id = acc.add_item(
        catalog_id=cat_id,
        name="Mexico",
        value="MX",
        code=0,
        catalog_type="SPATIAL",
        description="República Mexicana",
        item_id="itm_mx",
    )
    acc.add_alias(item_id=mx_id, value="MEX",    description="ISO 3166-1 alpha-3")
    acc.add_alias(item_id=mx_id, value="484",    value_type="NUMBER", description="ISO 3166-1 numérico")
    acc.add_alias(item_id=mx_id, value="Mexico", description="Nombre en inglés")

    state_ids: Dict[str, str] = {}
    for code, name, abbr, _ in MEXICO_STATES:
        val = _usk(abbr)
        s_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="SPATIAL",
            description=f"Estado de {name}, México (INEGI {code:02d})",
            item_id=f"itm_mx_{abbr.lower()}",
        )
        acc.add_alias(item_id=s_id, value=str(code),         value_type="NUMBER", description="Clave INEGI del estado")
        acc.add_alias(item_id=s_id, value=abbr,              description="Abreviatura oficial")
        acc.add_alias(item_id=s_id, value=name,              description="Nombre completo")
        acc.add_alias(item_id=s_id, value=f"{code:02d}",     description="Clave INEGI con cero")
        # México is the parent of all states
        acc.add_relationship(mx_id, s_id)
        state_ids[abbr] = s_id

    return cat_id, state_ids


def build_temporal(acc: CatalogAccumulator) -> Tuple[str, Dict[int, str]]:
    """Returns (catalog_id, {year -> item_id})."""
    cat_id = "cat_temporal_anios"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Dimension Temporal — Años de Reporte",
        value="TEMPORAL_ANIOS",
        catalog_type="TEMPORAL",
        description="Años calendario 2015–2023 presentes en los registros de salud pública.",
    )
    year_ids: Dict[int, str] = {}
    for i, year in enumerate(YEARS, start=1):
        dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
        y_id = acc.add_item(
            catalog_id=cat_id,
            name=str(year),
            value=f"Y{year}",
            code=year,
            catalog_type="TEMPORAL",
            value_type="DATETIME",
            temporal_value=dt,
            description=f"Año de reporte {year}",
            item_id=f"itm_year_{year}",
        )
        acc.add_alias(item_id=y_id, value=str(year),          value_type="NUMBER",   description="Año como entero")
        acc.add_alias(item_id=y_id, value=f"AÑO_{year}",      description="Etiqueta en español")
        acc.add_alias(item_id=y_id, value=f"YEAR_{year}",     description="Etiqueta en inglés")
        year_ids[year] = y_id

    return cat_id, year_ids


def build_sex(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    cat_id = "cat_sex"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Sexo Biologico",
        value="SEX",
        catalog_type="INTEREST",
        description="Clasificación por sexo biológico al nacimiento según registros administrativos de salud.",
    )
    sex_ids: Dict[str, str] = {}
    for code, name, val, desc in SEX_DATA:
        s_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="INTEREST",
            item_id=f"itm_sex_{val.lower()}",
        )
        acc.add_alias(item_id=s_id, value=str(code), value_type="NUMBER", description="Código numérico SINAVE")
        sex_ids[val] = s_id

    return cat_id, sex_ids


def build_age_groups(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    cat_id = "cat_age_group"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Grupos de Edad",
        value="AGE_GROUP",
        catalog_type="INTEREST",
        description="Clasificación por grupos quinquenales de edad para análisis epidemiológico.",
    )
    age_ids: Dict[str, str] = {}
    for code, name, val, desc in AGE_GROUP_DATA:
        a_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="INTEREST",
            description=desc,
            item_id=f"itm_age_{val.lower()}",
        )
        acc.add_alias(item_id=a_id, value=str(code), value_type="NUMBER", description="Código numérico")
        age_ids[val] = a_id

    return cat_id, age_ids


def build_cause_death(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    cat_id = "cat_causa_defuncion"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Causa de Defuncion (Top 10)",
        value="CAUSA_DEFUNCION",
        catalog_type="INTEREST",
        description=(
            "Principales causas de muerte en México según la Clasificación Internacional "
            "de Enfermedades (CIE-10), edición 2023. Fuente: SINAVE-DGIS."
        ),
    )
    cause_ids: Dict[str, str] = {}
    for code, name, val, cie_range, cie_desc in CAUSE_DEATH_DATA:
        c_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="INTEREST",
            description=f"{cie_desc} ({cie_range})",
            item_id=f"itm_causa_{val.lower()}",
        )
        acc.add_alias(item_id=c_id, value=cie_range,  description="Rango CIE-10")
        acc.add_alias(item_id=c_id, value=str(code),  value_type="NUMBER", description="Código secuencial")
        cause_ids[val] = c_id

    return cat_id, cause_ids


def build_cancer_cie10(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    cat_id = "cat_cancer_cie10"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Grupos de Cancer CIE-10 / IARC",
        value="CIE10_CANCER",
        catalog_type="INTEREST",
        description=(
            "Agrupación de neoplasias malignas según la CIE-10 y la clasificación "
            "de carcinogenicidad IARC (Grupos 1, 2A, 2B). Fuente: OPS / IARC / INCAN."
        ),
    )
    cancer_ids: Dict[str, str] = {}
    for code, name, val, cie_range, iarc_group in CANCER_CIE10_DATA:
        c_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="INTEREST",
            description=f"CIE-10 {cie_range}. Clasificación IARC: {iarc_group}.",
            item_id=f"itm_cancer_{val.lower()}",
        )
        acc.add_alias(item_id=c_id, value=cie_range,  description="Rango CIE-10")
        acc.add_alias(item_id=c_id, value=iarc_group, description="Grupo de carcinogenicidad IARC")
        acc.add_alias(item_id=c_id, value=str(code),  value_type="NUMBER", description="Código secuencial")
        cancer_ids[val] = c_id

    return cat_id, cancer_ids


def build_derechohabiencia(acc: CatalogAccumulator) -> Tuple[str, Dict[str, str]]:
    cat_id = "cat_derechohabiencia"
    acc.add_catalog(
        catalog_id=cat_id,
        name="Derechohabiencia / Afiliacion al Sistema de Salud",
        value="DERECHOHABIENCIA",
        catalog_type="INTEREST",
        description=(
            "Tipo de afiliación o acceso al sistema de salud en México. "
            "Fuente: Certificados de Defunción / ENSANUT."
        ),
    )
    derecho_ids: Dict[str, str] = {}
    for code, name, val, desc in DERECHOHABIENCIA_DATA:
        d_id = acc.add_item(
            catalog_id=cat_id,
            name=name,
            value=val,
            code=code,
            catalog_type="INTEREST",
            description=desc,
            item_id=f"itm_derecho_{val.lower()}",
        )
        acc.add_alias(item_id=d_id, value=str(code), value_type="NUMBER", description="Código numérico")
        derecho_ids[val] = d_id

    return cat_id, derecho_ids


# ─────────────────────────────────────────────────────────────────────────────
# Data record generators
# ─────────────────────────────────────────────────────────────────────────────

def _rnd_deaths(base: float, pop_m: float, noise: float = 0.25) -> int:
    """Convert a base-rate-per-100k and population to an integer death count."""
    raw = (base / 100_000) * pop_m * 1_000_000
    jitter = random.uniform(1 - noise, 1 + noise)
    return max(1, round(raw * jitter))


def gen_mortality_records(
    source_id: str,
    state_ids: Dict[str, str],
    year_ids: Dict[int, str],
    sex_ids: Dict[str, str],
    age_ids: Dict[str, str],
    cause_ids: Dict[str, str],
) -> List[Dict]:
    """
    One record per (state, year, sex, age_group, cause).
    All 32 states × 9 years × 2 sexes × 9 age_groups × 10 causes
    is too large (~51k); we generate for ALL states but only for years 2015,
    2018, 2020, 2021, 2023 and for the 2 main sexes to keep it ~30k → still
    too many; let's do all years, all states, 2 sexes, but only 5 top causes.
    32 × 9 × 2 × 5 = 2 880 records.
    """
    records: List[Dict] = []
    top_causes = ["ISQUEMICA_CORAZON", "DIABETES_MELLITUS", "TUMOR_MALIGNO",
                  "CEREBROVASCULAR", "COVID_19"]
    # COVID only from 2020
    sexes = ["HOMBRE", "MUJER"]

    for _, name, abbr, pop_m in MEXICO_STATES:
        state_item_id = state_ids[abbr]
        for year in YEARS:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_item_id = sex_ids[sex_val]
                for cause_val in top_causes:
                    if cause_val == "COVID_19" and year < 2020:
                        continue
                    cause_item_id = cause_ids[cause_val]
                    base = CAUSE_BASE_RATE.get(cause_val, 10.0)
                    if cause_val == "COVID_19":
                        base = 90.0 if year == 2021 else 40.0  # peak / tail

                    sex_mult = SEX_CAUSE_MULTIPLIER.get(cause_val, {}).get(sex_val, 1.0)
                    # Distribute across age groups, weighted
                    for age_val, age_mult in AGE_MULTIPLIER.items():
                        if age_val not in age_ids:
                            continue
                        age_item_id = age_ids[age_val]
                        effective_rate = base * sex_mult * age_mult
                        count = _rnd_deaths(effective_rate, pop_m)
                        records.append({
                            "record_id":              _uid("rec", 10),
                            "source_id":              source_id,
                            "spatial_id":             state_item_id,
                            "temporal_id":            year_dt,
                            "interest_ids":           [sex_item_id, age_item_id, cause_item_id],
                            "numerical_interest_ids": {"COUNT": float(count), "TASA_100K": round(effective_rate, 2)},
                            "raw_payload": {
                                "estado": name,
                                "year":   year,
                                "sexo":   sex_val,
                                "edad":   age_val,
                                "causa":  cause_val,
                            },
                        })
    return records


def gen_cancer_records(
    source_id: str,
    state_ids: Dict[str, str],
    year_ids: Dict[int, str],
    sex_ids: Dict[str, str],
    cancer_ids: Dict[str, str],
) -> List[Dict]:
    """
    One record per (state, year, sex, cancer_type).
    20 states × 8 years × 2 sexes × 14 cancer types = 4 480  → subset:
    all 32 states × 5 years × 2 sexes × 8 most-prevalent types = 2 560.
    """
    records: List[Dict] = []
    cancer_years = [2015, 2017, 2019, 2020, 2022]
    sexes = ["HOMBRE", "MUJER"]
    top_cancers = [
        "C_MAMA", "C_PROSTATA", "C_DIGESTIVO", "C_RESPIRATORIO",
        "C_LINFOHEMATOPOYETICO", "C_CERVIX", "C_HIGADO", "C_TIROIDES",
    ]

    for _, name, abbr, pop_m in MEXICO_STATES:
        state_item_id = state_ids[abbr]
        for year in cancer_years:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_item_id = sex_ids[sex_val]
                for cancer_val in top_cancers:
                    if cancer_val not in cancer_ids:
                        continue
                    cancer_item_id = cancer_ids[cancer_val]
                    base = CANCER_BASE_RATE.get(cancer_val, {}).get(sex_val, 0.0)
                    if base == 0.0:
                        continue  # skip sex-specific cancers when they don't apply
                    count = _rnd_deaths(base, pop_m, noise=0.30)
                    records.append({
                        "record_id":              _uid("rec", 10),
                        "source_id":              source_id,
                        "spatial_id":             state_item_id,
                        "temporal_id":            year_dt,
                        "interest_ids":           [sex_item_id, cancer_item_id],
                        "numerical_interest_ids": {"COUNT": float(count), "TASA_100K": round(base, 2)},
                        "raw_payload": {
                            "estado":  name,
                            "year":    year,
                            "sexo":    sex_val,
                            "cancer":  cancer_val,
                        },
                    })
    return records


def gen_chronic_records(
    source_id: str,
    state_ids: Dict[str, str],
    year_ids: Dict[int, str],
    sex_ids: Dict[str, str],
    cause_ids: Dict[str, str],
    derecho_ids: Dict[str, str],
) -> List[Dict]:
    """
    One record per (state, year, sex, cause, derechohabiencia).
    32 × 5 years × 2 sexes × 3 causes × 6 derecho = 5 760  → too many.
    Use 32 × 4 years × 2 sexes × 3 causes (no derecho split) = 768.
    """
    records: List[Dict] = []
    chronic_years = [2016, 2018, 2020, 2022]
    sexes = ["HOMBRE", "MUJER"]
    chronic_causes = ["DIABETES_MELLITUS", "ISQUEMICA_CORAZON", "HIPERTENSION"]

    for _, name, abbr, pop_m in MEXICO_STATES:
        state_item_id = state_ids[abbr]
        for year in chronic_years:
            year_dt = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc)
            for sex_val in sexes:
                sex_item_id = sex_ids[sex_val]
                for cause_val in chronic_causes:
                    if cause_val not in cause_ids:
                        continue
                    cause_item_id = cause_ids[cause_val]
                    base = CAUSE_BASE_RATE.get(cause_val, 10.0)
                    sex_mult = SEX_CAUSE_MULTIPLIER.get(cause_val, {}).get(sex_val, 1.0)
                    count = _rnd_deaths(base * sex_mult, pop_m)
                    # Pick a random derechohabiencia split
                    for d_val, d_id in derecho_ids.items():
                        split = {"IMSS": 0.35, "ISSSTE": 0.08,
                                 "PEMEX_SEDENA_MARINA": 0.03,
                                 "SEGURO_POPULAR_INSABI": 0.30,
                                 "PRIVADO": 0.05, "NINGUNA": 0.19}.get(d_val, 0.1)
                        d_count = max(1, round(count * split * random.uniform(0.85, 1.15)))
                        records.append({
                            "record_id":              _uid("rec", 10),
                            "source_id":              source_id,
                            "spatial_id":             state_item_id,
                            "temporal_id":            year_dt,
                            "interest_ids":           [sex_item_id, cause_item_id, d_id],
                            "numerical_interest_ids": {"COUNT": float(d_count), "PREVALENCIA_100K": round(base * sex_mult, 2)},
                            "raw_payload": {
                                "estado":            name,
                                "year":              year,
                                "sexo":              sex_val,
                                "causa":             cause_val,
                                "derechohabiencia":  d_val,
                            },
                        })
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Main seed coroutine
# ─────────────────────────────────────────────────────────────────────────────

async def seed(mongo_uri: str, db_name: str, clean: bool) -> None:
    rng_seed = 42
    random.seed(rng_seed)

    client = AsyncIOMotorClient(mongo_uri)
    db: AsyncIOMotorDatabase = client[db_name]

    # ── Optional clean ──────────────────────────────────────────────────────
    if clean:
        drop_cols = [
            "observatories", "products",
            "catalogs", "catalog_items", "catalog_item_aliases",
            "observatory_product_links", "product_catalogs_item_links",
            "catalog_item_relationships", "catalog_catalog_item_links",
            "catalog_item_catalog_alias_links", "observatory_catalog_links",
            "data_sources", "data_records",
        ]
        for col in drop_cols:
            await db.drop_collection(col)
            print(f"  🗑  dropped {col}")

    print("\n─── Step 1: Build catalogs ───────────────────────────────────────")
    acc                          = CatalogAccumulator()
    spatial_cat_id,  state_ids   = build_spatial(acc)
    temporal_cat_id, year_ids    = build_temporal(acc)
    sex_cat_id,      sex_ids     = build_sex(acc)
    age_cat_id,      age_ids     = build_age_groups(acc)
    cause_cat_id,    cause_ids   = build_cause_death(acc)
    cancer_cat_id,   cancer_ids  = build_cancer_cie10(acc)
    derecho_cat_id,  derecho_ids = build_derechohabiencia(acc)

    all_cat_ids: Dict[str, str] = {
        "SPATIAL_MX":      spatial_cat_id,
        "TEMPORAL_ANIOS":  temporal_cat_id,
        "SEX":             sex_cat_id,
        "AGE_GROUP":       age_cat_id,
        "CAUSA_DEFUNCION": cause_cat_id,
        "CIE10_CANCER":    cancer_cat_id,
        "DERECHOHABIENCIA":derecho_cat_id,
    }

    # Bulk inserts
    await db["catalogs"].insert_many(acc.catalogs)
    await db["catalog_items"].insert_many(acc.items)
    if acc.aliases:
        await db["catalog_item_aliases"].insert_many(acc.aliases)
    if acc.cat_item_links:
        await db["catalog_catalog_item_links"].insert_many(acc.cat_item_links)
    if acc.item_alias_links:
        await db["catalog_item_catalog_alias_links"].insert_many(acc.item_alias_links)
    if acc.relationships:
        await db["catalog_item_relationships"].insert_many(acc.relationships)

    print(f"  ✓ {len(acc.catalogs)} catalogs")
    print(f"  ✓ {len(acc.items)} catalog items")
    print(f"  ✓ {len(acc.aliases)} aliases")
    print(f"  ✓ {len(acc.cat_item_links)} catalog→item links")
    print(f"  ✓ {len(acc.item_alias_links)} item→alias links")
    print(f"  ✓ {len(acc.relationships)} item→item relationships")

    print("\n─── Step 2: Create observatories ─────────────────────────────────")
    obs_docs = []
    for obs in OBSERVATORIES:
        ts = _now()
        obs_docs.append({**obs, "created_at": ts, "updated_at": ts})
    await db["observatories"].insert_many(obs_docs)
    print(f"  ✓ {len(obs_docs)} observatories")

    print("\n─── Step 3: Create products & link to observatories ──────────────")
    all_product_docs: List[Dict] = []
    obs_product_link_docs: List[Dict] = []
    product_catalog_item_link_docs: List[Dict] = []

    for obs_id, products in PRODUCTS_BY_OBS.items():
        for prod in products:
            ts = _now()
            all_product_docs.append({
                "product_id":  prod["product_id"],
                "name":        prod["name"],
                "description": prod["description"],
                "metadata":    {},
                "created_at":  ts,
                "updated_at":  ts,
            })
            ts2 = _now()
            obs_product_link_docs.append({
                "observatory_id": obs_id,
                "product_id":     prod["product_id"],
                "created_at":     ts2,
                "updated_at":     ts2,
            })
            # Tag product with catalog items
            for cat_label in prod.get("tag_catalogs", []):
                cat_id = all_cat_ids.get(cat_label)
                if not cat_id:
                    continue
                # Grab first 3 items of that catalog to tag the product
                tagged = [
                    itm["catalog_item_id"]
                    for itm in acc.items
                    if itm.get("catalog_id") is None  # items don't store catalog_id directly
                ]
                # Filter by matching items in cat_item_links
                linked_item_ids = [
                    lnk["catalog_item_id"]
                    for lnk in acc.cat_item_links
                    if lnk["catalog_id"] == cat_id
                ][:5]
                for item_id in linked_item_ids:
                    ts3 = _now()
                    product_catalog_item_link_docs.append({
                        "product_id":      prod["product_id"],
                        "catalog_item_id": item_id,
                        "created_at":      ts3,
                        "updated_at":      ts3,
                    })

    await db["products"].insert_many(all_product_docs)
    await db["observatory_product_links"].insert_many(obs_product_link_docs)
    if product_catalog_item_link_docs:
        await db["product_catalogs_item_links"].insert_many(product_catalog_item_link_docs)
    print(f"  ✓ {len(all_product_docs)} products")
    print(f"  ✓ {len(obs_product_link_docs)} observatory→product links")
    print(f"  ✓ {len(product_catalog_item_link_docs)} product→catalog-item tags")

    print("\n─── Step 4: Link observatories to catalogs ───────────────────────")
    obs_catalog_link_docs: List[Dict] = []
    catalog_sets = {
        "obs_mortalidad_mx": [spatial_cat_id, temporal_cat_id, sex_cat_id, age_cat_id, cause_cat_id],
        "obs_cancer_mx":     [spatial_cat_id, temporal_cat_id, sex_cat_id, age_cat_id, cancer_cat_id],
        "obs_cronicas_mx":   [spatial_cat_id, temporal_cat_id, sex_cat_id, cause_cat_id, derecho_cat_id],
    }
    for obs_id, cat_ids in catalog_sets.items():
        for lvl, c_id in enumerate(cat_ids):
            ts = _now()
            obs_catalog_link_docs.append({
                "observatory_id": obs_id,
                "catalog_id":     c_id,
                "level":          lvl,
                "created_at":     ts,
                "updated_at":     ts,
            })
    await db["observatory_catalog_links"].insert_many(obs_catalog_link_docs)
    print(f"  ✓ {len(obs_catalog_link_docs)} observatory→catalog links")

    print("\n─── Step 5: Create data sources ─────────────────────────────────")
    ts = _now()
    sources = [
        {
            "source_id":      "src_sinave_defunciones",
            "name":           "SINAVE — Certificados de Defuncion 2015-2023",
            "description":    "Certificados de defunción con causa de muerte CIE-10 capturados por el SINAVE/DGIS para todas las entidades federativas.",
            "format":         "csv",
            "bucket_id":      "jub",
            "ball_id":        "",
            "connection_uri": None,
        },
        {
            "source_id":      "src_incan_registro_cancer",
            "name":           "Registro Nacional de Cancer INCAN 2015-2022",
            "description":    "Casos de cáncer registrados por el INCAN y la Red del Registro Histopatológico de Neoplasias en México.",
            "format":         "csv",
            "bucket_id":      "jub",
            "ball_id":        "",
            "connection_uri": None,
        },
        {
            "source_id":      "src_ensanut_cronicas",
            "name":           "ENSANUT — Enfermedades Cronicas 2016-2022",
            "description":    "Encuesta Nacional de Salud y Nutrición, módulo de enfermedades crónicas no transmisibles por derechohabiencia.",
            "format":         "csv",
            "bucket_id":      "jub",
            "ball_id":        "",
            "connection_uri": None,
        },
    ]
    for src in sources:
        src["created_at"] = _now()
    await db["data_sources"].insert_many(sources)
    print(f"  ✓ {len(sources)} data sources")

    print("\n─── Step 6: Generate data records ───────────────────────────────")
    mort_records = gen_mortality_records(
        "src_sinave_defunciones", state_ids, year_ids, sex_ids, age_ids, cause_ids
    )
    cancer_records = gen_cancer_records(
        "src_incan_registro_cancer", state_ids, year_ids, sex_ids, cancer_ids
    )
    chronic_records = gen_chronic_records(
        "src_ensanut_cronicas", state_ids, year_ids, sex_ids, cause_ids, derecho_ids
    )

    all_records = mort_records + cancer_records + chronic_records
    print(f"  · mortality records:  {len(mort_records):>5}")
    print(f"  · cancer records:     {len(cancer_records):>5}")
    print(f"  · chronic records:    {len(chronic_records):>5}")
    print(f"  · total:              {len(all_records):>5}")

    # Bulk insert in chunks to avoid large BSON documents
    CHUNK = 500
    for i in range(0, len(all_records), CHUNK):
        await db["data_records"].insert_many(all_records[i : i + CHUNK])
    print(f"  ✓ {len(all_records)} data records inserted")

    print("\n─── Done ─────────────────────────────────────────────────────────")
    print("  Database populated successfully.")
    print(f"  URI:      {mongo_uri}")
    print(f"  Database: {db_name}")
    client.close()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed the JUB database with sample health data.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27027",  help="MongoDB connection URI")
    parser.add_argument("--db-name",   default="jub",                        help="Target database name")
    parser.add_argument("--clean",     action="store_true",                  help="Drop existing data before seeding")
    args = parser.parse_args()

    print(f"JUB Seed Script")
    print(f"  mongo-uri : {args.mongo_uri}")
    print(f"  db-name   : {args.db_name}")
    print(f"  clean     : {args.clean}")
    print()

    asyncio.run(seed(args.mongo_uri, args.db_name, args.clean))


if __name__ == "__main__":
    main()
