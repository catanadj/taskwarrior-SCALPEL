from __future__ import annotations

import datetime as dt
import unittest

from scalpel.glimpse.app import GlimpseState, _detail_annotations, update_state
from scalpel.glimpse.details import task_details
from scalpel.glimpse.model import GlimpseSnapshot, GlimpseTask
from scalpel.glimpse.search import search_snapshot


class GlimpseDetailsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.task = GlimpseTask("u1", "Write report", "pending", "2026-08-27", 1, 2, 1, 3, 30, "work", ("focus",), True)

    def test_search_covers_description_project_tags_and_uuid(self) -> None:
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (self.task,))
        self.assertEqual(len(search_snapshot(snapshot, "report").tasks), 1)
        self.assertEqual(len(search_snapshot(snapshot, "work").tasks), 1)
        self.assertEqual(len(search_snapshot(snapshot, "focus").tasks), 1)
        self.assertEqual(len(search_snapshot(snapshot, "missing").tasks), 0)

    def test_details_are_readable_and_width_bounded(self) -> None:
        output = task_details(self.task, width=72, timezone_name="UTC", annotations=("Overlaps another task.",))
        self.assertIn("Write report", output)
        self.assertIn("Nautical     preview", output)
        self.assertIn("Overlaps another task.", output)
        self.assertTrue(all(len(line) <= 72 for line in output.splitlines()))

    def test_enter_and_escape_toggle_details(self) -> None:
        opened = update_state(GlimpseState(), "\n")
        self.assertTrue(opened.details_visible)
        self.assertFalse(update_state(opened, "\x1b").details_visible)

    def test_detail_annotations_explain_overlap_and_out_of_hours(self) -> None:
        base = int(dt.datetime(2026, 8, 27, 7, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        first = self.task.__class__(
            "u1", "First", "pending", "2026-08-27", base, None, base, base + 60 * 60_000, 60, None, (), False
        )
        second = self.task.__class__(
            "u2",
            "Second",
            "pending",
            "2026-08-27",
            base + 30 * 60_000,
            None,
            base + 30 * 60_000,
            base + 90 * 60_000,
            60,
            None,
            (),
            False,
        )
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (first, second), 8 * 60, 18 * 60)
        notes = _detail_annotations(snapshot, 0)
        self.assertIn("Overlaps another task.", notes)
        self.assertIn("Starts outside configured work hours.", notes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
