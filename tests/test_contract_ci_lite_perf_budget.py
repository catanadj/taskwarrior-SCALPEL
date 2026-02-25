import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / "scripts" / "scalpel_ci_lite.sh"
LOG_DIR = REPO_ROOT / "build" / "ci-lite"
SUMMARY = LOG_DIR / "summary.tsv"

class TestCILitePerfBudgetContract(unittest.TestCase):
    def setUp(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # Synthetic summary ensures deterministic behavior without relying on timing.
        SUMMARY.write_text(
            "step\trc\tms\tlog\n"
            "clean\t0\t123\tbuild/ci-lite/01_clean.log\n",
            encoding="utf-8",
        )

    def test_warn_only_does_not_fail(self) -> None:
        cmd = [
            str(CI),
            "--allow-dirty",
            "--no-clean", "--no-doctor", "--no-smoke", "--no-check",
            "--max-ms", "clean=100",
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}")
        self.assertIn("PERF WARN", combined)

    def test_perf_strict_fails(self) -> None:
        cmd = [
            str(CI),
            "--allow-dirty",
            "--no-clean", "--no-doctor", "--no-smoke", "--no-check",
            "--perf-strict",
            "--max-ms", "clean=100",
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertNotEqual(p.returncode, 0, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}")
        self.assertIn("PERF STRICT", combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
