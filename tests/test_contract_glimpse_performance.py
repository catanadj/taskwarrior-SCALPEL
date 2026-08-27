from __future__ import annotations

import datetime as dt
import time
import unittest

from scalpel.glimpse.model import GlimpseSnapshot, GlimpseTask
from scalpel.glimpse.render import render_agenda, render_week


class GlimpsePerformanceContractTests(unittest.TestCase):
    def test_agenda_handles_several_thousand_non_overlapping_tasks(self) -> None:
        base = int(dt.datetime(2026, 8, 27, tzinfo=dt.timezone.utc).timestamp() * 1000)
        tasks = tuple(
            GlimpseTask(
                f"task-{index}",
                f"Planning item {index}",
                "pending",
                "2026-08-27",
                base + index * 120_000,
                None,
                base + index * 120_000,
                base + index * 120_000 + 60_000,
                1,
                "work",
                (),
                False,
            )
            for index in range(3_000)
        )
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", tasks)

        started = time.perf_counter()
        output = render_agenda(snapshot, width=80)
        elapsed = time.perf_counter() - started

        self.assertIn("Planning item 2999", output)
        self.assertLess(elapsed, 3.0, f"agenda rendering took {elapsed:.3f}s")

    def test_very_narrow_widths_are_clamped_safely(self) -> None:
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", ())
        for renderer in (render_agenda, render_week):
            output = renderer(snapshot, width=1)
            self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
