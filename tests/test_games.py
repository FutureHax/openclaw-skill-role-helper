#!/usr/bin/env python3
"""Tests for game matching and reply formatting."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from games import (  # noqa: E402
    filter_games_in_lookahead,
    format_adjustment_message,
    match_games_to_role_ids,
)


class MatchTests(unittest.TestCase):
    def test_title_prefix_and_exact(self):
        mappings = [
            {"gameName": "Dragon Delves", "interestedGroupId": "role-dd"},
            {"gameName": "Tomb of Annihilation", "interestedGroupId": "role-tomb"},
        ]
        games = [
            {"id": "1", "title": "Dragon Delves - A Baker's Doesn't"},
            {"id": "2", "title": "Tomb of Annihilation"},
            {"id": "3", "title": "Something Else"},
        ]
        matched = match_games_to_role_ids(games, mappings, ["role-dd"])
        self.assertEqual([g["id"] for g in matched], ["1"])

    def test_system_fallback(self):
        mappings = [{"systemName": "Pirate Borg", "gameName": "", "interestedGroupId": "role-pb"}]
        games = [
            {"id": "1", "title": "Open table", "system": {"name": "Pirate Borg"}},
            {"id": "2", "title": "Other", "system": {"name": "D&D 5E"}},
        ]
        matched = match_games_to_role_ids(games, mappings, ["role-pb"])
        self.assertEqual([g["id"] for g in matched], ["1"])


class LookaheadTests(unittest.TestCase):
    def test_filters_window(self):
        now = datetime(2026, 8, 25, tzinfo=timezone.utc)
        games = [
            {"id": "a", "nextSession": (now + timedelta(days=2)).isoformat()},
            {"id": "b", "nextSession": (now + timedelta(days=10)).isoformat()},
            {"id": "c", "nextSession": (now - timedelta(days=1)).isoformat()},
        ]
        out = filter_games_in_lookahead(games, now=now, days=7)
        self.assertEqual([g["id"] for g in out], ["a"])


class FormatTests(unittest.TestCase):
    def test_add_with_channel_and_games(self):
        msg = format_adjustment_message(
            action="add",
            label="Dragon Delves",
            general_channel_id="1391218431243714683",
            upcoming_games=[
                {
                    "title": "Dragon Delves - A Baker's Doesn't",
                    "nextSession": "2026-08-28T22:00:00.000Z",
                }
            ],
        )
        self.assertIn("**Added:** Dragon Delves", msg)
        self.assertIn("**Gained access to:** <#1391218431243714683>", msg)
        self.assertIn("**Open games (next 7 days):**", msg)
        self.assertIn("Dragon Delves - A Baker's Doesn't", msg)
        self.assertIn("<t:", msg)

    def test_remove_no_games(self):
        msg = format_adjustment_message(
            action="remove",
            label="Pirate Borg",
            general_channel_id="1322063509718302730",
        )
        self.assertIn("**Removed:** Pirate Borg", msg)
        self.assertIn("**Lost access to:** <#1322063509718302730>", msg)
        self.assertNotIn("Open games", msg)

    def test_add_omits_empty_sections(self):
        msg = format_adjustment_message(action="add", label="Ten Candles", general_channel_id="")
        self.assertEqual(msg, "**Added:** Ten Candles")


if __name__ == "__main__":
    unittest.main()
