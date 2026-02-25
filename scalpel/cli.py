from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import webbrowser
from pathlib import Path

from .ai import apply_plan_result, load_plan_overrides, load_plan_result
from .payload import build_payload
from .render.inline import build_html
from .util.timeparse import parse_date_yyyy_mm_dd, parse_workhours
from .util.tz import resolve_tz, today_date, normalize_tz_name


def main(argv: list[str] | None = None) -> None:
    default_out = os.path.join("build", "scalpel_schedule.html")
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

    ap.add_argument("--goals", default=os.path.join(script_dir, "goals.json"),
                    help="Goals config JSON (default: script folder /goals.json). If missing, goals are disabled.")

    ap.add_argument("--plan-overrides", default=None, help="JSON file of plan overrides to apply")
    ap.add_argument("--plan-result", default=None, help="JSON file of AI plan result to apply")
    ap.add_argument(
        "--no-nautical-hooks",
        action="store_true",
        help="Disable nautical anchor/cp preview task expansion for this run",
    )

    ap.add_argument("--no-open", action="store_true", help="Do not open the generated HTML in a browser")

    args = ap.parse_args(argv)

    tz_name = normalize_tz_name(args.tz)
    display_tz = normalize_tz_name(args.display_tz)

    if args.start:
        start_date = parse_date_yyyy_mm_dd(args.start)
    else:
        try:
            start_date = today_date(resolve_tz(tz_name))
        except ValueError as e:
            raise SystemExit(f"Invalid --tz value: {e}")

    work_start, work_end = parse_workhours(args.workhours)

    plan_overrides = None
    plan_result = None
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

    html = build_html(data)

    out_path = os.path.abspath(args.out)
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        # If caller used the default relative path from an unwritable CWD,
        # transparently fall back to a user-writable location.
        if args.out == default_out:
            fallback = Path.home() / ".scalpel" / "build" / "scalpel_schedule.html"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            out_path = str(fallback)
            print(
                f"[scalpel] WARN: default output directory is not writable; using {out_path}",
                file=sys.stderr,
            )
        else:
            raise SystemExit(f"Cannot create output directory '{Path(out_path).parent}': {e}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(out_path)

    if not getattr(args, "no_open", False):
        try:
            webbrowser.open("file://" + out_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
