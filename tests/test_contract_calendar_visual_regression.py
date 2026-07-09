from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset
from scalpel.render.markup.header import MARKUP as HEADER_MARKUP
from scalpel.render.markup.overlays import MARKUP as OVERLAY_MARKUP


class CalendarVisualRegressionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.calendar_css = read_render_asset("css/part05_calendar.css")
        cls.tokens_css = read_render_asset("css/part01_tokens_theme.css")
        cls.modal_css = read_render_asset("css/part07_modals_misc.css")
        cls.palette_js = read_render_asset("js/part02_palette_goals.js")
        cls.selection_js = read_render_asset("js/part03_selection_ops.js")
        cls.rendering_js = read_render_asset("js/part04_rendering.js")
        cls.drag_js = read_render_asset("js/part06_drag_resize.js")
        cls.init_js = read_render_asset("js/part07_init.js")

    def test_dense_cards_keep_compact_readability_affordances(self) -> None:
        self.assertIn('if (hPx < 68 || ev.laneCount >= 3) cls += " evt-crowded"', self.rendering_js)
        self.assertIn(".evt.evt-crowded{", self.calendar_css)
        self.assertIn("border-left-width: max(var(--event-accent-width), 6px)", self.calendar_css)
        self.assertIn(".evt.evt-crowded .evt-title", self.calendar_css)
        self.assertIn(".evt.evt-crowded .evt-time .time-start", self.calendar_css)
        self.assertIn(".evt.evt-crowded .evt-time .time-range", self.calendar_css)
        self.assertIn(".evt.evt-crowded:hover .evt-time .time-range", self.calendar_css)
        self.assertIn(".evt.evt-crowded.selected .evt-time .time-range", self.calendar_css)

    def test_overlap_conflicts_use_gutters_and_pulses_without_replacing_content(self) -> None:
        self.assertIn("conflict-gutter", self.rendering_js)
        self.assertIn("pulseConflictTasks", self.rendering_js)
        self.assertIn('classList.add("conflict-pulse")', self.rendering_js)
        self.assertIn("pulseConflictTasks(uuids)", self.drag_js)
        self.assertIn(".evt .conflict-gutter", self.calendar_css)
        self.assertIn(".evt.warn-overlap .conflict-gutter", self.calendar_css)
        self.assertIn(".evt.conflict-pulse", self.calendar_css)
        self.assertIn("@keyframes conflict_task_pulse", self.calendar_css)
        self.assertIn("@keyframes conflict_gutter_pulse", self.calendar_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.calendar_css)
        self.assertNotIn('content: "OVERLAP"', self.calendar_css)
        self.assertNotIn(".evt.warn-overlap::before", self.calendar_css)
        self.assertNotIn(".evt.warn-overlap .evt-time::after", self.calendar_css)

    def test_selection_focus_dims_noise_without_hiding_selected_context(self) -> None:
        self.assertIn("__syncCalendarSelectionFocusState", self.rendering_js)
        self.assertIn("calendar-selection-focus", self.rendering_js)
        self.assertIn('evNode.dataset.preview !== "1"', self.rendering_js)
        self.assertIn("body.calendar-selection-focus .evt:not(.selected)", self.calendar_css)
        self.assertIn("body.calendar-selection-focus .evt.completed-task:not(.selected)", self.calendar_css)
        self.assertIn("body.calendar-selection-focus .evt.nautical-preview:not(.selected)", self.calendar_css)
        self.assertIn("body.calendar-selection-focus .evt:not(.selected):hover", self.calendar_css)
        self.assertIn("body.calendar-selection-focus .evt.selected", self.calendar_css)
        self.assertIn("body.calendar-selection-focus .day-col.active-day", self.calendar_css)

    def test_current_time_marker_and_busy_day_headers_remain_scannable(self) -> None:
        self.assertIn("function renderNowLine()", self.selection_js)
        self.assertIn("near-start", self.selection_js)
        self.assertIn("near-end", self.selection_js)
        self.assertIn("now-dot", self.selection_js)
        self.assertIn("Current time:", self.selection_js)
        self.assertIn(".now-line .now-dot", self.calendar_css)
        self.assertIn(".now-line .now-label strong", self.calendar_css)
        self.assertIn(".now-line.near-start .now-label", self.calendar_css)
        self.assertIn(".now-line.near-end .now-label", self.calendar_css)
        self.assertIn("daysummary", self.selection_js)
        self.assertIn("__dayHeaderSummary", self.rendering_js)
        self.assertIn("taskCount: events.length", self.rendering_js)
        self.assertIn("summary.textContent = headerSummary.text", self.rendering_js)
        self.assertIn("summary.title = headerSummary.title", self.rendering_js)
        self.assertIn(".day-h .daysummary", self.calendar_css)
        self.assertIn(".day-h.has-warning .daysummary", self.calendar_css)

    def test_planning_bands_stay_editable_background_layers(self) -> None:
        self.assertIn("btnTimeBands", HEADER_MARKUP)
        self.assertIn("btnBandEditor", HEADER_MARKUP)
        self.assertIn("DEFAULT_TIME_BANDS", self.selection_js)
        self.assertIn("normalizeTimeBands", self.selection_js)
        self.assertIn("renderTimeBandsInColumn", self.selection_js)
        self.assertIn('className = "time-bands"', self.selection_js)
        self.assertIn("TIME_BANDS_KEY", self.init_js)
        self.assertIn("TIME_BANDS_CONFIG_KEY", self.init_js)
        self.assertIn("openBandEditor", self.init_js)
        self.assertIn("saveBandEditor", self.init_js)
        self.assertIn("TIME_BAND_STYLE_OPTIONS", self.selection_js)
        self.assertIn('label: "Green"', self.selection_js)
        self.assertIn(".time-bands", self.calendar_css)
        self.assertIn("pointer-events: none", self.calendar_css)
        self.assertIn(".time-band-green", self.calendar_css)
        self.assertIn(".time-band-violet", self.calendar_css)
        self.assertIn("bandModal", OVERLAY_MARKUP)
        self.assertIn(".band-edit-row", self.modal_css)

    def test_completed_tasks_remain_completion_strips_not_full_planning_blocks(self) -> None:
        self.assertIn("markerHPx", self.rendering_js)
        self.assertIn('isCompleted ? "8px"', self.rendering_js)
        self.assertIn('layoutOverlapGroups(normalEvents)', self.rendering_js)
        self.assertIn('if (!isCompleted) allByDay[di].push', self.selection_js)
        self.assertIn('String(tt.status || "").toLowerCase() === "completed"', self.drag_js)
        self.assertIn(".evt.completed-task", self.calendar_css)
        self.assertIn("border-radius: 999px", self.calendar_css)
        self.assertIn(".evt.completed-task .resize", self.calendar_css)
        self.assertIn(".evt.completed-task .completed-pill", self.calendar_css)

    def test_theme_tokens_cover_calendar_visual_state_layers(self) -> None:
        structural_tokens = (
            "--event-radius",
            "--event-accent-width",
            "--event-bg",
            "--event-shadow",
            "--ghost-bg",
            "--ghost-border",
            "--now-line",
            "--now-label-bg",
            "--task-selected",
        )
        for token in structural_tokens:
            self.assertIn(token, self.tokens_css)

        for token in (
            "--accent",
            "--warn",
            "--bad",
            "--bg",
            "--panel",
            "--text",
            "--block",
            "--block2",
            "--task-title-text",
            "--task-body-text",
        ):
            self.assertIn(token, self.palette_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
