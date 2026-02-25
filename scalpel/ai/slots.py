"""Candidate slot generation for AI planning.

Design goals:
  - Avoid time algebra in the model: the engine enumerates feasible slots.
  - Use cfg.tz for ISO readability; store ms in slot_catalog for application.
  - Keep output bounded (prompt-friendly) and deterministic.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from scalpel.interval import infer_interval_ms
from scalpel.util.tz import normalize_tz_name, midnight_epoch_ms, resolve_tz


MIN_MS = 60_000


@dataclass(frozen=True)
class Slot:
    slot_id: str
    start_ms: int
    due_ms: int
    start_iso: str
    due_iso: str
    day_key: str


def _base36(n: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    sign = ""
    if n < 0:
        sign = "-"
        n = -n
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(alphabet[r])
    return sign + "".join(reversed(out))


def _slot_id_for_start(start_ms: int) -> str:
    # Compact, stable, globally unique enough for our horizon.
    return f"S{_base36(int(start_ms))}"


def _iso_min(ms: int, tz: dt.tzinfo) -> str:
    d = dt.datetime.fromtimestamp(ms / 1000.0, tz=tz).replace(second=0, microsecond=0)
    # Include offset; local models handle this well.
    return d.isoformat(timespec="minutes")


def _iter_tasks(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        for t in tasks:
            if isinstance(t, dict):
                yield t


def _effective_interval_ms(t: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[Tuple[int, int, int]]:
    """Return (start_ms, end_ms, dur_min) or None."""

    s = t.get("start_calc_ms")
    e = t.get("end_calc_ms")
    if isinstance(s, int) and isinstance(e, int) and e > s:
        dur = t.get("dur_calc_min")
        if not isinstance(dur, int) or dur <= 0:
            dur = max(1, int((e - s) // MIN_MS))
        return int(s), int(e), int(dur)

    due_ms = t.get("due_ms")
    scheduled_ms = t.get("scheduled_ms")
    duration_min = t.get("duration_min")
    default_dur = int(cfg.get("default_duration_min") or 30)
    max_infer = int(cfg.get("max_infer_duration_min") or 240)

    iv = infer_interval_ms(
        due_ms=due_ms if isinstance(due_ms, int) else None,
        scheduled_ms=scheduled_ms if isinstance(scheduled_ms, int) else None,
        duration_min=duration_min if isinstance(duration_min, int) else None,
        default_duration_min=default_dur,
        max_infer_duration_min=max_infer,
    )
    if iv is None or not iv.ok:
        return None
    return int(iv.start_ms), int(iv.end_ms), int(iv.duration_min)


def _union_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    out: List[Tuple[int, int]] = []
    cur_s, cur_e = intervals[0]
    for s, e in intervals[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            out.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    out.append((cur_s, cur_e))
    return out


def _subtract(base: Tuple[int, int], blocks: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Subtract unioned blocks from base and return list of free intervals."""
    a, b = base
    if a >= b:
        return []
    out: List[Tuple[int, int]] = []
    cur = a
    for s, e in blocks:
        if e <= cur:
            continue
        if s >= b:
            break
        if s > cur:
            out.append((cur, min(s, b)))
        cur = max(cur, e)
        if cur >= b:
            break
    if cur < b:
        out.append((cur, b))
    return [(s, e) for s, e in out if e > s]


def _ceil_to_snap(ms: int, snap_ms: int) -> int:
    if snap_ms <= 0:
        return ms
    r = ms % snap_ms
    if r == 0:
        return ms
    return ms + (snap_ms - r)


def build_candidate_slots(
    payload: Dict[str, Any],
    selected_uuids: List[str],
    *,
    max_slots_per_task: int = 24,
    max_days_scan: Optional[int] = None,
) -> Tuple[Dict[str, List[Slot]], Dict[str, Dict[str, int]]]:
    """Return (candidates_by_uuid, slot_catalog).

    slot_catalog maps slot_id -> {start_ms, due_ms}.
    """

    cfg = payload.get("cfg") if isinstance(payload.get("cfg"), dict) else {}
    tz_name = normalize_tz_name(cfg.get("tz") if isinstance(cfg.get("tz"), str) else "local")
    tz = resolve_tz(tz_name)

    view_start_ms = cfg.get("view_start_ms")
    days = int(cfg.get("days") or 7)
    if not isinstance(view_start_ms, int):
        # Best-effort: base on today in tz.
        today = dt.datetime.now(tz=tz).date()
        view_start_ms = midnight_epoch_ms(today, tz)

    if max_days_scan is not None:
        days = min(days, int(max_days_scan))

    horizon_start_ms = int(view_start_ms)
    # Compute per-day using midnight_epoch_ms to handle DST.
    start_date = dt.datetime.fromtimestamp(horizon_start_ms / 1000.0, tz=tz).date()
    dates = [start_date + dt.timedelta(days=i) for i in range(max(1, days))]

    work_start_min = int(cfg.get("work_start_min") or 0)
    work_end_min = int(cfg.get("work_end_min") or 24 * 60)
    snap_min = int(cfg.get("snap_min") or 10)
    snap_ms = max(1, snap_min) * MIN_MS

    sel = set(u for u in selected_uuids if isinstance(u, str) and u)

    # Build busy intervals (exclude selected tasks so they can move).
    busy: List[Tuple[int, int]] = []
    for t in _iter_tasks(payload):
        u = t.get("uuid")
        if not isinstance(u, str) or not u:
            continue
        if u in sel:
            continue
        st = str(t.get("status") or "pending").lower()
        if st in {"completed", "deleted"}:
            continue
        iv = _effective_interval_ms(t, cfg)
        if iv is None:
            continue
        s, e, _ = iv
        if e <= horizon_start_ms:
            continue
        # coarse horizon end: last day end
        # (we don't need exact; filter later when intersecting day windows)
        busy.append((s, e))
    busy_u = _union_intervals(busy)

    # Build free intervals for each day within work hours.
    free_by_day: Dict[str, List[Tuple[int, int]]] = {}
    for d in dates:
        day0 = midnight_epoch_ms(d, tz)
        w0 = day0 + work_start_min * MIN_MS
        w1 = day0 + work_end_min * MIN_MS
        if w1 <= w0:
            continue

        # Intersect busy blocks with this work window.
        blocks = []
        for s, e in busy_u:
            if e <= w0:
                continue
            if s >= w1:
                break
            blocks.append((max(s, w0), min(e, w1)))
        blocks = _union_intervals(blocks)
        free = _subtract((w0, w1), blocks)
        free_by_day[d.isoformat()] = free

    # Determine effective duration for each selected task.
    dur_by_uuid: Dict[str, int] = {}
    by_uuid = payload.get("indices", {}).get("by_uuid") if isinstance(payload.get("indices"), dict) else None
    if isinstance(by_uuid, dict):
        for u in sel:
            idx = by_uuid.get(u)
            if isinstance(idx, int):
                tasks = payload.get("tasks")
                if isinstance(tasks, list) and 0 <= idx < len(tasks) and isinstance(tasks[idx], dict):
                    iv = _effective_interval_ms(tasks[idx], cfg)
                    if iv is not None:
                        dur_by_uuid[u] = int(iv[2])
    # Fallback if indices missing.
    if not dur_by_uuid:
        for t in _iter_tasks(payload):
            u = t.get("uuid")
            if u in sel:
                iv = _effective_interval_ms(t, cfg)
                if iv is not None:
                    dur_by_uuid[u] = int(iv[2])

    candidates: Dict[str, List[Slot]] = {u: [] for u in selected_uuids if u in sel}
    slot_catalog: Dict[str, Dict[str, int]] = {}

    for u in selected_uuids:
        if u not in sel:
            continue
        dur_min = int(dur_by_uuid.get(u) or int(cfg.get("default_duration_min") or 30))
        dur_ms = max(1, dur_min) * MIN_MS
        out_slots: List[Slot] = []

        for day_key, free_list in free_by_day.items():
            for a, b in free_list:
                s = _ceil_to_snap(a, snap_ms)
                while s + dur_ms <= b:
                    e = s + dur_ms
                    sid = _slot_id_for_start(s)
                    if sid not in slot_catalog:
                        slot_catalog[sid] = {"start_ms": int(s), "due_ms": int(e)}
                    out_slots.append(
                        Slot(
                            slot_id=sid,
                            start_ms=int(s),
                            due_ms=int(e),
                            start_iso=_iso_min(int(s), tz),
                            due_iso=_iso_min(int(e), tz),
                            day_key=day_key,
                        )
                    )
                    if len(out_slots) >= max_slots_per_task:
                        break
                    s += snap_ms
                if len(out_slots) >= max_slots_per_task:
                    break
            if len(out_slots) >= max_slots_per_task:
                break
        candidates[u] = out_slots

    return candidates, slot_catalog
