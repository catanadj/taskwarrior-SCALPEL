import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


def _py() -> str:
    return os.environ.get("PYTHON", "python3")


class TestPlanResultCLIContract(unittest.TestCase):
    def test_render_payload_with_plan_result(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        plan = {
            "overrides": {
                "a": {"start_ms": 1577869200000, "due_ms": 1577872800000, "duration_min": 60}
            },
            "added_tasks": [
                {"uuid": "new-1", "description": "New", "status": "pending", "tags": []}
            ],
            "task_updates": {"a": {"description": "Updated"}},
            "warnings": [],
            "notes": [],
            "model_id": "local",
        }
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            payload_path = td / "payload.json"
            plan_path = td / "plan.json"
            out_html = td / "out.html"

            payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

            cmd = [
                _py(),
                "-m",
                "scalpel.tools.render_payload",
                "--in",
                str(payload_path),
                "--out",
                str(out_html),
                "--plan-result",
                str(plan_path),
            ]
            p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertEqual(p.returncode, 0, combined)
            self.assertTrue(out_html.exists(), combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
