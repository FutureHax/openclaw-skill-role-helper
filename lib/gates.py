"""Hard gates for conversational role changes."""

from __future__ import annotations

from typing import Any

from resolve import resolve_for_write


def assert_self_only(caller_id: str, target_user_id: str | None = None) -> dict[str, Any] | None:
    """Player self-serve may only change the caller's own roles."""
    caller = (caller_id or "").strip()
    if not caller:
        return {"ok": False, "error": "caller_id required"}
    target = (target_user_id or caller).strip()
    if target != caller:
        return {
            "ok": False,
            "error": "can only manage your own game roles",
            "caller": caller,
            "target": target,
        }
    return None


def gate_write(
    catalog: dict[str, Any],
    caller_id: str,
    role_query: str,
    target_user_id: str | None = None,
) -> dict[str, Any]:
    """Return ok+role for Discord write, or an error that must not hit Discord."""
    blocked = assert_self_only(caller_id, target_user_id)
    if blocked:
        return blocked
    resolved = resolve_for_write(catalog, role_query)
    if not resolved.get("ok"):
        return resolved
    return {
        "ok": True,
        "caller": caller_id.strip(),
        "userId": caller_id.strip(),
        "role": resolved["role"],
    }
