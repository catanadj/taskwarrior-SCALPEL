import unittest
import datetime as dt

from scalpel.planner import (
    op_align_ends,
    op_align_starts,
    op_distribute,
    op_nudge,
    op_stack,
)


class TestPlannerOpsContract(unittest.TestCase):
    def test_align_starts(self) -> None:
        base = 1577836800000
        h = 60 * 60000
        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
            "b": (base + 11 * h, base + 12 * h, 60),
            "c": (base + 9 * h, base + 10 * h, 60),
        }
        out = op_align_starts(["a", "b", "c"], events, snap_min=1)
        self.assertEqual(out["a"].start_ms, base + 9 * h)
        self.assertEqual(out["b"].start_ms, base + 9 * h)
        self.assertEqual(out["c"].start_ms, base + 9 * h)

    def test_align_ends(self) -> None:
        base = 1577836800000
        h = 60 * 60000
        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
            "b": (base + 11 * h, base + 12 * h, 60),
            "c": (base + 9 * h, base + 10 * h, 60),
        }
        out = op_align_ends(["a", "b", "c"], events, snap_min=1)
        self.assertEqual(out["a"].due_ms, base + 12 * h)
        self.assertEqual(out["b"].due_ms, base + 12 * h)
        self.assertEqual(out["c"].due_ms, base + 12 * h)

    def test_stack(self) -> None:
        base = 1577836800000
        h = 60 * 60000
        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
            "b": (base + 11 * h, base + 12 * h, 60),
            "c": (base + 10 * h, base + 11 * h, 60),
        }
        out = op_stack(["a", "b", "c"], events, snap_min=1)
        self.assertEqual(out["a"].start_ms, base + 9 * h)
        self.assertEqual(out["c"].start_ms, base + 10 * h)
        self.assertEqual(out["b"].start_ms, base + 11 * h)

    def test_distribute(self) -> None:
        base = 1577836800000
        h = 60 * 60000
        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
            "b": (base + 12 * h, base + 13 * h, 60),
            "c": (base + 15 * h, base + 16 * h, 60),
        }
        out = op_distribute(["a", "b", "c"], events, snap_min=1)
        self.assertEqual(out["a"].start_ms, base + 9 * h)
        self.assertEqual(out["b"].start_ms, base + 12 * h)
        self.assertEqual(out["c"].start_ms, base + 15 * h)

    def test_nudge(self) -> None:
        base = 1577836800000
        h = 60 * 60000
        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
        }
        out = op_nudge(["a"], events, delta_min=30)
        self.assertEqual(out["a"].start_ms, base + 9 * h + 30 * 60000)
        self.assertEqual(out["a"].due_ms, base + 10 * h + 30 * 60000)

    def test_align_starts_groups_by_cfg_timezone_day(self) -> None:
        a_start = int(dt.datetime(2020, 1, 1, 23, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        b_start = int(dt.datetime(2020, 1, 2, 0, 30, tzinfo=dt.timezone.utc).timestamp() * 1000)
        h = 60 * 60000
        events = {
            "a": (a_start, a_start + h, 60),
            "b": (b_start, b_start + h, 60),
        }

        out = op_align_starts(["a", "b"], events, snap_min=1, tz_name="America/New_York")
        self.assertEqual(out["a"].start_ms, a_start)
        self.assertEqual(out["b"].start_ms, a_start)


if __name__ == "__main__":
    unittest.main(verbosity=2)
