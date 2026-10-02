"""
10 — Data source ("database") linked to the observatory
=======================================================

A data source holds records. Each record is described with catalog items:

    spatial_id              where  → a COUNTRY item
    temporal_id             when   → an ISO date
    interest_ids            what   → CAR_BRAND items
    numerical_interest_ids  numbers, e.g. {"UNITS": 1200}

We store yearly car sales per country and brand, then query them.
In `query_records()` identifiers are catalog item ids.

Run:
    python examples/client/basics/10_datasource.py
"""

import asyncio
import os
import random
from pathlib import Path

from dotenv import load_dotenv
import jub.dto.v2 as DTO
from jub.client.v2 import JubClientBuilder

load_dotenv(Path(__file__).resolve().parents[1] / ".env.examples")

API_URL        = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME       = os.environ["JUB_USERNAME"]
PASSWORD       = os.environ["JUB_PASSWORD"]
OBSERVATORY_ID = f"cars_{USERNAME}"
CARS_DIR       = Path(__file__).resolve().parents[3] / "source" / "cars"
COUNTRIES      = ["MX", "US", "JP", "DE", "KR"]


def item_id(value: str) -> str:
    return f"{value}_{USERNAME}"


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    cars   = [image.stem.upper().split("_") for image in CARS_DIR.glob("*_*_*_*.*")]
    brands = sorted({brand.replace("-", "_") for brand, _, _, _ in cars})
    years  = sorted({int(year) for _, _, _, year in cars})

    # ── Create the data source and link it ───────────────────────────────
    source = (await client.register_data_source(DTO.DataSourceCreateDTO(
        name        = f"Car sales ({USERNAME})",
        description = "Units sold per country, brand and year (random numbers).",
        format      = "json",
    ))).unwrap()
    (await client.link_datasource_to_observatory(OBSERVATORY_ID, source.source_id)).unwrap()
    print(f"Data source {source.source_id} linked to {OBSERVATORY_ID}")

    # ── Add records ──────────────────────────────────────────────────────
    records = [
        DTO.DataRecordCreateDTO(
            record_id              = f"{country}_{brand}_{year}_{USERNAME}",
            spatial_id             = item_id(country),
            temporal_id            = f"{year}-01-01T00:00:00Z",
            interest_ids           = [item_id(brand)],
            numerical_interest_ids = {"UNITS": random.randint(1_000, 50_000)},
            raw_payload            = {"country": country, "brand": brand, "year": year},
        )
        for country in COUNTRIES
        for brand in brands
        for year in years
    ]
    inserted = (await client.ingest_records(source.source_id, records)).unwrap()
    print(f"Inserted {inserted.inserted} records")

    # ── Query: sales of the first brand in Mexico ────────────────────────
    query = f"jub.v1.VS({item_id('MX')}).VI({item_id(brands[0])})"
    rows = (await client.query_records(source.source_id, DTO.DataSourceQueryDTO(query=query))).unwrap()
    print(f"\n{query}")
    for row in rows:
        print(f"  {row['raw_payload']['year']}  {row['raw_payload']['brand']:<10} {row['numerical_interest_ids']['UNITS']:>8,.0f} units")


if __name__ == "__main__":
    asyncio.run(main())
