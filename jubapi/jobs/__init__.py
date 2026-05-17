import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorDatabase

from jubapi.storage import StorageBackend
from jubapi.log.log import Log

L = Log(
    name=__name__,
    path=os.environ.get("JUB_LOG_PATH", "/log"),
)


async def run_orphan_check(
    storage: StorageBackend,
    db: AsyncIOMotorDatabase,
    delete: bool,
) -> None:
    scanned = 0
    orphans_found = 0
    deleted = 0

    L.info({"action": "job.orphan_check.start", "result": {"dry_run": not delete}})

    try:
        candidates = await storage.list_directories(storage.namespace)
    except Exception as e:
        L.error({"action": "job.orphan_check.list_failed", "error": str(e)})
        return

    for product_id in candidates:
        scanned += 1
        existing = await db["products"].find_one({"product_id": product_id})
        if existing:
            continue

        orphans_found += 1
        try:
            file_count = len(await storage.list(storage.prefix_for(product_id)))
        except Exception:
            file_count = -1

        L.info({
            "action": "job.orphan_check.orphan_found",
            "input": {"product_id": product_id, "file_count": file_count},
        })

        if delete:
            try:
                files_deleted = await storage.delete_prefix(storage.prefix_for(product_id))
                deleted += files_deleted
                L.info({
                    "action": "job.orphan_check.orphan_deleted",
                    "result": {"product_id": product_id, "files_deleted": files_deleted},
                })
            except Exception as e:
                L.error({
                    "action": "job.orphan_check.delete_failed",
                    "error": str(e),
                    "input": {"product_id": product_id},
                })

    L.info({
        "action": "job.orphan_check.complete",
        "result": {"scanned": scanned, "orphans_found": orphans_found, "deleted": deleted},
    })


async def orphan_check_loop(
    storage: StorageBackend,
    db: AsyncIOMotorDatabase,
    interval: int,
    delete: bool,
) -> None:
    while True:
        try:
            await run_orphan_check(storage, db, delete)
        except Exception as e:
            L.error({"action": "job.orphan_check.loop_error", "error": str(e)})
        await asyncio.sleep(interval)
