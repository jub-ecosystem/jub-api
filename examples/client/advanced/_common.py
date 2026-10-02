"""
Shared helpers for the JUB client examples.

Every example is a standalone script, but they are meant to be run in order
(03 → 12). Each step stores the ids it creates in `.state.json` next to this
file so the following steps can reuse them. The state belongs to one user:
when JUB_USERNAME changes, it starts empty again.

Environment variables:
    JUB_API_URL    Base URL of the JUB API (default: http://localhost:5000)
    JUB_USERNAME   Defaults to invitado (../.env.examples), or the user
    JUB_PASSWORD   printed by ../01_signup.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, TypeVar

import httpx
from dotenv import load_dotenv
from option import Result

import jub.dto.v2 as DTO
from jub.client.v2 import JubClient, JubClientBuilder

T = TypeVar("T")

EXAMPLES_DIR = Path(__file__).parent
STATE_PATH   = EXAMPLES_DIR / ".state.json"
FIXTURES_DIR = EXAMPLES_DIR / "fixtures"
CHARTS_DIR   = EXAMPLES_DIR.parents[2] / "source"   # heatmap.html, radar.html

load_dotenv(EXAMPLES_DIR.parent / ".env.examples")   # defaults: invitado / invitado

API_URL      = os.environ.get("JUB_API_URL", "http://localhost:5000")
USERNAME     = os.environ.get("JUB_USERNAME") or sys.exit("Set JUB_USERNAME and JUB_PASSWORD (see ../.env.examples).")
PASSWORD     = os.environ.get("JUB_PASSWORD") or sys.exit("Set JUB_USERNAME and JUB_PASSWORD (see ../.env.examples).")
SUFFIX       = USERNAME   # keeps observatory ids and names unique per user


# ---------------------------------------------------------------------------
# State shared between steps
# ---------------------------------------------------------------------------

def load_state() -> Dict[str, Any]:
    """State of the current user; empty if there is none or it belongs to another user."""
    if not STATE_PATH.exists():
        return {}
    state = json.loads(STATE_PATH.read_text())
    return state if state.get("username") == USERNAME else {}


def save_state(**values: Any) -> Dict[str, Any]:
    """Merges `values` into .state.json and returns the full state."""
    state = load_state()
    state.update(values, username=USERNAME)
    STATE_PATH.write_text(json.dumps(state, indent=2))
    return state


def require(key: str, step: str) -> Any:
    """Returns state[key] or exits telling the user which step to run first."""
    value = load_state().get(key)
    if value is None:
        sys.exit(f"'{key}' not found in {STATE_PATH.name}. Run {step} first.")
    return value


# ---------------------------------------------------------------------------
# Result handling
# ---------------------------------------------------------------------------

def describe_error(error: Exception) -> str:
    """Human-readable error, including the HTTP status and body when available."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}: {error.response.text}"
    return f"{type(error).__name__}: {error}"


def unwrap(result: Result[T, Exception], action: str) -> T:
    """Returns the Ok value, or prints the error and exits the script."""
    if result.is_err:
        sys.exit(f"✗ {action} failed → {describe_error(result.unwrap_err())}")
    return result.unwrap()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

async def build_client(upload_registry_path: Optional[str] = None) -> JubClient:
    """Authenticated client for JUB_USERNAME / JUB_PASSWORD."""
    builder = JubClientBuilder(api_url=API_URL, username=USERNAME, password=PASSWORD)
    if upload_registry_path:
        builder = builder.with_upload_registry(upload_registry_path)
    return unwrap(await builder.build(), f"login as '{USERNAME}'")


# ---------------------------------------------------------------------------
# Catalog & task helpers
# ---------------------------------------------------------------------------

def index_catalog_items(catalog: DTO.CatalogResponseDTO) -> Dict[str, str]:
    """Flattens a catalog's item tree into {item value: catalog_item_id}."""
    index: Dict[str, str] = {}

    def walk(items: Iterable[DTO.CatalogItemResponseDTO]) -> None:
        for it in items:
            index[it.value] = it.catalog_item_id
            walk(it.children)

    walk(catalog.items)
    return index


def item_ids(catalog_key: str, values: Optional[Iterable[str]] = None) -> list[str]:
    """catalog_item_ids stored by 03/05 for `catalog_key` (all of them, or only `values`)."""
    items: Dict[str, str] = require("items", "03_catalogs.py").get(catalog_key)
    if items is None:
        sys.exit(f"Catalog '{catalog_key}' not found in {STATE_PATH.name}. Run 03_catalogs.py / 05_link_catalogs.py first.")
    if values is None:
        return list(items.values())
    return [items[v] for v in values]


async def wait_for_task(client: JubClient, task_id: str, timeout: float = 60.0, interval: float = 1.0) -> DTO.TaskXDTO:
    """Polls GET /tasks/{id} until the task leaves pending/running (or times out)."""
    elapsed = 0.0
    while True:
        task = unwrap(await client.get_task(task_id), f"get task {task_id}")
        if task.current_status not in ("pending", "running") or elapsed >= timeout:
            return task
        await asyncio.sleep(interval)
        elapsed += interval
