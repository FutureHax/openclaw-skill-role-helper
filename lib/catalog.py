"""Load and query the game-access role catalog.

Only roleIds present in catalog.json may be granted or removed.
Never match against Discord's full guild role list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SNOWFLAKE_RE = re.compile(r"^\d{17,20}$")
NOT_SELF_SERVE = "that is not a self-serve game role"


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parent.parent / "catalog.json"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or default_catalog_path()
    if not catalog_path.is_file():
        raise FileNotFoundError(f"catalog missing: {catalog_path}")
    with catalog_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("catalog has no categories")
    flat = flatten_roles(data)
    if not flat:
        raise ValueError("catalog has no roles")
    return data


def flatten_roles(catalog: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for category in catalog.get("categories") or []:
        category_id = str(category.get("id") or "")
        category_label = str(category.get("label") or category_id)
        for role in category.get("roles") or []:
            role_id = str(role.get("roleId") or "").strip()
            label = str(role.get("label") or "").strip()
            if not role_id or not label:
                continue
            rows.append(
                {
                    "roleId": role_id,
                    "label": label,
                    "categoryId": category_id,
                    "categoryLabel": category_label,
                    "generalChannelId": str(role.get("generalChannelId") or ""),
                }
            )
    return rows


def allowlisted_ids(catalog: dict[str, Any]) -> set[str]:
    return {row["roleId"] for row in flatten_roles(catalog)}


def is_snowflake(value: str) -> bool:
    return bool(SNOWFLAKE_RE.match(value.strip()))


def filter_member_roles_to_catalog(
    member_role_ids: list[str], catalog: dict[str, Any]
) -> list[dict[str, str]]:
    allow = allowlisted_ids(catalog)
    by_id = {row["roleId"]: row for row in flatten_roles(catalog)}
    out: list[dict[str, str]] = []
    for role_id in member_role_ids:
        if role_id in allow and role_id in by_id:
            out.append(by_id[role_id])
    return out
