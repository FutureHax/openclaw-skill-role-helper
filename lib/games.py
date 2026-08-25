"""Match upcoming games to catalog role IDs (same rules as Zordon role menus)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

LOOKAHEAD_DAYS = 7


def mapping_matches_game(mapping: dict[str, Any], game: dict[str, Any]) -> bool:
    title = (game.get("title") or "").lower()
    system_obj = game.get("system") or {}
    system = (system_obj.get("name") if isinstance(system_obj, dict) else None) or game.get("systemName") or ""
    system = str(system).lower()
    game_name = (mapping.get("gameName") or "").strip().lower()
    system_name = (mapping.get("systemName") or "").strip().lower()

    if game_name:
        return (
            title == game_name
            or title.startswith(f"{game_name}:")
            or title.startswith(f"{game_name} -")
            or title.startswith(f"{game_name} ")
        )
    if system_name:
        return system == system_name
    return False


def match_games_to_role_ids(
    games: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    role_ids: list[str],
) -> list[dict[str, Any]]:
    wanted = set(role_ids)
    relevant = [
        m
        for m in mappings
        if m.get("interestedGroupId") and m["interestedGroupId"] in wanted
    ]
    matched: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for game in games:
        key = game.get("id") or game.get("title")
        if key in seen:
            continue
        if any(mapping_matches_game(m, game) for m in relevant):
            seen.add(key)
            matched.append(game)
    return matched


def filter_games_in_lookahead(
    games: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    days: int = LOOKAHEAD_DAYS,
) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    end = now + timedelta(days=days)
    out: list[dict[str, Any]] = []
    for game in games:
        raw = game.get("nextSession")
        if not raw:
            continue
        try:
            session = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if session.tzinfo is None:
            session = session.replace(tzinfo=timezone.utc)
        if now <= session <= end:
            out.append(game)
    return out


def format_game_line(game: dict[str, Any]) -> str:
    title = game.get("title") or "Untitled"
    raw = game.get("nextSession")
    if not raw:
        return f"- {title}"
    try:
        session = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if session.tzinfo is None:
            session = session.replace(tzinfo=timezone.utc)
        unix = int(session.timestamp())
        return f"- {title} (<t:{unix}:F>, <t:{unix}:R>)"
    except ValueError:
        return f"- {title}"


def format_adjustment_message(
    *,
    action: str,
    label: str,
    general_channel_id: str = "",
    upcoming_games: list[dict[str, Any]] | None = None,
) -> str:
    """Mirror Zordon role-menu copy: Added/Removed + Gained/Lost access + optional games."""
    lines: list[str] = []
    channel_mention = f"<#{general_channel_id}>" if general_channel_id else ""

    if action == "add":
        lines.append(f"**Added:** {label}")
        if channel_mention:
            lines.append(f"**Gained access to:** {channel_mention}")
        games = upcoming_games or []
        if games:
            lines.append("")
            lines.append("**Open games (next 7 days):**")
            lines.extend(format_game_line(g) for g in games)
    else:
        lines.append(f"**Removed:** {label}")
        if channel_mention:
            lines.append(f"**Lost access to:** {channel_mention}")

    return "\n".join(lines)
