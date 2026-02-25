from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCILiteFailureShrinkContract(unittest.TestCase):
    def test_ci_lite_produces_shrink_artifacts_on_failure(self):
        with TemporaryDirectory() as td:
            td = Path(td)
            log_dir = td / "ci-lite"
            out_html = td / "smoke.html"

            env = dict(os.environ)
            env["SCALPEL_CI_LOG_DIR"] = str(log_dir)
            env["SCALPEL_CI_FAIL_AFTER_SMOKE"] = "1"

            cmd = [
                str(REPO_ROOT / "scripts" / "scalpel_ci_lite.sh"),
                "--allow-dirty",
                "--no-doctor",
                "--no-check",
                "--clean-logs",
                "--out",
                str(out_html),
            ]
            p = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)

            # Must fail (this is intentional).
            self.assertNotEqual(p.returncode, 0, (p.stdout or "") + "\n" + (p.stderr or ""))

            fail_dir = log_dir / "fail"
            self.assertTrue(fail_dir.exists(), "fail_dir missing; shrink did not run?")

            fail_payload = fail_dir / "payload.json"
            self.assertTrue(fail_payload.exists(), "fail payload.json missing")

            # At least one minified artifact should exist.
            mins = sorted(fail_dir.glob("min_*.json"))
            self.assertTrue(mins, "no min_*.json artifacts written")

            # Validate the first minified artifact end-to-end.
            cmdv = [sys.executable, "-m", "scalpel.tools.validate_payload", "--in", str(mins[0])]
            pv = subprocess.run(cmdv, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)
            combinedv = (pv.stdout or "") + "\n" + (pv.stderr or "")
            self.assertEqual(pv.returncode, 0, combinedv)
