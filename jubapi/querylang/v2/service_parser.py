"""
Simple query language for the Service domain.

Syntax:
    jub.v1.SVC(*)                 — return all services
    jub.v1.SVC(name=cancer)       — name contains "cancer" (case-insensitive)
    jub.v1.SVC(public=true)       — only public services
    jub.v1.SVC(owner=usr_abc)     — services owned by this user
    jub.v1.SVC(provider=NEZ)      — filter by provider (XELHUA, NEZ, EXTERNAL, OTHER)
    jub.v1.SVC(name=x,public=true)— combine filters with comma
"""

import re
from typing import Any, Dict

_PREFIX  = "jub.v1."
_PATTERN = re.compile(r'^jub\.v1\.SVC\((.*)\)$', re.IGNORECASE)

_BOOL_MAP = {"true": True, "false": False, "1": True, "0": False}


class ServiceQuery:
    """Parsed representation of a SVC(...) query."""

    def __init__(self, filters: Dict[str, Any]) -> None:
        self.filters = filters  # empty dict ⟹ match all

    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def parse(query_str: str) -> "ServiceQuery":
        query_str = query_str.strip()
        match = _PATTERN.match(query_str)
        if not match:
            raise ValueError(
                f"Invalid service query '{query_str}'. "
                "Expected format: jub.v1.SVC(*) or jub.v1.SVC(key=value,...)"
            )

        content = match.group(1).strip()

        if content == "*" or content == "":
            return ServiceQuery(filters={})

        filters: Dict[str, Any] = {}
        for part in content.split(","):
            part = part.strip()
            if "=" not in part:
                raise ValueError(
                    f"Invalid filter token '{part}'. Use key=value syntax or '*' for all."
                )
            key, _, raw_val = part.partition("=")
            key     = key.strip().lower()
            raw_val = raw_val.strip()

            if key not in {"name", "public", "owner", "id", "provider"}:
                raise ValueError(
                    f"Unknown filter key '{key}'. Allowed: name, public, owner, id, provider."
                )

            if key == "public":
                if raw_val.lower() not in _BOOL_MAP:
                    raise ValueError(f"'public' must be true or false, got '{raw_val}'.")
                filters[key] = _BOOL_MAP[raw_val.lower()]
            else:
                filters[key] = raw_val

        return ServiceQuery(filters=filters)

    # ──────────────────────────────────────────────────────────────────────
    def to_mongo_filter(self) -> Dict[str, Any]:
        """Convert parsed filters to a MongoDB query dict."""
        if not self.filters:
            return {}

        mongo: Dict[str, Any] = {}
        for key, value in self.filters.items():
            if key == "name":
                mongo["name"] = {"$regex": re.escape(str(value)), "$options": "i"}
            elif key == "public":
                mongo["public"] = value
            elif key == "owner":
                mongo["owner_id"] = value
            elif key == "id":
                mongo["service_id"] = value
            elif key == "provider":
                mongo["provider"] = value.upper()

        return mongo

    def __repr__(self) -> str:
        return f"ServiceQuery(filters={self.filters})"
