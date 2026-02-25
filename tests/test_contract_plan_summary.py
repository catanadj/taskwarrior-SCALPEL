import json
import unittest
from pathlib import Path

from scalpel.ai import PlanOverride
from scalpel.planner import build_plan_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


class TestPlanSummaryContract(unittest.TestCase):
    def test_plan_summary_matches_fixture(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
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

        summary = build_plan_summary(
            payload,
            overrides=overrides,
            selected_uuids=expected["selection_metrics"]["uuids"],
        )

        self.assertEqual(summary.events, {k: tuple(v) for k, v in expected["events"].items()})

        got_conflicts = sorted(
            [
                {
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "uuids": list(s.uuids),
                    "kind": s.kind,
                }
                for s in summary.conflicts
            ],
            key=lambda x: (x["start_ms"], x["end_ms"], x["kind"], ",".join(x["uuids"])),
        )
        want_conflicts = sorted(
            expected["conflicts"],
            key=lambda x: (x["start_ms"], x["end_ms"], x["kind"], ",".join(x["uuids"])),
        )
        self.assertEqual(got_conflicts, want_conflicts)

        self.assertEqual(summary.metrics.count, expected["selection_metrics"]["count"])
        self.assertEqual(summary.metrics.duration_min, expected["selection_metrics"]["duration_min"])
        self.assertEqual(summary.metrics.span_min, expected["selection_metrics"]["span_min"])
        self.assertEqual(summary.metrics.gap_min, expected["selection_metrics"]["gap_min"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
