from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


class TestMinifyFixtureToolContract(unittest.TestCase):
    def test_minify_fixture_is_deterministic_and_validates(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        tasks = payload.get("tasks") or []
        self.assertIsInstance(tasks, list)
        self.assertTrue(tasks, "golden fixture has no tasks")
        t0 = tasks[0]
        self.assertIsInstance(t0, dict)
        u = t0.get("uuid")
        self.assertIsInstance(u, str)
        self.assertTrue(u)

        with subprocess.Popen(["true"]) as _:
            pass

        with self.subTest("runs twice identically"):
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                out1 = td / "a.json"
                out2 = td / "b.json"

                cmd1 = [
                    sys.executable, "-m", "scalpel.tools.minify_fixture",
                    "--in", str(FIXTURE),
                    "--q", f"uuid:{u}",
                    "--out", str(out1),
                    "--pretty",
                ]
                p1 = subprocess.run(cmd1, cwd=str(REPO_ROOT), capture_output=True, text=True)
                combined1 = (p1.stdout or "") + "\n" + (p1.stderr or "")
                self.assertEqual(p1.returncode, 0, combined1)

                cmd2 = [
                    sys.executable, "-m", "scalpel.tools.minify_fixture",
                    "--in", str(FIXTURE),
                    "--q", f"uuid:{u}",
                    "--out", str(out2),
                    "--pretty",
                ]
                p2 = subprocess.run(cmd2, cwd=str(REPO_ROOT), capture_output=True, text=True)
                combined2 = (p2.stdout or "") + "\n" + (p2.stderr or "")
                self.assertEqual(p2.returncode, 0, combined2)

                a = out1.read_text(encoding="utf-8")
                b = out2.read_text(encoding="utf-8")
                self.assertEqual(a, b, "minified fixture output should be deterministic")

                # And it should validate with the public validator tool (end-to-end)
                cmdv = [sys.executable, "-m", "scalpel.tools.validate_payload", "--in", str(out1)]
                pv = subprocess.run(cmdv, cwd=str(REPO_ROOT), capture_output=True, text=True)
                combinedv = (pv.stdout or "") + "\n" + (pv.stderr or "")
                self.assertEqual(pv.returncode, 0, combinedv)

        with self.subTest("manifest upsert"):
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                outp = td / "m.json"
                man = td / "manifest.json"
                cmdm = [
                    sys.executable, "-m", "scalpel.tools.minify_fixture",
                    "--in", str(FIXTURE),
                    "--q", f"uuid:{u}",
                    "--out", str(outp),
                    "--name", "tiny_uuid_fixture",
                    "--update-manifest",
                    "--manifest", str(man),
                ]
                pm = subprocess.run(cmdm, cwd=str(REPO_ROOT), capture_output=True, text=True)
                combinedm = (pm.stdout or "") + "\n" + (pm.stderr or "")
                self.assertEqual(pm.returncode, 0, combinedm)

                mj = json.loads(man.read_text(encoding="utf-8"))
                self.assertIsInstance(mj, list)
                names = {d.get("name") for d in mj if isinstance(d, dict)}
                self.assertIn("tiny_uuid_fixture", names)
