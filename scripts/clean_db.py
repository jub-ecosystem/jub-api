#!/usr/bin/env python3
"""
clean_db.py — Removes all JUB v2 data and the uploaded product files.

Deletes every document of every collection in `CollectionNames`
(jubapi/db/constants.py) except user profiles and the legacy v1 collections:
observatories, catalogs, catalog items and aliases, products, data sources and
records, services / workflows / stages / patterns / building blocks, tasks,
notifications, reviews, search suggestions and every link collection.
It also deletes the uploaded files under <storage-path>/products.

Users are kept, both the profiles here and the accounts in Xolo.

Usage:
    python scripts/clean_db.py --dry-run
    python scripts/clean_db.py
    python scripts/clean_db.py --mongo-uri mongodb://localhost:27027 --db-name jub_test --storage-path /jub
    python scripts/clean_db.py --yes            # no confirmation prompt
    python scripts/clean_db.py --keep-files     # database only
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import shutil
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

# Load only the constants module: importing the `jubapi` package would also load
# its .env file, which could silently change the target database.
_CONSTANTS = Path(__file__).resolve().parents[1] / "jubapi" / "db" / "constants.py"
_spec = importlib.util.spec_from_file_location("jub_db_constants", _CONSTANTS)
_constants = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_constants)
CollectionNames = _constants.CollectionNames

KEEP = {CollectionNames.USER_PROFILES.value} | {c.value for c in CollectionNames if c.value.endswith("_v1")}
COLLECTIONS_TO_CLEAN = sorted(c.value for c in CollectionNames if c.value not in KEEP)

# LocalStorageBackend stores every product under <storage-path>/products/<product_id>/...
FILES_NAMESPACE = "products"


def count_files(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file()) if root.exists() else 0


async def clean(mongo_uri: str, db_name: str, files_root: Path | None, dry_run: bool) -> None:
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    for name in COLLECTIONS_TO_CLEAN:
        if dry_run:
            count = await db[name].count_documents({})
            print(f"  [dry-run] would delete {count:>7} documents from {name}")
        else:
            result = await db[name].delete_many({})
            print(f"  deleted {result.deleted_count:>7} documents from {name}")
    client.close()

    if files_root is None:
        print("\n  files kept (--keep-files)")
    elif dry_run:
        print(f"\n  [dry-run] would delete {count_files(files_root):>7} files under {files_root}")
    else:
        deleted = count_files(files_root)
        for child in files_root.iterdir() if files_root.exists() else []:
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        print(f"\n  deleted {deleted:>7} files under {files_root}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete all JUB v2 data and uploaded product files (users are kept).")
    parser.add_argument("--mongo-uri",    default=os.environ.get("JUB_MONGODB_URI", "mongodb://localhost:27027"), help="MongoDB connection URI (default: $JUB_MONGODB_URI)")
    parser.add_argument("--db-name",      default=os.environ.get("JUB_MONGODB_DATABASE_NAME", "jub"),             help="Database name (default: $JUB_MONGODB_DATABASE_NAME)")
    parser.add_argument("--storage-path", default=os.environ.get("JUB_STORAGE_PATH", "/jub"),                     help="Storage base path of the API (default: $JUB_STORAGE_PATH)")
    parser.add_argument("--keep-files",   action="store_true", help="Do not delete uploaded files")
    parser.add_argument("--dry-run",      action="store_true", help="Show what would be deleted without changing anything")
    parser.add_argument("--yes", "-y",    action="store_true", help="Do not ask for confirmation")
    args = parser.parse_args()

    files_root = None if args.keep_files else Path(args.storage_path) / FILES_NAMESPACE

    print("JUB Clean Script")
    print(f"  mongo-uri : {args.mongo_uri}")
    print(f"  db-name   : {args.db_name}")
    print(f"  files     : {files_root or 'kept'}")
    print(f"  kept      : {', '.join(sorted(KEEP))}")
    print(f"  dry-run   : {args.dry_run}\n")

    if not args.dry_run and not args.yes:
        answer = input(f"This deletes all data in '{args.db_name}'{' and the uploaded files' if files_root else ''}. Type the database name to continue: ")
        if answer.strip() != args.db_name:
            sys.exit("Aborted.")

    asyncio.run(clean(args.mongo_uri, args.db_name, files_root, args.dry_run))
    print("\nDry run complete — nothing was modified." if args.dry_run else "\nClean complete.")


if __name__ == "__main__":
    main()
