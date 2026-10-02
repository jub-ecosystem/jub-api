"""
10 — Data sources ("databases") and records
===========================================

A data source is a dataset of records that an observatory exposes. Every record
is described with the same catalogs as the products:

    spatial_id              catalog item id   where   (e.g. TAMS)
    temporal_id             ISO-8601 datetime when
    interest_ids            catalog item ids  what    (e.g. MUJER, COVID_19)
    numerical_interest_ids  {metric: number}  measurements used by VO(SUM/AVG)
    raw_payload             anything else you want to keep

    1. register_data_source()             create it
    2. link_datasource_to_observatory()   make it part of the observatory
    3. ingest_records()                   push records in chunks
    4. query_records()                    DSL filter over ONE data source
    5. generate_plot()                    DSL aggregation (VO + BY) → ECharts JSON

About identifiers: query_records() resolves each identifier (a value like TAMS
or an alias) to ONE catalog item across the whole database. When the same
value exists in several catalogs — as it does after running these examples
more than once — use the catalog_item_id, which is always unambiguous.

Run:
    python examples/client/advanced/10_datasource.py
"""

import asyncio
import datetime as DT
import random
from typing import Any, Dict, List

import jub.dto.v2 as DTO

import _domain as D
from _common import SUFFIX, build_client, describe_error, item_ids, require, save_state, unwrap

CHUNK_SIZE = 500


def generate_records(rng: random.Random) -> List[DTO.DataRecordCreateDTO]:
    """32 states × 9 years × 2 sexes × 5 causes (COVID-19 only from 2020) ≈ 2 560 records."""
    states = dict(zip((abbr for _, _, abbr, _ in D.MEXICO_STATES), item_ids("spatial", [a for _, _, a, _ in D.MEXICO_STATES])))
    sexes  = dict(zip(["HOMBRE", "MUJER"], item_ids("sex", ["HOMBRE", "MUJER"])))
    causes = dict(zip(D.CAUSE_BASE_RATE, item_ids("causa_defuncion", D.CAUSE_BASE_RATE)))

    records: List[DTO.DataRecordCreateDTO] = []
    for _, state_name, abbr, pop_m in D.MEXICO_STATES:
        for year in D.YEARS:
            for sex, sex_id in sexes.items():
                for cause, cause_id in causes.items():
                    if cause == "COVID_19" and year < 2020:
                        continue
                    rate   = D.CAUSE_BASE_RATE[cause] * (2.2 if cause == "COVID_19" and year == 2021 else 1.0)
                    rate  *= rng.uniform(0.8, 1.2)
                    deaths = round(rate * pop_m * 10 / 2)   # per 100k, split by sex
                    records.append(DTO.DataRecordCreateDTO(
                        record_id              = f"rec_{rng.getrandbits(48):012x}",
                        spatial_id             = states[abbr],
                        temporal_id            = DT.datetime(year, 1, 1, tzinfo=DT.timezone.utc).isoformat(),
                        interest_ids           = [sex_id, cause_id],
                        numerical_interest_ids = {"DEFUNCIONES": float(deaths), "TASA_100K": round(rate, 2)},
                        raw_payload            = {"estado": state_name, "anio": year, "sexo": sex, "causa": cause},
                    ))
    return records


async def main() -> None:
    client = await build_client()
    obs_id = require("observatory_id", "04_observatories.py")
    suffix = SUFFIX

    # ── 1. Register ──────────────────────────────────────────────────────
    source = unwrap(
        await client.register_data_source(DTO.DataSourceCreateDTO(
            name        = f"SINAVE — Certificados de Defuncion 2015-2023 ({suffix})",
            description = "Defunciones por causa, entidad, año y sexo (datos sinteticos).",
            format      = "json",
        )),
        "register data source",
    )
    print(f"✓ [register_data_source]           {source.source_id}")

    # ── 2. Link to the observatory ───────────────────────────────────────
    unwrap(await client.link_datasource_to_observatory(obs_id, source.source_id), "link data source")
    print(f"✓ [link_datasource_to_observatory] {source.source_id} → {obs_id}")
    save_state(source_id=source.source_id)

    # ── 3. Ingest in chunks ──────────────────────────────────────────────
    records  = generate_records(random.Random(42))
    inserted = 0
    for start in range(0, len(records), CHUNK_SIZE):
        chunk = records[start:start + CHUNK_SIZE]
        inserted += unwrap(await client.ingest_records(source.source_id, chunk), f"ingest chunk at {start}").inserted
    print(f"✓ [ingest_records]                 {inserted:,}/{len(records):,} records in chunks of {CHUNK_SIZE}")

    # ── 4. Filter records ────────────────────────────────────────────────
    tams  = item_ids("spatial", ["TAMS"])[0]
    covid = item_ids("causa_defuncion", ["COVID_19"])[0]
    mujer = item_ids("sex", ["MUJER"])[0]

    query = f"jub.v1.VS({tams}).VT(>= 2020).VI({covid} AND {mujer})"
    rows: List[Dict[str, Any]] = unwrap(
        await client.query_records(source.source_id, DTO.DataSourceQueryDTO(query=query, limit=10)),
        "query records",
    )
    print(f"\n[query_records] Tamaulipas · 2020+ · COVID-19 · mujeres  ({len(rows)} records)\n  {query}")
    for r in sorted(rows, key=lambda r: r["raw_payload"]["anio"]):
        print(f"  {r['raw_payload']['anio']}  defunciones={r['numerical_interest_ids']['DEFUNCIONES']:>6,.0f}  tasa_100k={r['numerical_interest_ids']['TASA_100K']}")

    # ── 5. Aggregate: total COVID-19 deaths in Tamaulipas per year ───────
    plot_query = f"jub.v1.VS({tams}).VI({covid}).VO(SUM(DEFUNCIONES)).BY(TEMPORAL)"
    plot = await client.generate_plot(DTO.PlotQueryDTO(query=plot_query, observatory_id=obs_id, chart_type="bar"))
    print(f"\n[generate_plot]\n  {plot_query}")
    if plot.is_err:
        print(f"  ✗ {describe_error(plot.unwrap_err())}")
    else:
        chart = plot.unwrap()
        print(f"  ECharts option keys: {', '.join(chart.keys()) if isinstance(chart, dict) else type(chart).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
