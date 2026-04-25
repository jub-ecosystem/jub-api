#!/usr/bin/env python3
"""
seed_api.py — Seeds JUB via the HTTP API (the right path for all users).

Unlike seed_db.py (which writes directly to MongoDB), this script goes through
the same endpoints that frontends and integrators use:

  1.  POST /api/v2/observatories/setup              → disabled observatory + PENDING task
  2.  POST /api/v2/observatories/{id}/catalogs/bulk → create & link all catalogs
  3.  GET  /api/v2/catalogs/{id}                    → fetch item IDs for product tagging
  4.  POST /api/v2/observatories/{id}/products/bulk → create & link products with tags
  5.  POST /api/v2/products/{id}/upload             → upload chart file (requires auth)
  6.  POST /api/v2/tasks/{task_id}/complete         → enable the observatory

Chart files uploaded come from the project's source/ directory:
  · source/heatmap.html  (geographic / spatial products)
  · source/radar.html    (multi-dimensional / temporal products)

Usage:
    python examples/seed_api.py
    python examples/seed_api.py --api-url http://localhost:5000
    python examples/seed_api.py --username admin --password secret
    python examples/seed_api.py --signup --username newuser --password pass \\
                                 --email me@example.com --first-name Ada --last-name Lovelace
"""

from __future__ import annotations

import argparse
import asyncio
import sys
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
# Domain data (same dataset as seed_db.py)
# ---------------------------------------------------------------------------

MEXICO_STATES: List[Tuple[int, str, str]] = [
    (1,  "Aguascalientes",                   "AGS"),
    (2,  "Baja California",                  "BC"),
    (3,  "Baja California Sur",              "BCS"),
    (4,  "Campeche",                         "CAM"),
    (5,  "Coahuila de Zaragoza",             "COAH"),
    (6,  "Colima",                           "COL"),
    (7,  "Chiapas",                          "CHIS"),
    (8,  "Chihuahua",                        "CHIH"),
    (9,  "Ciudad de Mexico",                 "CDMX"),
    (10, "Durango",                          "DGO"),
    (11, "Guanajuato",                       "GTO"),
    (12, "Guerrero",                         "GRO"),
    (13, "Hidalgo",                          "HGO"),
    (14, "Jalisco",                          "JAL"),
    (15, "Estado de Mexico",                 "MEX"),
    (16, "Michoacan de Ocampo",              "MICH"),
    (17, "Morelos",                          "MOR"),
    (18, "Nayarit",                          "NAY"),
    (19, "Nuevo Leon",                       "NL"),
    (20, "Oaxaca",                           "OAX"),
    (21, "Puebla",                           "PUE"),
    (22, "Queretaro",                        "QRO"),
    (23, "Quintana Roo",                     "QROO"),
    (24, "San Luis Potosi",                  "SLP"),
    (25, "Sinaloa",                          "SIN"),
    (26, "Sonora",                           "SON"),
    (27, "Tabasco",                          "TAB"),
    (28, "Tamaulipas",                       "TAMS"),
    (29, "Tlaxcala",                         "TLAX"),
    (30, "Veracruz de Ignacio de la Llave",  "VER"),
    (31, "Yucatan",                          "YUC"),
    (32, "Zacatecas",                        "ZAC"),
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
        for code, name, abbr in MEXICO_STATES
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

def _check(resp: httpx.Response, label: str) -> Dict:
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


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def do_login(client: httpx.AsyncClient, username: str,
                   password: str, scope: str) -> Tuple[str, str]:
    resp = await client.post("/users/auth", json={
        "username":   username,
        "password":   password,
        "scope":      scope,
        "expiration": "1h",
    })
    data = _check(resp, f"login as '{username}'")
    token          = data["access_token"]
    temporal_secret = data.get("temporal_secret_key") or ""
    user_id        = data["user_profile"]["user_id"]
    print(f"  ✓ Authenticated as '{username}' (user_id={user_id})")
    return token, temporal_secret, user_id


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
) -> None:

    # Validate source files exist before starting
    for f in (HEATMAP_FILE, RADAR_FILE):
        if not f.exists():
            print(f"  ✗ Source file not found: {f}")
            sys.exit(1)

    async with httpx.AsyncClient(base_url=api_url, timeout=60.0) as client:

        # ── Optional clean ──────────────────────────────────────────────────
        if clean:
            print("\n─── Cleaning existing observatories ──────────────────────────────")
            for obs_def in OBSERVATORIES:
                oid = obs_def["observatory_id"]
                resp = await client.delete(f"/observatories/{oid}")
                if resp.status_code in (200, 204):
                    print(f"  ✓ Deleted {oid}")
                elif resp.status_code == 404:
                    print(f"  · Not found (skip): {oid}")
                else:
                    print(f"  ✗ Delete {oid} [{resp.status_code}]: {resp.text[:200]}")

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
        # Set auth headers on the client so all subsequent requests (incl. multipart uploads) include them
        client.headers["Authorization"]      = f"Bearer {token}"
        client.headers["Temporal-Secret-Key"] = temporal_secret

        # ── Observatories ───────────────────────────────────────────────────
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
            catalog_ids = bulk_cats["catalog_ids"]
            label_to_cat_id = dict(zip(catalog_labels, catalog_ids))
            print(f"  ✓ {len(catalog_ids)} catalogs created and linked")

            # 3. Fetch each catalog to retrieve item IDs for product tagging
            label_to_item_ids: Dict[str, List[str]] = {}
            for label, cat_id in label_to_cat_id.items():
                cat_data = _check(
                    await client.get(f"/catalogs/{cat_id}"),
                    f"fetch catalog {label}",
                )
                label_to_item_ids[label] = extract_item_ids(cat_data["items"])
            print(f"  ✓ Catalog item IDs fetched for product tagging")

            # 4. Build and bulk-assign products
            products_in_obs = PRODUCTS_BY_OBS[obs_key]
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
            print(f"  ─ Uploading chart files …")
            for prod_def, created in zip(products_in_obs, created_products):
                pid       = created["product_id"]
                src_file  = HEATMAP_FILE if prod_def["chart"] == "heatmap" else RADAR_FILE

                with open(src_file, "rb") as fh:
                    upload_resp = await client.post(
                        f"/products/{pid}/upload",
                        files={"file": (src_file.name, fh, "text/html")},
                    )
                upload_data = _check(upload_resp, f"upload for {pid}")
                job_id = upload_data["job_id"]
                print(f"    → {prod_def['name'][:40]:<40} [{src_file.name}] job_id={job_id}")

            # 6. Complete setup task — enables the observatory
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
    print("  All observatories, catalogs, products, and files created via API.")
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
                        help="Delete existing observatories before seeding.")
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
    print(f"  api-url  : {args.api_url}")
    print(f"  username : {args.username}")
    print(f"  signup   : {args.signup}")
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
    ))


if __name__ == "__main__":
    main()
