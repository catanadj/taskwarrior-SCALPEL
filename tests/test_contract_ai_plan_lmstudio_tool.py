import json
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from scalpel.tools import ai_plan_lmstudio


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestAiPlanLmStudioToolContract(unittest.TestCase):
    def test_lmstudio_tool_writes_plan(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            payload_path = td / "payload.json"
            selected_path = td / "selected.json"
            out_path = td / "plan.json"

            payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            selected_path.write_text(json.dumps(["a"], indent=2) + "\n", encoding="utf-8")

            plan_obj = {
                "schema": "scalpel.plan.v1",
                "overrides": {"a": {"start_ms": 1, "due_ms": 2, "duration_min": 1}},
                "added_tasks": [],
                "task_updates": {},
                "warnings": [],
                "notes": [],
                "model_id": "stub",
            }
            fake_resp = _FakeResponse(
                {"choices": [{"message": {"content": json.dumps(plan_obj)}}]}
            )

            with mock.patch("scalpel.tools.ai_plan_lmstudio.request.urlopen", return_value=fake_resp):
                rc = ai_plan_lmstudio.main(
                    [
                        "--in",
                        str(payload_path),
                        "--selected",
                        str(selected_path),
                        "--prompt",
                        "align starts",
                        "--out",
                        str(out_path),
                        "--base-url",
                        "http://127.0.0.1:1234",
                        "--model",
                        "ministral-3-14b-reasoning",
                    ]
                )
            self.assertEqual(rc, 0)
            out = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(out.get("schema"), "scalpel.plan.v1")
            self.assertIn("a", out.get("overrides", {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
