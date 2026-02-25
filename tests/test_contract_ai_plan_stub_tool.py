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


class TestAiPlanStubToolContract(unittest.TestCase):
    def test_ai_plan_stub_emits_plan(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            payload_path = td / "payload.json"
            selected_path = td / "selected.json"
            out_path = td / "plan.json"

            payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            selected_path.write_text(json.dumps(["a", "b"], indent=2) + "\n", encoding="utf-8")

            cmd = [
                _py(),
                "-m",
                "scalpel.tools.ai_plan_stub",
                "--in",
                str(payload_path),
                "--selected",
                str(selected_path),
                "--prompt",
                "align starts",
                "--out",
                str(out_path),
            ]
            p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertEqual(p.returncode, 0, combined)

            plan = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(plan.get("schema"), "scalpel.plan.v1")
            self.assertIn("overrides", plan)
            self.assertIn("a", plan["overrides"])
            self.assertIn("b", plan["overrides"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
