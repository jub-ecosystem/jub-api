"""
Domain data shared by the JUB client examples.

Same theme as examples/seed_api.py: public-health mortality data for Mexico.
The builders return plain dicts that match `CatalogCreateDTO`, so they can be
passed to the client as-is or wrapped in the DTO.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# (inegi_code, full_name, abbr, population_millions)
MEXICO_STATES = [
    (1,  "Aguascalientes",                  "AGS",  1.43),
    (2,  "Baja California",                 "BC",   3.77),
    (3,  "Baja California Sur",             "BCS",  0.80),
    (4,  "Campeche",                        "CAM",  1.00),
    (5,  "Coahuila de Zaragoza",            "COAH", 3.15),
    (6,  "Colima",                          "COL",  0.73),
    (7,  "Chiapas",                         "CHIS", 5.54),
    (8,  "Chihuahua",                       "CHIH", 3.74),
    (9,  "Ciudad de Mexico",                "CDMX", 9.21),
    (10, "Durango",                         "DGO",  1.83),
    (11, "Guanajuato",                      "GTO",  6.17),
    (12, "Guerrero",                        "GRO",  3.54),
    (13, "Hidalgo",                         "HGO",  3.08),
    (14, "Jalisco",                         "JAL",  8.35),
    (15, "Estado de Mexico",                "MEX",  16.99),
    (16, "Michoacan de Ocampo",             "MICH", 4.75),
    (17, "Morelos",                         "MOR",  1.97),
    (18, "Nayarit",                         "NAY",  1.24),
    (19, "Nuevo Leon",                      "NL",   5.78),
    (20, "Oaxaca",                          "OAX",  4.13),
    (21, "Puebla",                          "PUE",  6.58),
    (22, "Queretaro",                       "QRO",  2.37),
    (23, "Quintana Roo",                    "QROO", 1.86),
    (24, "San Luis Potosi",                 "SLP",  2.82),
    (25, "Sinaloa",                         "SIN",  3.03),
    (26, "Sonora",                          "SON",  2.94),
    (27, "Tabasco",                         "TAB",  2.40),
    (28, "Tamaulipas",                      "TAMS", 3.64),
    (29, "Tlaxcala",                        "TLAX", 1.34),
    (30, "Veracruz de Ignacio de la Llave", "VER",  8.06),
    (31, "Yucatan",                         "YUC",  2.32),
    (32, "Zacatecas",                       "ZAC",  1.62),
]

# States on the US border, used to show one item belonging to two catalogs.
NORTHERN_BORDER_STATES = ["BC", "SON", "CHIH", "COAH", "NL", "TAMS"]

YEARS = list(range(2015, 2024))

SEX_DATA = [
    (1, "Hombre",          "HOMBRE"),
    (2, "Mujer",           "MUJER"),
    (9, "No especificado", "NO_ESPECIFICADO"),
]

AGE_GROUP_DATA = [
    (1, "0-4 años",      "G0_4",    "Infancia temprana"),
    (2, "5-14 años",     "G5_14",   "Infancia y preadolescencia"),
    (3, "15-24 años",    "G15_24",  "Adolescencia y juventud"),
    (4, "25-34 años",    "G25_34",  "Adultos jovenes"),
    (5, "35-44 años",    "G35_44",  "Adultos en edad media"),
    (6, "45-54 años",    "G45_54",  "Adultos maduros"),
    (7, "55-64 años",    "G55_64",  "Adultos mayores tempranos"),
    (8, "65-74 años",    "G65_74",  "Adultos mayores"),
    (9, "75 años y más", "G75_MAS", "Adultos mayores avanzados"),
]

# Base mortality rate per 100k inhabitants, used to generate records in 10.
CAUSE_BASE_RATE: Dict[str, float] = {
    "ISQUEMICA_CORAZON": 85.0,
    "DIABETES_MELLITUS": 75.0,
    "TUMOR_MALIGNO":     60.0,
    "CEREBROVASCULAR":   32.0,
    "COVID_19":          40.0,
}


# ---------------------------------------------------------------------------
# Payload builders (CatalogCreateDTO-shaped dicts)
# ---------------------------------------------------------------------------

def alias(value: str, value_type: str = "STRING", description: str = "") -> Dict[str, Any]:
    return {"value": value, "value_type": value_type, "description": description}


def item(
    name: str,
    value: str,
    code: int,
    value_type: str = "STRING",
    description: str = "",
    aliases: Optional[List[Dict]] = None,
    children: Optional[List[Dict]] = None,
    temporal_value: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "name":           name,
        "value":          value,
        "code":           code,
        "value_type":     value_type,
        "description":    description,
        "temporal_value": temporal_value,
        "aliases":        aliases or [],
        "children":       children or [],
    }


def spatial_catalog() -> Dict[str, Any]:
    """Two-level hierarchy: Mexico → 32 states. Each state has 2 aliases."""
    states = [
        item(
            name        = name,
            value       = abbr,
            code        = code,
            description = f"Entidad federativa {code:02d} (INEGI)",
            aliases     = [
                alias(name,          "STRING", "Nombre oficial"),
                alias(f"{code:02d}", "STRING", "Clave INEGI"),
            ],
        )
        for code, name, abbr, _ in MEXICO_STATES
    ]
    mexico = item(
        name        = "Mexico",
        value       = "MX",
        code        = 0,
        description = "Republica Mexicana",
        aliases     = [alias("MEX", "STRING", "ISO 3166-1 alpha-3"), alias("484", "NUMBER", "ISO 3166-1 numerico")],
        children    = states,
    )
    return {
        "name":         "Dimension Espacial — Mexico",
        "value":        "SPATIAL_MX",
        "catalog_type": "SPATIAL",
        "description":  "Jerarquia geografica de Mexico: Pais → Estado. Codigos INEGI 2020.",
        "items":        [mexico],
    }


def sex_catalog() -> Dict[str, Any]:
    return {
        "name":         "Sexo Biologico",
        "value":        "SEX",
        "catalog_type": "INTEREST",
        "description":  "Clasificacion por sexo biologico segun registros administrativos de salud.",
        "items": [
            item(name, value, code, aliases=[alias(str(code), "NUMBER", "Codigo SINAVE")])
            for code, name, value in SEX_DATA
        ],
    }


def age_group_catalog() -> Dict[str, Any]:
    return {
        "name":         "Grupos de Edad",
        "value":        "AGE_GROUP",
        "catalog_type": "INTEREST",
        "description":  "Grupos quinquenales de edad para analisis epidemiologico.",
        "items": [
            item(name, value, code, description=desc)
            for code, name, value, desc in AGE_GROUP_DATA
        ],
    }


# ---------------------------------------------------------------------------
# Products (06) — `tag_catalogs` are the catalogs (keys from 03/05) whose items
# tag the product; `chart` is the file under source/ uploaded in 07/09.
# ---------------------------------------------------------------------------

PRODUCTS: List[Dict[str, Any]] = [
    {
        "key":          "mort_causa_estado",
        "name":         "Mortalidad por Causa y Estado",
        "description":  "Distribucion de defunciones por causa de muerte (top 10) y entidad federativa.",
        "tag_catalogs": ["causa_defuncion", "spatial"],
        "chart":        "heatmap.html",
    },
    {
        "key":          "mort_edad_sexo",
        "name":         "Mortalidad por Grupo de Edad y Sexo",
        "description":  "Mortalidad segun grupo etario y sexo. Identifica grupos vulnerables.",
        "tag_catalogs": ["sex", "age_group"],
        "chart":        "radar.html",
    },
    {
        "key":          "mort_tendencia",
        "name":         "Tendencia de Mortalidad 2015-2023",
        "description":  "Serie temporal de mortalidad. Incluye el impacto del COVID-19 en 2020-2021.",
        "tag_catalogs": ["temporal", "causa_defuncion"],
        "chart":        "radar.html",
    },
    {
        "key":          "cronicas_derecho",
        "name":         "Enfermedades Cronicas por Derechohabiencia",
        "description":  "Mortalidad cronica segun afiliacion al sistema de salud.",
        "tag_catalogs": ["derechohabiencia", "causa_defuncion"],
        "chart":        "radar.html",
    },
    {
        # Created without tags on purpose — tagged in 08.
        "key":          "mort_covid_estado",
        "name":         "Mortalidad por COVID-19 por Estado",
        "description":  "Defunciones por COVID-19 por entidad federativa, 2020-2023.",
        "tag_catalogs": [],
        "chart":        "heatmap.html",
    },
]
