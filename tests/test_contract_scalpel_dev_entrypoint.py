import subprocess
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV = REPO_ROOT / "scripts" / "scalpel_dev.sh"


class TestScalpelDevEntrypointContract(unittest.TestCase):
    def _run(self, args):
        return subprocess.run(
            [str(DEV)] + args,
            cwd=str(REPO_ROOT),
            text=True,
            capture_output=True,
        )

    def test_help(self):
        self.assertTrue(DEV.exists(), f"missing: {DEV}")
        p = self._run(["--help"])
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertIn("Commands:", combined)

    def test_dry_run_ci(self):
        p = self._run(["--dry-run", "ci", "--out", "build/x.html"])
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertIn("scalpel_ci_lite.sh", combined)

    def test_dry_run_test(self):
        p = self._run(["--dry-run", "test"])
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertTrue(("scalpel_test_contract.sh" in combined) or ("unittest discover" in combined))

    def test_dry_run_smoke_includes_validate(self):
        p = self._run(["--dry-run", "smoke", "--out", "build/s.html", "--json", "build/p.json", "--", "--days", "3"])
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
        self.assertTrue(("scalpel_smoke_strict.sh" in combined) or ("scalpel.tools.smoke_build" in combined))
        self.assertTrue(("scalpel_validate_payload.sh" in combined) or ("scalpel.tools.validate_payload" in combined))


if __name__ == "__main__":
    unittest.main(verbosity=2)
