# scalpel/planner.py
from __future__ import annotations

import datetime as dt
import shlex
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .interval import infer_interval_ms
from .model import Task, CalendarConfig, PlanOverride, ConflictSegment, SelectionMetrics
from .util.tz import day_key_from_ms, midnight_epoch_ms, normalize_tz_name, resolve_tz


def apply_overrides(
    tasks: list[Task],
    overrides: dict[str, PlanOverride],
    cfg: CalendarConfig,
) -> dict[str, tuple[int, int, int]]:
    """
    Returns per-uuid (start_ms, due_ms, duration_min) AFTER applying overrides/inference.
    """
    events: Dict[str, Tuple[int, int, int]] = {}

    default_duration_min = int(cfg.get("default_duration_min", 10) or 10)
    max_infer_duration_min = int(cfg.get("max_infer_duration_min", 480) or 480)

    for t in tasks:
        if not isinstance(t, dict):
            continue
        uuid = t.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            continue

        if uuid in overrides:
            ov = overrides[uuid]
            start_ms = int(ov.start_ms)
            due_ms = int(ov.due_ms)
            if due_ms <= start_ms:
                continue
            dur_min = ov.duration_min
            if dur_min is None:
                dur_min = max(1, (due_ms - start_ms) // 60000)
            events[uuid] = (start_ms, due_ms, int(dur_min))
            continue

        start_calc = t.get("start_calc_ms")
        end_calc = t.get("end_calc_ms")
        dur_calc = t.get("dur_calc_min")
        if isinstance(start_calc, int) and isinstance(end_calc, int) and end_calc > start_calc:
            if isinstance(dur_calc, int) and dur_calc > 0:
                dur_min = int(dur_calc)
            else:
                dur_min = int((end_calc - start_calc) // 60000)
            events[uuid] = (int(start_calc), int(end_calc), int(dur_min))
            continue

        due_ms = t.get("due_ms")
        scheduled_ms = t.get("scheduled_ms")
        duration_min = t.get("duration_min")
        if isinstance(due_ms, int) and due_ms > 0:
            iv = infer_interval_ms(
                due_ms=due_ms,
                scheduled_ms=scheduled_ms if isinstance(scheduled_ms, int) else None,
                duration_min=duration_min if isinstance(duration_min, int) else None,
                default_duration_min=default_duration_min,
                max_infer_duration_min=max_infer_duration_min,
            )
            if iv and iv.ok and iv.end_ms > iv.start_ms:
                events[uuid] = (iv.start_ms, iv.end_ms, int(iv.duration_min))

    return events


def detect_conflicts(events: dict[str, tuple[int, int, int]], cfg: CalendarConfig) -> list[ConflictSegment]:
    """Overlap detection and out-of-workhours segments."""
    segments: List[ConflictSegment] = []

    # Overlaps (sweep line, similar to JS computeConflictSegments).
    pts: List[Tuple[int, int, str]] = []
    for uuid, (start_ms, due_ms, _dur) in events.items():
        pts.append((start_ms, +1, uuid))
        pts.append((due_ms, -1, uuid))
    pts.sort(key=lambda x: (x[0], -x[1]))

    active: set[str] = set()
    prev_t: Optional[int] = None

    for t_ms, kind, uuid in pts:
        if prev_t is not None and t_ms > prev_t and len(active) >= 2:
            uuids = tuple(sorted(active))
            key = ",".join(uuids)
            last = segments[-1] if segments else None
            if last and last.kind == "overlap" and last.key == key and last.end_ms == prev_t:
                segments[-1] = ConflictSegment(
                    start_ms=last.start_ms,
                    end_ms=t_ms,
                    uuids=last.uuids,
                    key=last.key,
                    kind=last.kind,
                )
            else:
                segments.append(ConflictSegment(start_ms=prev_t, end_ms=t_ms, uuids=uuids, key=key, kind="overlap"))

        if kind == +1:
            active.add(uuid)
        else:
            active.discard(uuid)
        prev_t = t_ms

    # Out-of-workhours segments (day-by-day in cfg.tz).
    work_start_min = int(cfg.get("work_start_min", 0) or 0)
    work_end_min = int(cfg.get("work_end_min", 1440) or 1440)
    work_start_min = max(0, min(1440, work_start_min))
    work_end_min = max(0, min(1440, work_end_min))
    if work_end_min <= work_start_min:
        work_start_min, work_end_min = 0, 1440

    tz_name = normalize_tz_name(cfg.get("tz"))
    tzinfo = resolve_tz(tz_name)

    for uuid, (start_ms, due_ms, _dur) in events.items():
        if due_ms <= start_ms:
            continue

        try:
            day_date = dt.datetime.fromtimestamp(start_ms / 1000.0, tz=tzinfo).date()
        except Exception:
            continue

        guard = 0
        while guard < 400:
            guard += 1

            day_start = midnight_epoch_ms(day_date, tzinfo)
            next_day = day_date + dt.timedelta(days=1)
            next_day_start = midnight_epoch_ms(next_day, tzinfo)

            seg_start = max(start_ms, day_start)
            seg_end = min(due_ms, next_day_start)
            if seg_end > seg_start:
                work_start_ms = day_start + work_start_min * 60000
                work_end_ms = day_start + work_end_min * 60000

                if seg_start < work_start_ms:
                    out_end = min(seg_end, work_start_ms)
                    if out_end > seg_start:
                        segments.append(
                            ConflictSegment(
                                start_ms=seg_start,
                                end_ms=out_end,
                                uuids=(uuid,),
                                key=uuid,
                                kind="out_of_hours",
                            )
                        )

                if seg_end > work_end_ms:
                    out_start = max(seg_start, work_end_ms)
                    if seg_end > out_start:
                        segments.append(
                            ConflictSegment(
                                start_ms=out_start,
                                end_ms=seg_end,
                                uuids=(uuid,),
                                key=uuid,
                                kind="out_of_hours",
                            )
                        )

            if next_day_start >= due_ms:
                break
            day_date = next_day

    return segments


def selection_metrics(selected_uuids: list[str], events: dict[str, tuple[int, int, int]]) -> SelectionMetrics:
    """sum duration, span, total gaps (between sorted intervals)."""
    ints: List[Tuple[int, int]] = []
    total_min = 0

    for u in selected_uuids:
        ev = events.get(u)
        if not ev:
            continue
        start_ms, due_ms, dur_min = ev
        if due_ms <= start_ms:
            continue
        ints.append((start_ms, due_ms))
        total_min += int(dur_min)

    if not ints:
        return SelectionMetrics(count=0, duration_min=0, span_min=0, gap_min=0)

    ints.sort(key=lambda x: x[0])
    span_min = int((ints[-1][1] - ints[0][0]) // 60000)

    gap_min = 0
    prev_end = ints[0][1]
    for start_ms, due_ms in ints[1:]:
        if start_ms > prev_end:
            gap_min += int((start_ms - prev_end) // 60000)
        prev_end = max(prev_end, due_ms)

    return SelectionMetrics(
        count=len(ints),
        duration_min=int(total_min),
        span_min=int(span_min),
        gap_min=int(gap_min),
    )


def generate_modify_commands(selected: list[str], events: dict[str, tuple[int, int, int]]) -> list[str]:
    """
    Emit:
      task <uuid> modify scheduled:... due:... duration:...
    Leave timezone to TW (local time strings, no offset).
    """

    def _fmt_local(ms: int) -> str:
        return dt.datetime.fromtimestamp(int(ms) / 1000.0).strftime("%Y-%m-%dT%H:%M")

    out: List[Tuple[int, str]] = []
    for uuid in selected:
        ev = events.get(uuid)
        if not ev:
            continue
        start_ms, due_ms, dur_min = ev
        if due_ms <= start_ms:
            continue
        if not isinstance(dur_min, int) or dur_min <= 0:
            continue
        sch = _fmt_local(start_ms)
        due = _fmt_local(due_ms)
        safe_uuid = shlex.quote(uuid)
        out.append((start_ms, f"task {safe_uuid} modify scheduled:{sch} due:{due} duration:{dur_min}min"))

    out.sort(key=lambda x: x[0])
    return [line for _, line in out]


@dataclass(frozen=True)
class PlanSummary:
    events: Dict[str, Tuple[int, int, int]]
    conflicts: List[ConflictSegment]
    commands: List[str]
    metrics: SelectionMetrics


def build_plan_summary(
    payload: dict,
    *,
    overrides: Optional[Dict[str, PlanOverride]] = None,
    selected_uuids: Optional[List[str]] = None,
) -> PlanSummary:
    """Compute a deterministic plan summary for payload+overrides."""
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    cfg = payload.get("cfg") if isinstance(payload, dict) else None
    tasks_list: list[Task] = tasks if isinstance(tasks, list) else []
    cfg_dict: CalendarConfig = cfg if isinstance(cfg, dict) else {}

    overrides = overrides or {}
    events = apply_overrides(tasks_list, overrides, cfg_dict)

    selected = list(selected_uuids) if selected_uuids is not None else sorted(events.keys())
    conflicts = detect_conflicts(events, cfg_dict)
    commands = generate_modify_commands(selected, events)
    metrics = selection_metrics(selected, events)

    return PlanSummary(events=events, conflicts=conflicts, commands=commands, metrics=metrics)


# scheduling ops (these should operate on the events dict + return new overrides)
def _snap_ms(ms: int, snap_min: int) -> int:
    if snap_min <= 1:
        return int(ms)
    snap_ms = int(snap_min) * 60000
    return int(round(ms / snap_ms) * snap_ms)


def _group_by_day(
    uuids: list[str],
    events: dict[str, tuple[int, int, int]],
    *,
    tz_name: str | None = "UTC",
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    try:
        tzinfo = resolve_tz(normalize_tz_name(tz_name))
    except ValueError:
        tzinfo = dt.timezone.utc

    for u in uuids:
        ev = events.get(u)
        if not ev:
            continue
        start_ms, due_ms, _dur = ev
        day = day_key_from_ms(start_ms, tzinfo) or day_key_from_ms(due_ms, tzinfo)
        if not day:
            day = dt.datetime.utcfromtimestamp(int(start_ms) / 1000.0).date().isoformat()
        groups.setdefault(day, []).append(u)
    return groups


def op_align_starts(
    uuids: list[str],
    events: dict[str, tuple[int, int, int]],
    snap_min: int,
    tz_name: str | None = "UTC",
) -> dict[str, PlanOverride]:
    out: dict[str, PlanOverride] = {}
    groups = _group_by_day(uuids, events, tz_name=tz_name)
    for _day, arr in groups.items():
        if len(arr) < 2:
            continue
        ref = min((events[u][0], u) for u in arr if u in events)[1]
        target_start = events[ref][0]
        target_start = _snap_ms(target_start, snap_min)
        for u in arr:
            _start_ms, _due_ms, dur_min = events[u]
            new_start = target_start
            new_due = new_start + int(dur_min) * 60000
            out[u] = PlanOverride(start_ms=new_start, due_ms=new_due, duration_min=int(dur_min))
    return out


def op_align_ends(
    uuids: list[str],
    events: dict[str, tuple[int, int, int]],
    snap_min: int,
    tz_name: str | None = "UTC",
) -> dict[str, PlanOverride]:
    out: dict[str, PlanOverride] = {}
    groups = _group_by_day(uuids, events, tz_name=tz_name)
    for _day, arr in groups.items():
        if len(arr) < 2:
            continue
        ref = max((events[u][1], u) for u in arr if u in events)[1]
        target_due = events[ref][1]
        target_due = _snap_ms(target_due, snap_min)
        for u in arr:
            _start_ms, _due_ms, dur_min = events[u]
            new_due = target_due
            new_start = new_due - int(dur_min) * 60000
            out[u] = PlanOverride(start_ms=new_start, due_ms=new_due, duration_min=int(dur_min))
    return out


def op_stack(
    uuids: list[str],
    events: dict[str, tuple[int, int, int]],
    snap_min: int,
    tz_name: str | None = "UTC",
) -> dict[str, PlanOverride]:
    out: dict[str, PlanOverride] = {}
    groups = _group_by_day(uuids, events, tz_name=tz_name)
    for _day, arr in groups.items():
        items = [(u, events[u]) for u in arr if u in events]
        if len(items) < 2:
            continue
        items.sort(key=lambda x: x[1][0])
        cursor = _snap_ms(items[0][1][0], snap_min)
        for u, ev in items:
            _start_ms, _due_ms, dur_min = ev
            new_start = cursor
            new_due = new_start + int(dur_min) * 60000
            out[u] = PlanOverride(start_ms=new_start, due_ms=new_due, duration_min=int(dur_min))
            cursor = new_due
    return out


def op_distribute(
    uuids: list[str],
    events: dict[str, tuple[int, int, int]],
    snap_min: int,
    tz_name: str | None = "UTC",
) -> dict[str, PlanOverride]:
    out: dict[str, PlanOverride] = {}
    groups = _group_by_day(uuids, events, tz_name=tz_name)
    for _day, arr in groups.items():
        items = [(u, events[u]) for u in arr if u in events]
        if len(items) < 3:
            continue
        items.sort(key=lambda x: x[1][0])
        min_start = items[0][1][0]
        max_end = max(ev[1] for _, ev in items)
        total_dur = sum(int(ev[2]) * 60000 for _, ev in items)
        window = max_end - min_start
        gap = 0
        if len(items) > 1:
            gap = int((window - total_dur) // (len(items) - 1))
            if gap < 0:
                gap = 0
        cursor = _snap_ms(min_start, snap_min)
        for u, ev in items:
            dur_ms = int(ev[2]) * 60000
            new_start = cursor
            new_due = new_start + dur_ms
            out[u] = PlanOverride(start_ms=new_start, due_ms=new_due, duration_min=int(ev[2]))
            cursor = new_due + gap
    return out


def op_nudge(uuids: list[str], events: dict[str, tuple[int, int, int]], delta_min: int) -> dict[str, PlanOverride]:
    out: dict[str, PlanOverride] = {}
    if not delta_min:
        return out
    delta_ms = int(delta_min) * 60000
    for u in uuids:
        ev = events.get(u)
        if not ev:
            continue
        start_ms, due_ms, dur_min = ev
        new_start = start_ms + delta_ms
        new_due = due_ms + delta_ms
        out[u] = PlanOverride(start_ms=new_start, due_ms=new_due, duration_min=int(dur_min))
    return out
