"""
08 — Tag products and search them
=================================

Tags are catalog item ids. We tag every car photo with its brand, model,
color, year and country (the items created in 03). The country is where the
brand comes from (TOYOTA → JP, FORD → US). Then we search with the DSL:

    jub.v1.VI(CAR_BRAND.TOYOTA)                      interest: CATALOG.VALUE
    jub.v1.VI(CAR_BRAND.TOYOTA AND CAR_COLOR.RED)    both tags
    jub.v1.VT(>= 2022)                               temporal: by date
    jub.v1.VS(COUNTRY.JP)                            spatial: by place
    jub.v1.VS(COUNTRY.JP).VI(CAR_COLOR.RED)          combine blocks

VS(*) means "any place": it applies no filter, so it returns every product.

`observatory_id` limits the search to our observatory.

Run:
    python examples/client/basics/08_tag_and_search.py
"""

import asyncio
import os
import sys
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

# Where each brand comes from — must be a COUNTRY item created in 03
BRAND_COUNTRY = {
    "TOYOTA": "JP", "NISSAN": "JP", "MITSUBISHI": "JP", "HONDA": "JP", "MAZDA": "JP",
    "FORD": "US", "CHEVROLET": "US", "DODGE": "US",
    "VOLKSWAGEN": "DE", "BMW": "DE", "MERCEDES": "DE", "AUDI": "DE", "PORSCHE": "DE",
    "HYUNDAI": "KR", "KIA": "KR",
}


def item_id(value: str) -> str:
    return f"{value}_{USERNAME}"


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()
    images = sorted(CARS_DIR.glob("*_*_*_*.*"))

    unknown = sorted({image.stem.split("_")[0].upper() for image in images} - BRAND_COUNTRY.keys())
    if unknown:
        sys.exit(f"Add these brands to BRAND_COUNTRY: {', '.join(unknown)}")

    # ── Tag ──────────────────────────────────────────────────────────────
    for image in images:
        brand, model, color, year = (part.upper().replace("-", "_") for part in image.stem.split("_"))
        country = BRAND_COUNTRY[brand]
        tags = DTO.TagProductDTO(catalog_item_ids=[
            item_id(brand), item_id(model), item_id(color), item_id(f"Y{year}"), item_id(country),
        ])
        (await client.add_product_tags(f"{image.stem}_{USERNAME}", tags)).unwrap()
    print(f"Tagged {len(images)} products")

    # ── Read the tags of one product ─────────────────────────────────────
    first = f"{images[0].stem}_{USERNAME}"
    tags = (await client.get_product_tag_details(first)).unwrap()
    print(f"{first}: {', '.join(tag.name for tag in tags)}")

    # ── Search ───────────────────────────────────────────────────────────
    brand, _, color, year = (part.upper().replace("-", "_") for part in images[0].stem.split("_"))
    country = BRAND_COUNTRY[brand]
    queries = [
        f"jub.v1.VI(CAR_BRAND.{brand})",
        f"jub.v1.VI(CAR_BRAND.{brand} AND CAR_COLOR.{color})",
        f"jub.v1.VT(>= {year})",
        f"jub.v1.VI(CAR_BRAND.{brand}).VT(>= {year})",
        f"jub.v1.VS(COUNTRY.{country})",
        f"jub.v1.VS(COUNTRY.{country}).VI(CAR_COLOR.{color})",
    ]
    for query in queries:
        results = (await client.search(DTO.SearchQueryDTO(query=query, observatory_id=OBSERVATORY_ID, limit=50))).unwrap()
        print(f"\n{query} → {len(results)} products")
        for product in results:
            print(f"  {product['name']:<40} {product['spatial_variable']['value']}")


if __name__ == "__main__":
    asyncio.run(main())
