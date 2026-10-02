"""
04 — Observatories
==================

An observatory is the page users browse: it groups catalogs (05), products
(06), a data source (10) and services (11).

`setup_observatory()` creates it DISABLED and opens a setup task. We fill it
while nobody can see it, and 12 completes the task to publish it.
(`create_observatory()` would create it enabled right away.)

Run:
    python examples/client/basics/04_observatories.py
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

    setup = (await client.setup_observatory(DTO.ObservatorySetupDTO(
        observatory_id = OBSERVATORY_ID,
        title          = f"Cars ({USERNAME})",
        description    = "Photos of cars by brand, model, color and year.",
        metadata       = {"topic": "cars"},
    ))).unwrap()

    print(f"Observatory {setup.observatory_id} created (disabled)")
    print(f"Setup task  {setup.task_id} is {setup.status}")

    observatory = (await client.get_observatory(OBSERVATORY_ID)).unwrap()
    print(f"\n{observatory.title}\n{observatory.description}")


if __name__ == "__main__":
    asyncio.run(main())
