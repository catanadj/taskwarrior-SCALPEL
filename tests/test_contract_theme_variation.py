from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset


class ThemeVariationContractTests(unittest.TestCase):
    def test_structural_theme_tokens_drive_shared_components(self) -> None:
        tokens = read_render_asset("css/part01_tokens_theme.css")
        base = read_render_asset("css/part02_base.css")
        header = read_render_asset("css/part03_header_layout.css")
        panels = read_render_asset("css/part04_panels_palette.css")
        calendar = read_render_asset("css/part05_calendar.css")
        for token in (
            "--page-bg",
            "--card-bg",
            "--card-shadow",
            "--control-radius",
            "--event-radius",
            "--event-bg",
            "--event-shadow",
        ):
            self.assertIn(token, tokens)
        self.assertIn("background: var(--page-bg)", base)
        self.assertIn("border-radius: var(--control-radius)", header)
        self.assertIn("background: var(--card-bg)", panels)
        self.assertIn("background: var(--event-bg)", calendar)

    def test_dark_profiles_define_distinct_material_and_geometry(self) -> None:
        tokens = read_render_asset("css/part01_tokens_theme.css")
        muted = tokens.split("body.theme-muted{", 1)[1].split("body.theme-vivid{", 1)[0]
        vivid = tokens.split("body.theme-vivid{", 1)[1].split("body.theme-contrast{", 1)[0]
        contrast = tokens.split("body.theme-contrast{", 1)[1].split("body.theme-light .dimmed", 1)[0]
        self.assertIn("--card-backdrop-filter: none", muted)
        self.assertIn("--event-accent-width: 3px", muted)
        self.assertIn("--radius: 18px", vivid)
        self.assertIn("--event-accent-width: 6px", vivid)
        self.assertIn("--radius: 2px", contrast)
        self.assertIn("--card-shadow: none", contrast)
        self.assertIn("--ambient-opacity: 0", contrast)

    def test_custom_theme_exports_include_structural_tokens(self) -> None:
        theme_js = read_render_asset("js/part02_palette_goals.js")
        for token in (
            "--page-bg",
            "--card-bg",
            "--control-radius",
            "--event-bg",
            "--event-shadow",
        ):
            self.assertIn(f'"{token}"', theme_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
