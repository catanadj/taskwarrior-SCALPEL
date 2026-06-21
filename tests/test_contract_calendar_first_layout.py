from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset
from scalpel.render.markup.header import MARKUP as HEADER_MARKUP
from scalpel.render.markup.layout_open import MARKUP as LAYOUT_OPEN_MARKUP


class CalendarFirstLayoutContractTests(unittest.TestCase):
    def test_compact_toolbar_preserves_controls_and_exposes_sidebars(self) -> None:
        self.assertIn('class="header-toolbar"', HEADER_MARKUP)
        self.assertNotIn('class="header-secondary"', HEADER_MARKUP)
        for control_id in (
            "btnToggleBacklog",
            "btnToggleCommands",
            "btnCopy",
            "btnMoreActions",
            "vwStart",
            "vwDays",
            "vwOverdue",
            "zoom",
        ):
            self.assertIn(f'id="{control_id}"', HEADER_MARKUP)

    def test_commands_are_collapsed_before_javascript_initializes(self) -> None:
        self.assertIn('class="layout commands-collapsed"', LAYOUT_OPEN_MARKUP)

    def test_independent_panel_state_is_persisted_and_command_sections_reveal_panel(self) -> None:
        selection_js = read_render_asset("js/part03_selection_ops.js")
        init_js = read_render_asset("js/part07_init.js")
        self.assertIn("leftPanelCollapsed", selection_js)
        self.assertIn("commandsPanelCollapsed", selection_js)
        self.assertIn("__scalpel_setSidePanelVisible", selection_js)
        self.assertIn('__scalpel_setSidePanelVisible("commands", true)', init_js)

    def test_layout_css_supports_each_sidebar_combination(self) -> None:
        css = read_render_asset("css/part03_header_layout.css")
        self.assertIn(".layout.commands-collapsed", css)
        self.assertIn(".layout.left-collapsed", css)
        self.assertIn(".layout.left-collapsed.commands-collapsed", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
