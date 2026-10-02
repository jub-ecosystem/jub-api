"""
06 — Products
=============

A product is something the observatory publishes — here, one product per car
photo. `create_product()` creates it and links it to `observatory_id` in the
same call.

The photos are uploaded in 07/09 and the products are tagged in 08.

Run:
    python examples/client/basics/06_products.py
"""

import asyncio
import os
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


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    for image in sorted(CARS_DIR.glob("*_*_*_*.*")):
        brand, model, color, year = image.stem.split("_")
        product = (await client.create_product(DTO.ProductCreateDTO(
            product_id     = f"{image.stem}_{USERNAME}",
            name           = f"{brand.title()} {model.title()} ({color}, {year})",
            description    = f"Photo of a {color} {brand.title()} {model.title()} from {year}.",
            observatory_id = OBSERVATORY_ID,
        ))).unwrap()
        print(f"Created {product.product_id}  {product.name}")

    products = (await client.list_observatory_products(OBSERVATORY_ID)).unwrap()
    print(f"\n{OBSERVATORY_ID} has {len(products)} products")


if __name__ == "__main__":
    asyncio.run(main())
