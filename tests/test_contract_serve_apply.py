from __future__ import annotations

import unittest
from unittest.mock import patch

from scalpel.process import CommandFailedError, CommandResult
from scalpel import serve_apply


class TestServeApplyContract(unittest.TestCase):
    def test_preview_rejects_non_task_command(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            serve_apply.preview_apply_commands(["echo nope"])
        self.assertIn("must start with `task`", str(ctx.exception))

    def test_execute_adds_confirmation_override_and_succeeds(self) -> None:
        seen: list[list[str]] = []

        def fake_run_checked(argv: list[str], *, timeout_s: float | None = None) -> CommandResult:
            self.assertEqual(timeout_s, 30.0)
            seen.append(list(argv))
            return CommandResult(tuple(argv), 0, "ok", "")

        with patch("scalpel.serve_apply.run_checked", side_effect=fake_run_checked):
            out = serve_apply.execute_apply_commands(
                [
                    "task 12345678 modify scheduled:2026-03-11T09:00 due:2026-03-11T10:00 duration:60min",
                    "task 12345678 done",
                ]
            )

        self.assertTrue(out["ok"])
        self.assertEqual(out["applied"], 2)
        self.assertEqual(
            seen[0],
            [
                "task",
                "rc.confirmation=no",
                "12345678",
                "modify",
                "scheduled:2026-03-11T09:00",
                "due:2026-03-11T10:00",
                "duration:60min",
            ],
        )
        self.assertEqual(seen[1], ["task", "rc.confirmation=no", "12345678", "done"])

    def test_execute_stops_after_first_failure(self) -> None:
        def fake_run_checked(argv: list[str], *, timeout_s: float | None = None) -> CommandResult:
            if argv[-1] == "done":
                result = CommandResult(tuple(argv), 1, "", "boom")
                raise CommandFailedError(result, (0,))
            return CommandResult(tuple(argv), 0, "", "")

        with patch("scalpel.serve_apply.run_checked", side_effect=fake_run_checked):
            out = serve_apply.execute_apply_commands(
                [
                    "task 12345678 done",
                    "task 12345678 delete",
                ]
            )

        self.assertFalse(out["ok"])
        self.assertEqual(out["applied"], 0)
        self.assertEqual(out["selected"], 2)
        self.assertEqual(len(out["commands"]), 1)
        self.assertEqual(out["commands"][0]["stderr"], "boom")
