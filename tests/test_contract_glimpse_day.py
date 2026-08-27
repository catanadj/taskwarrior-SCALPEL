from __future__ import annotations

import datetime as dt
import unittest

from scalpel.glimpse.model import GlimpseSnapshot, GlimpseTask
from scalpel.glimpse.render import render_day


class GlimpseDayContractTests(unittest.TestCase):
    def test_day_view_has_hourly_grid_and_empty_hours(self) -> None:
        output = render_day(
            GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", ()),
            width=40,
            color=False,
        )
        self.assertIn("SCALPEL · Day · Thu 27 Aug 2026", output)
        self.assertIn("08:00 │", output)
        self.assertIn("23:00 │", output)
        self.assertIn("0 tasks · 0m planned · 0 conflicts", output)
        self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))

    def test_day_view_shows_duration_bars_and_conflict_marker(self) -> None:
        base = int(dt.datetime(2026, 8, 27, 9, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        tasks = (
            GlimpseTask(
                "a", "Focus block", "pending", "2026-08-27", base, None, base, base + 7_200_000, 120, "work", (), False
            ),
            GlimpseTask(
                "b",
                "Review",
                "pending",
                "2026-08-27",
                base + 1_800_000,
                None,
                base + 1_800_000,
                base + 2_700_000,
                15,
                None,
                (),
                False,
            ),
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", tasks), color=False)
        self.assertIn("09:00 │", output)
        self.assertIn("⚠", output)
        self.assertIn("████", output)
        self.assertIn("Focus block", output)
        self.assertEqual(output.count("Focus block"), 1)
        self.assertIn("continues", output)
        self.assertIn("Review", output)
        self.assertIn("1 conflict", output)

    def test_day_view_shows_bands_now_marker_and_out_of_hours_tasks(self) -> None:
        base = int(dt.datetime(2026, 8, 27, 5, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        task = GlimpseTask(
            "early", "Early task", "pending", "2026-08-27", base, None, base, base + 30 * 60_000, 30, None, (), False
        )
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (task,), 8 * 60, 18 * 60)
        output = render_day(snapshot, width=80, now_ms=base)
        self.assertIn("[Morning]", output)
        self.assertIn("◀ now", output)
        self.assertIn("outside work hours", output)
        self.assertIn("L1", output)

    def test_day_view_handles_overnight_task(self) -> None:
        start = int(dt.datetime(2026, 8, 27, 23, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        task = GlimpseTask(
            "overnight",
            "Overnight handoff",
            "pending",
            "2026-08-27",
            start,
            None,
            start,
            start + 90 * 60_000,
            90,
            None,
            (),
            False,
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (task,)), width=40)
        self.assertIn("23:00 │", output)
        self.assertIn("Overnight handoff", output)
        self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))

    def test_day_view_keeps_continuing_tasks_in_the_same_lane(self) -> None:
        base = int(dt.datetime(2026, 8, 27, 9, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        tasks = (
            GlimpseTask(
                "a", "Long focus", "pending", "2026-08-27", base, None, base, base + 3 * 60 * 60_000,
                180, None, (), False
            ),
            GlimpseTask(
                "b", "Short task", "pending", "2026-08-27", base + 30 * 60_000, None,
                base + 30 * 60_000, base + 60 * 60_000, 30, None, (), False
            ),
            GlimpseTask(
                "c", "Late task", "pending", "2026-08-27", base + 75 * 60_000, None,
                base + 75 * 60_000, base + 90 * 60_000, 15, None, (), False
            ),
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", tasks), width=80)
        hour_10 = output.split("10:00 │", 1)[1].split("11:00 │", 1)[0]
        self.assertIn("L1", hour_10)
        self.assertIn("L2", hour_10)
        self.assertIn("Long focus", output)
        self.assertEqual(output.count("Long focus"), 1)

    def test_day_view_handles_dst_transition_in_named_timezone(self) -> None:
        start = int(dt.datetime(2026, 3, 8, 6, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        task = GlimpseTask(
            "dst",
            "DST morning task",
            "pending",
            "2026-03-08",
            start,
            None,
            start,
            start + 60 * 60_000,
            60,
            None,
            (),
            False,
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 3, 8), 1, "America/New_York", (task,)), width=40)
        self.assertIn("Sun 08 Mar 2026", output)
        self.assertIn("DST morning task", output)
        self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))

    def test_day_view_uses_local_boundaries_on_dst_fall_back(self) -> None:
        start = int(dt.datetime(2026, 11, 1, 6, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        task = GlimpseTask(
            "dst-fall",
            "DST fallback task",
            "pending",
            "2026-11-01",
            start,
            None,
            start,
            start + 60 * 60_000,
            60,
            None,
            (),
            False,
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 11, 1), 1, "America/New_York", (task,)), width=40)
        self.assertIn("DST fallback task", output)
        self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))

    def test_day_view_ignores_invalid_reverse_interval(self) -> None:
        start = int(dt.datetime(2026, 8, 27, 9, tzinfo=dt.timezone.utc).timestamp() * 1000)
        task = GlimpseTask(
            "invalid",
            "Invalid interval",
            "pending",
            "2026-08-27",
            start,
            None,
            start,
            start - 60 * 60_000,
            60,
            None,
            (),
            False,
        )
        output = render_day(GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (task,)), width=40)
        self.assertNotIn("Invalid interval", output)
        self.assertIn("0 conflicts", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
