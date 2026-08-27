from __future__ import annotations

import datetime as dt
import unittest

from scalpel.glimpse.model import GlimpseSnapshot, GlimpseTask
from scalpel.glimpse.render import render_week


class GlimpseWeekContractTests(unittest.TestCase):
    def test_week_view_uses_columns_at_wide_width(self) -> None:
        task = GlimpseTask("a", "Monday review", "pending", "2026-08-24", 0, None, 0, 1, 30, "work", (), False)
        output = render_week(GlimpseSnapshot(dt.date(2026, 8, 24), 7, "UTC", (task,)), width=120)
        self.assertIn("Mon 24", output)
        self.assertIn("Sun 30", output)
        self.assertIn("Monday…", output)
        self.assertLessEqual(max(len(line) for line in output.splitlines()), 120)

    def test_week_view_stacks_days_when_narrow(self) -> None:
        tasks = (
            GlimpseTask("a", "Monday review", "pending", "2026-08-24", 1, None, 1, 1, 30, None, (), False),
            GlimpseTask("b", "Wednesday focus", "pending", "2026-08-26", 2, None, 2, 2, 60, None, (), True),
        )
        output = render_week(GlimpseSnapshot(dt.date(2026, 8, 24), 7, "UTC", tasks), width=80)
        self.assertIn("Mon 24", output)
        self.assertIn("Wed 26", output)
        self.assertIn("⚓", output)
        self.assertIn("Monday review", output)
        self.assertIn("Wednesday focus", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
