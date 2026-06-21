from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset
from scalpel.render.markup.calendar_panel import MARKUP as CALENDAR_MARKUP
from scalpel.render.markup.header import MARKUP as HEADER_MARKUP
from scalpel.render.markup.layout_open import MARKUP as LAYOUT_OPEN_MARKUP
from scalpel.render.markup.right_panel import MARKUP as RIGHT_PANEL_MARKUP


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

    def test_contextual_selection_bar_exposes_primary_actions(self) -> None:
        self.assertIn('id="selectionBar"', CALENDAR_MARKUP)
        self.assertIn('role="toolbar"', CALENDAR_MARKUP)
        for control_id in (
            "selectionComplete",
            "selectionDelete",
            "selectionArrange",
            "selectionFocus",
            "selectionClear",
        ):
            self.assertIn(f'id="{control_id}"', CALENDAR_MARKUP)
        selection_js = read_render_asset("js/part03_selection_ops.js")
        init_js = read_render_asset("js/part07_init.js")
        self.assertIn("elSelectionBar.hidden = n < 1", selection_js)
        self.assertIn('delegateSelectionAction("selectionComplete", "actDone")', init_js)
        self.assertIn('__scalpel_openCommandSection("arrange")', init_js)

    def test_commands_use_a_dismissible_overlay_drawer_on_desktop(self) -> None:
        self.assertIn('id="commandsDrawerBackdrop"', RIGHT_PANEL_MARKUP)
        self.assertIn('id="btnCloseCommands"', RIGHT_PANEL_MARKUP)
        layout_css = read_render_asset("css/part03_header_layout.css")
        responsive_css = read_render_asset("css/part07_modals_misc.css")
        self.assertIn("position: fixed", layout_css)
        self.assertIn("translateX(calc(100% + 20px))", layout_css)
        self.assertIn(".layout > section.commands", responsive_css)

    def test_compact_density_does_not_restore_a_commands_grid_column(self) -> None:
        base_css = read_render_asset("css/part02_base.css")
        compact_layout = base_css.split("body.compact .layout{", 1)[1].split("}", 1)[0]
        self.assertNotIn("grid-template-columns", compact_layout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
