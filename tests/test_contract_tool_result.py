from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel.tools import doctor
from scalpel.tools.result import (
    ToolCliError,
    ToolIssue,
    exit_code_for_status,
    result_from_issues,
    step_status_for_returncode,
)


class TestToolResultContract(unittest.TestCase):
    def test_exit_codes_and_step_statuses_are_stable(self) -> None:
        self.assertEqual(exit_code_for_status("ok"), 0)
        self.assertEqual(exit_code_for_status("warn"), 1)
        self.assertEqual(exit_code_for_status("fail"), 2)

        self.assertEqual(step_status_for_returncode(0, {0, 1}), "ok")
        self.assertEqual(step_status_for_returncode(1, {0, 1}), "warn")
        self.assertEqual(step_status_for_returncode(2, {0, 1}), "fail")

    def test_issue_driven_result_escalates_strict_warnings(self) -> None:
        warn_only = [ToolIssue("warning", "lint missing")]
        error_only = [ToolIssue("error", "broken")]

        self.assertEqual(result_from_issues(tool="x", issues=[]).status, "ok")
        self.assertEqual(result_from_issues(tool="x", issues=warn_only).status, "warn")
        self.assertEqual(result_from_issues(tool="x", issues=warn_only, strict_warnings=True).status, "fail")
        self.assertEqual(result_from_issues(tool="x", issues=error_only).status, "fail")

    def test_doctor_result_uses_shared_issue_model(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(doctor, "_scan_tree_issues", return_value=[ToolIssue("warning", "cache found")]):
                with patch.object(doctor, "_smoke_inline_build_issues", return_value=[]):
                    result = doctor._build_result(root, strict=False, verbose_artifacts=False)
                    strict_result = doctor._build_result(root, strict=True, verbose_artifacts=False)

        self.assertEqual(result.status, "warn")
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(strict_result.status, "fail")
        self.assertEqual(strict_result.exit_code, 2)

    def test_tool_cli_error_carries_exit_code(self) -> None:
        err = ToolCliError("bad", exit_code=7)
        self.assertEqual(str(err), "bad")
        self.assertEqual(err.exit_code, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
