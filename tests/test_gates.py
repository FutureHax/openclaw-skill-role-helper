#!/usr/bin/env python3
"""Unit tests for catalog allowlist gates (no live Discord)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from catalog import (  # noqa: E402
    NOT_SELF_SERVE,
    allowlisted_ids,
    filter_member_roles_to_catalog,
    flatten_roles,
    load_catalog,
)
from gates import assert_self_only, gate_write  # noqa: E402
from resolve import lookup_catalog, resolve_for_write  # noqa: E402


SAMPLE = {
    "categories": [
        {
            "id": "dnd-5e",
            "label": "D&D 5e",
            "roles": [
                {
                    "roleId": "1400202365331837051",
                    "label": "Tomb of Annihilation",
                    "generalChannelId": "1400202203775369448",
                },
                {
                    "roleId": "1391218705894998028",
                    "label": "Dragon Delves",
                    "generalChannelId": "1391218431243714683",
                },
            ],
        },
        {
            "id": "other",
            "label": "Other systems",
            "roles": [
                {
                    "roleId": "1322063277898989660",
                    "label": "Pirate Borg",
                    "generalChannelId": "1322063509718302730",
                },
            ],
        },
    ]
}


class CatalogTests(unittest.TestCase):
    def test_allowlisted_ids(self):
        ids = allowlisted_ids(SAMPLE)
        self.assertEqual(
            ids,
            {
                "1400202365331837051",
                "1391218705894998028",
                "1322063277898989660",
            },
        )

    def test_load_catalog_fail_closed_missing(self):
        with self.assertRaises(FileNotFoundError):
            load_catalog(Path("/tmp/does-not-exist-role-helper-catalog.json"))

    def test_load_catalog_fail_closed_empty(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"categories": []}, handle)
            path = Path(handle.name)
        try:
            with self.assertRaises(ValueError):
                load_catalog(path)
        finally:
            path.unlink(missing_ok=True)

    def test_status_filters_non_catalog_roles(self):
        member = [
            "1400202365331837051",
            "999999999999999999",  # staff-looking snowflake not in catalog
            "1322063277898989660",
        ]
        filtered = filter_member_roles_to_catalog(member, SAMPLE)
        self.assertEqual(
            [row["roleId"] for row in filtered],
            ["1400202365331837051", "1322063277898989660"],
        )


class LookupTests(unittest.TestCase):
    def test_exact_label(self):
        result = lookup_catalog(SAMPLE, "Pirate Borg")
        self.assertTrue(result["ok"])
        self.assertEqual(result["unique"]["roleId"], "1322063277898989660")

    def test_partial_unique(self):
        result = lookup_catalog(SAMPLE, "tomb")
        self.assertTrue(result["ok"])
        self.assertEqual(result["unique"]["label"], "Tomb of Annihilation")

    def test_ambiguous(self):
        # "d" matches both Dragon Delves and Tomb of Annihilation? "d" is in both...
        # Better: use a catalog with two "Dragon" labels. For SAMPLE, "dragon" is unique.
        dual = {
            "categories": [
                {
                    "id": "x",
                    "label": "X",
                    "roles": [
                        {"roleId": "111111111111111111", "label": "House Alpha", "generalChannelId": "1"},
                        {"roleId": "222222222222222222", "label": "House Beta", "generalChannelId": "2"},
                    ],
                }
            ]
        }
        result = lookup_catalog(dual, "House")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "ambiguous match")
        self.assertEqual(len(result["matches"]), 2)

    def test_snowflake_in_catalog(self):
        result = lookup_catalog(SAMPLE, "1400202365331837051")
        self.assertTrue(result["ok"])
        self.assertEqual(result["unique"]["label"], "Tomb of Annihilation")

    def test_snowflake_not_in_catalog_refused(self):
        # Plausible staff-looking ID; must not grant and must not name it as privileged
        result = lookup_catalog(SAMPLE, "2783474262582231041")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], NOT_SELF_SERVE)
        self.assertEqual(result["matches"], [])

    def test_guild_role_name_not_in_catalog_no_hit(self):
        # Label that might exist as a guild role but is NOT in the catalog
        result = lookup_catalog(SAMPLE, "Moderator")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "no catalog match")
        self.assertEqual(result["matches"], [])

    def test_at_everyone_refused(self):
        result = lookup_catalog(SAMPLE, "@everyone")
        self.assertFalse(result["ok"])
        self.assertEqual(result["matches"], [])

    def test_empty_query(self):
        result = lookup_catalog(SAMPLE, "  ")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "empty query")


class GateTests(unittest.TestCase):
    def test_caller_mismatch_blocked(self):
        err = assert_self_only("111", "222")
        self.assertIsNotNone(err)
        self.assertFalse(err["ok"])

    def test_write_refuses_non_catalog_before_http(self):
        result = gate_write(SAMPLE, "111111111111111111", "999999999999999999")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], NOT_SELF_SERVE)
        self.assertNotIn("role", result)

    def test_write_unique_ok(self):
        result = gate_write(SAMPLE, "111111111111111111", "Pirate Borg")
        self.assertTrue(result["ok"])
        self.assertEqual(result["role"]["roleId"], "1322063277898989660")
        self.assertEqual(result["userId"], "111111111111111111")

    def test_write_cannot_target_other_user(self):
        result = gate_write(
            SAMPLE,
            "111111111111111111",
            "Pirate Borg",
            target_user_id="222222222222222222",
        )
        self.assertFalse(result["ok"])
        self.assertIn("own game roles", result["error"])

    def test_resolve_for_write_ambiguous(self):
        dual = {
            "categories": [
                {
                    "id": "x",
                    "label": "X",
                    "roles": [
                        {"roleId": "111111111111111111", "label": "House Alpha", "generalChannelId": "1"},
                        {"roleId": "222222222222222222", "label": "House Beta", "generalChannelId": "2"},
                    ],
                }
            ]
        }
        result = resolve_for_write(dual, "House")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "ambiguous match")


class LiveCatalogTests(unittest.TestCase):
    def test_shipped_catalog_loads(self):
        data = load_catalog(ROOT / "catalog.json")
        rows = flatten_roles(data)
        self.assertGreaterEqual(len(rows), 10)
        ids = allowlisted_ids(data)
        self.assertIn("1400202365331837051", ids)
        self.assertIn("1322063277898989660", ids)


if __name__ == "__main__":
    unittest.main()
