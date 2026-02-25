from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


class TestDdminShrinkToolContract(unittest.TestCase):
    def test_ddmin_can_minimize_to_single_trigger_task(self):
        self.assertTrue(FIXTURE.exists(), "golden_payload_v1.json missing")

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        tasks = payload.get("tasks") or []
        self.assertTrue(tasks and isinstance(tasks, list), "fixture has no tasks")
        target = None
        for t in tasks:
            if isinstance(t, dict) and isinstance(t.get("uuid"), str) and t.get("uuid"):
                target = t["uuid"]
                break
        self.assertTrue(target, "no uuid found in fixture tasks")

        with TemporaryDirectory() as td:
            td = Path(td)
            outp = td / "ddmin.json"

            # Fail iff target uuid is present.
            cmd = (
                "python3 -c "
                + repr(
                    "import json,sys; p=json.load(open(sys.argv[1],'r',encoding='utf-8')); "
                    "u=" + repr(target) + "; "
                    "sys.exit(1 if any((isinstance(t,dict) and t.get('uuid')==u) for t in (p.get('tasks') or [])) else 0)"
                )
                + " {in}"
            )

            env = dict(os.environ)
            env["PYTHONPATH"] = str(REPO_ROOT)

            p = subprocess.run(
                [sys.executable, "-m", "scalpel.tools.ddmin_shrink", "--in", str(FIXTURE), "--out", str(outp), "--cmd", cmd, "--max-tests", "200", "--pretty"],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertEqual(p.returncode, 0, combined)
            self.assertTrue(outp.exists(), "ddmin output not written")

            out_obj = json.loads(outp.read_text(encoding="utf-8"))
            out_tasks = out_obj.get("tasks") or []
            self.assertEqual(len(out_tasks), 1, f"expected 1 task, got {len(out_tasks)}")
            self.assertEqual(out_tasks[0].get("uuid"), target)
