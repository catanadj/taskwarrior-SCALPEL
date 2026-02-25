from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from scalpel.taskwarrior import parse_tw_utc_to_epoch_ms, run_task_export


class TestTaskwarriorFilterQuotingContract(unittest.TestCase):
    def test_filter_uses_shell_compatible_quoting(self) -> None:
        seen = {}

        def fake_run(cmd, stdout=None, stderr=None, check=None, timeout=None):  # type: ignore[no-untyped-def]
            seen["cmd"] = cmd
            seen["timeout"] = timeout
            return subprocess.CompletedProcess(cmd, 0, stdout=b"[]", stderr=b"")

        with patch("subprocess.run", side_effect=fake_run):
            out = run_task_export('project:"Big Project" status:pending +next')

        self.assertEqual(out, [])
        self.assertEqual(
            seen.get("cmd"),
            ["task", "project:Big Project", "status:pending", "+next", "export"],
        )
        self.assertGreater(float(seen.get("timeout") or 0), 0.0)

    def test_invalid_filter_quoting_fails_fast(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            run_task_export('project:"unterminated')
        self.assertIn("Invalid Taskwarrior filter expression", str(ctx.exception))

    def test_missing_task_binary_fails_with_actionable_message(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaises(SystemExit) as ctx:
                run_task_export("status:pending")
        self.assertIn("binary 'task' not found", str(ctx.exception))

    def test_task_export_timeout_fails_fast(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["task"], timeout=0.01)):
            with self.assertRaises(SystemExit) as ctx:
                run_task_export("status:pending")
        self.assertIn("timed out", str(ctx.exception))

    def test_malformed_compact_timestamp_returns_none(self) -> None:
        self.assertIsNone(parse_tw_utc_to_epoch_ms("20251301T000000Z"))
        self.assertIsNone(parse_tw_utc_to_epoch_ms("20250230T000000Z"))
        self.assertIsNone(parse_tw_utc_to_epoch_ms("20251201T246000Z"))

    def test_valid_compact_timestamp_parses(self) -> None:
        got = parse_tw_utc_to_epoch_ms("20250101T000000Z")
        self.assertIsInstance(got, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
