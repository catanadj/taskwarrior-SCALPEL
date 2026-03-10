from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any, Callable

from .process import CommandFailedError, CommandNotFoundError, CommandTimeoutError, run_checked
from .serve import TaskExportLookupResult, TimewExportResult, TimewInterval
from .util.timeparse import parse_date_yyyy_mm_dd
from .util.tz import normalize_tz_name, resolve_tz

RunProcFn = Callable[..., Any]
ParseUtcFn = Callable[[str], int | None]
TaskExportFn = Callable[[str], list[dict[str, Any]]]

_YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UUID_QUERY_RE = re.compile(r"^[0-9A-Fa-f][0-9A-Fa-f-]{7,35}$")


def _timew_timeout_s() -> float:
    raw = (os.getenv("SCALPEL_TIMEW_TIMEOUT_S", "25") or "").strip()
    try:
        v = float(raw)
        if v > 0:
            return v
    except Exception:
        pass
    return 25.0


def _day_window_utc_ms(day_ymd: str, tz_name: str) -> tuple[int, int]:
    if not _YMD_RE.match(str(day_ymd or "")):
        raise ValueError("day must be YYYY-MM-DD")
    d = parse_date_yyyy_mm_dd(day_ymd)
    tzinfo = resolve_tz(normalize_tz_name(tz_name))
    local_start = dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tzinfo)
    local_end = local_start + dt.timedelta(days=1)
    start_ms = int(local_start.astimezone(dt.timezone.utc).timestamp() * 1000)
    end_ms = int(local_end.astimezone(dt.timezone.utc).timestamp() * 1000)
    return start_ms, end_ms


def run_timew_export_for_day(
    *,
    day_ymd: str,
    tz_name: str,
    run_proc: RunProcFn,
    parse_utc: ParseUtcFn,
) -> TimewExportResult:
    start_ms, end_ms = _day_window_utc_ms(day_ymd, tz_name)
    cmd = ["timew", day_ymd, "export"]

    try:
        result = run_checked(
            cmd,
            timeout_s=_timew_timeout_s(),
            run_proc=run_proc,
        )
    except CommandNotFoundError:
        raise SystemExit("Timewarrior binary 'timew' not found on PATH.")
    except CommandTimeoutError:
        raise SystemExit("Timewarrior export timed out.")
    except CommandFailedError as ex:
        err = ex.result.combined_output.strip()
        msg = f"Timewarrior export failed (exit {ex.result.returncode})."
        if err:
            msg = f"{msg} {err}"
        raise SystemExit(msg)

    text = result.stdout.strip()
    if not text:
        return {"day": day_ymd, "intervals": []}

    try:
        raw = json.loads(text)
    except Exception as e:
        raise SystemExit(f"Failed to parse `timew export` JSON: {e}")
    if not isinstance(raw, list):
        raise SystemExit("`timew export` did not return a JSON list.")

    out: list[TimewInterval] = []
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    for it in raw:
        if not isinstance(it, dict):
            continue
        s_ms = parse_utc(str(it.get("start") or ""))
        e_ms = parse_utc(str(it.get("end") or ""))
        if not isinstance(s_ms, int):
            continue
        if not isinstance(e_ms, int):
            e_ms = now_ms
        if e_ms <= s_ms:
            continue

        s_ms = max(s_ms, start_ms)
        e_ms = min(e_ms, end_ms)
        if e_ms <= s_ms:
            continue

        tags = it.get("tags")
        tags_out: list[str] = []
        if isinstance(tags, list):
            for t in tags:
                ts = str(t or "").strip()
                if ts:
                    tags_out.append(ts)
        annotation = str(it.get("annotation") or "").strip()
        out.append(
            {
                "start_ms": s_ms,
                "end_ms": e_ms,
                "tags": tags_out,
                "annotation": annotation,
            }
        )

    out.sort(key=lambda x: (int(x.get("start_ms") or 0), int(x.get("end_ms") or 0)))
    return {"day": day_ymd, "intervals": out}


def run_task_export_for_uuid(
    uuid_query: str,
    *,
    run_export: TaskExportFn,
) -> TaskExportLookupResult:
    uq = str(uuid_query or "").strip()
    if not _UUID_QUERY_RE.match(uq):
        raise ValueError("Query param 'uuid' must be 8-36 hex/hyphen characters.")

    tasks = run_export(f"uuid:{uq}")
    if not tasks:
        return {"task": None, "matched": 0, "exact": False}

    uq_l = uq.lower()
    exact = [t for t in tasks if isinstance(t, dict) and str(t.get("uuid") or "").lower() == uq_l]
    if exact:
        return {"task": exact[0], "matched": len(tasks), "exact": True}
    if len(tasks) == 1 and isinstance(tasks[0], dict):
        return {"task": tasks[0], "matched": 1, "exact": False}
    raise SystemExit(f"Task query '{uq}' matched {len(tasks)} tasks; provide full UUID.")
