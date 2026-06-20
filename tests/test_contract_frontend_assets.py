from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset
from scalpel.render.inline_css import CSS_ASSET_PATHS, CSS_BLOCK
from scalpel.render.inline_js import JS_ASSET_PATHS, JS_BLOCK


class FrontendAssetContractTests(unittest.TestCase):
    def test_javascript_asset_order_and_assembly(self) -> None:
        self.assertEqual(
            JS_ASSET_PATHS,
            (
                "js/part01_core.js",
                "js/part02_palette_goals.js",
                "js/part03_selection_ops.js",
                "js/part04_rendering.js",
                "js/part05_commands.js",
                "js/part06_drag_resize.js",
                "js/part08_notes.js",
                "js/part07_init.js",
            ),
        )
        self.assertEqual(JS_BLOCK, "\n".join(read_render_asset(path) for path in JS_ASSET_PATHS))

    def test_css_asset_order_and_assembly(self) -> None:
        self.assertEqual(
            CSS_ASSET_PATHS,
            (
                "css/part01_tokens_theme.css",
                "css/part02_base.css",
                "css/part03_header_layout.css",
                "css/part04_panels_palette.css",
                "css/part05_calendar.css",
                "css/part07_modals_misc.css",
            ),
        )
        self.assertEqual(CSS_BLOCK, "\n".join(read_render_asset(path) for path in CSS_ASSET_PATHS))

    def test_loader_rejects_paths_outside_render_package(self) -> None:
        for path in ("", "/tmp/example.js", "../example.js", "js/../../example.js"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                read_render_asset(path)

    def test_missing_asset_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "failed to load packaged render asset"):
            read_render_asset("js/missing.js")


if __name__ == "__main__":
    unittest.main()
