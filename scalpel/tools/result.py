from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

IssueLevel = Literal["warning", "error"]
ToolStatus = Literal["ok", "warn", "fail"]


@dataclass(frozen=True)
class ToolIssue:
    level: IssueLevel
    message: str


@dataclass(frozen=True)
class ToolStepResult:
    label: str
    returncode: int
    elapsed_ms: int
    output: str
    status: ToolStatus


@dataclass(frozen=True)
class ToolResult:
    tool: str
    status: ToolStatus
    issues: tuple[ToolIssue, ...] = field(default_factory=tuple)
    steps: tuple[ToolStepResult, ...] = field(default_factory=tuple)

    @property
    def exit_code(self) -> int:
        return exit_code_for_status(self.status)

    def issues_for_level(self, level: IssueLevel) -> list[ToolIssue]:
        return [issue for issue in self.issues if issue.level == level]


class ToolCliError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def exit_code_for_status(status: ToolStatus) -> int:
    if status == "ok":
        return 0
    if status == "warn":
        return 1
    return 2


def step_status_for_returncode(returncode: int, ok_returncodes: set[int]) -> ToolStatus:
    if returncode == 0:
        return "ok"
    if returncode in ok_returncodes:
        return "warn"
    return "fail"


def result_from_issues(*, tool: str, issues: list[ToolIssue], strict_warnings: bool = False) -> ToolResult:
    has_error = any(issue.level == "error" for issue in issues)
    has_warning = any(issue.level == "warning" for issue in issues)
    if has_error:
        status: ToolStatus = "fail"
    elif has_warning and strict_warnings:
        status = "fail"
    elif has_warning:
        status = "warn"
    else:
        status = "ok"
    return ToolResult(tool=tool, status=status, issues=tuple(issues))
