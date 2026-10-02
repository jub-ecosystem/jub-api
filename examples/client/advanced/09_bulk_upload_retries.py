"""
09 — Bulk uploads with retries, without re-uploading
====================================================

For more than a handful of files, queue them and let the client upload them
concurrently:

    register_upload(product_id, path_or_bytes)   queue a job (nothing is sent yet)
    wait_uploads(workers, max_retries)           run the queue → BulkUploadResult
                                                   .succeeded  .failed  .skipped
    bulk_upload_products([(id, payload), …])     both steps in one call (--oneshot)

Retries: a failed job is put back in the queue immediately (no backoff) until
it has been attempted `max_retries` times. Note that `max_retries` is the
TOTAL number of attempts: the default 1 means "no retry".

No re-uploads: build the client with `.with_upload_registry(path)` and every
outcome is persisted to that JSON file. On the next run, products already
marked `succeeded` are reported in `.skipped` instead of being sent again.
Failed products are NOT skipped — they are retried on every run.

    reset_failed_uploads()   drop `failed` entries from the file (housekeeping)
    clear_upload_registry()  forget everything → next run uploads all again

The registry records `succeeded` when the server ACCEPTS the upload (HTTP 202).
Storing the file happens afterwards in a background task, so step 3 checks
those tasks.

The client also prints one JSON log line per upload event (job_started,
job_failed_retry, job_skipped_already_uploaded, bulk_complete, …).

This run includes a product id that does not exist, to show a permanent failure.
Run it twice to see the second run skip everything that already succeeded:

    python examples/client/advanced/09_bulk_upload_retries.py
    python examples/client/advanced/09_bulk_upload_retries.py              # → skipped
    python examples/client/advanced/09_bulk_upload_retries.py --oneshot    # bulk_upload_products()
    python examples/client/advanced/09_bulk_upload_retries.py --forget-failed
    python examples/client/advanced/09_bulk_upload_retries.py --reset      # clear registry first
"""

import argparse
import asyncio

import _domain as D
from _common import CHARTS_DIR, EXAMPLES_DIR, SUFFIX, build_client, require, unwrap, wait_for_task

REGISTRY_PATH = EXAMPLES_DIR / ".upload_registry.json"


async def main(args: argparse.Namespace) -> None:
    client   = await build_client(upload_registry_path=str(REGISTRY_PATH))
    products = require("products", "06_products.py")
    suffix   = SUFFIX

    if args.reset:
        unwrap(client.clear_upload_registry(), "clear upload registry")
        print(f"✓ [clear_upload_registry] {REGISTRY_PATH.name} emptied")

    uploads = [(products[p["key"]], str(CHARTS_DIR / p["chart"])) for p in D.PRODUCTS]
    uploads.append((f"prod_does_not_exist_{suffix}", str(CHARTS_DIR / "radar.html")))

    # ── 1 + 2. Queue and run ─────────────────────────────────────────────
    if args.oneshot:
        result = unwrap(
            await client.bulk_upload_products(uploads, workers=3, max_retries=3),
            "bulk upload products",
        )
    else:
        for product_id, path in uploads:
            unwrap(client.register_upload(product_id, path), f"register upload {product_id}")
        print(f"✓ [register_upload] {len(uploads)} jobs requested")
        result = unwrap(await client.wait_uploads(workers=3, max_retries=3), "wait uploads")

    print("\n[wait_uploads] BulkUploadResult")
    print(f"  succeeded ({len(result.succeeded)})")
    for up in result.succeeded:
        print(f"    {up.product_id}  job={up.job_id}")
    print(f"  skipped   ({len(result.skipped)})  already uploaded in a previous run")
    for product_id in result.skipped:
        print(f"    {product_id}")
    print(f"  failed    ({len(result.failed)})")
    for f in result.failed:
        print(f"    {f.product_id}  attempts={f.attempts}  {f.last_error[:80]}")

    # ── 3. Accepted ≠ stored: check the background tasks ─────────────────
    if result.succeeded:
        print("\n[get_task] background storage")
        for up in result.succeeded:
            task = await wait_for_task(client, up.job_id)
            print(f"  {up.product_id}  {task.current_status}")

    # ── Housekeeping ─────────────────────────────────────────────────────
    if args.forget_failed:
        removed = unwrap(client.reset_failed_uploads(), "reset failed uploads")
        print(f"\n✓ [reset_failed_uploads] removed {removed} failed entries from {REGISTRY_PATH.name}")

    print(f"\nRegistry: {REGISTRY_PATH}  — run again to see the successful uploads skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--oneshot",       action="store_true", help="use bulk_upload_products() instead of register + wait")
    parser.add_argument("--reset",         action="store_true", help="clear the upload registry before uploading")
    parser.add_argument("--forget-failed", action="store_true", help="call reset_failed_uploads() at the end")
    asyncio.run(main(parser.parse_args()))
