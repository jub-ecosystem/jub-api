#!/usr/bin/env python3
"""
seed_services.py — Seeds the full service chain:
  3 building blocks → 3 patterns → 3 stages → 1 workflow → N services

Usage:
    python examples/seed_services.py
    python examples/seed_services.py --service-count 5 --username admin --password secret
    python examples/seed_services.py --api-url http://localhost:5000/api/v2
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import httpx

BUILDING_BLOCKS = [
    {
        "name":        "BB Data Ingestion",
        "command":     "python ingest.py",
        "image":       "python:3.11-slim",
        "description": "Ingests raw records from upstream sources.",
    },
    {
        "name":        "BB Transformation",
        "command":     "python transform.py",
        "image":       "python:3.11-slim",
        "description": "Applies field normalization and enrichment.",
    },
    {
        "name":        "BB Aggregation",
        "command":     "python aggregate.py",
        "image":       "python:3.11-slim",
        "description": "Aggregates records into summary statistics.",
    },
]

PATTERNS = [
    {"name": "Ingest Pattern",    "task": "ingest",    "pattern": "pipeline",   "description": "Streaming ingestion pipeline."},
    {"name": "Transform Pattern", "task": "transform", "pattern": "map-reduce", "description": "Map-reduce transformation."},
    {"name": "Aggregate Pattern", "task": "aggregate", "pattern": "batch",      "description": "Batch aggregation."},
]

STAGES = [
    {
        "name":     "Ingest Stage",
        "source":   "s3://raw/input",
        "sink":     "s3://processed/ingest",
        "endpoint": "http://stage-ingest.internal/run",
    },
    {
        "name":     "Transform Stage",
        "source":   "s3://processed/ingest",
        "sink":     "s3://processed/transform",
        "endpoint": "http://stage-transform.internal/run",
    },
    {
        "name":     "Aggregate Stage",
        "source":   "s3://processed/transform",
        "sink":     "s3://output/aggregated",
        "endpoint": "http://stage-aggregate.internal/run",
    },
]


def _check(resp: httpx.Response, label: str) -> Any:
    if resp.status_code >= 300:
        print(f"  ✗ {label} failed [{resp.status_code}]: {resp.text[:400]}")
        sys.exit(1)
    return resp.json()


async def main(api_url: str, username: str, password: str, service_count: int) -> None:
    async with httpx.AsyncClient(base_url=api_url, timeout=60.0) as client:
        resp = await client.post("/users/auth", json={
            "username":   username,
            "password":   password,
            "scope":      "openid",
            "expiration": "1h",
        })
        data = _check(resp, f"login as '{username}'")
        client.headers["Authorization"] = f"Bearer {data['access_token']}"
        if data.get("temporal_secret_key"):
            client.headers["Temporal-Secret-Key"] = data["temporal_secret_key"]
        user_id = data["user_profile"]["user_id"]
        print(f"  ✓ Authenticated as '{username}' (user_id={user_id})")

        # Building blocks
        print("\n─── Building Blocks ───────────────────────────────────────────────")
        bb_ids = []
        for bb in BUILDING_BLOCKS:
            result = _check(await client.post("/building-blocks", json=bb), f"create {bb['name']}")
            bb_ids.append(result["building_block_id"])
            print(f"  ✓ {bb['name']}  id={result['building_block_id']}")

        # Patterns — one per building block
        print("\n─── Patterns ──────────────────────────────────────────────────────")
        pattern_ids = []
        for pat, bb_id in zip(PATTERNS, bb_ids):
            payload = {**pat, "building_block_id": bb_id}
            result  = _check(await client.post("/patterns", json=payload), f"create {pat['name']}")
            pattern_ids.append(result["pattern_id"])
            print(f"  ✓ {pat['name']}  id={result['pattern_id']}")

        # Stages — one per pattern
        print("\n─── Stages ────────────────────────────────────────────────────────")
        stage_ids = []
        for stg, pat_id in zip(STAGES, pattern_ids):
            payload = {**stg, "transformation_id": pat_id}
            result  = _check(await client.post("/stages", json=payload), f"create {stg['name']}")
            stage_ids.append(result["stage_id"])
            print(f"  ✓ {stg['name']}  id={result['stage_id']}")

        # Workflow — all 3 stages
        print("\n─── Workflow ──────────────────────────────────────────────────────")
        wf = _check(
            await client.post("/workflows", json={
                "name":      "Main Seed Workflow",
                "stage_ids": stage_ids,
            }),
            "create workflow",
        )
        workflow_id = wf["workflow_id"]
        print(f"  ✓ Main Seed Workflow  id={workflow_id}")

        # Services — all reference the same workflow
        print(f"\n─── Services ({service_count}) ──────────────────────────────────────────────")
        for i in range(1, service_count + 1):
            svc = _check(
                await client.post("/services", json={
                    "name":        f"Seed Service {i:02d}",
                    "description": f"Auto-generated service #{i} using the main seed workflow.",
                    "owner_id":    user_id,
                    "public":      True,
                    "provider":    "INTERNAL",
                    "workflow_id": workflow_id,
                }),
                f"create service {i}",
            )
            print(f"  ✓ {svc['name']}  id={svc['service_id']}")

        print(
            f"\n✓ Done — 3 building blocks, 3 patterns, 3 stages, "
            f"1 workflow, {service_count} services."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed service chain: building blocks → patterns → stages → workflow → services.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--api-url",       default="http://localhost:5000/api/v2", help="API base URL")
    parser.add_argument("--username",      default="admin",  help="Login username")
    parser.add_argument("--password",      default="admin",  help="Login password")
    parser.add_argument("--service-count", type=int, default=10, help="Number of services to create")
    args = parser.parse_args()
    asyncio.run(main(args.api_url, args.username, args.password, args.service_count))
