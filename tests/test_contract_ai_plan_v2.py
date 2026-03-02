import json
import tempfile
import unittest
from pathlib import Path

from scalpel.ai import load_plan_result, validate_plan_result
from scalpel.ai.plan_v2 import compile_plan_v2
from scalpel.ai.slots import build_candidate_slots


class TestAiPlanV2Contract(unittest.TestCase):
    def test_slot_ids_are_unique_across_different_durations(self) -> None:
        payload = {
            "cfg": {
                "tz": "UTC",
                "view_start_ms": 0,
                "days": 1,
                "work_start_min": 0,
                "work_end_min": 120,
                "snap_min": 30,
                "default_duration_min": 30,
                "max_infer_duration_min": 480,
            },
            "tasks": [
                {"uuid": "u1", "status": "pending", "due_ms": 3_600_000, "duration_min": 60},
                {"uuid": "u2", "status": "pending", "due_ms": 3_600_000, "duration_min": 30},
            ],
            "indices": {"by_uuid": {"u1": 0, "u2": 1}},
        }

        candidates, slot_catalog = build_candidate_slots(payload, ["u1", "u2"], max_slots_per_task=1)
        self.assertEqual(len(candidates["u1"]), 1)
        self.assertEqual(len(candidates["u2"]), 1)

        s1 = candidates["u1"][0]
        s2 = candidates["u2"][0]
        self.assertNotEqual(s1.slot_id, s2.slot_id)
        self.assertEqual(slot_catalog[s1.slot_id]["due_ms"], s1.due_ms)
        self.assertEqual(slot_catalog[s2.slot_id]["due_ms"], s2.due_ms)

    def test_compile_plan_v2_uses_correct_duration_for_each_slot_id(self) -> None:
        obj = {
            "schema": "scalpel.plan.v2",
            "ops": [
                {"op": "place", "target": "u1", "slot_id": "S0-100"},
                {"op": "place", "target": "u2", "slot_id": "S0-80"},
            ],
            "slot_catalog": {
                "S0-100": {"start_ms": 0, "due_ms": 3_600_000},
                "S0-80": {"start_ms": 0, "due_ms": 1_800_000},
            },
            "warnings": [],
            "notes": [],
        }
        plan = compile_plan_v2(obj)
        self.assertEqual(plan.overrides["u1"].duration_min, 60)
        self.assertEqual(plan.overrides["u2"].duration_min, 30)

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
