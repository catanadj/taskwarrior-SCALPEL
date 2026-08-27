from __future__ import annotations

import datetime as dt
import unittest

from scalpel.glimpse.cli import build_parser
from scalpel.glimpse.model import GlimpseSnapshot
from scalpel.glimpse.source import snapshot_from_payload


class GlimpseFoundationContractTests(unittest.TestCase):
    def test_snapshot_is_immutable_and_preserves_terminal_fields(self) -> None:
        payload = {
            "tasks": [
                {
                    "uuid": "u1",
                    "description": "Plan week",
                    "status": "pending",
                    "day_key": "2026-08-27",
                    "scheduled_ms": 1000,
                    "due_ms": 2000,
                    "duration_min": 30,
                    "project": "work",
                    "tags": ["focus", ""],
                    "nautical_preview": True,
                },
                {"description": "missing identity"},
            ]
        }

        snapshot = snapshot_from_payload(
            payload,
            start_date=dt.date(2026, 8, 27),
            days=0,
            timezone_name="UTC",
        )

        self.assertIsInstance(snapshot, GlimpseSnapshot)
        self.assertEqual(snapshot.days, 1)
        self.assertEqual(len(snapshot.tasks), 1)
        self.assertEqual(snapshot.tasks[0].tags, ("focus",))
        self.assertTrue(snapshot.tasks[0].nautical_preview)
        with self.assertRaises(AttributeError):
            snapshot.tasks[0].description = "changed"  # type: ignore[misc]

    def test_cli_parser_has_stable_program_identity(self) -> None:
        self.assertEqual(build_parser().prog, "scalpel-glimpse")


if __name__ == "__main__":
    unittest.main(verbosity=2)
