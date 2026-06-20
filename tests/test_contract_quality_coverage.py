from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel import query
from scalpel.ai.io import load_plan_overrides
from scalpel.goals import load_goals_config
from scalpel.tools import ai_plan_tasks
from scalpel.tools.check_frontend import main as check_frontend


class TestQueryHelpers(unittest.TestCase):
    def setUp(self) -> None:
        self.tasks = [
            {"uuid": "a", "status": "pending", "project": "work", "tags": ["focus"], "day_key": "2026-01-01"},
            {"uuid": "b", "status": "completed", "project": "home", "tags": ["quick"], "day_key": "2026-01-02"},
        ]
        self.payload = {
            "tasks": self.tasks,
            "indices": {
                "by_uuid": {"a": 0, "stale": 99},
                "by_status": {"pending": [0, "bad", 99]},
                "by_project": {"work": [0]},
                "by_tag": {"quick": [1]},
                "by_day": {"2026-01-02": [1]},
            },
        }

    def test_indexed_queries_and_fallbacks(self) -> None:
        self.assertEqual(list(query.iter_tasks(self.payload)), self.tasks)
        self.assertEqual(query.task_by_uuid(self.payload, "a"), self.tasks[0])
        self.assertEqual(query.task_by_uuid(self.payload, "b"), self.tasks[1])
        self.assertIsNone(query.task_by_uuid(self.payload, ""))
        self.assertEqual(query.tasks_by_status(self.payload, "pending"), [self.tasks[0]])
        self.assertEqual(query.tasks_by_project(self.payload, "work"), [self.tasks[0]])
        self.assertEqual(query.tasks_by_tag(self.payload, "quick"), [self.tasks[1]])
        self.assertEqual(query.tasks_by_day(self.payload, "2026-01-02"), [self.tasks[1]])
        with self.assertRaises(KeyError):
            query.require_task_by_uuid(self.payload, "missing")

    def test_malformed_payload_is_tolerated(self) -> None:
        malformed = {"tasks": "bad", "indices": "bad"}
        self.assertEqual(list(query.iter_tasks(malformed)), [])
        self.assertIsNone(query.task_by_uuid(malformed, "a"))
        self.assertEqual(query.tasks_by_status(malformed, "pending"), [])
        self.assertEqual(query.tasks_by_project(malformed, "work"), [])
        self.assertEqual(query.tasks_by_tag(malformed, "focus"), [])
        self.assertEqual(query.tasks_by_day(malformed, "2026-01-01"), [])


class TestGoalsAndOverrides(unittest.TestCase):
    def test_goals_normalization_and_invalid_inputs(self) -> None:
        self.assertIsNone(load_goals_config(""))
        self.assertIsNone(load_goals_config("/definitely/missing/goals.json"))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "goals.json"
            path.write_text(
                json.dumps(
                    {
                        "goals": [
                            {"name": "Deep Work", "color": "#abcdef", "projects": ["work"], "tags": ["focus"]},
                            {"name": "Named", "color": "RED", "mode": "invalid"},
                            {"name": "", "color": "#fff"},
                            {"name": "Bad", "color": "not a color!"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = load_goals_config(str(path))
            self.assertIsNotNone(result)
            goals = result["goals"] if result else []
            self.assertEqual([goal["id"] for goal in goals], ["deep-work", "named"])
            self.assertEqual(goals[1]["color"], "red")
            self.assertEqual(goals[1]["mode"], "any")
            path.write_text("{", encoding="utf-8")
            self.assertIsNone(load_goals_config(str(path)))

    def test_plan_override_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "overrides.json"
            path.write_text(json.dumps({"a": {"start_ms": 10, "due_ms": 20, "duration_min": 1}}), encoding="utf-8")
            loaded = load_plan_overrides(path)
            self.assertEqual(loaded["a"].due_ms, 20)
            for bad in (
                [],
                {"a": None},
                {"a": {"start_ms": True, "due_ms": 20}},
                {"a": {"start_ms": 20, "due_ms": 10}},
                {"a": {"start_ms": 10, "due_ms": 20, "duration_min": 0}},
            ):
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_plan_overrides(path)


class TestAiPlanTaskHelpers(unittest.TestCase):
    def test_selection_json_and_time_helpers(self) -> None:
        tasks = [
            {"uuid": "abcdefgh-1", "project": "work.deep", "tags": ["focus"], "status": "pending"},
            {"uuid": "done", "project": "work", "tags": [], "status": "completed"},
            {"description": "missing uuid"},
        ]
        goal = {"projects": ["work"], "tags": ["focus"], "mode": "all"}
        self.assertEqual(ai_plan_tasks._select_tasks(tasks, projects=["work"], goal=goal), [tasks[0]])
        self.assertEqual(ai_plan_tasks._select_tasks(tasks, include_done=True, filter_uuids={"done"}), [tasks[1]])
        self.assertEqual(ai_plan_tasks._extract_json_from_text('prefix {"ops": []} suffix'), {"ops": []})
        with self.assertRaises(ValueError):
            ai_plan_tasks._extract_json_from_text("no object")
        self.assertEqual(ai_plan_tasks._iso_to_tw_utc("2026-01-01T12:30:00+00:00"), "20260101T123000Z")
        with self.assertRaises(ValueError):
            ai_plan_tasks._iso_to_tw_utc("2026-01-01T12:30:00")

    def test_apply_ops_and_summaries(self) -> None:
        before = [{"uuid": "abcdefgh-1", "description": "Old", "status": "pending", "tags": []}]
        ops = [
            {"op": "update_task", "uuid": "abcdefgh", "patch": {"description": "New", "tags": ["focus"]}},
            {"op": "create_task", "temp_id": "t1", "description": "Created", "due_iso": "2026-01-01T12:00:00Z"},
            {"op": "complete_task", "target": "t1"},
            {"op": "delete_task", "uuid": "missing"},
            {"op": "unknown"},
        ]
        after = ai_plan_tasks._apply_ops(before, ops, default_project="inbox")
        self.assertEqual(after[0]["description"], "New")
        created = next(task for task in after if task.get("description") == "Created")
        self.assertEqual(created["status"], "completed")
        self.assertEqual(created["project"], "inbox")
        self.assertIn("update_task", ai_plan_tasks._summarize_ops(ops, {"abcdefgh-1": before[0]}))
        self.assertIn("added: 1", ai_plan_tasks._diff_summary(before, after))
        self.assertTrue(ai_plan_tasks._diff_preview(before, after))
        self.assertTrue(ai_plan_tasks._diff_tasks(before, after))
        self.assertIn("total: 2", ai_plan_tasks._selection_summary(after))

    def test_plan_normalization_and_frontend_check(self) -> None:
        normalized = ai_plan_tasks._normalize_ops(
            [None, {"op": "update_task", "uuid": "a", "description": "New"}, {"op": "complete_task", "uuid": "a"}]
        )
        self.assertEqual(normalized[0]["patch"], {"description": "New"})
        summary = ai_plan_tasks._update_summary("prior", "next", {"ops": normalized, "warnings": ["w"]}, 200)
        self.assertIn("Model ops: 2", summary)
        self.assertIn("properties", ai_plan_tasks._taskplan_schema()["schema"])
        with patch("scalpel.tools.check_frontend.shutil.which", return_value=None):
            self.assertEqual(check_frontend([]), 0)
            self.assertEqual(check_frontend(["--require-node"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
