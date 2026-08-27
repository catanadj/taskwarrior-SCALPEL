from __future__ import annotations

import datetime as dt
import re
import unittest

from scalpel.glimpse.model import GlimpseSnapshot, GlimpseTask
from scalpel.glimpse.render import render_agenda


class GlimpseAgendaContractTests(unittest.TestCase):
    def test_agenda_is_width_bounded_and_describes_empty_days(self) -> None:
        snapshot = GlimpseSnapshot(
            start_date=dt.date(2026, 8, 27),
            days=2,
            timezone_name="UTC",
            tasks=(),
        )

        output = render_agenda(snapshot, width=40)
        self.assertTrue(all(len(line) <= 40 for line in output.splitlines()))
        self.assertIn("Thu 27 Aug", output)
        self.assertIn("Fri 28 Aug", output)
        self.assertIn("No tasks scheduled.", output)
        self.assertIn("Planned 0m · 0 conflicts · 0 tasks", output)

    def test_agenda_marks_statuses_nautical_tasks_and_overlaps(self) -> None:
        base = 1_788_120_000_000
        snapshot = GlimpseSnapshot(
            start_date=dt.date(2026, 8, 27),
            days=1,
            timezone_name="UTC",
            tasks=(
                GlimpseTask("a", "Long planning task", "pending", "2026-08-27", base, None, base, base + 3_600_000, 60, "work", (), False),
                GlimpseTask("b", "Recurring preview", "pending", "2026-08-27", base + 1_800_000, None, base + 1_800_000, base + 2_700_000, 15, None, (), True),
                GlimpseTask("c", "Completed task", "completed", "2026-08-27", base + 7_200_000, None, base + 7_200_000, base + 7_500_000, 5, None, (), False),
                GlimpseTask("d", "Unlinked preview", "pending", "2026-08-27", base + 10_800_000, None, base + 10_800_000, base + 11_700_000, 15, None, (), True),
            ),
        )

        output = render_agenda(snapshot, width=80, color=False)
        self.assertIn("⚠", output)
        self.assertIn("⚓", output)
        self.assertIn("✓", output)
        self.assertIn("Long planning task", output)
        self.assertIn("Recurring preview", output)
        self.assertIn("work", output)
        self.assertIn("1 conflict", output)
        self.assertNotRegex(output, r"\x1b\[")

    def test_color_output_is_optional_and_can_be_stripped(self) -> None:
        task = GlimpseTask("a", "Colored task", "pending", "2026-08-27", 0, None, 0, 60_000, 1, None, (), False)
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", (task,))
        output = render_agenda(snapshot, width=80, color=True)
        self.assertRegex(output, r"\x1b\[")
        self.assertIn("Colored task", re.sub(r"\x1b\[[0-9;]*m", "", output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
