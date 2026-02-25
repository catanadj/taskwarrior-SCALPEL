import unittest

from scalpel.ai import validate_plan_result


class TestAiPlanContract(unittest.TestCase):
    def test_validate_plan_result_ok(self) -> None:
        obj = {
            "schema": "scalpel.plan.v1",
            "overrides": {"u1": {"start_ms": 1, "due_ms": 2}},
            "added_tasks": [{"uuid": "n1", "description": "New", "status": "pending", "tags": []}],
            "task_updates": {"u1": {"description": "x"}},
            "warnings": ["w"],
            "notes": [],
            "model_id": "m1",
        }
        self.assertEqual(validate_plan_result(obj), [])

    def test_validate_plan_result_errors(self) -> None:
        obj = {
            "schema": "bad",
            "overrides": {"": {"start_ms": "x", "due_ms": 2}},
            "added_tasks": [{}],
            "task_updates": {"u1": "bad"},
            "warnings": "nope",
            "notes": [1],
            "model_id": 2,
        }
        errs = validate_plan_result(obj)
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
