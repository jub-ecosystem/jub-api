"""
09 — Upload many files, with retries and without re-uploading
=============================================================

    .with_upload_registry(path)            remember which uploads succeeded
    register_upload(product_id, path)      queue a file (nothing is sent yet)
    wait_uploads(workers, max_retries)     upload the queue

`max_retries` is the total number of attempts per file (1 = no retry).
Uploads already marked as succeeded in the registry file are skipped, so run
this script twice: the second time every photo is reported as skipped.

Run:
    python examples/client/basics/09_upload_retries.py
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
REGISTRY = Path(__file__).parent / ".upload_registry.json"


async def main() -> None:
    client = (await (
        JubClientBuilder(API_URL, USERNAME, PASSWORD)
        .with_upload_registry(str(REGISTRY))
        .build()
    )).unwrap()

    for image in sorted(CARS_DIR.glob("*_*_*_*.*")):
        client.register_upload(f"{image.stem}_{USERNAME}", str(image)).unwrap()

    result = (await client.wait_uploads(workers=2, max_retries=3)).unwrap()

    print(f"\nUploaded: {len(result.succeeded)}")
    print(f"Skipped (already uploaded): {len(result.skipped)}")
    print(f"Failed: {len(result.failed)}")
    for failure in result.failed:
        print(f"  {failure.product_id} after {failure.attempts} attempts: {failure.last_error}")


if __name__ == "__main__":
    asyncio.run(main())
