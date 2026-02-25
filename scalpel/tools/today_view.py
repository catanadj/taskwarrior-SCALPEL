from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from scalpel.payload import build_payload
from scalpel.util.timeparse import parse_workhours
from scalpel.util.tz import normalize_tz_name, resolve_tz, today_date, day_key_from_ms, midnight_epoch_ms


def _task_interval_ms(task: Dict[str, Any]) -> Optional[tuple[int, int]]:
    start = task.get("start_calc_ms")
    end = task.get("end_calc_ms")
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return start, end

    due_ms = task.get("due_ms") if isinstance(task.get("due_ms"), int) else None
    sch_ms = task.get("scheduled_ms") if isinstance(task.get("scheduled_ms"), int) else None
    dur_min = task.get("duration_min") if isinstance(task.get("duration_min"), int) else None
    if due_ms is not None and dur_min is not None and dur_min > 0:
        return due_ms - dur_min * 60000, due_ms
    if sch_ms is not None and dur_min is not None and dur_min > 0:
        return sch_ms, sch_ms + dur_min * 60000
    if sch_ms is not None and due_ms is not None and due_ms > sch_ms:
        return sch_ms, due_ms
    return None


def _layout_lanes(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = sorted(items, key=lambda x: (x["start_ms_vis"], x["end_ms_vis"]))
    groups: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    max_end = -1
    for ev in items:
        if not cur:
            cur = [ev]
            max_end = ev["end_ms_vis"]
            continue
        if ev["start_ms_vis"] < max_end:
            cur.append(ev)
            max_end = max(max_end, ev["end_ms_vis"])
        else:
            groups.append(cur)
            cur = [ev]
            max_end = ev["end_ms_vis"]
    if cur:
        groups.append(cur)

    out: List[Dict[str, Any]] = []
    cluster_id = 0
    for g in groups:
        lanes: List[int] = []
        assigned: List[Dict[str, Any]] = []
        for ev in g:
            lane_index = -1
            for i, lane_end in enumerate(lanes):
                if lane_end <= ev["start_ms_vis"]:
                    lane_index = i
                    break
            if lane_index < 0:
                lane_index = len(lanes)
                lanes.append(ev["end_ms_vis"])
            else:
                lanes[lane_index] = ev["end_ms_vis"]
            ev2 = dict(ev)
            ev2["lane"] = lane_index
            assigned.append(ev2)
        total = max(1, len(lanes))
        for ev in assigned:
            ev["total_lanes"] = total
            ev["overlap"] = total > 1
            ev["cluster_id"] = cluster_id
            out.append(ev)
        cluster_id += 1
    return out


def _compute_gaps(
    day_start_ms: int,
    work_start_min: int,
    work_end_min: int,
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    work_start_ms = day_start_ms + work_start_min * 60000
    work_end_ms = day_start_ms + work_end_min * 60000
    ints = []
    for it in items:
        s = max(work_start_ms, min(work_end_ms, it["start_ms_vis"]))
        e = max(work_start_ms, min(work_end_ms, it["end_ms_vis"]))
        if e > s:
            ints.append((s, e))
    ints.sort()
    merged: List[tuple[int, int]] = []
    for s, e in ints:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    gaps = []
    cur = work_start_ms
    for s, e in merged:
        if s > cur:
            gaps.append({"start_ms": cur, "end_ms": s, "dur_min": int((s - cur) / 60000)})
        cur = max(cur, e)
    if cur < work_end_ms:
        gaps.append({"start_ms": cur, "end_ms": work_end_ms, "dur_min": int((work_end_ms - cur) / 60000)})
    return gaps


def _day_payload(
    *,
    payload: Dict[str, Any],
    day: dt.date,
    tzinfo: dt.tzinfo,
    work_start: int,
    work_end: int,
    px_per_min: float,
    label: str,
    filter_label: str,
) -> Dict[str, Any]:
    day_start_ms = midnight_epoch_ms(day, tzinfo)
    day_key = day.isoformat()
    work_start_ms = day_start_ms + work_start * 60000
    work_end_ms = day_start_ms + work_end * 60000

    tasks_out: List[Dict[str, Any]] = []
    for t in payload.get("tasks", []):
        if not isinstance(t, dict):
            continue
        dk = day_key_from_ms(t.get("due_ms"), tzinfo) or day_key_from_ms(t.get("scheduled_ms"), tzinfo)
        if dk != day_key:
            continue

        iv = _task_interval_ms(t)
        if not iv:
            continue
        start_ms, end_ms = iv
        if end_ms <= start_ms:
            continue

        start_vis = max(start_ms, work_start_ms)
        end_vis = min(end_ms, work_end_ms)
        if end_vis <= start_vis:
            continue

        dur_min = int(max(1, round((end_vis - start_vis) / 60000)))
        tasks_out.append(
            {
                "uuid": t.get("uuid"),
                "short": str(t.get("uuid") or "")[:8],
                "description": t.get("description") or "",
                "project": t.get("project"),
                "tags": t.get("tags") or [],
                "dur_min": dur_min,
                "start_ms_vis": int(start_vis),
                "end_ms_vis": int(end_vis),
            }
        )

    tasks_out = _layout_lanes(tasks_out)
    tasks_out.sort(key=lambda x: (x["start_ms_vis"], x["end_ms_vis"], x.get("description") or ""))
    overlap_count = sum(1 for t in tasks_out if t.get("overlap"))
    load_min = sum(int((t["end_ms_vis"] - t["start_ms_vis"]) / 60000) for t in tasks_out)
    gaps = _compute_gaps(day_start_ms, work_start, work_end, tasks_out)

    return {
        "day_label": label,
        "date_iso": day.isoformat(),
        "day_start_ms": int(day_start_ms),
        "work_start_min": int(work_start),
        "work_end_min": int(work_end),
        "workhours": f"{work_start//60:02d}:{work_start%60:02d}-{work_end//60:02d}:{work_end%60:02d}",
        "px_per_min": float(px_per_min),
        "filter_label": filter_label,
        "summary": {
            "task_count": len(tasks_out),
            "load_min": int(load_min),
            "overlap_count": int(overlap_count),
        },
        "tasks": tasks_out,
        "gaps": gaps,
        "palette": {"projectColors": {}, "tagColors": {}},
    }


def _inject_data(template: str, data: Dict[str, Any], title: str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    out = re.sub(
        r'(<script id="data" type="application/json">)(.*?)(</script>)',
        r"\1" + payload + r"\3",
        template,
        flags=re.S,
    )
    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", out)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate compact day-only HTML views for yesterday/today/tomorrow.")
    ap.add_argument("--filter", default="status:pending", help="Taskwarrior filter for export (default: status:pending)")
    ap.add_argument("--workhours", default="06:00-23:00", help="Work hours window, e.g. 06:00-23:00")
    ap.add_argument("--snap", type=int, default=10, help="Snap minutes for drag/resize (default: 10)")
    ap.add_argument("--default-duration", type=int, default=10, help="Default minutes when duration is missing (default: 10)")
    ap.add_argument("--max-infer-duration", type=int, default=480, help="Max minutes to infer duration from due-scheduled (default: 480)")
    ap.add_argument("--px-per-min", type=float, default=1.5, help="Vertical scale in pixels per minute (default: 1.5)")
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
    ap.add_argument("--out-dir", default="build", help="Output directory (default: build)")
    ap.add_argument(
        "--template",
        default=None,
        help="HTML template path (default: scalpel/render/today_template.html)",
    )
    ap.add_argument(
        "--no-nautical-hooks",
        action="store_true",
        help="Disable nautical anchor/cp preview task expansion for this run",
    )
    ap.add_argument("--no-open", action="store_true", help="Do not open generated HTML")

    args = ap.parse_args(argv)

    tz_name = normalize_tz_name(args.tz)
    try:
        tzinfo = resolve_tz(tz_name)
    except ValueError as e:
        raise SystemExit(f"Invalid --tz value: {e}")
    display_tz = normalize_tz_name(args.display_tz)
    today = today_date(tzinfo)
    work_start, work_end = parse_workhours(args.workhours)

    payload = build_payload(
        filter_str=args.filter,
        start_date=today - dt.timedelta(days=1),
        days=3,
        work_start=int(work_start),
        work_end=int(work_end),
        snap=int(args.snap),
        default_duration_min=int(args.default_duration),
        max_infer_duration_min=int(args.max_infer_duration),
        px_per_min=float(args.px_per_min),
        goals_path=str(Path(__file__).resolve().parents[1] / "goals.json"),
        tz=tz_name,
        display_tz=display_tz,
        plan_overrides=None,
        nautical_hooks_enabled=not bool(args.no_nautical_hooks),
    )

    template_path = (
        Path(args.template)
        if args.template
        else Path(__file__).resolve().parents[1] / "render" / "today_template.html"
    )
    template = template_path.read_text(encoding="utf-8")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    days = [
        (today - dt.timedelta(days=1), "Yesterday"),
        (today, "Today"),
        (today + dt.timedelta(days=1), "Tomorrow"),
    ]

    day_payloads = [
        _day_payload(
            payload=payload,
            day=d,
            tzinfo=tzinfo,
            work_start=work_start,
            work_end=work_end,
            px_per_min=float(args.px_per_min),
            label=label,
            filter_label=args.filter,
        )
        for d, label in days
    ]

    data = {
        "days": day_payloads,
        "day_index": 1,
    }
    title = "Today • Taskwarrior Schedule"
    html = _inject_data(template, data, title)
    out_path = out_dir / "tw_today.html"
    out_path.write_text(html, encoding="utf-8")
    print(str(out_path))

    if not args.no_open:
        try:
            import webbrowser

            webbrowser.open("file://" + str(out_path))
        except Exception:
            pass


if __name__ == "__main__":
    main()
