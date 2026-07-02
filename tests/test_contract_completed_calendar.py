from __future__ import annotations

import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel.payload import build_payload

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestCompletedCalendarContract(unittest.TestCase):
    def test_show_completed_exports_default_completed_companion_filter_and_places_by_end(self) -> None:
        seen_filters: list[str] = []

        def fake_export(filter_str: str) -> list[dict[str, object]]:
            seen_filters.append(filter_str)
            if filter_str == "status:pending":
                return [
                    {
                        "uuid": "pending-1",
                        "description": "Pending",
                        "status": "pending",
                        "due": "20260101T100000Z",
                        "duration": "30min",
                    }
                ]
            if filter_str == "status:completed":
                return [
                    {
                        "uuid": "done-1",
                        "description": "Done",
                        "status": "completed",
                        "scheduled": "20260101T110000Z",
                        "due": "20260101T120000Z",
                        "end": "20260101T113000Z",
                    }
                ]
            return []

        with (
            patch("scalpel.payload.run_task_export", side_effect=fake_export),
            patch("scalpel.payload._load_nautical_core", return_value=None),
        ):
            payload = build_payload(
                filter_str="status:pending",
                start_date=dt.date(2026, 1, 1),
                days=1,
                work_start=480,
                work_end=1020,
                snap=10,
                default_duration_min=10,
                max_infer_duration_min=480,
                px_per_min=2,
                goals_path="does-not-exist.json",
                tz="UTC",
                display_tz="UTC",
                show_completed=True,
            )

        self.assertEqual(seen_filters, ["status:pending", "status:completed"])
        self.assertTrue(payload["cfg"]["show_completed"])
        done = next(t for t in payload["tasks"] if t["uuid"] == "done-1")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["due_ms"], done["completed_end_ms"])
        self.assertEqual(done["end_calc_ms"], done["completed_end_ms"])
        self.assertEqual(done["dur_src"], "infer_due_minus_scheduled")

    def test_completed_frontend_has_toggle_and_completed_style(self) -> None:
        header = (REPO_ROOT / "scalpel" / "render" / "markup" / "header.py").read_text(encoding="utf-8")
        core = (REPO_ROOT / "scalpel" / "render" / "js" / "part01_core.js").read_text(encoding="utf-8")
        init = (REPO_ROOT / "scalpel" / "render" / "js" / "part07_init.js").read_text(encoding="utf-8")
        rendering = (REPO_ROOT / "scalpel" / "render" / "js" / "part04_rendering.js").read_text(encoding="utf-8")
        css = (REPO_ROOT / "scalpel" / "render" / "css" / "part05_calendar.css").read_text(encoding="utf-8")

        self.assertIn("btnShowCompleted", header)
        self.assertIn("showCompletedTasks", core)
        self.assertIn("hasCompletedTasks", core)
        self.assertIn("syncCompletedToggle", init)
        self.assertIn("completed-task", rendering)
        self.assertIn("completed-pill", rendering)
        self.assertIn(".evt.completed-task", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
