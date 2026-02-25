from __future__ import annotations

import argparse
import datetime as dt
import os
import webbrowser
from pathlib import Path

from scalpel.payload import build_payload
from scalpel.render.inline import build_html
from scalpel.util.timeparse import parse_workhours
from scalpel.util.tz import normalize_tz_name, resolve_tz, today_date


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Generate a compact 3-day calendar (yesterday/today/tomorrow) with a 1-day view window."
    )
    ap.add_argument("--filter", default="status:pending", help="Taskwarrior filter for export (default: status:pending)")
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

    script_dir = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.path.join("build", "scalpel_mobile.html"), help="Output HTML path")
    ap.add_argument("--goals", default=os.path.join(Path(script_dir).parent, "goals.json"),
                    help="Goals config JSON (default: scalpel/goals.json). If missing, goals are disabled.")
    ap.add_argument(
        "--no-nautical-hooks",
        action="store_true",
        help="Disable nautical anchor/cp preview task expansion for this run",
    )
    ap.add_argument("--no-open", action="store_true", help="Do not open the generated HTML in a browser")

    args = ap.parse_args(argv)

    tz_name = normalize_tz_name(args.tz)
    display_tz = normalize_tz_name(args.display_tz)

    try:
        today = today_date(resolve_tz(tz_name))
    except ValueError as e:
        raise SystemExit(f"Invalid --tz value: {e}")
    start_date = today - dt.timedelta(days=1)

    work_start, work_end = parse_workhours(args.workhours)

    data = build_payload(
        filter_str=args.filter,
        start_date=start_date,
        days=3,
        work_start=int(work_start),
        work_end=int(work_end),
        snap=int(args.snap),
        default_duration_min=int(args.default_duration),
        max_infer_duration_min=int(args.max_infer_duration),
        px_per_min=float(args.px_per_min),
        goals_path=str(args.goals),
        tz=tz_name,
        display_tz=display_tz,
        plan_overrides=None,
        nautical_hooks_enabled=not bool(args.no_nautical_hooks),
    )

    data_cfg = data.get("cfg") if isinstance(data, dict) else None
    if isinstance(data_cfg, dict):
        data_cfg["viewwin_seed"] = {
            "startYmd": today.isoformat(),
            "futureDays": 1,
            "overdueDays": 0,
        }

    html = build_html(data)

    out_path = os.path.abspath(args.out)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
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
