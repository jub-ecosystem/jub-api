"""
generate_data_records.py
Reads muestra_benceno.csv and produces a list of DataRecord-compatible dicts.

Column mapping:
  spatial_id            <- "estado_cve_ent" + "municipio_cve_mun"  (e.g. "1_1" = Aguascalientes/Aguascalientes)
  temporal_id           <- "anio"           (ISO datetime: Jan 1 of that year)
  interest_ids          <- sustancia_cas, sustancia_grupo_iarc (as catalog item IDs)
  numerical_interest_ids <- cantidad_kg, index_kg, umbral_nom_eyt, umbral_nom_mpu,
                            umbral_nom_eyt_index, umbral_nom_mpu_index,
                            umbral_nom_eyt_residuo, umbral_nom_mpu_residuo
  raw_payload           <- entire original row
"""

import csv
import uuid
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any


CSV_PATH = Path("./muestra_benceno.csv")      # adjust if needed
OUTPUT_PATH = Path("./data_records.json")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def make_record_id() -> str:
    return f"rec_{uuid.uuid4().hex[:10]}"

def make_source_id() -> str:
    """Fixed source ID for this CSV file."""
    return "src_benceno_001"

def build_spatial_id(row: Dict[str, str]) -> str:
    """
    Builds a spatial catalog-item-like ID from state + municipality codes.
    e.g.  estado=1, municipio=1  ->  "MX_1_1"
    """
    estado   = row["estado_cve_ent"].strip()
    municipio = row["municipio_cve_mun"].strip()
    return f"MX_{estado}_{municipio}"

def build_temporal_id(row: Dict[str, str]) -> str:
    """Returns ISO 8601 datetime string for Jan 1 of the reported year."""
    year = int(row["anio"].strip())
    dt   = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
    return dt.isoformat()

def build_interest_ids(row: Dict[str, str]) -> List[str]:
    """
    Maps qualitative catalog dimensions to catalog-item-like IDs.
      - sustancia_cas        -> "CAS_{value}"        e.g. "CAS_71-43-2"
      - sustancia_grupo_iarc -> "IARC_{value}"       e.g. "IARC_1"
      - sustancia_nombre     -> "SUST_{upper_snake}"  e.g. "SUST_BENCENO"
    """
    cas    = row["sustancia_cas"].strip().replace(" ", "_")
    iarc   = row["sustancia_grupo_iarc"].strip()
    nombre = row["sustancia_nombre"].strip().upper().replace(" ", "_")

    ids = [
        f"CAS_{cas}",
        f"IARC_{iarc}",
        f"SUST_{nombre}",
    ]

    # Boolean flags as interest tags (presence = True)
    if row.get("umbral_nom_eyt_excede", "").strip().upper() == "TRUE":
        ids.append("EXCEDE_NOM_EYT")
    if row.get("umbral_nom_mpu_excede", "").strip().upper() == "TRUE":
        ids.append("EXCEDE_NOM_MPU")

    return ids

def build_numerical_interest_ids(row: Dict[str, str]) -> Dict[str, float]:
    """
    Maps numeric columns to { catalog_item_id_like_key: float_value }.
    Keys mirror what you would name in the spatial/interest catalogs.
    """
    numeric_cols = {
        "CANTIDAD_KG"          : "cantidad_kg",
        "INDEX_KG"             : "index_kg",
        "UMBRAL_NOM_EYT"       : "umbral_nom_eyt",
        "UMBRAL_NOM_MPU"       : "umbral_nom_mpu",
        "UMBRAL_NOM_EYT_INDEX" : "umbral_nom_eyt_index",
        "UMBRAL_NOM_MPU_INDEX" : "umbral_nom_mpu_index",
        "UMBRAL_NOM_EYT_RESIDUO": "umbral_nom_eyt_residuo",
        "UMBRAL_NOM_MPU_RESIDUO": "umbral_nom_mpu_residuo",
        "ANIOS_REPORTE"        : "anios_reporte",
    }

    result: Dict[str, float] = {}
    for key, col in numeric_cols.items():
        raw = row.get(col, "").strip()
        if raw == "" or raw == "-1":
            continue
        try:
            result[key] = float(raw)
        except ValueError:
            pass  # skip non-parseable values silently

    return result


# ──────────────────────────────────────────────
# Main builder
# ──────────────────────────────────────────────

def build_data_records(csv_path: Path) -> List[Dict[str, Any]]:
    records = []
    source_id = make_source_id()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                "record_id"              : make_record_id(),
                "source_id"              : source_id,
                "spatial_id"             : build_spatial_id(row),
                "temporal_id"            : build_temporal_id(row),
                "interest_ids"           : build_interest_ids(row),
                "numerical_interest_ids" : build_numerical_interest_ids(row),
                "raw_payload"            : dict(row),
            }
            records.append(record)

    return records


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    records = build_data_records(CSV_PATH)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"✅  Generated {len(records)} DataRecord(s) → {OUTPUT_PATH}")

    # Preview first record
    print("\n── Sample record ──────────────────────────────")
    print(json.dumps(records[0], indent=2))