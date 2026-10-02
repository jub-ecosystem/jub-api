"""
07 — Upload files to products
=============================

`upload_product(product_id, payload)` attaches a file to a product. `payload`
can be:

    str    a path on disk (the file name is kept)
    bytes  content generated in memory (stored as "<product_id>_upload")

The upload is asynchronous on the server: the call returns right away with a
`job_id`, which is a task id. The file is stored in the background and the
task ends as `success` or `failed` — poll it with get_task() before relying
on the file. download_product() returns the latest file of a product.

For many files, retries and skipping already-uploaded products, see 09.

Run:
    python examples/client/advanced/07_upload_files.py
"""

import asyncio
import csv
import io

import _domain as D
from _common import CHARTS_DIR, build_client, require, unwrap, wait_for_task


def mortality_csv() -> bytes:
    """A small CSV built in memory, to show uploading bytes instead of a path."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["estado", "poblacion_millones"])
    for _, name, _, pop_m in D.MEXICO_STATES:
        writer.writerow([name, pop_m])
    return buffer.getvalue().encode("utf-8")


async def upload_and_wait(client, product_id: str, payload, label: str) -> None:
    job = unwrap(await client.upload_product(product_id, payload), f"upload {label}")
    print(f"✓ [upload_product] {label} → job {job.job_id} ({job.status})")

    task = await wait_for_task(client, job.job_id)
    print(f"  task finished as '{task.current_status}' {task.progress_message}".rstrip())
    if task.current_status != "success":
        raise SystemExit(f"✗ upload of {label} did not succeed")


async def main() -> None:
    client   = await build_client()
    products = require("products", "06_products.py")

    # ── 1. From a path ───────────────────────────────────────────────────
    heatmap_path = CHARTS_DIR / "heatmap.html"
    await upload_and_wait(client, products["mort_causa_estado"], str(heatmap_path), "heatmap.html (path)")

    downloaded = unwrap(await client.download_product(products["mort_causa_estado"]), "download product")
    same = downloaded == heatmap_path.read_bytes()
    print(f"✓ [download_product] {len(downloaded):,} bytes, identical to the original: {same}")

    # ── 2. From bytes ────────────────────────────────────────────────────
    content = mortality_csv()
    await upload_and_wait(client, products["mort_edad_sexo"], content, "in-memory CSV (bytes)")

    downloaded = unwrap(await client.download_product(products["mort_edad_sexo"]), "download product")
    print(f"✓ [download_product] {len(downloaded):,} bytes, identical to the original: {downloaded == content}")


if __name__ == "__main__":
    asyncio.run(main())
