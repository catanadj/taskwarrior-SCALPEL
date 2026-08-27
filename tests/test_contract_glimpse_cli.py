from __future__ import annotations

import datetime as dt
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scalpel.glimpse.cli import build_parser, main
from scalpel.process import CommandNotFoundError


def _payload() -> dict[str, object]:
    start = int(dt.datetime(2026, 8, 27, tzinfo=dt.timezone.utc).timestamp() * 1000)
    return {
        "cfg": {
            "view_start_ms": start,
            "days": 1,
            "tz": "UTC",
            "display_tz": "UTC",
        },
        "tasks": [],
    }


class GlimpseCliContractTests(unittest.TestCase):
    def test_live_mode_builds_payload_with_operational_defaults(self) -> None:
        with patch("scalpel.glimpse.cli.build_payload", return_value=_payload()) as builder:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--start",
                            "2026-08-27",
                            "--days",
                            "3",
                            "--filter",
                            "status:pending project:work",
                            "--workhours",
                            "08:00-18:00",
                            "--tz",
                            "UTC",
                            "--display-tz",
                            "Europe/Bucharest",
                            "--plain",
                        ]
                    ),
                    0,
                )
        self.assertIn("No tasks", output.getvalue())
        self.assertEqual(builder.call_args.kwargs["start_date"], dt.date(2026, 8, 27))
        self.assertEqual(builder.call_args.kwargs["days"], 3)
        self.assertEqual(builder.call_args.kwargs["work_start"], 8 * 60)
        self.assertEqual(builder.call_args.kwargs["work_end"], 18 * 60)
        self.assertEqual(builder.call_args.kwargs["tz"], "UTC")
        self.assertEqual(builder.call_args.kwargs["display_tz"], "Europe/Bucharest")

    def test_payload_mode_replays_file_without_building_live_data(self) -> None:
        with (
            patch("scalpel.glimpse.cli.load_payload_from_json", return_value=_payload()) as loader,
            patch("scalpel.glimpse.cli.build_payload") as builder,
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--payload", "fixture.json", "--plain"]), 0)
        loader.assert_called_once_with(Path("fixture.json"))
        builder.assert_not_called()
        self.assertIn("No tasks", output.getvalue())

    def test_invalid_live_option_is_reported_as_a_cli_error(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(main(["--workhours", "18:00-08:00"]), 2)
        self.assertIn("workhours end must be after start", error.getvalue())

    def test_plain_is_a_no_color_alias(self) -> None:
        args = build_parser().parse_args(["--plain"])
        self.assertTrue(args.no_color)

    def test_default_width_uses_terminal_columns(self) -> None:
        with patch("scalpel.glimpse.cli.shutil.get_terminal_size", return_value=os.terminal_size((120, 24))):
            output = io.StringIO()
            with redirect_stdout(output):
                with patch("scalpel.glimpse.cli.build_payload", return_value=_payload()):
                    self.assertEqual(main(["--plain"]), 0)
        self.assertTrue(all(len(line) <= 120 for line in output.getvalue().splitlines()))

    def test_negative_width_is_reported_as_a_cli_error(self) -> None:
        error = io.StringIO()
        with patch("scalpel.glimpse.cli.build_payload", return_value=_payload()), redirect_stderr(error):
            self.assertEqual(main(["--width", "-1"]), 2)
        self.assertIn("--width must be zero", error.getvalue())

    def test_today_date_alias_and_ascii_mode_are_supported(self) -> None:
        with patch("scalpel.glimpse.cli.build_payload", return_value=_payload()):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--start", "today", "--date", "today", "--ascii"]), 0)
        self.assertNotRegex(output.getvalue(), "[⚠✓⚓┃│█─…]")

    def test_degraded_terminal_uses_ascii_output(self) -> None:
        with (
            patch.dict("os.environ", {"TERM": "dumb"}, clear=False),
            patch("scalpel.glimpse.cli.build_payload", return_value=_payload()),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([]), 0)
        self.assertNotRegex(output.getvalue(), "[⚠✓⚓┃│█─…]")

    def test_broken_output_pipe_is_a_successful_exit(self) -> None:
        with (
            patch("scalpel.glimpse.cli.build_payload", return_value=_payload()),
            patch("builtins.print", side_effect=BrokenPipeError),
        ):
            self.assertEqual(main(["--plain"]), 0)

    def test_degraded_terminal_rejects_interactive_mode_cleanly(self) -> None:
        error = io.StringIO()
        with (
            patch.dict("os.environ", {"TERM": "dumb"}, clear=False),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            redirect_stderr(error),
        ):
            self.assertEqual(main(["--interactive"]), 2)
        self.assertIn("curses-capable terminal", error.getvalue())

    def test_missing_taskwarrior_is_reported_as_a_concise_cli_error(self) -> None:
        error = io.StringIO()
        with (
            patch("scalpel.glimpse.cli.build_payload", side_effect=CommandNotFoundError(["task"])),
            redirect_stderr(error),
        ):
            self.assertEqual(main([]), 2)
        self.assertIn("Command not found: task", error.getvalue())

    def test_empty_live_database_renders_a_successful_empty_agenda(self) -> None:
        output = io.StringIO()
        with patch("scalpel.payload.run_task_export", return_value=[]), redirect_stdout(output):
            self.assertEqual(main(["--start", "2026-08-27", "--tz", "UTC", "--plain"]), 0)
        self.assertIn("No tasks scheduled.", output.getvalue())
        self.assertIn("Planned 0m", output.getvalue())

    def test_interactive_forwards_requested_view_date_and_terminal_style(self) -> None:
        with (
            patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=False),
            patch("scalpel.glimpse.cli.run_interactive") as interactive,
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
        ):
            self.assertEqual(
                main(["--interactive", "--view", "day", "--date", "2026-08-28", "--ascii", "--no-color"]), 0
            )
        self.assertEqual(interactive.call_args.kwargs["view"], "day")
        self.assertEqual(interactive.call_args.kwargs["initial_date"], dt.date(2026, 8, 28))
        self.assertTrue(interactive.call_args.kwargs["ascii_only"])
        self.assertFalse(interactive.call_args.kwargs["color"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
