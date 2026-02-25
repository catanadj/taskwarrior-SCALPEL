from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

class TestBenchToolContract(unittest.TestCase):
    def test_help_runs(self):
        cmd = ["python3", "-m", "scalpel.tools.bench", "--help"]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, (p.stdout or "") + "\n" + (p.stderr or ""))

    def test_small_bench_runs_fast_path(self):
        cmd = ["python3", "-m", "scalpel.tools.bench", "--n", "250", "--repeats", "1", "--warmup", "0", "--no-render"]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertIn("[scalpel-bench] base=", combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
