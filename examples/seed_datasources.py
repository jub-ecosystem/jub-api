#!/usr/bin/env python3
"""
seed_datasources.py — Creates N synthetic data sources, each with 10-100 random records.

Usage:
    python examples/seed_datasources.py
    python examples/seed_datasources.py --count 50 --username admin --password secret
    python examples/seed_datasources.py --api-url http://localhost:5000/api/v2
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as DT
import random
import sys
import uuid
from typing import Any, Dict, List

import httpx

SPATIAL_IDS  = [f"SPA_{i:03d}" for i in range(10)]
YEARS        = list(range(2015, 2025))
INTEREST_IDS = [f"INT_{i:02d}" for i in range(20)]


def _check(resp: httpx.Response, label: str) -> Any:
    if resp.status_code >= 300:
        print(f"  ✗ {label} failed [{resp.status_code}]: {resp.text[:400]}")
        sys.exit(1)
    return resp.json()


def gen_records(source_id: str, n: int) -> List[Dict]:
    records = []
    for _ in range(n):
        year = random.choice(YEARS)
        records.append({
            "record_id":              uuid.uuid4().hex,
            "spatial_id":             random.choice(SPATIAL_IDS),
            "temporal_id":            DT.datetime(year, random.randint(1, 12), 1).isoformat(),
            "interest_ids":           random.sample(INTEREST_IDS, k=random.randint(1, 4)),
            "numerical_interest_ids": {"value": round(random.uniform(1.0, 1000.0), 2)},
        })
    return records


async def main(api_url: str, username: str, password: str, count: int) -> None:
    async with httpx.AsyncClient(base_url=api_url, timeout=60.0) as client:
        resp = await client.post("/users/auth", json={
            "username":   username,
            "password":   password,
            "scope":      "jub",
            "expiration": "1h",
        })
        data = _check(resp, f"login as '{username}'")
        client.headers["Authorization"] = f"Bearer {data['access_token']}"
        if data.get("temporal_secret_key"):
            client.headers["Temporal-Secret-Key"] = data["temporal_secret_key"]
        print(f"  ✓ Authenticated as '{username}'")

        print(f"\n─── Creating {count} data sources ─────────────────────────────────")
        for i in range(1, count + 1):
            ds_data = _check(
                await client.post("/datasources", json={
                    "name":        f"Synthetic DS {i:03d}",
                    "description": f"Auto-generated data source #{i}",
                    "format":      "json",
                }),
                f"create datasource {i}",
            )
            source_id = ds_data["source_id"]
            n_records = random.randint(10, 100)
            records   = gen_records(source_id, n_records)

            CHUNK    = 50
            inserted = 0
            for j in range(0, len(records), CHUNK):
                chunk  = records[j : j + CHUNK]
                result = _check(
                    await client.post(f"/datasources/{source_id}/records", json=chunk),
                    f"ingest chunk for {source_id}",
                )
                inserted += result.get("inserted", len(chunk))

            print(f"  [{i:3d}/{count}] {source_id}  ({inserted} records)")

        print(f"\n✓ Done — {count} data sources created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed synthetic data sources with random records.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api-url",  default="http://localhost:5000/api/v2", help="API base URL")
    parser.add_argument("--username", default="admin",  help="Login username")
    parser.add_argument("--password", default="admin",  help="Login password")
    parser.add_argument("--count",    type=int, default=100, help="Number of data sources to create")
    args = parser.parse_args()
    asyncio.run(main(args.api_url, args.username, args.password, args.count))
