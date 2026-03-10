from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestRuntimePersistenceContract(unittest.TestCase):
    def test_runtime_js_prefers_store_helpers_over_direct_local_storage(self) -> None:
        core = (REPO_ROOT / "scalpel" / "render" / "js" / "part01_core.py").read_text(
            encoding="utf-8", errors="replace"
        )
        self.assertIn("__scalpel_storeGet", core)
        self.assertIn("__scalpel_storeSet", core)
        self.assertIn("__scalpel_storeSetJSON", core)
        self.assertIn("__scalpel_storeDel", core)

        for rel in (
            "scalpel/render/js/part02_palette_goals.py",
            "scalpel/render/js/part06_drag_resize.py",
            "scalpel/render/js/part07_init.py",
            "scalpel/render/js/part08_notes.py",
        ):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("localStorage.getItem(", text, rel)
            self.assertNotIn("localStorage.setItem(", text, rel)
            self.assertNotIn("localStorage.removeItem(", text, rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
