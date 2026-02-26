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


class TestAiFlowEndToEndContract(unittest.TestCase):
    def test_stub_plan_apply_render(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            payload_path = td / "payload.json"
            selected_path = td / "selected.json"
            plan_path = td / "plan.json"
            updated_path = td / "payload_planned.json"
            out_html = td / "planned.html"

            payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            selected_path.write_text(json.dumps(["a", "b"], indent=2) + "\n", encoding="utf-8")

            cmd_plan = [
                _py(),
                "-m",
                "scalpel.tools.ai_plan_stub",
                "--in",
                str(payload_path),
                "--selected",
                str(selected_path),
                "--prompt",
                "stack",
                "--out",
                str(plan_path),
            ]
            p1 = subprocess.run(cmd_plan, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined1 = (p1.stdout or "") + "\n" + (p1.stderr or "")
            self.assertEqual(p1.returncode, 0, combined1)

            cmd_apply = [
                _py(),
                "-m",
                "scalpel.tools.apply_plan_result",
                "--in",
                str(payload_path),
                "--plan",
                str(plan_path),
                "--out",
                str(updated_path),
            ]
            p2 = subprocess.run(cmd_apply, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined2 = (p2.stdout or "") + "\n" + (p2.stderr or "")
            self.assertEqual(p2.returncode, 0, combined2)

            cmd_render = [
                _py(),
                "-m",
                "scalpel.tools.render_payload",
                "--in",
                str(updated_path),
                "--out",
                str(out_html),
            ]
            p3 = subprocess.run(cmd_render, cwd=str(REPO_ROOT), text=True, capture_output=True)
            combined3 = (p3.stdout or "") + "\n" + (p3.stderr or "")
            self.assertEqual(p3.returncode, 0, combined3)

            html = out_html.read_text(encoding="utf-8", errors="replace")
            self.assertIn("<title>SCALPEL</title>", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
