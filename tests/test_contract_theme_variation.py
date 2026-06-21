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

    def test_paper_profile_uses_neutral_stock_and_ink_colors(self) -> None:
        tokens = read_render_asset("css/part01_tokens_theme.css")
        paper = tokens.split("body.theme-paper{", 1)[1].split("/* Muted:", 1)[0]
        self.assertIn("--panel: #ffffff", paper)
        self.assertIn("--cal-surface: #ffffff", paper)
        self.assertIn("--text: #25292d", paper)
        self.assertIn("--accent: #3f6179", paper)
        self.assertIn("--ambient-opacity: 0", paper)
        self.assertIn("radial-gradient(circle", paper)
        self.assertNotIn("--accent: #b06c25", paper)

    def test_calendar_layers_use_the_theme_surface_without_transparent_gaps(self) -> None:
        calendar = read_render_asset("css/part05_calendar.css")
        self.assertIn(".calendar > .card-b", calendar)
        self.assertIn("background: var(--cal-surface)", calendar)
        days_col = calendar.split(".days-col {", 1)[1].split("}", 1)[0]
        days_body = calendar.split(".days-body {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--cal-surface)", days_col)
        self.assertIn("background: var(--cal-surface)", days_body)

    def test_light_themes_use_high_legibility_nautical_ghost_tokens(self) -> None:
        tokens = read_render_asset("css/part01_tokens_theme.css")
        calendar = read_render_asset("css/part05_calendar.css")
        light = tokens.split("body.theme-light{", 1)[1].split("body.theme-paper{", 1)[0]
        paper = tokens.split("body.theme-paper{", 1)[1].split("/* Muted:", 1)[0]
        for profile in (light, paper):
            self.assertIn("--ghost-opacity: 0.96", profile)
            self.assertIn("--ghost-text-shadow: none", profile)
            self.assertIn("--ghost-border: rgba(var(--accent-rgb), 0.68)", profile)
        self.assertIn("background: var(--ghost-bg)", calendar)
        self.assertIn("color: var(--ghost-text)", calendar)
        self.assertIn("opacity: var(--ghost-opacity)", calendar)

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
