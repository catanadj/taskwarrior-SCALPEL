from __future__ import annotations
import datetime as dt
import json
import os
import shlex
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from ..process import run_command


USAGE = """scalpel_ci_lite.sh - CI-lite runner for SCALPEL

Steps:
  1) clean
  2) doctor
  3) smoke (strict)
  4) check

Options:
  --out PATH         Output HTML path (default: build/scalpel_ci_smoke.html)
  --allow-dirty      Do not fail if git working tree is dirty before/after
  --no-clean         Skip clean step
  --no-doctor        Skip doctor step
  --no-smoke         Skip smoke step
  --no-check         Skip check step
  --clean-logs       Remove existing step logs in build/ci-lite before running
  --print-logs       Print step log paths at end (also on failure)
  --max-ms STEP=MS   Warn if STEP exceeds MS (repeatable)
  --perf-strict      Fail if any step exceeds its --max-ms budget

  --selftest-fail STEP  Force a failure in the named step (for testing log/tail UX)
  -h, --help         Show this help

Pass-through:
  All args after `--` are forwarded to the smoke step.
"""


@dataclass
class Options:
    repo_root: Path
    out: str = "build/scalpel_ci_smoke.html"
    allow_dirty: bool = False
    no_clean: bool = False
    no_doctor: bool = False
    no_smoke: bool = False
    no_check: bool = False
    clean_logs: bool = False
    print_logs: bool = False
    perf_strict: bool = False
    selftest_fail: str = ""
    smoke_args: list[str] = field(default_factory=list)
    max_ms_rules: list[str] = field(default_factory=list)

    @property
    def log_dir(self) -> Path:
        raw = os.getenv("SCALPEL_CI_LOG_DIR", "build/ci-lite")
        return self.repo_root / raw

    @property
    def json_out(self) -> Path:
        return self.log_dir / "payload.json"

    @property
    def fail_dir(self) -> Path:
        return self.log_dir / "fail"

    @property
    def fail_json(self) -> Path:
        return self.fail_dir / "payload.json"

    @property
    def fail_ddmin_json(self) -> Path:
        return self.fail_dir / "ddmin.json"

    @property
    def fail_html(self) -> Path:
        return self.fail_dir / "smoke.html"

    @property
    def summary(self) -> Path:
        return self.log_dir / "summary.tsv"

    @property
    def tail_lines(self) -> int:
        raw = os.getenv("SCALPEL_CI_TAIL_LINES", "120").strip()
        try:
            v = int(raw)
            if v > 0:
                return v
        except Exception:
            pass
        return 120

    @property
    def py_exec(self) -> str:
        return os.getenv("PY", os.getenv("PYTHON", "python3"))


@dataclass
class StepContext:
    options: Options
    log_files: list[Path] = field(default_factory=list)
    step_n: int = 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _die(msg: str) -> NoReturn:
    print(f"[ci-lite] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _parse_args(argv: list[str]) -> Options:
    opts = Options(repo_root=_repo_root())
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--out":
            if i + 1 >= len(argv):
                _die("--out requires a value")
            opts.out = argv[i + 1]
            i += 2
            continue
        if arg == "--allow-dirty":
            opts.allow_dirty = True
            i += 1
            continue
        if arg == "--no-clean":
            opts.no_clean = True
            i += 1
            continue
        if arg == "--no-doctor":
            opts.no_doctor = True
            i += 1
            continue
        if arg == "--no-smoke":
            opts.no_smoke = True
            i += 1
            continue
        if arg == "--no-check":
            opts.no_check = True
            i += 1
            continue
        if arg == "--clean-logs":
            opts.clean_logs = True
            i += 1
            continue
        if arg == "--print-logs":
            opts.print_logs = True
            i += 1
            continue
        if arg == "--selftest-fail":
            if i + 1 >= len(argv):
                _die("--selftest-fail requires a step name (clean|doctor|smoke|check)")
            opts.selftest_fail = argv[i + 1]
            i += 2
            continue
        if arg == "--max-ms":
            if i + 1 >= len(argv):
                _die("--max-ms requires STEP=MS")
            opts.max_ms_rules.append(argv[i + 1])
            i += 2
            continue
        if arg == "--perf-strict":
            opts.perf_strict = True
            i += 1
            continue
        if arg in {"-h", "--help"}:
            print(USAGE)
            raise SystemExit(0)
        if arg == "--":
            opts.smoke_args = argv[i + 1 :]
            break
        _die(f"Unknown argument: {arg} (use --help)")

    env_rules = os.getenv("SCALPEL_CI_MAX_MS", "")
    if env_rules:
        for rule in env_rules.split(","):
            rule = rule.strip()
            if rule:
                opts.max_ms_rules.append(rule)

    if opts.selftest_fail:
        valid = opts.selftest_fail in {"clean", "doctor", "check"} or opts.selftest_fail.startswith("smoke")
        if not valid:
            _die("--selftest-fail must be one of: clean|doctor|smoke|check")

    return opts


def _sanitize_step_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def _log_path(ctx: StepContext, name: str) -> Path:
    return ctx.options.log_dir / f"{ctx.step_n:02d}_{_sanitize_step_name(name)}.log"


def _selftest_match(name: str, want: str) -> bool:
    if not want:
        return False
    if want == name:
        return True
    if want == "smoke" and name.startswith("smoke"):
        return True
    if want.startswith("smoke") and name.startswith("smoke"):
        return True
    return False


def _require_git_clean(repo_root: Path) -> None:
    if shutil.which("git") is None:
        return
    result = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_root)
    if result.returncode != 0:
        return
    status = run_command(["git", "status", "--porcelain"], cwd=repo_root)
    if status.stdout.strip():
        sys.stderr.write(status.stdout)
        _die("Git working tree is dirty (use --allow-dirty to bypass)")


def _write_log_header(logfile: Path, name: str, cmd: list[str]) -> None:
    ts = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with logfile.open("w", encoding="utf-8") as fh:
        fh.write(f"[ci-lite] ts: {ts}\n")
        fh.write(f"[ci-lite] step: {name}\n")
        fh.write(f"[ci-lite] cmd: {shlex.join(cmd)}\n")
        fh.write(
            "[ci-lite] env: "
            f"SCALPEL_SKIP_DOCTOR={os.getenv('SCALPEL_SKIP_DOCTOR', '')} "
            f"SCALPEL_SKIP_SMOKE={os.getenv('SCALPEL_SKIP_SMOKE', '')} "
            f"PYTHON={os.getenv('PYTHON', '')}\n\n"
        )


def _append_log(logfile: Path, text: str) -> None:
    with logfile.open("a", encoding="utf-8") as fh:
        fh.write(text)


def _tail_text(path: Path, lines: int) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    tail = content[-lines:]
    return "\n".join(tail) + ("\n" if tail else "")


def _ensure_summary_header(path: Path) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("step\trc\tms\tlog\n", encoding="utf-8")


def _record_summary(path: Path, name: str, rc: int, elapsed_ms: int, logfile: Path) -> None:
    _ensure_summary_header(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{name}\t{rc}\t{elapsed_ms}\t{logfile}\n")


def _minify_fallback(in_path: Path, out_path: Path) -> None:
    obj: dict[str, object]
    try:
        obj = json.loads(in_path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            obj = {}
    except Exception:
        obj = {}

    cfg = obj.get("cfg") if isinstance(obj.get("cfg"), dict) else {}
    meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
    tasks_obj = obj.get("tasks")
    tasks_raw: list[object] = tasks_obj if isinstance(tasks_obj, list) else []
    tasks = [t for t in tasks_raw if isinstance(t, dict)][:1]
    payload: dict[str, object] = {"cfg": cfg, "tasks": tasks, "meta": meta}

    try:
        from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload

        payload = upgrade_payload(payload, target_version=int(LATEST_SCHEMA_VERSION))
    except Exception:
        payload.setdefault("schema_version", obj.get("schema_version", 2))
        payload.setdefault("indices", {})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _try_minify(opts: Options, query: str, out_path: Path) -> None:
    cmd = [
        opts.py_exec,
        "-m",
        "scalpel.tools.minify_fixture",
        "--in",
        str(opts.fail_json),
        "--q",
        query,
        "--out",
        str(out_path),
        "--pretty",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(opts.repo_root)
    run_command(cmd, cwd=opts.repo_root, env=env)
    if not out_path.exists() or out_path.stat().st_size == 0:
        _minify_fallback(opts.fail_json, out_path)


def _failure_shrink(opts: Options, step: str) -> None:
    if os.getenv("SCALPEL_CI_NO_SHRINK", "0") == "1":
        return
    opts.fail_dir.mkdir(parents=True, exist_ok=True)
    if opts.json_out.exists():
        shutil.copyfile(opts.json_out, opts.fail_json)
    if Path(opts.out).exists():
        shutil.copyfile(opts.out, opts.fail_html)

    notes = [
        "scalpel CI-lite failure shrink",
        f"step: {step}",
        f"repo_root: {opts.repo_root}",
        f"log_dir: {opts.log_dir}",
        f"fail_dir: {opts.fail_dir}",
        "",
    ]
    if opts.fail_json.exists():
        notes.extend(
            [
                "Repro (validate payload):",
                f'  PYTHONPATH="{opts.repo_root}" {opts.py_exec} -m scalpel.tools.validate_payload --in "{opts.fail_json}"',
                "",
                "Repro (render replay from payload):",
                f'  PYTHONPATH="{opts.repo_root}" {opts.py_exec} -m scalpel.tools.render_payload --in "{opts.fail_json}" --out "{opts.fail_dir / "replay.html"}"',
                "",
                "Minify examples:",
                f'  PYTHONPATH="{opts.repo_root}" {opts.py_exec} -m scalpel.tools.minify_fixture --in "{opts.fail_json}" --q "status:pending" --out "{opts.fail_dir / "min_pending.json"}" --pretty',
                f'  PYTHONPATH="{opts.repo_root}" {opts.py_exec} -m scalpel.tools.minify_fixture --in "{opts.fail_json}" --q "uuid:<UUID>" --out "{opts.fail_dir / "min_uuid_1.json"}" --pretty',
            ]
        )
    else:
        notes.append(f"No payload JSON found at JSON_OUT={opts.json_out}")
    (opts.fail_dir / "README.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")

    if not opts.fail_json.exists():
        (opts.fail_dir / "min_stub.json").write_text(
            '{"schema_version":2,"cfg":{},"tasks":[],"indices":{},"meta":{}}\n', encoding="utf-8"
        )
        return

    _try_minify(opts, "status:pending", opts.fail_dir / "min_pending.json")
    _try_minify(opts, "status:completed", opts.fail_dir / "min_completed.json")

    try:
        obj = json.loads(opts.fail_json.read_text(encoding="utf-8"))
    except Exception:
        obj = {}
    tasks = obj.get("tasks") if isinstance(obj, dict) else None
    uuids: list[str] = []
    if isinstance(tasks, list):
        for item in tasks:
            if not isinstance(item, dict):
                continue
            uuid_val = str(item.get("uuid") or "").strip()
            if uuid_val:
                uuids.append(uuid_val)
            if len(uuids) >= 5:
                break
    for idx, uuid_val in enumerate(uuids, start=1):
        _try_minify(opts, f"uuid:{uuid_val}", opts.fail_dir / f"min_uuid_{idx}.json")


def _run_step(ctx: StepContext, name: str, cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    logfile = _log_path(ctx, name)
    ctx.log_files.append(logfile)

    print()
    print(f"[ci-lite] === {name} ===")
    print(f"[ci-lite] log: {logfile}")
    _write_log_header(logfile, name, cmd)

    t0 = time.time_ns()
    rc = 0
    combined = ""
    if _selftest_match(name, ctx.options.selftest_fail):
        rc = 99
        combined = f"[ci-lite] selftest: forced failure for step: {name}\n"
    else:
        result = run_command(cmd, cwd=ctx.options.repo_root, env=env)
        rc = result.returncode
        combined = result.combined_output
        if combined and not combined.endswith("\n"):
            combined += "\n"
    elapsed_ms = int((time.time_ns() - t0) / 1_000_000)

    if combined:
        sys.stdout.write(combined)
        sys.stdout.flush()
        _append_log(logfile, combined)

    _record_summary(ctx.options.summary, name, rc, elapsed_ms, logfile)

    if rc != 0:
        print(file=sys.stderr)
        print(f"[ci-lite] FAILED step: {name} (exit {rc})", file=sys.stderr)
        _failure_shrink(ctx.options, name)
        print(f"[ci-lite] log: {logfile}", file=sys.stderr)
        print(f"[ci-lite] --- tail ({ctx.options.tail_lines} lines) ---", file=sys.stderr)
        sys.stderr.write(_tail_text(logfile, ctx.options.tail_lines))
        print("[ci-lite] --- /tail ---", file=sys.stderr)
        raise SystemExit(rc)


def _print_logs(ctx: StepContext) -> None:
    if not ctx.log_files:
        return
    print()
    print("[ci-lite] === logs ===")
    out_path = ctx.options.out
    out_status = "exists" if Path(out_path).exists() else "missing"
    print(f"[ci-lite] out: {out_path} ({out_status})")
    dir_status = "exists" if ctx.options.log_dir.is_dir() else "missing"
    print(f"[ci-lite] dir: {ctx.options.log_dir} ({dir_status})")
    for log_file in ctx.log_files:
        st = "exists" if log_file.exists() else "missing"
        print(f"[ci-lite] log: {log_file} ({st})")


def _load_perf_rules(rules: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for rule in rules:
        step, sep, raw_ms = rule.partition("=")
        if not sep:
            continue
        step = step.strip()
        raw_ms = raw_ms.strip()
        if not step or not raw_ms.isdigit():
            continue
        out[step] = int(raw_ms)
    return out


def _check_perf_budgets(opts: Options) -> int:
    rules = _load_perf_rules(opts.max_ms_rules)
    if not rules or not opts.summary.exists():
        return 0

    violations = 0
    lines = opts.summary.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        step, _rc, ms_s, log = parts
        budget = rules.get(step)
        if budget is None:
            continue
        try:
            ms = int(ms_s)
        except Exception:
            continue
        if ms > budget:
            violations += 1
            print(f"[ci-lite] PERF WARN: step '{step}' took {ms}ms > budget {budget}ms (log: {log})", file=sys.stderr)
    if violations and opts.perf_strict:
        print(f"[ci-lite] PERF STRICT: failing due to {violations} budget violation(s).", file=sys.stderr)
        return 3
    return 0


def _script_cmd(repo_root: Path, name: str) -> Path:
    return repo_root / "scripts" / name


def _resolve_steps(ctx: StepContext) -> list[tuple[str, list[str], dict[str, str] | None]]:
    opts = ctx.options
    repo_root = opts.repo_root
    steps: list[tuple[str, list[str], dict[str, str] | None]] = []

    if not opts.no_clean:
        clean_script = _script_cmd(repo_root, "scalpel_clean.sh")
        if clean_script.is_file() and os.access(clean_script, os.X_OK):
            steps.append(("clean", [str(clean_script)], None))
        elif shutil.which("scalpel-clean"):
            steps.append(("clean", ["scalpel-clean"], None))
        else:
            steps.append(("clean", ["bash", "-lc", f"rm -f {shlex.quote(opts.out)}"], None))

    if not opts.no_doctor:
        doctor_script = _script_cmd(repo_root, "scalpel_doctor.sh")
        if doctor_script.is_file() and os.access(doctor_script, os.X_OK):
            steps.append(("doctor", [str(doctor_script)], None))
        elif shutil.which("scalpel-doctor"):
            steps.append(("doctor", ["scalpel-doctor"], None))
        else:
            _die("No doctor runner found (expected ./scripts/scalpel_doctor.sh or scalpel-doctor on PATH)")

    if not opts.no_smoke:
        smoke_script = _script_cmd(repo_root, "scalpel_smoke_strict.sh")
        smoke_env = os.environ.copy()
        smoke_env["SCALPEL_SKIP_DOCTOR"] = "1"
        smoke_env["SCALPEL_SMOKE_OUT_JSON"] = str(opts.json_out)
        if smoke_script.is_file() and os.access(smoke_script, os.X_OK):
            steps.append(("smoke(strict)", [str(smoke_script), opts.out, *opts.smoke_args], smoke_env))
        elif shutil.which("scalpel-smoke-build"):
            steps.append(("smoke(strict)", ["scalpel-smoke-build", "--out", opts.out, "--strict", *opts.smoke_args], None))
        else:
            _die("No smoke runner found (expected ./scripts/scalpel_smoke_strict.sh or scalpel-smoke-build on PATH)")

        validate_script = _script_cmd(repo_root, "scalpel_validate_payload.sh")
        if validate_script.is_file() and os.access(validate_script, os.X_OK):
            steps.append(
                ("validate(payload)", [str(validate_script), "--from-html", opts.out, "--in", str(opts.json_out)], None)
            )
        else:
            steps.append(
                (
                    "validate(payload)",
                    [opts.py_exec, "-m", "scalpel.tools.validate_payload", "--from-html", opts.out, "--in", str(opts.json_out)],
                    _python_env(opts),
                )
            )

        if os.getenv("SCALPEL_CI_FAIL_AFTER_SMOKE", "0") == "1":
            steps.append(("selftest(fail-after-smoke)", ["bash", "-lc", "exit 1"], None))

    if not opts.no_check:
        check_script = _script_cmd(repo_root, "scalpel_check_strict.sh")
        check_env = os.environ.copy()
        check_env["SCALPEL_SKIP_DOCTOR"] = "1"
        check_env["SCALPEL_SKIP_SMOKE"] = "1"
        if check_script.is_file() and os.access(check_script, os.X_OK):
            steps.append(("check", [str(check_script), "--out", opts.out, "--skip-doctor", "--skip-smoke"], check_env))
        elif shutil.which("scalpel-check"):
            steps.append(("check", ["scalpel-check", "--out", opts.out], None))
        else:
            _die("No check runner found (expected ./scripts/scalpel_check_strict.sh or scalpel-check on PATH)")

    return steps


def _python_env(opts: Options) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(opts.repo_root)
    return env


def main(argv: list[str] | None = None) -> int:
    opts = _parse_args(list(sys.argv[1:] if argv is None else argv))
    ctx = StepContext(options=opts)
    os.chdir(opts.repo_root)

    opts.log_dir.mkdir(parents=True, exist_ok=True)
    if opts.clean_logs:
        for log_file in opts.log_dir.glob("*.log"):
            try:
                log_file.unlink()
            except FileNotFoundError:
                pass
        try:
            opts.summary.unlink()
        except FileNotFoundError:
            pass

    try:
        if not opts.allow_dirty:
            _require_git_clean(opts.repo_root)

        Path(opts.out).parent.mkdir(parents=True, exist_ok=True)

        for name, cmd, env in _resolve_steps(ctx):
            ctx.step_n += 1
            _run_step(ctx, name, cmd, env=env)

        if not opts.allow_dirty:
            _require_git_clean(opts.repo_root)

        perf_rc = _check_perf_budgets(opts)
        if perf_rc != 0:
            return perf_rc

        print()
        print(f"[ci-lite] OK: {opts.out}")
        print(f"[ci-lite] logs: {opts.log_dir}")
        print(f"[ci-lite] summary: {opts.summary}")
        return 0
    finally:
        if opts.print_logs:
            _print_logs(ctx)


if __name__ == "__main__":
    raise SystemExit(main())
