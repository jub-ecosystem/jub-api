"""
generate_catalogs.py
Reads muestra_benceno.csv and produces 4 CatalogCreateDTO-compatible payloads:

  1. SPATIAL   — Mexico → States → Municipalities  (3-level hierarchy)
  2. TEMPORAL  — Unique report years
  3. SUSTANCIA — Chemical substances + CAS / IARC aliases
  4. NOM_UMBRAL — Regulatory thresholds (EYT & MPU)

Output: catalogs.json  (list of CatalogCreateDTO dicts, ready for POST /catalogs)
"""

import csv
import json
import datetime
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional

CSV_PATH    = Path("./muestra_benceno.csv")
OUTPUT_PATH = Path("./catalogs.json")


# ──────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────

def to_upper_snake(v: str) -> str:
    v = re.sub(r'([a-z])([A-Z])', r'\1_\2', v)
    v = re.sub(r'[^A-Za-z0-9]+', '_', v)
    return v.upper().strip('_')

def alias(value: str, value_type: str = "STRING", description: str = "") -> Dict:
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
) -> Dict:
    return {
        "name"          : name,
        "value"         : to_upper_snake(value),
        "code"          : code,
        "value_type"    : value_type,
        "description"   : description,
        "temporal_value": temporal_value,
        "aliases"       : aliases  or [],
        "children"      : children or [],
    }

def catalog(
    name: str,
    value: str,
    catalog_type: str,
    description: str = "",
    items: Optional[List[Dict]] = None,
) -> Dict:
    return {
        "name"        : name,
        "value"       : to_upper_snake(value),
        "catalog_type": catalog_type,
        "description" : description,
        "items"       : items or [],
    }


# ──────────────────────────────────────────────────────────────
# 1. SPATIAL  (Mexico → State → Municipality)
# ──────────────────────────────────────────────────────────────

def build_spatial_catalog(rows: List[Dict]) -> Dict:
    # Collect unique states and their municipalities
    # state_code -> { name, municipalities: { mun_code -> name } }
    states: Dict[str, Dict] = {}

    for row in rows:
        s_code = row["estado_cve_ent"].strip()
        s_name = row["estado_nombre"].strip()
        m_code = row["municipio_cve_mun"].strip()
        m_name = row["municipio_nombre"].strip()

        if s_code not in states:
            states[s_code] = {"name": s_name, "municipalities": {}}
        states[s_code]["municipalities"][m_code] = m_name

    # Build state items (with municipality children)
    state_items = []
    for s_code, s_data in sorted(states.items(), key=lambda x: int(x[0])):
        s_name  = s_data["name"]
        s_value = to_upper_snake(s_name)

        # Municipality children
        mun_items = []
        for m_code, m_name in sorted(s_data["municipalities"].items(), key=lambda x: int(x[0])):
            mun_items.append(item(
                name        = m_name,
                value       = to_upper_snake(m_name),
                code        = int(m_code),
                value_type  = "STRING",
                description = f"Municipio de {m_name}, {s_name}",
                aliases     = [
                    alias(m_code,  "INTEGER", "Clave INEGI del municipio"),
                    alias(m_name,  "STRING",  "Nombre oficial"),
                ],
            ))

        state_items.append(item(
            name        = s_name,
            value       = s_value,
            code        = int(s_code),
            value_type  = "STRING",
            description = f"Estado de {s_name}, México",
            aliases     = [
                alias(s_code,  "INTEGER", "Clave INEGI del estado"),
                alias(s_name,  "STRING",  "Nombre oficial"),
            ],
            children    = mun_items,
        ))

    # Root Mexico item wrapping all states
    mexico = item(
        name        = "México",
        value       = "MX",
        code        = 0,
        value_type  = "STRING",
        description = "República Mexicana",
        aliases     = [
            alias("MEX",    "STRING",  "Código ISO 3166-1 alpha-3"),
            alias("Mexico", "STRING",  "Nombre en inglés"),
            alias("484",    "INTEGER", "Código numérico ISO 3166-1"),
        ],
        children    = state_items,
    )

    return catalog(
        name         = "Dimensión Espacial — México",
        value        = "SPATIAL_MX",
        catalog_type = "SPATIAL",
        description  = "Jerarquía geográfica: País → Estado → Municipio (fuente: INEGI)",
        items        = [mexico],
    )


# ──────────────────────────────────────────────────────────────
# 2. TEMPORAL  (unique report years)
# ──────────────────────────────────────────────────────────────

def build_temporal_catalog(rows: List[Dict]) -> Dict:
    years = sorted({int(row["anio"].strip()) for row in rows})

    year_items = []
    for code, year in enumerate(years, start=1):
        dt_str = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc).isoformat()
        year_items.append(item(
            name           = str(year),
            value          = f"Y{year}",
            code           = year,
            value_type     = "DATETIME",
            temporal_value = dt_str,
            description    = f"Año de reporte {year}",
            aliases        = [
                alias(str(year),         "INTEGER", "Año como entero"),
                alias(f"AÑO_{year}",     "STRING",  "Etiqueta en español"),
                alias(f"YEAR_{year}",    "STRING",  "Etiqueta en inglés"),
            ],
        ))

    return catalog(
        name         = "Dimensión Temporal — Años de Reporte",
        value        = "TEMPORAL_ANIO",
        catalog_type = "TEMPORAL",
        description  = "Años calendario presentes en los reportes de emisiones",
        items        = year_items,
    )


# ──────────────────────────────────────────────────────────────
# 3. SUSTANCIA  (chemical substances)
# ──────────────────────────────────────────────────────────────

def build_sustancia_catalog(rows: List[Dict]) -> Dict:
    # Collect unique substances: cas -> { nombre, grupo_iarc }
    sustancias: Dict[str, Dict] = {}
    for row in rows:
        cas   = row["sustancia_cas"].strip()
        name  = row["sustancia_nombre"].strip()
        grupo = row["sustancia_grupo_iarc"].strip()
        if cas not in sustancias:
            sustancias[cas] = {"name": name, "grupo_iarc": grupo}

    sust_items = []
    for code, (cas, data) in enumerate(sorted(sustancias.items()), start=1):
        name  = data["name"]
        grupo = data["grupo_iarc"]
        sust_items.append(item(
            name        = name,
            value       = to_upper_snake(name),
            code        = code,
            value_type  = "STRING",
            description = f"{name} — CAS {cas}, Grupo IARC {grupo}",
            aliases     = [
                alias(cas,             "STRING",  "Número CAS"),
                alias(f"IARC_{grupo}", "STRING",  "Clasificación IARC"),
                alias(f"GRUPO_{grupo}","STRING",  "Grupo IARC (etiqueta)"),
                alias(name.lower(),    "STRING",  "Nombre en minúsculas"),
                alias(name.upper(),    "STRING",  "Nombre en mayúsculas"),
            ],
        ))

    return catalog(
        name         = "Sustancias Químicas RETC",
        value        = "SUSTANCIA_RETC",
        catalog_type = "INTEREST",
        description  = "Sustancias químicas reportadas en el RETC con su número CAS y grupo IARC",
        items        = sust_items,
    )


# ──────────────────────────────────────────────────────────────
# 4. NOM_UMBRAL  (regulatory thresholds)
# ──────────────────────────────────────────────────────────────

def build_umbral_catalog(rows: List[Dict]) -> Dict:
    # Collect unique threshold pairs
    seen = set()
    umbral_items = []
    code = 1

    for row in rows:
        eyt = row["umbral_nom_eyt"].strip()
        mpu = row["umbral_nom_mpu"].strip()
        key = (eyt, mpu)
        if key in seen:
            continue
        seen.add(key)

        # EYT item
        umbral_items.append(item(
            name        = f"Umbral NOM-EYT ({eyt} kg)",
            value       = f"NOM_EYT_{eyt}",
            code        = code,
            value_type  = "FLOAT",
            description = "Umbral de reporte NOM — Emisiones y Transferencias (kg/año)",
            aliases     = [
                alias(eyt,             "FLOAT",  "Valor numérico en kg"),
                alias(f"{eyt} kg/año", "STRING", "Valor con unidad"),
                alias("NOM_EYT",       "STRING", "Clave de norma"),
            ],
        ))
        code += 1

        # MPU item
        umbral_items.append(item(
            name        = f"Umbral NOM-MPU ({mpu} kg)",
            value       = f"NOM_MPU_{mpu}",
            code        = code,
            value_type  = "FLOAT",
            description = "Umbral de reporte NOM — Manejo, Procesamiento y Uso (kg/año)",
            aliases     = [
                alias(mpu,             "FLOAT",  "Valor numérico en kg"),
                alias(f"{mpu} kg/año", "STRING", "Valor con unidad"),
                alias("NOM_MPU",       "STRING", "Clave de norma"),
            ],
        ))
        code += 1

    return catalog(
        name         = "Umbrales Normativos NOM-RETC",
        value        = "NOM_UMBRAL_RETC",
        catalog_type = "REGULATORY",
        description  = "Umbrales de reporte obligatorio definidos por la NOM para el RETC",
        items        = umbral_items,
    )





# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    catalogs = [
        build_spatial_catalog(rows),
        build_temporal_catalog(rows),
        build_sustancia_catalog(rows),
        build_umbral_catalog(rows),
    ]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalogs, f, ensure_ascii=False, indent=2)

    print(f"✅  Generated {len(catalogs)} catalog(s) → {OUTPUT_PATH}")
    for c in catalogs:
        total_items = count_items(c["items"])
        print(f"     • [{c['catalog_type']}] {c['name']}  —  {total_items} item(s) (including children)")


def count_items(items: List[Dict]) -> int:
    total = 0
    for i in items:
        total += 1 + count_items(i.get("children", []))
    return total


if __name__ == "__main__":
    main()