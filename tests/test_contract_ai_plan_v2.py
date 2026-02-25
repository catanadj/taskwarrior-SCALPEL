import json
import tempfile
import unittest
from pathlib import Path

from scalpel.ai import load_plan_result, validate_plan_result


class TestAiPlanV2Contract(unittest.TestCase):
    def test_validate_plan_v2_slot_catalog_required(self) -> None:
        obj = {
            "schema": "scalpel.plan.v2",
            "ops": [{"op": "place", "target": "u1", "slot_id": "S1"}],
            "warnings": [],
            "notes": [],
        }
        errs = validate_plan_result(obj)
        self.assertIn("place slot_id requires slot_catalog", errs)

    def test_validate_plan_v2_slot_id_exists(self) -> None:
        obj = {
            "schema": "scalpel.plan.v2",
            "ops": [{"op": "place", "target": "u1", "slot_id": "S1"}],
            "slot_catalog": {},
            "warnings": [],
            "notes": [],
        }
        errs = validate_plan_result(obj)
        self.assertIn("slot_catalog missing slot_id: S1", errs)

    def test_validate_plan_v2_duration_min_positive(self) -> None:
        obj = {
            "schema": "scalpel.plan.v2",
            "ops": [
                {"op": "create_task", "temp_id": "t1", "description": "New", "duration_min": 0},
                {
                    "op": "split_task",
                    "uuid": "u1",
                    "subtasks": [{"temp_id": "t2", "description": "Sub", "duration_min": -5}],
                },
            ],
            "warnings": [],
            "notes": [],
        }
        errs = validate_plan_result(obj)
        self.assertIn("create_task duration_min must be positive when provided", errs)
        self.assertIn("split_task subtasks duration_min must be positive", errs)

    def test_load_plan_result_v2_compiles(self) -> None:
        data = {
            "schema": "scalpel.plan.v2",
            "ops": [
                {"op": "create_task", "temp_id": "t1", "description": "New task", "duration_min": 30},
                {"op": "place", "target": "t1", "slot_id": "S1"},
            ],
            "slot_catalog": {"S1": {"start_ms": 60000, "due_ms": 120000}},
            "warnings": [],
            "notes": ["note"],
            "model_id": "m1",
        }

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

            plan = load_plan_result(path)
            self.assertIn("tmp:t1", plan.overrides)
            self.assertEqual(plan.added_tasks[0]["uuid"], "tmp:t1")
            self.assertEqual(plan.notes, ("note",))
            self.assertEqual(plan.model_id, "m1")

    def test_load_plan_result_v2_tmp_prefix_is_stable(self) -> None:
        data = {
            "schema": "scalpel.plan.v2",
            "ops": [
                {"op": "create_task", "temp_id": "tmp:t1", "description": "New task", "duration_min": 30},
                {"op": "place", "target": "tmp:t1", "slot_id": "S1"},
            ],
            "slot_catalog": {"S1": {"start_ms": 60000, "due_ms": 120000}},
            "warnings": [],
            "notes": [],
        }

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plan.json"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

            plan = load_plan_result(path)
            self.assertIn("tmp:t1", plan.overrides)
            self.assertEqual(plan.added_tasks[0]["uuid"], "tmp:t1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
