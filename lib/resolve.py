"""Resolve user queries against the game-access catalog only."""

from __future__ import annotations

from typing import Any

from catalog import NOT_SELF_SERVE, flatten_roles, is_snowflake


def lookup_catalog(catalog: dict[str, Any], query: str) -> dict[str, Any]:
    """Fuzzy-match catalog labels. Never consult Discord guild roles."""
    q = (query or "").strip()
    if not q:
        return {
            "ok": False,
            "error": "empty query",
            "matches": [],
            "unique": None,
        }

    rows = flatten_roles(catalog)

    if is_snowflake(q):
        hit = next((row for row in rows if row["roleId"] == q), None)
        if hit:
            return {"ok": True, "matches": [hit], "unique": hit, "query": q}
        return {
            "ok": False,
            "error": NOT_SELF_SERVE,
            "matches": [],
            "unique": None,
            "query": q,
        }

    q_lower = q.lower()
    exact = [row for row in rows if row["label"].lower() == q_lower]
    if len(exact) == 1:
        return {"ok": True, "matches": exact, "unique": exact[0], "query": q}
    if len(exact) > 1:
        return {
            "ok": False,
            "error": "ambiguous match",
            "matches": exact,
            "unique": None,
            "query": q,
        }

    partial = [
        row
        for row in rows
        if q_lower in row["label"].lower() or row["label"].lower() in q_lower
    ]
    if len(partial) == 1:
        return {"ok": True, "matches": partial, "unique": partial[0], "query": q}
    if len(partial) > 1:
        return {
            "ok": False,
            "error": "ambiguous match",
            "matches": partial,
            "unique": None,
            "query": q,
        }
    return {
        "ok": False,
        "error": "no catalog match",
        "matches": [],
        "unique": None,
        "query": q,
        "hint": "Use /get-roles to browse self-serve game roles.",
    }


def resolve_for_write(catalog: dict[str, Any], query: str) -> dict[str, Any]:
    """Resolve a role for add/remove. Fail closed unless unique + allowlisted."""
    result = lookup_catalog(catalog, query)
    if result.get("unique"):
        return {
            "ok": True,
            "role": result["unique"],
            "query": query,
        }
    if result.get("error") == NOT_SELF_SERVE:
        return {"ok": False, "error": NOT_SELF_SERVE, "query": query}
    if result.get("error") == "ambiguous match":
        return {
            "ok": False,
            "error": "ambiguous match",
            "matches": result.get("matches") or [],
            "query": query,
        }
    if result.get("error") == "empty query":
        return {"ok": False, "error": "empty query", "query": query}
    return {
        "ok": False,
        "error": NOT_SELF_SERVE if is_snowflake((query or "").strip()) else "no catalog match",
        "matches": [],
        "query": query,
        "hint": result.get("hint"),
    }
