import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _py() -> str:
    return os.environ.get("PYTHON", "python3")


class TestValidatePlanResultToolContract(unittest.TestCase):
    def test_validate_plan_result_tool(self) -> None:
        plan = {
            "overrides": {"u1": {"start_ms": 1, "due_ms": 2}},
            "added_tasks": [{"uuid": "n1", "description": "New", "status": "pending", "tags": []}],
            "task_updates": {},
            "warnings": [],
            "notes": [],
        }
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            plan_path = td / "plan.json"
            plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

            cmd = [
                _py(),
                "-m",
                "scalpel.tools.validate_plan_result",
                "--in",
                str(plan_path),
            ]
            p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertEqual(p.returncode, 0, combined)
            self.assertIn("[scalpel-validate-plan-result] OK", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
