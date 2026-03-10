from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scalpel.tools import doctor


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestRepoHygieneContract(unittest.TestCase):
    def test_gitignore_covers_common_local_artifacts(self) -> None:
        text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace")
        for needle in (
            ".venv/",
            "dist/",
            "*.egg-info/",
            ".ship-safe/",
            "ship-safe-report.html",
            ".mypy_cache/",
            ".pytest_cache/",
            ".ruff_cache/",
        ):
            self.assertIn(needle, text)

    def test_clean_script_removes_generated_dirs_and_reports(self) -> None:
        text = (REPO_ROOT / "scripts" / "scalpel_clean.sh").read_text(encoding="utf-8", errors="replace")
        for needle in (
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "*.egg-info",
            "dist",
            ".ship-safe",
            "ship-safe-report.html",
        ):
            self.assertIn(needle, text)

    def test_doctor_skips_expected_generated_dirs_but_flags_repo_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.pyc").write_bytes(b"x")
            (root / "dist").mkdir()
            (root / "dist" / "ignored.pyc").write_bytes(b"x")
            (root / "pkg").mkdir()
            (root / "pkg" / "__pycache__").mkdir()
            (root / "pkg" / "__pycache__" / "kept.pyc").write_bytes(b"x")
            (root / "tools").mkdir()
            (root / "tools" / "temp.py.bak").write_text("x", encoding="utf-8")

            warnings, errors = doctor._scan_tree(root)

        combined_warnings = "\n".join(warnings)
        combined_errors = "\n".join(errors)
        self.assertIn("__pycache__", combined_warnings)
        self.assertIn(".pyc files", combined_warnings)
        self.assertIn(".bak files", combined_warnings)
        self.assertNotIn(".venv", combined_warnings)
        self.assertNotIn("dist", combined_warnings)
        self.assertEqual(combined_errors, "")

    def test_doctor_ignores_gitignored_artifacts_but_keeps_repo_visible_ones(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / ".gitignore").write_text("__pycache__/\n*.pyc\n*.bak\n", encoding="utf-8")
            (root / "pkg").mkdir()
            (root / "pkg" / "__pycache__").mkdir()
            (root / "pkg" / "__pycache__" / "ignored.pyc").write_bytes(b"x")
            (root / "ignored.py.bak").write_text("x", encoding="utf-8")
            (root / "scratch.tmp").write_text("x", encoding="utf-8")
            (root / "scratch.tmp.rej").write_text("x", encoding="utf-8")

            warnings, errors = doctor._scan_tree(root)

        combined_warnings = "\n".join(warnings)
        combined_errors = "\n".join(errors)
        self.assertEqual(combined_warnings, "")
        self.assertIn("scratch.tmp.rej", combined_errors)
        self.assertNotIn("__pycache__", combined_errors)
        self.assertNotIn(".pyc", combined_errors)
        self.assertNotIn(".bak", combined_errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
