import subprocess
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "install_pre_commit_hook.py"


class TestInstallPreCommitHookContract(unittest.TestCase):
    def test_installer_help_runs(self):
        self.assertTrue(INSTALLER.exists(), f"missing: {INSTALLER}")
        p = subprocess.run(
            ["python3", str(INSTALLER), "--help"],
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertIn("install_pre_commit_hook.py", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
