from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset


class EventReadabilityContractTests(unittest.TestCase):
    def test_event_markup_has_semantic_title_time_and_context(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        for class_name in (
            "evt-title",
            "time-start",
            "time-range",
            "dur-pill",
            "evt-project",
            "evt-tags",
        ):
            self.assertIn(class_name, rendering)
        self.assertIn('el.setAttribute("aria-label"', rendering)
        self.assertIn('tooltipParts.join("\\n")', rendering)
        self.assertNotIn('(t.uuid||"").slice(0,8)', rendering)

    def test_event_detail_levels_follow_rendered_height(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        calendar_css = read_render_asset("css/part05_calendar.css")
        self.assertIn('if (hPx < 46) cls += " evt-short"', rendering)
        self.assertIn('else if (hPx < 84) cls += " evt-medium"', rendering)
        self.assertIn(".evt.evt-short", calendar_css)
        self.assertIn(".evt.evt-medium", calendar_css)
        self.assertIn(".evt.evt-narrow", calendar_css)
        self.assertIn("-webkit-line-clamp: 2", calendar_css)

    def test_drag_preview_updates_both_time_presentations(self) -> None:
        drag_js = read_render_asset("js/part06_drag_resize.js")
        self.assertIn('querySelector(".evt-time .time-range")', drag_js)
        self.assertIn('querySelector(".evt-time .time-start")', drag_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
