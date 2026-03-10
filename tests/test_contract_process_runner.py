from __future__ import annotations

import subprocess
import unittest

from scalpel.process import (
    CommandFailedError,
    CommandNotFoundError,
    CommandTimeoutError,
    run_checked,
    run_command,
)


class TestProcessRunnerContract(unittest.TestCase):
    def test_run_command_normalizes_bytes_output(self) -> None:
        seen: dict[str, object] = {}

        def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            seen["cmd"] = cmd
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout=b"out", stderr=b"err")

        result = run_command(["echo", "x"], timeout_s=2.5, run_proc=fake_run)

        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")
        self.assertEqual(result.combined_output, "out\nerr")
        self.assertEqual(seen["cmd"], ["echo", "x"])
        kwargs = seen["kwargs"]
        self.assertIsInstance(kwargs, dict)
        self.assertEqual(kwargs.get("stdout"), subprocess.PIPE)
        self.assertEqual(kwargs.get("stderr"), subprocess.PIPE)
        self.assertEqual(kwargs.get("check"), False)
        self.assertEqual(kwargs.get("timeout"), 2.5)

    def test_run_command_uses_text_mode_for_stdin_payloads(self) -> None:
        seen: dict[str, object] = {}

        def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        result = run_command(["git", "check-ignore"], input_text="a\0b\0", run_proc=fake_run)

        self.assertEqual(result.stdout, "ok")
        kwargs = seen["kwargs"]
        self.assertIsInstance(kwargs, dict)
        self.assertEqual(kwargs.get("input"), "a\0b\0")
        self.assertEqual(kwargs.get("text"), True)

    def test_run_checked_raises_typed_errors(self) -> None:
        def missing(cmd, **kwargs):  # type: ignore[no-untyped-def]
            raise FileNotFoundError()

        def timeout(cmd, **kwargs):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.0)

        def failing(cmd, **kwargs):  # type: ignore[no-untyped-def]
            return subprocess.CompletedProcess(cmd, 7, stdout=b"bad", stderr=b"worse")

        with self.assertRaises(CommandNotFoundError):
            run_checked(["task"], run_proc=missing)
        with self.assertRaises(CommandTimeoutError):
            run_checked(["task"], timeout_s=1.0, run_proc=timeout)
        with self.assertRaises(CommandFailedError) as ctx:
            run_checked(["task"], run_proc=failing)

        self.assertEqual(ctx.exception.result.returncode, 7)
        self.assertEqual(ctx.exception.result.combined_output, "bad\nworse")


if __name__ == "__main__":
    unittest.main(verbosity=2)
