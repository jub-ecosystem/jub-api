"""
05 — Link catalogs to an observatory
====================================

Catalogs exist on their own; linking one to an observatory makes it part of
that observatory. The same catalog can be linked to many observatories.
`level` is the catalog's depth in the observatory's catalog hierarchy
(0 = root).

Run:
    python examples/client/basics/05_link_catalogs.py
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


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    catalogs = [f"brands_{USERNAME}", f"colors_{USERNAME}", f"years_{USERNAME}", f"countries_{USERNAME}"]
    for level, catalog_id in enumerate(catalogs):
        link = DTO.LinkCatalogDTO(catalog_id=catalog_id, level=level)
        (await client.link_catalog_to_observatory(OBSERVATORY_ID, link)).unwrap()
        print(f"Linked {catalog_id} (level {level})")

    print(f"\nCatalogs of {OBSERVATORY_ID}:")
    for catalog in (await client.list_observatory_catalogs(OBSERVATORY_ID)).unwrap():
        print(f"  {catalog.value:<10} {catalog.catalog_type:<9} {catalog.name}")


if __name__ == "__main__":
    asyncio.run(main())
