from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestNotesToggleContract(unittest.TestCase):
    def test_showing_notes_opens_actions_section(self) -> None:
        text = (REPO_ROOT / "scalpel" / "render" / "js" / "part08_notes.py").read_text(
            encoding="utf-8",
            errors="replace",
        )
        self.assertIn('setCommandSectionOpen("actions", true, true)', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
