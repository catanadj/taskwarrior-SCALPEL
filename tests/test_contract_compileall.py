# SCALPEL_CONTRACT_COMPILEALL_V1
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCompileAllContract(unittest.TestCase):
    def test_compileall_scalpel_package(self):
        pkg_dir = REPO_ROOT / "scalpel"
        self.assertTrue(pkg_dir.exists(), f"Missing package dir: {pkg_dir}")

        cmd = [sys.executable, "-m", "compileall", "-q", str(pkg_dir)]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)

        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(
            p.returncode,
            0,
            "compileall failed:\n"
            f"cmd: {cmd}\n"
            f"stdout/stderr:\n{combined}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
