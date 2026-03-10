from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCIHygieneContract(unittest.TestCase):
    def test_ci_hygiene_script_uses_snapshot_archive_and_doctor(self) -> None:
        text = (REPO_ROOT / "scripts" / "scalpel_ci_hygiene.sh").read_text(encoding="utf-8", errors="replace")
        self.assertIn("mktemp -d", text)
        self.assertIn("git -C \"$ROOT\" archive --format=tar HEAD", text)
        self.assertIn("python3 -m scalpel.tools.doctor --root \"$SNAP_REPO\" --strict", text)
        self.assertIn("PYTHONPATH=\"$SNAP_REPO\"", text)

    def test_ci_workflow_runs_snapshot_hygiene_job(self) -> None:
        text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8", errors="replace")
        self.assertIn("hygiene:", text)
        self.assertIn("Snapshot Hygiene Gate", text)
        self.assertIn("./scripts/scalpel_ci_hygiene.sh", text)

    def test_ci_hygiene_script_runs_cleanly_on_current_repo(self) -> None:
        script = REPO_ROOT / "scripts" / "scalpel_ci_hygiene.sh"
        p = subprocess.run(
            ["bash", str(script)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p.returncode, 0, msg=p.stdout + "\n" + p.stderr)
        self.assertIn("[scalpel-ci-hygiene] snapshot:", p.stdout)
        self.assertIn("[scalpel-doctor] RESULT: OK", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
