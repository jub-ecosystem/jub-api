"""
07 — Upload a file to a product
===============================

`upload_product(product_id, path)` sends the file and returns right away with
a `job_id`. The server stores the file in the background; the job is a task
you can poll with `get_task()` until it is `success` or `failed`.
`download_product()` returns the latest file of a product.

Here we upload the first photo. 09 uploads all of them.

Run:
    python examples/client/basics/07_upload_files.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from jub.client.v2 import JubClientBuilder

load_dotenv(Path(__file__).resolve().parents[1] / ".env.examples")

API_URL  = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME = os.environ["JUB_USERNAME"]
PASSWORD = os.environ["JUB_PASSWORD"]
CARS_DIR = Path(__file__).resolve().parents[3] / "source" / "cars"


async def main() -> None:
    client = (await JubClientBuilder(API_URL, USERNAME, PASSWORD).build()).unwrap()

    image      = sorted(CARS_DIR.glob("*_*_*_*.*"))[0]
    product_id = f"{image.stem}_{USERNAME}"

    job = (await client.upload_product(product_id, str(image))).unwrap()
    print(f"Uploading {image.name} → {product_id} (job {job.job_id})")

    task = (await client.get_task(job.job_id)).unwrap()
    while task.current_status in ("pending", "running"):
        await asyncio.sleep(1)
        task = (await client.get_task(job.job_id)).unwrap()
    print(f"Upload finished: {task.current_status}")

    content = (await client.download_product(product_id)).unwrap()
    print(f"Downloaded {len(content):,} bytes, same as the original: {content == image.read_bytes()}")


if __name__ == "__main__":
    asyncio.run(main())
