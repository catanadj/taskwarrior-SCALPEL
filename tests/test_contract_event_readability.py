from __future__ import annotations

import unittest

from scalpel.render.assets import read_render_asset
from scalpel.render.markup.header import MARKUP as HEADER_MARKUP
from scalpel.render.markup.overlays import MARKUP as OVERLAY_MARKUP


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
        self.assertIn("__eventTooltipLines", rendering)
        self.assertIn("__eventAriaLabel", rendering)
        self.assertIn("__eventWarningLabels", rendering)
        self.assertIn("Task: ", rendering)
        self.assertIn("Time: ", rendering)
        self.assertIn("Status: completed at", rendering)
        self.assertIn("Warnings: ", rendering)
        self.assertIn("Double-click to edit", rendering)
        self.assertIn('tooltipParts.join("\\n")', rendering)
        self.assertNotIn('(t.uuid||"").slice(0,8)', rendering)

    def test_event_detail_levels_follow_rendered_height(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        calendar_css = read_render_asset("css/part05_calendar.css")
        self.assertIn('if (hPx < 46) cls += " evt-short"', rendering)
        self.assertIn('else if (hPx < 84) cls += " evt-medium"', rendering)
        self.assertIn('cls += " evt-crowded"', rendering)
        self.assertIn(".evt.evt-short", calendar_css)
        self.assertIn(".evt.evt-medium", calendar_css)
        self.assertIn(".evt.evt-narrow", calendar_css)
        self.assertIn(".evt.evt-crowded", calendar_css)
        self.assertIn(".evt.evt-crowded .evt-time .time-range", calendar_css)
        self.assertIn("-webkit-line-clamp: 2", calendar_css)

    def test_drag_preview_updates_both_time_presentations(self) -> None:
        drag_js = read_render_asset("js/part06_drag_resize.js")
        self.assertIn('querySelector(".evt-time .time-range")', drag_js)
        self.assertIn('querySelector(".evt-time .time-start")', drag_js)

    def test_selected_calendar_tasks_enable_focus_readability_mode(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        calendar_css = read_render_asset("css/part05_calendar.css")

        self.assertIn("__syncCalendarSelectionFocusState", rendering)
        self.assertIn("calendar-selection-focus", rendering)
        self.assertIn("evNode.dataset.preview !== \"1\"", rendering)
        self.assertIn("body.calendar-selection-focus .evt:not(.selected)", calendar_css)
        self.assertIn("body.calendar-selection-focus .evt:not(.selected):hover", calendar_css)
        self.assertIn("body.calendar-selection-focus .evt.selected", calendar_css)
        self.assertIn("body.calendar-selection-focus .day-col.active-day", calendar_css)

    def test_now_line_is_labelled_and_edge_aware(self) -> None:
        selection = read_render_asset("js/part03_selection_ops.js")
        calendar_css = read_render_asset("css/part05_calendar.css")

        self.assertIn("function renderNowLine()", selection)
        self.assertIn("near-start", selection)
        self.assertIn("near-end", selection)
        self.assertIn("now-dot", selection)
        self.assertIn("Current time:", selection)
        self.assertIn(".now-line .now-dot", calendar_css)
        self.assertIn(".now-line .now-label strong", calendar_css)
        self.assertIn(".now-line.near-start .now-label", calendar_css)
        self.assertIn(".now-line.near-end .now-label", calendar_css)

    def test_day_headers_include_busy_day_summary(self) -> None:
        selection = read_render_asset("js/part03_selection_ops.js")
        rendering = read_render_asset("js/part04_rendering.js")
        calendar_css = read_render_asset("css/part05_calendar.css")

        self.assertIn("daysummary", selection)
        self.assertIn("__dayHeaderSummary", rendering)
        self.assertIn("taskCount: events.length", rendering)
        self.assertIn("visible scheduled task", rendering)
        self.assertIn("summary.textContent = headerSummary.text", rendering)
        self.assertIn("summary.title = headerSummary.title", rendering)
        self.assertIn(".day-h .daysummary", calendar_css)
        self.assertIn(".day-h.has-warning .daysummary", calendar_css)

    def test_overlap_warning_does_not_replace_event_content(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        drag = read_render_asset("js/part06_drag_resize.js")
        calendar_css = read_render_asset("css/part05_calendar.css")
        self.assertIn("conflict-gutter", rendering)
        self.assertIn("pulseConflictTasks", rendering)
        self.assertIn('classList.add("conflict-pulse")', rendering)
        self.assertIn("pulseConflictTasks(uuids)", drag)
        self.assertIn(".evt .conflict-gutter", calendar_css)
        self.assertIn(".evt.warn-overlap .conflict-gutter", calendar_css)
        self.assertIn(".evt.conflict-pulse", calendar_css)
        self.assertIn("@keyframes conflict_task_pulse", calendar_css)
        self.assertIn("@keyframes conflict_gutter_pulse", calendar_css)
        self.assertNotIn(".evt.warn-overlap::before", calendar_css)
        self.assertNotIn(".evt.warn-overlap .evt-time::after", calendar_css)
        self.assertNotIn('content: "OVERLAP"', calendar_css)

    def test_task_editor_exposes_nautical_fields_as_default_rows(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        self.assertIn('key: "anchor"', rendering)
        self.assertIn('label: "anchor"', rendering)
        self.assertIn('detailsTask.anchor ?? fallbackTask.anchor', rendering)
        self.assertIn('key: "cp"', rendering)
        self.assertIn('label: "cp"', rendering)
        self.assertIn('detailsTask.cp ?? fallbackTask.cp', rendering)
        self.assertIn('"anchor", "cp"', rendering)

    def test_completed_tasks_render_as_completion_strips_not_planning_blocks(self) -> None:
        rendering = read_render_asset("js/part04_rendering.js")
        selection = read_render_asset("js/part03_selection_ops.js")
        drag = read_render_asset("js/part06_drag_resize.js")
        css = read_render_asset("css/part05_calendar.css")

        self.assertIn("markerHPx", rendering)
        self.assertIn('isCompleted ? "8px"', rendering)
        self.assertIn('layoutOverlapGroups(normalEvents)', rendering)
        self.assertIn('if (!isCompleted) allByDay[di].push', selection)
        self.assertIn('String(tt.status || "").toLowerCase() === "completed"', drag)
        self.assertIn(".evt.completed-task", css)
        self.assertIn("border-radius: 999px", css)
        self.assertIn(".evt.completed-task .resize", css)

    def test_calendar_time_bands_are_background_layers_with_toggle(self) -> None:
        selection = read_render_asset("js/part03_selection_ops.js")
        palette = read_render_asset("js/part02_palette_goals.js")
        init = read_render_asset("js/part07_init.js")
        css = read_render_asset("css/part05_calendar.css")
        modal_css = read_render_asset("css/part07_modals_misc.css")

        self.assertIn("btnTimeBands", HEADER_MARKUP)
        self.assertIn("elBtnTimeBands", palette)
        self.assertIn("DEFAULT_TIME_BANDS", selection)
        self.assertIn("normalizeTimeBands", selection)
        self.assertIn("renderTimeBandsInColumn", selection)
        self.assertIn('className = "time-bands"', selection)
        self.assertIn("TIME_BANDS_KEY", init)
        self.assertIn(".time-bands", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("rgba(34, 197, 94, 0.18)", css)
        self.assertIn("rgba(139, 92, 246, 0.19)", css)
        self.assertIn(".time-band-green", css)
        self.assertIn(".time-band-violet", css)
        self.assertIn("bandModal", OVERLAY_MARKUP)
        self.assertIn(".band-edit-row", modal_css)

    def test_calendar_time_band_editor_is_persisted_and_editable(self) -> None:
        init = read_render_asset("js/part07_init.js")
        selection = read_render_asset("js/part03_selection_ops.js")

        for expected in (
            "bandModal",
            "bandRows",
            "bandAdd",
            "bandReset",
            "bandSave",
        ):
            self.assertIn(expected, OVERLAY_MARKUP)
        self.assertIn("btnBandEditor", HEADER_MARKUP)
        self.assertIn("TIME_BANDS_CONFIG_KEY", init)
        self.assertIn("openBandEditor", init)
        self.assertIn("saveBandEditor", init)
        self.assertIn("__scalpel_storeSetJSON(TIME_BANDS_CONFIG_KEY", init)
        self.assertIn("parseBandTimeToMin", selection)
        self.assertIn("formatBandTime", selection)
        self.assertIn("TIME_BAND_STYLE_OPTIONS", selection)
        self.assertIn("TIME_BAND_STYLE_KEYS", selection)
        self.assertIn('focus: "green"', selection)
        self.assertIn("normalizeTimeBandKey", selection)
        self.assertIn("option.label", init)


if __name__ == "__main__":
    unittest.main(verbosity=2)
