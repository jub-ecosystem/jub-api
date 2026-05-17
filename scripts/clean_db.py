#!/usr/bin/env python3
"""
clean_db.py — Removes observatories, products, catalogs, catalog items,
and all associated link collections from the JUB database.

Usage:
    python scripts/clean_db.py
    python scripts/clean_db.py --mongo-uri mongodb://localhost:27027 --db-name jub
    python scripts/clean_db.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

COLLECTIONS_TO_CLEAN = [
    # Core entities
    # Link / graph-edge collections
    "catalog_catalog_item_inks",
    "catalog_item_aliases",
    "catalog_item_catalog_alias_links",
    "catalog_item_relationships",
    "catalog_items",
    "catalogs",
    "observatories",
    "observatory_catalog_links",
    "observatory_product_links",
    "observatory_reviews",
    "product_catalogs_item_links",
    "products",
    "tasks"
]


async def clean(mongo_uri: str, db_name: str, dry_run: bool) -> None:
    client = AsyncIOMotorClient(mongo_uri)
    db: AsyncIOMotorDatabase = client[db_name]

    print(f"Connected to {mongo_uri}, database: {db_name}\n")

    for col_name in COLLECTIONS_TO_CLEAN:
        col = db[col_name]
        count = await col.count_documents({})
        if dry_run:
            print(f"  [dry-run] would delete {count:>6} documents from  {col_name}")
        else:
            result = await col.delete_many({})
            print(f"  deleted {result.deleted_count:>6} documents from  {col_name}")

    client.close()

    if dry_run:
        print("\nDry run complete — no data was modified.")
    else:
        print("\nClean complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete observatories, products, catalogs, items and all related links from the JUB database."
    )
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27027", help="MongoDB connection URI")
    parser.add_argument("--db-name", default="jub", help="Target database name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without making changes")
    args = parser.parse_args()

    print("JUB Clean Script")
    print(f"  mongo-uri : {args.mongo_uri}")
    print(f"  db-name   : {args.db_name}")
    print(f"  dry-run   : {args.dry_run}")
    print()

    asyncio.run(clean(args.mongo_uri, args.db_name, args.dry_run))


if __name__ == "__main__":
    main()
