#!/usr/bin/env python3
"""
seed_scenario_1.py — Three-observatory stress scenario seeded via the HTTP API.

Observatory 1  (observatory-1)  — VS + VT only, 10 products
Observatory 2  (observatory-2)  — VS 3-level + VI Cancer CIE-10 2-level + VT, 100 products, aliases
Observatory 3  (observatory-3)  — VS + VT + Sex + Age + Cause (10 levels), 1000 products

Every product gets:
  • Mandatory VS tag  (random Mexican state)
  • Mandatory VT tag  (random year 1970-2026)
  • Random VI tags    (per observatory catalogue)
  • A random file uploaded from  data/figs/

Each observatory gets:
  • randint(1, 5) data sources  linked via POST /observatories/{id}/datasources
  • randint(1, 10) services     linked via POST /observatories/{id}/services

Usage:
    python examples/seed_scenario_1.py
    python examples/seed_scenario_1.py --clean
    python examples/seed_scenario_1.py --clean-only
    python examples/seed_scenario_1.py --api-url http://localhost:5000/api/v2 --username admin --password secret
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent.parent
FIGS_DIR = ROOT_DIR / "data" / "figs"

# ---------------------------------------------------------------------------
# Domain data
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

YEARS_1970_2026 = list(range(1970, 2027))

# 3 broad cancer groups with the 14 CIE-10 types distributed as children
CANCER_GROUPS = [
    {
        "name": "Canceres Reproductivos",
        "value": "C_REPRODUCTIVO_GRP",
        "code": 100,
        "children": [
            (6,  "Mama",           "C_MAMA",    "C50"),
            (7,  "Cervix uterino", "C_CERVIX",  "C53"),
            (8,  "Utero",          "C_UTERO",   "C54"),
            (9,  "Ovario",         "C_OVARIO",  "C56"),
            (10, "Prostata",       "C_PROSTATA","C61"),
        ],
    },
    {
        "name": "Canceres Digestivos y Respiratorios",
        "value": "C_DIGESTIVO_GRP",
        "code": 200,
        "children": [
            (1,  "Labio y cavidad oral",        "C_ORAL_FARINGE",  "C00-C14"),
            (2,  "Esofago, estomago e intestinos","C_DIGESTIVO",   "C15-C26"),
            (3,  "Higado y vias biliares",       "C_HIGADO",       "C22-C24"),
            (4,  "Pancreas",                     "C_PANCREAS",     "C25"),
            (5,  "Organos respiratorios",        "C_RESPIRATORIO", "C30-C39"),
        ],
    },
    {
        "name": "Otros Canceres",
        "value": "C_OTROS_GRP",
        "code": 300,
        "children": [
            (11, "Vias urinarias",              "C_URINARIO",            "C64-C68"),
            (12, "Cerebro y SNC",               "C_SNC",                 "C70-C72"),
            (13, "Tiroides",                    "C_TIROIDES",            "C73"),
            (14, "Tejido linfoide/hematopoyetico","C_LINFOHEMATOPOYETICO","C81-C96"),
        ],
    },
]

SEX_ITEMS = [
    (1, "Hombre",          "HOMBRE"),
    (2, "Mujer",           "MUJER"),
    (3, "No especificado", "NO_ESPECIFICADO"),
]

AGE_BROAD_GROUPS = [
    {
        "name": "Infancia y Adolescencia",
        "value": "AGE_JOVEN_GRP",
        "code": 10,
        "children": [
            (1, "0-4 anios",   "G0_4",   "Infancia temprana"),
            (2, "5-14 anios",  "G5_14",  "Infancia y preadolescencia"),
            (3, "15-24 anios", "G15_24", "Adolescencia y juventud"),
        ],
    },
    {
        "name": "Adultos",
        "value": "AGE_ADULTO_GRP",
        "code": 20,
        "children": [
            (4, "25-34 anios", "G25_34", "Adultos jovenes"),
            (5, "35-44 anios", "G35_44", "Adultos en edad media"),
            (6, "45-54 anios", "G45_54", "Adultos maduros"),
            (7, "55-64 anios", "G55_64", "Adultos mayores tempranos"),
        ],
    },
    {
        "name": "Adultos Mayores",
        "value": "AGE_MAYOR_GRP",
        "code": 30,
        "children": [
            (8, "65-74 anios",    "G65_74",  "Adultos mayores"),
            (9, "75 anios y mas", "G75_MAS", "Adultos mayores avanzados"),
        ],
    },
]

CAUSE_CATEGORY_GROUPS = [
    {
        "name": "Enfermedades Cardiovasculares",
        "value": "CAUSA_CARDIO_GRP",
        "code": 10,
        "children": [
            (1, "Enfermedades isquemicas del corazon", "ISQUEMICA_CORAZON",   "I20-I25"),
            (4, "Enfermedades cerebrovasculares",       "CEREBROVASCULAR",     "I60-I69"),
            (9, "Hipertension arterial sistemica",      "HIPERTENSION",        "I10-I15"),
        ],
    },
    {
        "name": "Enfermedades Metabolicas e Infecciosas",
        "value": "CAUSA_METABOLICA_GRP",
        "code": 20,
        "children": [
            (2, "Diabetes mellitus",     "DIABETES_MELLITUS",  "E10-E14"),
            (5, "Neumonia e influenza",  "NEUMONIA_INFLUENZA",  "J09-J18"),
            (10,"COVID-19",              "COVID_19",            "U07"),
        ],
    },
    {
        "name": "Otras Causas",
        "value": "CAUSA_OTRAS_GRP",
        "code": 30,
        "children": [
            (3, "Tumores malignos",           "TUMOR_MALIGNO",       "C00-D48"),
            (6, "Enfermedades del higado",    "ENFERMEDAD_HIGADO",   "K70-K76"),
            (7, "Accidentes de transito",     "ACCIDENTE_TRANSITO",  "V01-V99"),
            (8, "Insuficiencia renal cronica","INSUFICIENCIA_RENAL", "N17-N19"),
        ],
    },
]

# Municipalities sampled per state (abbr -> list of (name, value))
SAMPLE_MUNICIPALITIES: Dict[str, List[Tuple[str, str]]] = {
    "AGS":  [("Aguascalientes", "MUN_AGS_1"), ("Asientos", "MUN_AGS_2"), ("Calvillo", "MUN_AGS_3")],
    "BC":   [("Tijuana", "MUN_BC_1"), ("Mexicali", "MUN_BC_2"), ("Ensenada", "MUN_BC_3")],
    "CDMX": [("Benito Juarez", "MUN_CDMX_1"), ("Iztapalapa", "MUN_CDMX_2"), ("Coyoacan", "MUN_CDMX_3")],
    "JAL":  [("Guadalajara", "MUN_JAL_1"), ("Zapopan", "MUN_JAL_2"), ("Tlaquepaque", "MUN_JAL_3")],
    "MEX":  [("Toluca", "MUN_MEX_1"), ("Ecatepec", "MUN_MEX_2"), ("Naucalpan", "MUN_MEX_3")],
    "NL":   [("Monterrey", "MUN_NL_1"), ("San Nicolas", "MUN_NL_2"), ("Apodaca", "MUN_NL_3")],
    "PUE":  [("Puebla", "MUN_PUE_1"), ("Tehuacan", "MUN_PUE_2"), ("San Andres Cholula", "MUN_PUE_3")],
    "VER":  [("Veracruz", "MUN_VER_1"), ("Xalapa", "MUN_VER_2"), ("Coatzacoalcos", "MUN_VER_3")],
}

SERVICE_NAMES = [
    "Analisis Epidemiologico Automatico",
    "Deteccion de Anomalias Temporales",
    "Generador de Reportes PDF",
    "Clasificador de Riesgo Poblacional",
    "Proyeccion de Tendencias",
    "Alertas de Mortalidad Excesiva",
    "Exportador FHIR R4",
    "Comparador Interobservatorio",
    "Indexador de Productos",
    "Monitor de Actualizaciones",
    "Validador de Registros",
    "Servicio de Geocodificacion",
    "Pipeline de Ingestion Continua",
    "Motor de Busqueda Semantica",
    "Servicio de Visualizacion Avanzada",
]

DATASOURCE_NAMES = [
    "SINAVE — Certificados de Defuncion",
    "INEGI — Estadisticas Vitales",
    "ENSANUT — Encuesta Nacional de Salud",
    "INCAN — Registro Nacional de Cancer",
    "IMSS — Estadisticas de Salud",
    "ISSSTE — Datos de Derechohabiencia",
    "SSA — Sistema Nacional de Salud",
    "CONAPO — Proyecciones de Poblacion",
    "RHNM — Red Hospitalaria Nacional",
    "SUIVE — Sistema de Vigilancia Epidemiologica",
]

# ---------------------------------------------------------------------------
# DTO helpers
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


# ---------------------------------------------------------------------------
# Catalog builders
# ---------------------------------------------------------------------------

def build_spatial_obs1() -> Dict:
    """VS: Country -> 32 States (2 levels)."""
    state_items = [
        _item(
            name        = name,
            value       = abbr,
            code        = code,
            description = f"Estado {name} (INEGI {code:02d})",
            aliases     = [
                _alias(str(code),     "NUMBER", "Clave INEGI"),
                _alias(f"{code:02d}", "STRING", "Clave INEGI con cero"),
                _alias(name,          "STRING", "Nombre completo"),
            ],
        )
        for code, name, abbr in MEXICO_STATES
    ]
    mx_root = _item(
        name="Mexico", value="MX", code=0,
        description="Republica Mexicana",
        aliases=[_alias("MEX", "STRING", "ISO alpha-3"), _alias("484", "NUMBER", "ISO numerico")],
        children=state_items,
    )
    return {
        "name": "Dimension Espacial — Mexico",
        "value": "SPATIAL_MX",
        "catalog_type": "SPATIAL",
        "description": "Jerarquia geografica: Pais -> Estado.",
        "items": [mx_root],
    }


def build_spatial_obs2() -> Dict:
    """VS: Country -> State -> Municipality (3 levels), only states with sample municipalities."""
    state_items = []
    for code, name, abbr in MEXICO_STATES:
        munis = SAMPLE_MUNICIPALITIES.get(abbr, [])
        muni_items = [
            _item(
                name=mname, value=mval, code=code * 100 + i + 1,
                description=f"Municipio de {mname}, {name}",
                aliases=[
                    _alias(mname, "STRING", "Nombre completo"),
                    _alias(mval,  "STRING", "Clave interna"),
                ],
            )
            for i, (mname, mval) in enumerate(munis)
        ]
        state_items.append(
            _item(
                name=name, value=abbr, code=code,
                description=f"Estado {name} (INEGI {code:02d})",
                aliases=[
                    _alias(str(code),     "NUMBER", "Clave INEGI"),
                    _alias(abbr,          "STRING", "Abreviatura"),
                    _alias(f"{abbr}_EST", "STRING", "Etiqueta estado"),
                ],
                children=muni_items,
            )
        )
    mx_root = _item(
        name="Mexico", value="MX", code=0,
        description="Republica Mexicana",
        aliases=[_alias("MEX", "STRING", "ISO alpha-3")],
        children=state_items,
    )
    return {
        "name": "Dimension Espacial — Mexico (con municipios)",
        "value": "SPATIAL_MX_MUN",
        "catalog_type": "SPATIAL",
        "description": "Jerarquia geografica: Pais -> Estado -> Municipio.",
        "items": [mx_root],
    }


def build_temporal(obs_idx: int) -> Dict:
    """VT: years 1970-2026 as temporal items."""
    items = [
        _item(
            name=str(year), value=f"Y{year}", code=year,
            value_type="DATETIME",
            description=f"Anio de reporte {year}",
            temporal_value=f"{year}-01-01T00:00:00Z",
            aliases=[
                _alias(str(year),      "NUMBER", "Anio como entero"),
                _alias(f"YEAR_{year}", "STRING", "Etiqueta en ingles"),
            ],
        )
        for year in YEARS_1970_2026
    ]
    return {
        "name": f"Dimension Temporal 1970-2026",
        "value": f"TEMPORAL_OBS{obs_idx}",
        "catalog_type": "TEMPORAL",
        "description": "Anos calendario 1970-2026.",
        "items": items,
    }


def build_cancer_cie10_hierarchical() -> Dict:
    """VI: 3 cancer groups -> 14 types (2 levels)."""
    group_items = []
    for grp in CANCER_GROUPS:
        children = [
            _item(
                name=cname, value=cval, code=ccode,
                description=f"CIE-10 {cie}",
                aliases=[
                    _alias(cie,       "STRING", "Rango CIE-10"),
                    _alias(str(ccode),"NUMBER", "Codigo secuencial"),
                    _alias(cval,      "STRING", "Clave interna"),
                ],
            )
            for ccode, cname, cval, cie in grp["children"]
        ]
        group_items.append(
            _item(
                name=grp["name"], value=grp["value"], code=grp["code"],
                description=f"Grupo oncologico: {grp['name']}",
                aliases=[_alias(grp["value"], "STRING", "Clave de grupo")],
                children=children,
            )
        )
    return {
        "name": "Cancer CIE-10 — Grupos y Tipos",
        "value": "CIE10_CANCER_HIER",
        "catalog_type": "INTEREST",
        "description": "Neoplasias malignas CIE-10, agrupadas en 3 categorias con 14 tipos hoja.",
        "items": group_items,
    }


def build_sex() -> Dict:
    items = [
        _item(
            name=name, value=val, code=code,
            aliases=[
                _alias(str(code), "NUMBER", "Codigo numerico"),
                _alias(val,       "STRING", "Clave interna"),
            ],
        )
        for code, name, val in SEX_ITEMS
    ]
    return {
        "name": "Sexo Biologico",
        "value": "SEX",
        "catalog_type": "INTEREST",
        "description": "Clasificacion por sexo biologico.",
        "items": items,
    }


def build_age_hierarchical() -> Dict:
    """VI: 3 broad groups -> 9 age groups (2 levels -> 3 total with leaves)."""
    broad_items = []
    for grp in AGE_BROAD_GROUPS:
        children = [
            _item(
                name=cname, value=cval, code=ccode,
                description=cdesc,
                aliases=[_alias(str(ccode), "NUMBER", "Codigo")],
            )
            for ccode, cname, cval, cdesc in grp["children"]
        ]
        broad_items.append(
            _item(
                name=grp["name"], value=grp["value"], code=grp["code"],
                description=f"Grupo etario: {grp['name']}",
                aliases=[_alias(grp["value"], "STRING", "Clave de grupo")],
                children=children,
            )
        )
    return {
        "name": "Grupos de Edad",
        "value": "AGE_GROUP_HIER",
        "catalog_type": "INTEREST",
        "description": "Clasificacion etaria en 3 grupos amplios con 9 subgrupos.",
        "items": broad_items,
    }


def build_cause_hierarchical() -> Dict:
    """VI: 3 cause categories -> 10 causes (2 levels)."""
    cat_items = []
    for grp in CAUSE_CATEGORY_GROUPS:
        children = [
            _item(
                name=cname, value=cval, code=ccode,
                description=f"CIE-10 {cie}",
                aliases=[
                    _alias(cie,       "STRING", "Rango CIE-10"),
                    _alias(str(ccode),"NUMBER", "Codigo secuencial"),
                ],
            )
            for ccode, cname, cval, cie in grp["children"]
        ]
        cat_items.append(
            _item(
                name=grp["name"], value=grp["value"], code=grp["code"],
                description=f"Categoria: {grp['name']}",
                aliases=[_alias(grp["value"], "STRING", "Clave de categoria")],
                children=children,
            )
        )
    return {
        "name": "Causa de Defuncion",
        "value": "CAUSA_DEFUNCION_HIER",
        "catalog_type": "INTEREST",
        "description": "Causas de defuncion en 3 categorias con 10 causas hoja.",
        "items": cat_items,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(resp: httpx.Response, label: str) -> Any:
    if resp.status_code >= 300:
        print(f"\n  ✗ {label} failed [{resp.status_code}]: {resp.text[:400]}")
        sys.exit(1)
    return resp.json()


def _uid(n: int = 8) -> str:
    return uuid.uuid4().hex[:n]


def extract_leaf_ids(items: List[Dict]) -> List[str]:
    """Return only leaf item IDs (no children)."""
    ids: List[str] = []
    for item in items:
        children = item.get("children") or []
        if children:
            ids.extend(extract_leaf_ids(children))
        else:
            ids.append(item["catalog_item_id"])
    return ids


def extract_all_ids(items: List[Dict]) -> List[str]:
    """Return all item IDs including intermediate nodes."""
    ids: List[str] = []
    for item in items:
        ids.append(item["catalog_item_id"])
        if item.get("children"):
            ids.extend(extract_all_ids(item["children"]))
    return ids


def pick_figs(figs: List[Path], n: int) -> List[Path]:
    """Return n random fig paths (with replacement if needed)."""
    if not figs:
        return []
    return [random.choice(figs) for _ in range(n)]


async def upload_file(client: httpx.AsyncClient, product_id: str, fig: Path) -> None:
    mime = "image/jpeg" if fig.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    with open(fig, "rb") as fh:
        resp = await client.post(
            f"/products/{product_id}/upload",
            files={"file": (fig.name, fh, mime)},
        )
    if resp.status_code >= 300:
        print(f"    ⚠  upload failed for {product_id} [{resp.status_code}]")
    else:
        print(f"    ↑ {product_id} ← {fig.name}")


async def upload_batch(client: httpx.AsyncClient, pairs: List[Tuple[str, Path]], batch_size: int = 10) -> None:
    for i in range(0, len(pairs), batch_size):
        chunk = pairs[i: i + batch_size]
        await asyncio.gather(*[upload_file(client, pid, fig) for pid, fig in chunk])


async def create_and_link_datasources(
    client: httpx.AsyncClient,
    obs_id: str,
    obs_idx: int,
    n: int,
    used_sources: List[str],
) -> None:
    for m in range(1, n + 1):
        name = random.choice(DATASOURCE_NAMES)
        ds_data = _check(
            await client.post("/datasources", json={
                "name":        f"{name} — obs{obs_idx}-ds{m}",
                "description": f"Fuente de datos {m} para observatory-{obs_idx}.",
            }),
            f"create datasource obs{obs_idx}-{m}",
        )
        source_id = ds_data["source_id"]
        used_sources.append(source_id)
        _check(
            await client.post(f"/observatories/{obs_id}/datasources",
                              json={"source_id": source_id}),
            f"link datasource {source_id} to {obs_id}",
        )
    print(f"  ✓ {n} data sources created and linked")


async def create_and_link_services(
    client: httpx.AsyncClient,
    obs_id: str,
    obs_idx: int,
    n: int,
    user_id: str,
    used_services: List[str],
) -> None:
    for m in range(1, n + 1):
        name = random.choice(SERVICE_NAMES)
        svc_data = _check(
            await client.post("/services", json={
                "name":        f"{name} ({obs_idx}-{m})",
                "description": f"Servicio {m} para observatory-{obs_idx}.",
                "owner_id":    user_id,
                "public":      False,
                "provider":    "OTHER",
            }),
            f"create service obs{obs_idx}-{m}",
        )
        service_id = svc_data["service_id"]
        used_services.append(service_id)
        _check(
            await client.post(f"/observatories/{obs_id}/services",
                              json={"service_id": service_id}),
            f"link service {service_id} to {obs_id}",
        )
    print(f"  ✓ {n} services created and linked")


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

async def clean_scenario(client: httpx.AsyncClient) -> None:
    print("\n─── Cleaning scenario-1 entities ────────────────────────────────")

    # Remove the 3 scenario observatories (cascade removes obs→product links)
    for i in range(1, 4):
        obs_id = f"observatory-{i}"
        resp = await client.delete(f"/observatories/{obs_id}")
        if resp.status_code in (200, 204):
            print(f"  ✓ Deleted {obs_id}")
        elif resp.status_code == 404:
            print(f"  · Not found (skip): {obs_id}")
        else:
            print(f"  ✗ [{resp.status_code}] {obs_id}: {resp.text[:200]}")

    # Remove products
    print("  · Removing scenario products…")
    prod_list = _check(await client.get("/products", params={"limit": 2000}), "list products")
    scenario_prods = [p for p in prod_list if p["product_id"].startswith("product-")]
    for prod in scenario_prods:
        pid  = prod["product_id"]
        resp = await client.delete(f"/products/{pid}")
        if resp.status_code in (200, 204):
            print(f"    ✓ Deleted {pid}")
        elif resp.status_code != 404:
            print(f"    ✗ [{resp.status_code}] {pid}")

    # Remove datasources created for this scenario
    print("  · Removing scenario datasources…")
    ds_list = _check(await client.get("/datasources"), "list datasources")
    for ds in ds_list:
        if "obs1" in ds["name"] or "obs2" in ds["name"] or "obs3" in ds["name"]:
            sid  = ds["source_id"]
            resp = await client.delete(f"/datasources/{sid}")
            if resp.status_code in (200, 204):
                print(f"    ✓ Deleted datasource {sid}")

    print("  ✓ Clean complete.\n")


# ---------------------------------------------------------------------------
# Observatory seeders
# ---------------------------------------------------------------------------

async def seed_observatory_1(
    client: httpx.AsyncClient,
    figs: List[Path],
    user_id: str,
) -> None:
    obs_idx = 1
    obs_id  = f"observatory-{obs_idx}"
    print(f"\n─── Observatory {obs_idx}: VS + VT — 10 products ─────────────────────")

    # 1. Setup
    setup = _check(await client.post("/observatories/setup", json={
        "observatory_id": obs_id,
        "title":          "Observatory 1 — Espacial y Temporal",
        "description":    "Escenario minimo: solo dimensiones espacial (VS) y temporal (VT).",
        "user_id":        user_id,
        "metadata":       {"scenario": "1", "obs_index": "1"},
    }), "obs1 setup")
    task_id = setup["task_id"]
    print(f"  ✓ Observatory created — task_id={task_id}")

    # 2. Catalogs
    catalogs_payload = [build_spatial_obs1(), build_temporal(obs_idx)]
    bulk = _check(await client.post(f"/observatories/{obs_id}/catalogs/bulk",
                                    json={"catalogs": catalogs_payload}), "obs1 catalogs")
    cat_ids = bulk["catalog_ids"]
    print(f"  ✓ {len(cat_ids)} catalogs created")

    # 3. Fetch item IDs
    spatial_cat  = _check(await client.get(f"/catalogs/{cat_ids[0]}"), "obs1 spatial cat")
    temporal_cat = _check(await client.get(f"/catalogs/{cat_ids[1]}"), "obs1 temporal cat")
    state_ids = extract_leaf_ids(spatial_cat["items"])   # 32 states
    year_ids  = extract_all_ids(temporal_cat["items"])   # 57 years

    # 4. Products
    products_payload = []
    for j in range(1, 11):
        pid = f"product-{obs_idx}-{j}"
        tag_ids = [random.choice(state_ids), random.choice(year_ids)]
        products_payload.append({
            "product_id":       pid,
            "name":             f"Producto {obs_idx}-{j}",
            "description":      f"Producto {j} del observatorio {obs_idx}. VS+VT.",
            "catalog_item_ids": tag_ids,
        })
    bulk_p = _check(await client.post(f"/observatories/{obs_id}/products/bulk",
                                      json={"products": products_payload}), "obs1 products")
    created = bulk_p["products"]
    print(f"  ✓ {len(created)} products created")

    # 5. Upload random fig per product
    if figs:
        pairs = [(p["product_id"], random.choice(figs)) for p in created]
        print(f"  ─ Uploading {len(pairs)} figs…")
        await upload_batch(client, pairs)
    else:
        print("  ⚠  data/figs/ is empty — skipping uploads")

    # 6. Datasources + Services
    n_ds  = random.randint(1, 5)
    n_svc = random.randint(1, 10)
    used_sources: List[str] = []
    used_services: List[str] = []
    await create_and_link_datasources(client, obs_id, obs_idx, n_ds, used_sources)
    await create_and_link_services(client, obs_id, obs_idx, n_svc, user_id, used_services)

    # 7. Complete task
    _check(await client.post(f"/tasks/{task_id}/complete",
                             json={"success": True, "message": "Seeded by seed_scenario_1.py."}),
           "obs1 complete")
    print(f"  ✓ Observatory enabled")


async def seed_observatory_2(
    client: httpx.AsyncClient,
    figs: List[Path],
    user_id: str,
) -> None:
    obs_idx = 2
    obs_id  = f"observatory-{obs_idx}"
    print(f"\n─── Observatory {obs_idx}: VS(3-level) + VI Cancer(2-level) + VT — 100 products ─")

    setup = _check(await client.post("/observatories/setup", json={
        "observatory_id": obs_id,
        "title":          "Observatory 2 — Espacial Profundo + Cancer CIE-10",
        "description":    "VS pais->estado->municipio, VI cancer jerarquico 2 niveles, VT 1970-2026.",
        "user_id":        user_id,
        "metadata":       {"scenario": "1", "obs_index": "2"},
    }), "obs2 setup")
    task_id = setup["task_id"]
    print(f"  ✓ Observatory created — task_id={task_id}")

    catalogs_payload = [build_spatial_obs2(), build_cancer_cie10_hierarchical(), build_temporal(obs_idx)]
    bulk = _check(await client.post(f"/observatories/{obs_id}/catalogs/bulk",
                                    json={"catalogs": catalogs_payload}), "obs2 catalogs")
    cat_ids = bulk["catalog_ids"]
    print(f"  ✓ {len(cat_ids)} catalogs created")

    spatial_cat  = _check(await client.get(f"/catalogs/{cat_ids[0]}"), "obs2 spatial cat")
    cancer_cat   = _check(await client.get(f"/catalogs/{cat_ids[1]}"), "obs2 cancer cat")
    temporal_cat = _check(await client.get(f"/catalogs/{cat_ids[2]}"), "obs2 temporal cat")

    muni_ids    = extract_leaf_ids(spatial_cat["items"])    # municipalities
    state_ids   = [i["catalog_item_id"] for i in extract_all_ids_with_depth(spatial_cat["items"], depth=1)]
    cancer_leaf = extract_leaf_ids(cancer_cat["items"])     # 14 cancer types
    year_ids    = extract_all_ids(temporal_cat["items"])

    # fallback: use state ids if no municipalities
    vs_pool = muni_ids if muni_ids else extract_leaf_ids(spatial_cat["items"])

    products_payload = []
    for j in range(1, 101):
        pid = f"product-{obs_idx}-{j}"
        # mandatory VS + VT
        tag_ids = [random.choice(vs_pool), random.choice(year_ids)]
        # random 0-3 cancer tags
        n_vi = random.randint(0, 3)
        if n_vi:
            tag_ids.extend(random.sample(cancer_leaf, min(n_vi, len(cancer_leaf))))
        products_payload.append({
            "product_id":       pid,
            "name":             f"Producto {obs_idx}-{j}",
            "description":      f"Producto {j} — espacial profundo y cancer CIE-10.",
            "catalog_item_ids": list(set(tag_ids)),
        })

    bulk_p = _check(await client.post(f"/observatories/{obs_id}/products/bulk",
                                      json={"products": products_payload}), "obs2 products")
    created = bulk_p["products"]
    print(f"  ✓ {len(created)} products created")

    if figs:
        pairs = [(p["product_id"], random.choice(figs)) for p in created]
        print(f"  ─ Uploading {len(pairs)} figs (batched)…")
        await upload_batch(client, pairs)
    else:
        print("  ⚠  data/figs/ is empty — skipping uploads")

    n_ds  = random.randint(1, 5)
    n_svc = random.randint(1, 10)
    used_sources: List[str] = []
    used_services: List[str] = []
    await create_and_link_datasources(client, obs_id, obs_idx, n_ds, used_sources)
    await create_and_link_services(client, obs_id, obs_idx, n_svc, user_id, used_services)

    _check(await client.post(f"/tasks/{task_id}/complete",
                             json={"success": True, "message": "Seeded by seed_scenario_1.py."}),
           "obs2 complete")
    print(f"  ✓ Observatory enabled")


async def seed_observatory_3(
    client: httpx.AsyncClient,
    figs: List[Path],
    user_id: str,
) -> None:
    obs_idx = 3
    obs_id  = f"observatory-{obs_idx}"
    print(f"\n─── Observatory {obs_idx}: 10 levels (VS+VT+Sex+Age+Cause) — 1000 products ──")

    setup = _check(await client.post("/observatories/setup", json={
        "observatory_id": obs_id,
        "title":          "Observatory 3 — Multidimensional Completo",
        "description":    "VS+VT+Sexo+Edad(jerarquico)+Causa(jerarquico). 10 niveles, 1000 productos.",
        "user_id":        user_id,
        "metadata":       {"scenario": "1", "obs_index": "3"},
    }), "obs3 setup")
    task_id = setup["task_id"]
    print(f"  ✓ Observatory created — task_id={task_id}")

    catalogs_payload = [
        build_spatial_obs1(),         # VS: 2 levels
        build_temporal(obs_idx),      # VT: 1 level
        build_sex(),                  # VI-1: 1 level (flat)
        build_age_hierarchical(),     # VI-2: 3 levels (broad->group->leaf)
        build_cause_hierarchical(),   # VI-3: 3 levels (category->cause)
    ]
    bulk = _check(await client.post(f"/observatories/{obs_id}/catalogs/bulk",
                                    json={"catalogs": catalogs_payload}), "obs3 catalogs")
    cat_ids = bulk["catalog_ids"]
    print(f"  ✓ {len(cat_ids)} catalogs created (10 total hierarchy levels)")

    spatial_cat = _check(await client.get(f"/catalogs/{cat_ids[0]}"), "obs3 spatial")
    temporal_cat= _check(await client.get(f"/catalogs/{cat_ids[1]}"), "obs3 temporal")
    sex_cat     = _check(await client.get(f"/catalogs/{cat_ids[2]}"), "obs3 sex")
    age_cat     = _check(await client.get(f"/catalogs/{cat_ids[3]}"), "obs3 age")
    cause_cat   = _check(await client.get(f"/catalogs/{cat_ids[4]}"), "obs3 cause")

    state_ids = extract_leaf_ids(spatial_cat["items"])
    year_ids  = extract_all_ids(temporal_cat["items"])
    sex_ids   = extract_all_ids(sex_cat["items"])
    age_ids   = extract_leaf_ids(age_cat["items"])
    cause_ids = extract_leaf_ids(cause_cat["items"])

    print(f"  ─ Building 1000 product payloads…")
    products_payload = []
    for j in range(1, 1001):
        pid = f"product-{obs_idx}-{j}"
        tag_ids = [
            random.choice(state_ids),   # mandatory VS
            random.choice(year_ids),    # mandatory VT
            random.choice(sex_ids),     # 1 sex item
            random.choice(age_ids),     # 1 age leaf
            random.choice(cause_ids),   # 1 cause leaf
        ]
        products_payload.append({
            "product_id":       pid,
            "name":             f"Producto {obs_idx}-{j}",
            "description":      f"Producto {j} — multidimensional completo.",
            "catalog_item_ids": list(set(tag_ids)),
        })

    # Bulk in chunks of 200 to avoid huge payloads
    created: List[Dict] = []
    CHUNK = 200
    for i in range(0, len(products_payload), CHUNK):
        chunk = products_payload[i: i + CHUNK]
        resp = _check(await client.post(f"/observatories/{obs_id}/products/bulk",
                                        json={"products": chunk}), f"obs3 products chunk {i // CHUNK + 1}")
        created.extend(resp["products"])
        print(f"    · chunk {i // CHUNK + 1}: {len(resp['products'])} products")
    print(f"  ✓ {len(created)} products created")

    if figs:
        pairs = [(p["product_id"], random.choice(figs)) for p in created]
        print(f"  ─ Uploading {len(pairs)} figs (batched x10)…")
        await upload_batch(client, pairs, batch_size=10)
    else:
        print("  ⚠  data/figs/ is empty — skipping uploads")

    n_ds  = random.randint(1, 5)
    n_svc = random.randint(1, 10)
    used_sources: List[str] = []
    used_services: List[str] = []
    await create_and_link_datasources(client, obs_id, obs_idx, n_ds, used_sources)
    await create_and_link_services(client, obs_id, obs_idx, n_svc, user_id, used_services)

    _check(await client.post(f"/tasks/{task_id}/complete",
                             json={"success": True, "message": "Seeded by seed_scenario_1.py."}),
           "obs3 complete")
    print(f"  ✓ Observatory enabled")


def extract_all_ids_with_depth(items: List[Dict], depth: int, current: int = 0) -> List[Dict]:
    """Return items at exactly the given depth level."""
    result = []
    for item in items:
        if current == depth:
            result.append(item)
        elif item.get("children"):
            result.extend(extract_all_ids_with_depth(item["children"], depth, current + 1))
    return result


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def do_login(client: httpx.AsyncClient, username: str, password: str, scope: str) -> Tuple[str, str, str]:
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
# Entry point
# ---------------------------------------------------------------------------

async def run(
    api_url:    str,
    username:   str,
    password:   str,
    scope:      str,
    clean:      bool,
    clean_only: bool,
) -> None:
    random.seed(42)

    figs = sorted(FIGS_DIR.glob("*")) if FIGS_DIR.exists() else []
    figs = [f for f in figs if f.is_file()]
    if not figs:
        print(f"  ⚠  No files found in {FIGS_DIR} — uploads will be skipped")
    else:
        print(f"  ✓ Found {len(figs)} fig(s) in {FIGS_DIR}")

    async with httpx.AsyncClient(base_url=api_url, timeout=300.0) as client:
        print("\n─── Auth ─────────────────────────────────────────────────────────")
        token, temporal_secret, user_id = await do_login(client, username, password, scope)
        client.headers["Authorization"]       = f"Bearer {token}"
        client.headers["Temporal-Secret-Key"] = temporal_secret

        if clean or clean_only:
            await clean_scenario(client)
            if clean_only:
                print("─── Done (clean only) ────────────────────────────────────────────")
                return

        await seed_observatory_1(client, figs, user_id)
        await seed_observatory_2(client, figs, user_id)
        await seed_observatory_3(client, figs, user_id)

    print("\n─── Done ─────────────────────────────────────────────────────────")
    print("  Scenario 1 complete: 3 observatories, 1110 products, data sources, services.")
    print(f"  API: {api_url}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed JUB scenario 1 via the HTTP API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api-url",    default="http://localhost:5000/api/v2")
    parser.add_argument("--username",   default="invitado")
    parser.add_argument("--password",   default="invitado")
    parser.add_argument("--scope",      default="jub")
    parser.add_argument("--clean",      action="store_true",
                        help="Delete scenario entities before seeding.")
    parser.add_argument("--clean-only", action="store_true",
                        help="Delete scenario entities and exit.")
    args = parser.parse_args()
    asyncio.run(run(
        api_url    = args.api_url,
        username   = args.username,
        password   = args.password,
        scope      = args.scope,
        clean      = args.clean,
        clean_only = args.clean_only,
    ))


if __name__ == "__main__":
    main()
