from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CI_LITE = REPO_ROOT / "scripts" / "scalpel_ci_lite.sh"
LOG_DIR = REPO_ROOT / "build" / "ci-lite"


class TestCILiteSelftestFailContract(unittest.TestCase):
    def test_selftest_fail_produces_failure_banner_and_tail_and_log(self) -> None:
        # Force a failure in the first step only; keep it fast and isolated.
        cmd = [
            str(CI_LITE),
            "--allow-dirty",
            "--clean-logs",
            "--no-doctor",
            "--no-smoke",
            "--no-check",
            "--selftest-fail",
            "clean",
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)

        self.assertEqual(p.returncode, 99, f"Expected exit 99, got {p.returncode}\nSTDERR:\n{p.stderr}\nSTDOUT:\n{p.stdout}")

        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertIn("FAILED step: clean", combined)
        self.assertIn("--- tail (", combined)
        self.assertIn("--- /tail ---", combined)
        self.assertIn("selftest: forced failure for step:", combined)

        logs = list(LOG_DIR.glob("*_clean.log"))
        self.assertGreaterEqual(len(logs), 1, f"Expected *_clean.log in {LOG_DIR}")

        content = logs[0].read_text(encoding="utf-8", errors="replace")
        self.assertIn("selftest: forced failure for step:", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

