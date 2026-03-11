from __future__ import annotations

import os
import shlex
from typing import Collection, TypedDict

from .process import CommandFailedError, CommandNotFoundError, CommandTimeoutError, run_checked


class ApplyPreviewEntry(TypedDict):
    index: int
    kind: str
    line: str
    argv: list[str]


class ApplyExecutionEntry(TypedDict):
    index: int
    kind: str
    line: str
    argv: list[str]
    ok: bool
    returncode: int | None
    stdout: str
    stderr: str
    error: str | None


class ApplyExecutionResult(TypedDict):
    ok: bool
    applied: int
    selected: int
    commands: list[ApplyExecutionEntry]
    stopped_after_index: int | None


def _task_apply_timeout_s() -> float:
    raw = (os.getenv("SCALPEL_TASK_APPLY_TIMEOUT_S", "30") or "").strip()
    try:
        value = float(raw)
        if value > 0:
            return value
    except Exception:
        pass
    return 30.0


def _bad_apply_request(msg: str) -> SystemExit:
    raise SystemExit(msg)


def _parse_task_command_line(index: int, line: object) -> ApplyPreviewEntry:
    raw = str(line or "").strip()
    if not raw:
        _bad_apply_request(f"Command {index + 1} is empty.")
    try:
        argv = shlex.split(raw, posix=True)
    except ValueError as ex:
        _bad_apply_request(f"Command {index + 1} could not be parsed: {ex}")
    if not argv or argv[0] != "task":
        _bad_apply_request(f"Command {index + 1} must start with `task`.")

    kind = ""
    if len(argv) >= 3 and argv[1] == "add":
        kind = "add"
    elif len(argv) == 3 and argv[2] in {"done", "delete"}:
        kind = argv[2]
    elif len(argv) >= 4 and argv[2] == "modify":
        kind = "modify"
    else:
        _bad_apply_request(
            f"Command {index + 1} must be one of: `task add ...`, `task <id> modify ...`, `task <id> done`, `task <id> delete`."
        )

    return {
        "index": index,
        "kind": kind,
        "line": raw,
        "argv": [str(part) for part in argv],
    }


def preview_apply_commands(lines: Collection[object]) -> list[ApplyPreviewEntry]:
    return [_parse_task_command_line(idx, line) for idx, line in enumerate(lines)]


def _selected_indexes(preview: list[ApplyPreviewEntry], selected: Collection[object] | None) -> list[int]:
    max_index = len(preview) - 1
    if selected is None:
        return [entry["index"] for entry in preview]

    out: list[int] = []
    seen: set[int] = set()
    for raw in selected:
        if isinstance(raw, bool):
            _bad_apply_request("Selected command indexes must be integers.")
        if isinstance(raw, int):
            idx = raw
        elif isinstance(raw, str):
            try:
                idx = int(raw.strip())
            except Exception:
                _bad_apply_request("Selected command indexes must be integers.")
        else:
            _bad_apply_request("Selected command indexes must be integers.")
        if idx < 0 or idx > max_index:
            _bad_apply_request(f"Selected command index {idx} is out of range.")
        if idx in seen:
            continue
        seen.add(idx)
        out.append(idx)
    return out


def _task_argv_for_apply(argv: list[str]) -> list[str]:
    return ["task", "rc.confirmation=no", *argv[1:]]


def execute_apply_commands(
    lines: Collection[object],
    *,
    selected: Collection[object] | None = None,
) -> ApplyExecutionResult:
    preview = preview_apply_commands(lines)
    indexes = _selected_indexes(preview, selected)
    timeout_s = _task_apply_timeout_s()
    commands_by_index = {entry["index"]: entry for entry in preview}
    results: list[ApplyExecutionEntry] = []
    applied = 0

    for idx in indexes:
        entry = commands_by_index[idx]
        argv = entry["argv"]
        try:
            result = run_checked(_task_argv_for_apply(argv), timeout_s=timeout_s)
            results.append(
                {
                    "index": idx,
                    "kind": entry["kind"],
                    "line": entry["line"],
                    "argv": list(argv),
                    "ok": True,
                    "returncode": int(result.returncode),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "error": None,
                }
            )
            applied += 1
        except CommandNotFoundError:
            results.append(
                {
                    "index": idx,
                    "kind": entry["kind"],
                    "line": entry["line"],
                    "argv": list(argv),
                    "ok": False,
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "error": "Taskwarrior binary 'task' not found on PATH.",
                }
            )
            return {
                "ok": False,
                "applied": applied,
                "selected": len(indexes),
                "commands": results,
                "stopped_after_index": idx,
            }
        except CommandTimeoutError:
            results.append(
                {
                    "index": idx,
                    "kind": entry["kind"],
                    "line": entry["line"],
                    "argv": list(argv),
                    "ok": False,
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "error": f"Taskwarrior command timed out after {timeout_s:.1f}s.",
                }
            )
            return {
                "ok": False,
                "applied": applied,
                "selected": len(indexes),
                "commands": results,
                "stopped_after_index": idx,
            }
        except CommandFailedError as ex:
            results.append(
                {
                    "index": idx,
                    "kind": entry["kind"],
                    "line": entry["line"],
                    "argv": list(argv),
                    "ok": False,
                    "returncode": int(ex.result.returncode),
                    "stdout": ex.result.stdout,
                    "stderr": ex.result.stderr,
                    "error": f"Taskwarrior command failed with exit {ex.result.returncode}.",
                }
            )
            return {
                "ok": False,
                "applied": applied,
                "selected": len(indexes),
                "commands": results,
                "stopped_after_index": idx,
            }

    return {
        "ok": True,
        "applied": applied,
        "selected": len(indexes),
        "commands": results,
        "stopped_after_index": None,
    }
