import unittest

from scalpel.planner import detect_conflicts, selection_metrics


class TestPlannerCoreContract(unittest.TestCase):
    def test_detect_conflicts_overlap_and_out_of_hours(self) -> None:
        # 2020-01-01 UTC midnight baseline.
        base = 1577836800000
        h = 60 * 60000

        events = {
            "a": (base + 9 * h, base + 11 * h, 120),
            "b": (base + 10 * h, base + 12 * h, 120),
            "c": (base + 8 * h, base + 10 * h, 120),
            "d": (base + 16 * h, base + 18 * h, 120),
        }
        cfg = {"tz": "UTC", "work_start_min": 9 * 60, "work_end_min": 17 * 60}

        segs = detect_conflicts(events, cfg)

        overlap = [s for s in segs if s.kind == "overlap"]
        self.assertEqual(len(overlap), 2)
        spans = {(s.start_ms, s.end_ms, s.uuids) for s in overlap}
        self.assertIn((base + 9 * h, base + 10 * h, ("a", "c")), spans)
        self.assertIn((base + 10 * h, base + 11 * h, ("a", "b")), spans)

        out_hours = [s for s in segs if s.kind == "out_of_hours"]
        self.assertEqual(len(out_hours), 2)
        spans = {(s.start_ms, s.end_ms, s.uuids) for s in out_hours}
        self.assertIn((base + 8 * h, base + 9 * h, ("c",)), spans)
        self.assertIn((base + 17 * h, base + 18 * h, ("d",)), spans)

    def test_selection_metrics(self) -> None:
        base = 1577836800000
        h = 60 * 60000

        events = {
            "a": (base + 9 * h, base + 10 * h, 60),
            "b": (base + 12 * h, base + 13 * h, 60),
            "c": (base + 14 * h, base + 16 * h, 120),
        }

        m = selection_metrics(["a", "b", "c"], events)
        self.assertEqual(m.count, 3)
        self.assertEqual(m.duration_min, 240)
        self.assertEqual(m.span_min, 420)
        self.assertEqual(m.gap_min, 180)

    def test_detect_conflicts_out_of_hours_handles_multiday_events(self) -> None:
        # 2020-01-01 UTC midnight baseline.
        base = 1577836800000
        h = 60 * 60000

        events = {
            # Jan 1 16:00 -> Jan 2 10:00 UTC
            "x": (base + 16 * h, base + 34 * h, 18 * 60),
        }
        cfg = {"tz": "UTC", "work_start_min": 9 * 60, "work_end_min": 17 * 60}

        segs = detect_conflicts(events, cfg)
        out_hours = [s for s in segs if s.kind == "out_of_hours"]
        self.assertEqual(len(out_hours), 2)
        spans = {(s.start_ms, s.end_ms, s.uuids) for s in out_hours}
        self.assertIn((base + 17 * h, base + 24 * h, ("x",)), spans)
        self.assertIn((base + 24 * h, base + 33 * h, ("x",)), spans)


if __name__ == "__main__":
    unittest.main(verbosity=2)
