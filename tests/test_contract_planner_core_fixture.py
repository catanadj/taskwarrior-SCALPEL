import json
import unittest
from pathlib import Path

from scalpel.ai import PlanOverride
from scalpel.planner import apply_overrides, detect_conflicts, selection_metrics


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


class TestPlannerCoreFixtureContract(unittest.TestCase):
    def test_fixture_contract(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cfg = payload["cfg"]
        tasks = payload["tasks"]

        overrides_raw = payload.get("overrides", {})
        overrides = {
            uuid: PlanOverride(
                start_ms=int(v["start_ms"]),
                due_ms=int(v["due_ms"]),
                duration_min=v.get("duration_min"),
            )
            for uuid, v in overrides_raw.items()
        }

        expected = payload["expected"]

        events = apply_overrides(tasks, overrides, cfg)
        self.assertEqual(events, {k: tuple(v) for k, v in expected["events"].items()})

        segs = detect_conflicts(events, cfg)
        got_conflicts = sorted(
            [
                {
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "uuids": list(s.uuids),
                    "kind": s.kind,
                }
                for s in segs
            ],
            key=lambda x: (x["start_ms"], x["end_ms"], x["kind"], ",".join(x["uuids"])),
        )
        want_conflicts = sorted(
            expected["conflicts"],
            key=lambda x: (x["start_ms"], x["end_ms"], x["kind"], ",".join(x["uuids"])),
        )
        self.assertEqual(got_conflicts, want_conflicts)

        sel = expected["selection_metrics"]["uuids"]
        metrics = selection_metrics(sel, events)
        self.assertEqual(metrics.count, expected["selection_metrics"]["count"])
        self.assertEqual(metrics.duration_min, expected["selection_metrics"]["duration_min"])
        self.assertEqual(metrics.span_min, expected["selection_metrics"]["span_min"])
        self.assertEqual(metrics.gap_min, expected["selection_metrics"]["gap_min"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
