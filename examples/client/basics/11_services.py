"""
11 — Services
=============

A service describes a processing pipeline:

    Service → Workflow → Stage(s) → Pattern → Building block (container)

`index_service()` creates the whole tree in one call. Then we link the
service to the observatory.

Run:
    python examples/client/basics/11_services.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
import jub.dto.v2 as DTO
import jub.enums as ENUM
from jub.client.v2 import JubClientBuilder

load_dotenv(Path(__file__).resolve().parents[1] / ".env.examples")

API_URL        = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME       = os.environ["JUB_USERNAME"]
PASSWORD       = os.environ["JUB_PASSWORD"]
OBSERVATORY_ID = f"cars_{USERNAME}"


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    service = (await client.index_service(DTO.ServiceIndexDTO(
        name        = f"car-photo-classifier-{USERNAME}",
        owner_id    = client.user_id,
        description = "Detects brand, model and color in car photos.",
        public      = True,
        provider    = ENUM.ServiceProviderEnum.EXTERNAL,
        workflow    = DTO.WorkflowInlineDTO(
            name   = f"Classify photos {USERNAME}",
            stages = [
                DTO.StageInlineDTO(
                    name           = f"Classify {USERNAME}",
                    source         = "s3://cars/photos",
                    sink           = f"jub://observatories/{OBSERVATORY_ID}",
                    endpoint       = "http://classifier/run",
                    transformation = DTO.PatternInlineDTO(
                        name           = f"Classifier pattern {USERNAME}",
                        task           = "classify",
                        pattern        = "pipeline",
                        workers        = 1,
                        building_block = DTO.BuildingBlockInlineDTO(
                            name    = f"Car classifier {USERNAME}",
                            image   = "registry.example.com/car-classifier:latest",
                            command = "python classify.py",
                        ),
                    ),
                ),
            ],
        ),
    ))).unwrap()
    print(f"Service {service.service_id} created (workflow {service.workflow_id})")

    (await client.link_service_to_observatory(OBSERVATORY_ID, service.service_id)).unwrap()

    print(f"\nServices of {OBSERVATORY_ID}:")
    for s in (await client.list_observatory_services(OBSERVATORY_ID)).unwrap():
        print(f"  {s.service_id}  {s.name}")


if __name__ == "__main__":
    asyncio.run(main())
