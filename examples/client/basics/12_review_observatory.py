"""
12 — Review the observatory and publish it
==========================================

Lists everything linked to the observatory, then completes the setup task
opened in 04. Completing it with `success=True` enables the observatory.

Run:
    python examples/client/basics/12_review_observatory.py
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

    observatory = (await client.get_observatory(OBSERVATORY_ID)).unwrap()
    catalogs    = (await client.list_observatory_catalogs(OBSERVATORY_ID)).unwrap()
    products    = (await client.list_observatory_products(OBSERVATORY_ID)).unwrap()
    sources     = (await client.list_observatory_datasources(OBSERVATORY_ID)).unwrap()
    services    = (await client.list_observatory_services(OBSERVATORY_ID)).unwrap()

    print(f"{observatory.title}\n{observatory.description}\n")
    print(f"Catalogs ({len(catalogs)}): {', '.join(c.name for c in catalogs)}")
    print(f"Products ({len(products)}):")
    for p in products:
        print(f"  {p.name}")
    print(f"Data sources ({len(sources)}): {', '.join(s.name for s in sources)}")
    print(f"Services ({len(services)}): {', '.join(s.name for s in services)}")

    # ── Publish: complete the setup task from 04 ─────────────────────────
    tasks = (await client.list_my_tasks()).unwrap()
    setup = next(t for t in tasks if t.observatory_id == OBSERVATORY_ID and t.operation == "setup")
    if setup.current_status == "pending":
        done = (await client.complete_task(setup.task_id, DTO.TaskCompleteDTO(success=True))).unwrap()
        print(f"\nObservatory published: {done.observatory_enabled}")
    else:
        print(f"\nSetup task already {setup.current_status}")


if __name__ == "__main__":
    asyncio.run(main())
