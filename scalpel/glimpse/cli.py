from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

from ..api import load_payload_from_json
from ..payload import build_payload
from ..process import ProcessError
from ..util.timeparse import parse_date_yyyy_mm_dd, parse_workhours
from ..util.tz import normalize_tz_name, resolve_tz, today_date
from .app import run_interactive
from .model import GlimpseSnapshot
from .render import render_agenda, render_day, render_week
from .source import snapshot_from_payload
from .style import color_enabled


def _degraded_terminal() -> bool:
    return os.environ.get("TERM", "").strip().lower() in {"", "dumb", "unknown"}


def _output_width(requested: int) -> int:
    if requested < 0:
        raise ValueError("--width must be zero (auto) or a positive integer")
    if requested:
        return requested
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _version() -> str:
    try:
        return package_version("taskwarrior-scalpel")
    except PackageNotFoundError:
        return "source"


def _parse_date(value: str | None, *, fallback: dt.date) -> dt.date:
    if value is None or value.strip().lower() == "today":
        return fallback
    return parse_date_yyyy_mm_dd(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scalpel-glimpse",
        description="Read-only terminal calendar view for SCALPEL.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"scalpel-glimpse {_version()}",
    )
    parser.add_argument("--payload", type=Path, help="Read an existing SCALPEL payload JSON")
    parser.add_argument("--filter", default="status:pending", help="Taskwarrior filter (default: status:pending)")
    parser.add_argument("--start", help="View start date YYYY-MM-DD or today (default: today)")
    parser.add_argument("--days", type=_positive_int, default=7, help="Number of days to show (default: 7)")
    parser.add_argument("--workhours", default="06:00-23:00", help="Work hours, for example 06:00-23:00")
    parser.add_argument("--default-duration", type=_positive_int, default=10)
    parser.add_argument("--max-infer-duration", type=_positive_int, default=480)
    parser.add_argument("--snap", type=_positive_int, default=10)
    parser.add_argument("--px-per-min", type=float, default=2.0)
    parser.add_argument("--tz", default="local", help="Bucketing timezone")
    parser.add_argument("--display-tz", default="local", help="Display timezone")
    parser.add_argument("--goals", default="", help="Goals configuration JSON")
    parser.add_argument("--no-nautical-hooks", action="store_true")
    parser.add_argument("--show-completed", action="store_true")
    parser.add_argument("--view", choices=("agenda", "day", "week"), default="agenda", help="View to render")
    parser.add_argument("--date", help="Start day to render as YYYY-MM-DD")
    parser.add_argument(
        "--width", type=int, default=0, help="Maximum output width (default: terminal width, or 80 when piped)"
    )
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument("--color", action="store_true", help="Force ANSI colors")
    color_group.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    color_group.add_argument("--plain", dest="no_color", action="store_true", help="Alias for --no-color")
    parser.add_argument("--ascii", action="store_true", help="Use ASCII markers and rules only")
    parser.add_argument("--interactive", action="store_true", help="Open the interactive curses view")
    return parser


def _load_snapshot(args: argparse.Namespace, *, tz_name: str, display_tz: str, today: dt.date) -> GlimpseSnapshot:
    if args.payload:
        payload = load_payload_from_json(args.payload)
    else:
        start_date = _parse_date(args.start, fallback=today)
        work_start, work_end = parse_workhours(args.workhours)
        payload = build_payload(
            filter_str=args.filter,
            start_date=start_date,
            days=max(1, args.days),
            work_start=work_start,
            work_end=work_end,
            snap=args.snap,
            default_duration_min=args.default_duration,
            max_infer_duration_min=args.max_infer_duration,
            px_per_min=args.px_per_min,
            goals_path=args.goals,
            tz=tz_name,
            display_tz=display_tz,
            nautical_hooks_enabled=not args.no_nautical_hooks,
            show_completed=args.show_completed,
        )
    cfg = payload.get("cfg", {})
    view_start_ms = cfg.get("view_start_ms") if isinstance(cfg, dict) else None
    timezone_name = str(cfg.get("display_tz") or cfg.get("tz") or "UTC") if isinstance(cfg, dict) else "UTC"
    start_date = dt.date.today()
    if isinstance(view_start_ms, int):
        bucket_tz = resolve_tz(str(cfg.get("tz") or timezone_name)) if isinstance(cfg, dict) else dt.timezone.utc
        start_date = dt.datetime.fromtimestamp(view_start_ms / 1000, tz=bucket_tz).date()
    return snapshot_from_payload(
        payload,
        start_date=start_date,
        days=int(cfg.get("days", 1)) if isinstance(cfg, dict) else 1,
        timezone_name=timezone_name,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tz_name = normalize_tz_name(args.tz)
        display_tz = normalize_tz_name(args.display_tz)
        today = today_date(resolve_tz(tz_name))
        if args.interactive:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("--interactive requires a terminal")
            if _degraded_terminal():
                raise ValueError("--interactive requires a curses-capable terminal; use normal output instead")
            run_interactive(
                loader=lambda: _load_snapshot(args, tz_name=tz_name, display_tz=display_tz, today=today),
                view=args.view,
                initial_date=_parse_date(args.date, fallback=today) if args.date else None,
                color=color_enabled(requested=True if args.color else False if args.no_color else None),
                ascii_only=args.ascii or _degraded_terminal(),
            )
            return 0
        snapshot = _load_snapshot(args, tz_name=tz_name, display_tz=display_tz, today=today)
        color = color_enabled(requested=True if args.color else False if args.no_color else None)
        ascii_only = args.ascii or _degraded_terminal()
        width = _output_width(args.width)
        now_ms = int(dt.datetime.now().timestamp() * 1000)
        if args.view == "day":
            selected_day = _parse_date(args.date, fallback=snapshot.start_date)
            print(
                render_day(snapshot, day=selected_day, width=width, color=color, ascii_only=ascii_only, now_ms=now_ms)
            )
        elif args.view == "week":
            selected_day = _parse_date(args.date, fallback=snapshot.start_date)
            print(
                render_week(
                    snapshot,
                    week_start=selected_day,
                    width=width,
                    color=color,
                    ascii_only=ascii_only,
                    now_ms=now_ms,
                )
            )
        else:
            print(render_agenda(snapshot, width=width, color=color, ascii_only=ascii_only, now_ms=now_ms))
        return 0
    except BrokenPipeError:
        return 0
    except (OSError, ValueError, TypeError, ProcessError, json.JSONDecodeError) as exc:
        print(f"scalpel-glimpse: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
