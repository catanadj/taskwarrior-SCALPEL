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

    def test_snapshot_preserves_workhours_and_valid_custom_bands(self) -> None:
        snapshot = snapshot_from_payload(
            {"cfg": {"work_start_min": 480, "work_end_min": 1080, "time_bands": [
                {"label": "Focus", "start": 540, "end": 720},
                {"label": "Invalid", "start": 800, "end": 700},
            ]}},
            start_date=dt.date(2026, 8, 27),
            days=1,
            timezone_name="UTC",
        )
        self.assertEqual((snapshot.work_start_min, snapshot.work_end_min), (480, 1080))
        self.assertEqual([(band.label, band.start_min, band.end_min) for band in snapshot.bands], [("Focus", 540, 720)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
