from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import cast

from ..api import load_payload_from_json
from ..payload import build_payload
from ..util.timeparse import parse_date_yyyy_mm_dd, parse_workhours
from ..util.tz import normalize_tz_name, resolve_tz, today_date
from .render import render_agenda, render_day, render_week
from .source import snapshot_from_payload
from .style import color_enabled
from .app import run_interactive


def _parse_date(value: str | None, *, fallback: dt.date) -> dt.date:
    if value is None or value.strip().lower() == "today":
        return fallback
    return cast(dt.date, parse_date_yyyy_mm_dd(value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scalpel-glimpse",
        description="Read-only terminal calendar view for SCALPEL.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="scalpel-glimpse (agenda)",
    )
    parser.add_argument("--payload", type=Path, help="Read an existing SCALPEL payload JSON")
    parser.add_argument("--filter", default="status:pending", help="Taskwarrior filter (default: status:pending)")
    parser.add_argument("--start", help="View start date YYYY-MM-DD or today (default: today)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to show (default: 7)")
    parser.add_argument("--workhours", default="06:00-23:00", help="Work hours, for example 06:00-23:00")
    parser.add_argument("--default-duration", type=int, default=10)
    parser.add_argument("--max-infer-duration", type=int, default=480)
    parser.add_argument("--snap", type=int, default=10)
    parser.add_argument("--px-per-min", type=float, default=2.0)
    parser.add_argument("--tz", default="local", help="Bucketing timezone")
    parser.add_argument("--display-tz", default="local", help="Display timezone")
    parser.add_argument("--goals", default="", help="Goals configuration JSON")
    parser.add_argument("--no-nautical-hooks", action="store_true")
    parser.add_argument("--show-completed", action="store_true")
    parser.add_argument("--view", choices=("agenda", "day", "week"), default="agenda", help="View to render")
    parser.add_argument("--date", help="Start day to render as YYYY-MM-DD")
    parser.add_argument("--width", type=int, default=80, help="Maximum output width (default: 80)")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--plain", dest="no_color", action="store_true", help="Alias for --no-color")
    parser.add_argument("--ascii", action="store_true", help="Use ASCII markers and rules only")
    parser.add_argument("--interactive", action="store_true", help="Open the interactive curses view")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tz_name = normalize_tz_name(args.tz)
        display_tz = normalize_tz_name(args.display_tz)
        today = today_date(resolve_tz(tz_name))
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
        snapshot = snapshot_from_payload(
            payload,
            start_date=start_date,
            days=int(cfg.get("days", 1)) if isinstance(cfg, dict) else 1,
            timezone_name=timezone_name,
        )
        if args.interactive:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("--interactive requires a terminal")
            run_interactive(snapshot)
            return 0
        color = color_enabled(requested=False if args.no_color else None)
        if args.view == "day":
            selected_day = _parse_date(args.date, fallback=start_date)
            print(render_day(snapshot, day=selected_day, width=args.width, color=color, ascii_only=args.ascii))
        elif args.view == "week":
            selected_day = _parse_date(args.date, fallback=start_date)
            print(render_week(snapshot, week_start=selected_day, width=args.width, color=color, ascii_only=args.ascii))
        else:
            print(render_agenda(snapshot, width=args.width, color=color, ascii_only=args.ascii))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"scalpel-glimpse: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
