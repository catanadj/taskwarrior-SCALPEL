from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import serve as serve_mod
from . import serve_data as serve_data_mod
from .ai import AiPlanResult, PlanOverride, apply_plan_result, load_plan_overrides, load_plan_result
from .model import Payload
from .payload import build_payload
from .render.inline import build_html
from .taskwarrior import parse_tw_utc_to_epoch_ms, run_task_export
from .util.console import eprint
from .util.timeparse import parse_date_yyyy_mm_dd, parse_workhours
from .util.tz import resolve_tz, today_date, normalize_tz_name

TaskExportLookupResult = serve_mod.TaskExportLookupResult
TimewInterval = serve_mod.TimewInterval
TimewExportResult = serve_mod.TimewExportResult


def _build_parser(default_out: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Generate an interactive Taskwarrior calendar HTML (custom time-grid)."
    )
    ap.add_argument("--filter", default="status:pending", help="Taskwarrior filter for export (default: status:pending)")
    ap.add_argument("--start", default=None, help="View start date YYYY-MM-DD (default: today in --tz)")
    ap.add_argument("--days", type=int, default=7, help="Number of days to show (default: 7)")
    ap.add_argument("--workhours", default="06:00-23:00", help="Work hours window, e.g. 06:00-23:00")
    ap.add_argument("--snap", type=int, default=10, help="Snap minutes for drag/resize (default: 10)")
    ap.add_argument("--default-duration", type=int, default=10, help="Default minutes when duration is missing (default: 10)")
    ap.add_argument("--max-infer-duration", type=int, default=480, help="Max minutes to infer duration from due-scheduled (default: 480)")
    ap.add_argument("--px-per-min", type=float, default=2.0, help="Initial vertical scale in pixels per minute (default: 2.0)")

    ap.add_argument(
        "--tz",
        default=os.getenv("SCALPEL_TZ", "local"),
        help="Bucketing timezone for day boundaries (default: env SCALPEL_TZ or 'local')",
    )
    ap.add_argument(
        "--display-tz",
        default=os.getenv("SCALPEL_DISPLAY_TZ", "local"),
        help="Display timezone hint (default: env SCALPEL_DISPLAY_TZ or 'local')",
    )

    ap.add_argument(
        "--out",
        default=default_out,
        help="Output HTML path (default: ./build/scalpel_schedule.html)",
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument(
        "--goals",
        default=os.path.join(script_dir, "goals.json"),
        help="Goals config JSON (default: script folder /goals.json). If missing, goals are disabled.",
    )

    ap.add_argument("--plan-overrides", default=None, help="JSON file of plan overrides to apply")
    ap.add_argument("--plan-result", default=None, help="JSON file of AI plan result to apply")
    ap.add_argument(
        "--no-nautical-hooks",
        action="store_true",
        help="Disable nautical anchor/cp preview task expansion for this run",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--serve",
        dest="serve",
        action="store_true",
        help="Run the live local HTTP server (default; retained for compatibility).",
    )
    mode.add_argument(
        "--once",
        dest="serve",
        action="store_false",
        help="Render the HTML once and exit without starting the local server.",
    )
    ap.set_defaults(serve=True)
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for live mode (default: 127.0.0.1).",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for live mode (default: 8765, use 0 for auto).",
    )
    ap.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow live mode to bind non-loopback interfaces (requires --serve-token).",
    )
    ap.add_argument(
        "--serve-token",
        default=os.getenv("SCALPEL_SERVE_TOKEN", ""),
        help="Bearer/token for serve endpoints (required when --allow-remote is used).",
    )
    ap.add_argument("--no-open", action="store_true", help="Do not open the generated HTML in a browser")
    return ap


def _resolve_out_path(out_arg: str, default_out: str) -> str:
    out_path = os.path.abspath(out_arg)
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        # If caller used the default relative path from an unwritable CWD,
        # transparently fall back to a user-writable location.
        if out_arg == default_out:
            fallback = Path.home() / ".scalpel" / "build" / "scalpel_schedule.html"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            out_path = str(fallback)
            print(
                f"[scalpel] WARN: default output directory is not writable; using {out_path}",
                file=sys.stderr,
            )
        else:
            raise SystemExit(f"Cannot create output directory '{Path(out_path).parent}': {e}")
    return out_path


def _resolve_start_date(start_arg: str | None, tz_name: str) -> dt.date:
    if start_arg:
        return parse_date_yyyy_mm_dd(start_arg)
    try:
        return today_date(resolve_tz(tz_name))
    except ValueError as e:
        raise SystemExit(f"Invalid --tz value: {e}")


def _load_plan_inputs(args: argparse.Namespace) -> tuple[dict[str, PlanOverride] | None, AiPlanResult | None]:
    plan_overrides: dict[str, PlanOverride] | None = None
    plan_result: AiPlanResult | None = None
    if args.plan_overrides:
        try:
            plan_overrides = load_plan_overrides(Path(args.plan_overrides))
        except Exception as e:
            raise SystemExit(f"Failed to load plan overrides: {e}")
    if args.plan_result:
        try:
            plan_result = load_plan_result(Path(args.plan_result))
        except Exception as e:
            raise SystemExit(f"Failed to load plan result: {e}")
    return plan_overrides, plan_result


def _build_data(args: argparse.Namespace) -> Payload:
    tz_name = normalize_tz_name(args.tz)
    display_tz = normalize_tz_name(args.display_tz)
    start_date = _resolve_start_date(args.start, tz_name)

    work_start, work_end = parse_workhours(args.workhours)
    plan_overrides, plan_result = _load_plan_inputs(args)

    data = build_payload(
        filter_str=args.filter,
        start_date=start_date,
        days=int(args.days),
        work_start=int(work_start),
        work_end=int(work_end),
        snap=int(args.snap),
        default_duration_min=int(args.default_duration),
        max_infer_duration_min=int(args.max_infer_duration),
        px_per_min=float(args.px_per_min),
        goals_path=str(args.goals),
        tz=tz_name,
        display_tz=display_tz,
        plan_overrides=plan_overrides,
        nautical_hooks_enabled=not bool(args.no_nautical_hooks),
    )
    if plan_result:
        data = apply_plan_result(data, plan_result)
    return data


def _render_once(args: argparse.Namespace, out_path: str) -> Payload:
    data = _build_data(args)
    html = build_html(data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return data


def _obs_enabled() -> bool:
    return serve_mod._obs_enabled()


def _obs_line(event: str, **fields: Any) -> str:
    return serve_mod._obs_line(event, **fields)


def _obs_log(event: str, **fields: Any) -> None:
    serve_mod._obs_log(event, eprint_fn=eprint, **fields)


def _counter_inc(counters: dict[str, Any], key: str, *, path: str | None = None) -> None:
    serve_mod._counter_inc(counters, key, path=path)


def _counter_snapshot(counters: dict[str, Any]) -> dict[str, Any]:
    return serve_mod._counter_snapshot(counters)

def _run_timew_export_for_day(*, day_ymd: str, tz_name: str) -> TimewExportResult:
    return serve_data_mod.run_timew_export_for_day(
        day_ymd=day_ymd,
        tz_name=tz_name,
        run_proc=subprocess.run,
        parse_utc=parse_tw_utc_to_epoch_ms,
    )


def _run_task_export_for_uuid(uuid_query: str) -> TaskExportLookupResult:
    return serve_data_mod.run_task_export_for_uuid(uuid_query, run_export=run_task_export)


def _serve(args: argparse.Namespace, out_path: str, initial_payload: Payload) -> None:
    serve_mod.serve(
        args,
        out_path,
        initial_payload,
        render_once=_render_once,
        task_lookup=_run_task_export_for_uuid,
        timew_export=lambda day: _run_timew_export_for_day(day_ymd=day, tz_name=str(args.tz or "local")),
        server_factory=ThreadingHTTPServer,
        browser_open=webbrowser.open,
    )


def main(argv: list[str] | None = None) -> None:
    default_out = os.path.join("build", "scalpel_schedule.html")
    ap = _build_parser(default_out)
    args = ap.parse_args(argv)
    out_path = _resolve_out_path(args.out, default_out)
    payload = _render_once(args, out_path)

    print(out_path)

    if bool(getattr(args, "serve", False)):
        _serve(args, out_path, payload)
        return

    if not getattr(args, "no_open", False):
        try:
            webbrowser.open("file://" + out_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
