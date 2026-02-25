from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


def _repo_root() -> Path:
    # Expected location: <repo>/scalpel/tools/ci.py -> parents[2] == <repo>
    return Path(__file__).resolve().parents[2]


def _fmt_ms(ms: int) -> str:
    s = ms / 1000.0
    if s < 1:
        return f"{ms}ms"
    if s < 60:
        return f"{s:.2f}s"
    m = int(s // 60)
    ss = s - (m * 60)
    return f"{m}m{ss:04.1f}s"


def _run_step(*, label: str, cmd: List[str], cwd: Path, env: dict[str, str], ok_returncodes: set[int] | None = None) -> Tuple[int, str]:
    """Run one step; return (rc, combined_output)."""
    ok_returncodes = ok_returncodes or {0}

    start = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    dur_ms = int((time.time() - start) * 1000)

    out = (p.stdout or "")
    err = (p.stderr or "")
    combined = (out + ("\n" if out and err else "") + err).strip()

    if p.returncode == 0:
        status = "OK"
    elif p.returncode in ok_returncodes:
        status = "WARN"
    else:
        status = "FAIL"
    print(f"[scalpel-ci] {status}: {label} ({_fmt_ms(dur_ms)})")
    if combined:
        # Keep logs readable; do not indent each line to preserve copy/paste and pytest output.
        print(combined)

    return p.returncode, combined


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-ci",
        description="One-command CI gate (deterministic, UTC).",
    )
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors where applicable.")

    ap.add_argument("--skip-doctor", action="store_true", help="Skip repo hygiene checks.")
    ap.add_argument("--skip-compileall", action="store_true", help="Skip python -m compileall.")
    ap.add_argument("--skip-lint", action="store_true", help="Skip ruff checks (if installed).")
    ap.add_argument("--skip-tests", action="store_true", help="Skip unit/contract tests.")
    ap.add_argument("--skip-fixtures", action="store_true", help="Skip golden fixture check.")

    ap.add_argument(
        "--write-fixtures",
        action="store_true",
        help="Write fixtures instead of checking (dangerous; use intentionally).",
    )

    ap.add_argument(
        "--format",
        action="store_true",
        help="Also run 'ruff format --check' (only if ruff is installed).",
    )

    ns = ap.parse_args(argv)

    repo = _repo_root()

    # Determinism: run all steps in UTC.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    env["TZ"] = "UTC"
    env["SCALPEL_TZ"] = "UTC"
    env["SCALPEL_DISPLAY_TZ"] = "local"

    # Force tzset where available (POSIX).
    try:
        time.tzset()  # type: ignore[attr-defined]
    except Exception:
        pass

    steps: List[Tuple[str, List[str]]] = []

    if not ns.skip_doctor:
        steps.append(
            (
                "doctor",
                [
                    sys.executable,
                    "-m",
                    "scalpel.tools.doctor",
                    "--strict" if ns.strict else "",
                ],
            )
        )

    if not ns.skip_compileall:
        steps.append(("compileall", [sys.executable, "-m", "compileall", "-q", str(repo / "scalpel")]))

    if not ns.skip_lint:
        if _have("ruff"):
            steps.append(("ruff check", ["ruff", "check", "."]))
            if ns.format:
                steps.append(("ruff format --check", ["ruff", "format", "--check", "."]))
        else:
            print("[scalpel-ci] WARN: ruff not found; skipping lint")

    if not ns.skip_tests:
        steps.append(("unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]))

    if not ns.skip_fixtures:
        steps.append(
            (
                "fixtures",
                [
                    sys.executable,
                    "-m",
                    "scalpel.tools.gen_fixtures",
                    "--write" if ns.write_fixtures else "--check",
                ],
            )
        )

    # Execute.
    started = time.time()
    any_fail = False
    for label, cmd in steps:
        cmd = [c for c in cmd if c]  # drop empty strings
        ok_rcs: set[int] = {0}
        if label == "doctor" and not ns.strict:
            ok_rcs = {0, 1}
        rc, _ = _run_step(label=label, cmd=cmd, cwd=repo, env=env, ok_returncodes=ok_rcs)
        if rc not in ok_rcs:
            any_fail = True
            # Do not continue after a failure; fail fast to reduce noise.
            break

    total_ms = int((time.time() - started) * 1000)
    if any_fail:
        print(f"[scalpel-ci] RESULT: FAIL ({_fmt_ms(total_ms)})")
        return 2

    print(f"[scalpel-ci] RESULT: OK ({_fmt_ms(total_ms)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
