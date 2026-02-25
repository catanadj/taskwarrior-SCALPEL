from __future__ import annotations

import glob
import os
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CI_LITE = REPO_ROOT / "scripts" / "scalpel_ci_lite.sh"
LOG_DIR = REPO_ROOT / "build" / "ci-lite"


class TestCILiteLogContract(unittest.TestCase):
    def test_ci_lite_has_logging_instrumentation(self) -> None:
        s = CI_LITE.read_text(encoding="utf-8", errors="replace")

        # Static contract: do not allow “silent” CI-lite (visibility on failure).
        self.assertIn('LOG_DIR="build/ci-lite"', s)
        self.assertIn('tee -a "$logfile"', s)
        self.assertIn('PIPESTATUS[0]', s)
        self.assertIn('[ci-lite] log: $logfile', s)
        self.assertIn("--clean-logs", s)
        self.assertIn("--print-logs", s)
        self.assertIn("print_logs()", s)

    def test_clean_logs_flag_clears_log_dir(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        dummy = LOG_DIR / "dummy.log"
        dummy.write_text("x", encoding="utf-8")

        # Run a no-op pipeline so it’s fast, but triggers clean-logs.
        cmd = [
            str(CI_LITE),
            "--allow-dirty",
            "--no-clean",
            "--no-doctor",
            "--no-smoke",
            "--no-check",
            "--clean-logs",
        ]
        subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)

        self.assertTrue(LOG_DIR.exists())
        self.assertFalse(dummy.exists(), "dummy.log should have been removed by --clean-logs")

    def test_clean_step_produces_a_log_file(self) -> None:
        # Ensure logs start clean for the assertion
        if LOG_DIR.exists():
            for p in LOG_DIR.glob("*.log"):
                p.unlink()

        cmd = [
            str(CI_LITE),
            "--allow-dirty",
            "--no-doctor",
            "--no-smoke",
            "--no-check",
            "--clean-logs",
            "--out",
            "build/contract_ci_smoke.html",
        ]
        subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)

        logs = list(LOG_DIR.glob("*_clean.log"))
        self.assertGreaterEqual(len(logs), 1, f"Expected at least one *_clean.log file in {LOG_DIR}")




    def test_print_logs_outputs_log_paths(self) -> None:
        # Run a fast single-step pipeline, request log printing, and assert output includes *_clean.log
        cmd = [
            str(CI_LITE),
            "--allow-dirty",
            "--no-doctor",
            "--no-smoke",
            "--no-check",
            "--clean-logs",
            "--print-logs",
            "--out",
            "build/contract_ci_smoke.html",
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}")
        summary_path = REPO_ROOT / "build" / "ci-lite" / "summary.tsv"
        self.assertTrue(summary_path.exists(), "missing summary.tsv at: {}".format(summary_path))
        summary_txt = summary_path.read_text(encoding="utf-8", errors="replace")
        self.assertRegex(summary_txt, r"(?m)^clean\t0\t\d+\t.+_clean\.log")

        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertIn("[ci-lite] === logs ===", combined)
        self.assertIn("[ci-lite] out:", combined)
        self.assertRegex(combined, r"\[ci-lite\] log: .*_clean\.log")
        self.assertRegex(combined, r"\[ci-lite\] dir: .+ \((exists|missing)\)")
        self.assertRegex(combined, r"\[ci-lite\] out: .+ \((exists|missing)\)")
        self.assertRegex(combined, r"\[ci-lite\] log: .*_clean\.log")
if __name__ == "__main__":
    unittest.main(verbosity=2)

