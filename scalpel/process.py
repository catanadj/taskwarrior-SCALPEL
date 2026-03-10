from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Collection, Mapping, Sequence, cast

RunProcFn = Callable[..., Any]


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined_output(self) -> str:
        if self.stdout and self.stderr:
            return self.stdout + "\n" + self.stderr
        return self.stdout or self.stderr


class ProcessError(RuntimeError):
    def __init__(self, argv: Sequence[str]) -> None:
        self.argv = tuple(str(part) for part in argv)
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        return "Process execution failed."


class CommandNotFoundError(ProcessError):
    def _build_message(self) -> str:
        head = self.argv[0] if self.argv else "<unknown>"
        return f"Command not found: {head}"


class CommandTimeoutError(ProcessError):
    def __init__(self, argv: Sequence[str], timeout_s: float | None) -> None:
        self.timeout_s = timeout_s
        super().__init__(argv)

    def _build_message(self) -> str:
        if self.timeout_s is None:
            return "Command timed out."
        return f"Command timed out after {self.timeout_s:.1f}s."


class CommandFailedError(ProcessError):
    def __init__(self, result: CommandResult, ok_returncodes: Collection[int]) -> None:
        self.result = result
        self.ok_returncodes = tuple(sorted(set(int(code) for code in ok_returncodes)))
        super().__init__(result.argv)

    def _build_message(self) -> str:
        return f"Command exited with {self.result.returncode}."


def _normalize_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _normalize_cwd(cwd: str | Path | None) -> str | None:
    if cwd is None:
        return None
    return str(cwd)


def run_command(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: float | None = None,
    run_proc: RunProcFn | None = None,
) -> CommandResult:
    cmd = [str(part) for part in argv]
    runner = cast(RunProcFn, subprocess.run) if run_proc is None else run_proc
    kwargs: dict[str, object] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "check": False,
    }
    norm_cwd = _normalize_cwd(cwd)
    if norm_cwd is not None:
        kwargs["cwd"] = norm_cwd
    if env is not None:
        kwargs["env"] = dict(env)
    if input_text is not None:
        kwargs["input"] = input_text
        kwargs["text"] = True
    if timeout_s is not None:
        kwargs["timeout"] = timeout_s
    try:
        proc = runner(cmd, **kwargs)
    except FileNotFoundError as ex:
        raise CommandNotFoundError(cmd) from ex
    except subprocess.TimeoutExpired as ex:
        raise CommandTimeoutError(cmd, timeout_s) from ex

    return CommandResult(
        argv=tuple(cmd),
        returncode=int(getattr(proc, "returncode", 0)),
        stdout=_normalize_output(getattr(proc, "stdout", "")),
        stderr=_normalize_output(getattr(proc, "stderr", "")),
    )


def run_checked(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: float | None = None,
    ok_returncodes: Collection[int] = (0,),
    run_proc: RunProcFn | None = None,
) -> CommandResult:
    result = run_command(
        argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
        timeout_s=timeout_s,
        run_proc=run_proc,
    )
    if result.returncode not in ok_returncodes:
        raise CommandFailedError(result, ok_returncodes)
    return result
