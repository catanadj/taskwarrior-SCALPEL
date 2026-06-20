from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scalpel.render.inline_css import CSS_ASSET_PATHS
from scalpel.render.inline_js import JS_ASSET_PATHS
from scalpel.tools.check_wheel import validate_wheel


class WheelContentsContractTests(unittest.TestCase):
    def _write_wheel(self, path: Path, *, omit: str = "", stale: str = "") -> None:
        assets = [
            *(f"scalpel/render/{asset}" for asset in CSS_ASSET_PATHS),
            *(f"scalpel/render/{asset}" for asset in JS_ASSET_PATHS),
            "scalpel/render/js/persist.js",
        ]
        with zipfile.ZipFile(path, "w") as archive:
            for asset in assets:
                if asset != omit:
                    archive.writestr(asset, "asset")
            if stale:
                archive.writestr(stale, "wrapper")

    def test_complete_wheel_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wheel = Path(td) / "package.whl"
            self._write_wheel(wheel)
            self.assertEqual(validate_wheel(wheel), [])

    def test_missing_assets_and_stale_wrappers_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            wheel = Path(td) / "package.whl"
            missing = "scalpel/render/js/part01_core.js"
            stale = "scalpel/render/js/part01_core.py"
            self._write_wheel(wheel, omit=missing, stale=stale)
            errors = validate_wheel(wheel)
            self.assertIn(f"missing packaged asset: {missing}", errors)
            self.assertIn(f"obsolete frontend wrapper packaged: {stale}", errors)

    def test_missing_and_invalid_wheels_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.whl"
            self.assertIn("wheel does not exist", validate_wheel(missing)[0])
            invalid = Path(td) / "invalid.whl"
            invalid.write_text("not a zip", encoding="utf-8")
            self.assertIn("invalid wheel archive", validate_wheel(invalid)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
