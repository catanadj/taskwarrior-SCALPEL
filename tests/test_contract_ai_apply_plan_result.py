import json
import unittest
from pathlib import Path

from scalpel.ai import AiPlanResult, PlanOverride, apply_plan_result


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


class TestAiApplyPlanResultContract(unittest.TestCase):
    def test_apply_plan_result_adds_and_updates_tasks(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        base_uuid = payload["tasks"][0]["uuid"]

        plan = AiPlanResult(
            overrides={base_uuid: PlanOverride(start_ms=1577869200000, due_ms=1577872800000, duration_min=60)},
            task_updates={base_uuid: {"description": "Updated"}},
            added_tasks=(
                {
                    "uuid": "new-uuid-1",
                    "description": "New task",
                    "status": "pending",
                    "tags": [],
                },
            ),
        )

        out = apply_plan_result(payload, plan)
        uuids = [t.get("uuid") for t in out["tasks"] if isinstance(t, dict)]

        self.assertIn(base_uuid, uuids)
        self.assertIn("new-uuid-1", uuids)

        base = next(t for t in out["tasks"] if t.get("uuid") == base_uuid)
        self.assertEqual(base.get("description"), "Updated")

        added = next(t for t in out["tasks"] if t.get("uuid") == "new-uuid-1")
        self.assertEqual(added.get("status"), "pending")
        self.assertIn("indices", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
