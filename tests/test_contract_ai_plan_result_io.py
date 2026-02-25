import json
import tempfile
import unittest
from pathlib import Path

from scalpel.ai import load_plan_result


class TestAiPlanResultIOContract(unittest.TestCase):
    def test_load_plan_result(self) -> None:
        data = {
            "overrides": {
                "uuid-1": {"start_ms": 1700000000000, "due_ms": 1700003600000, "duration_min": 60}
            },
            "added_tasks": [{"uuid": "new-1", "description": "New", "status": "pending", "tags": []}],
            "task_updates": {"uuid-1": {"description": "Updated"}},
            "warnings": [],
            "notes": ["note"],
            "model_id": "local-model",
        }

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

            plan = load_plan_result(path)
            self.assertIn("uuid-1", plan.overrides)
            self.assertEqual(plan.overrides["uuid-1"].duration_min, 60)
            self.assertEqual(plan.added_tasks[0]["uuid"], "new-1")
            self.assertEqual(plan.task_updates["uuid-1"]["description"], "Updated")
            self.assertEqual(plan.notes, ("note",))
            self.assertEqual(plan.model_id, "local-model")


if __name__ == "__main__":
    unittest.main(verbosity=2)
