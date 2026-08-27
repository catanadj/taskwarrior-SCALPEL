from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Sequence, cast

from .ai import PlanOverride, apply_plan_overrides
from .goals import load_goals_config
from .interval import infer_interval_ms
from .model import CalendarConfig, Payload, RawTask, Task
from .normalize import normalize_task
from .process import CommandFailedError, CommandNotFoundError, CommandTimeoutError, run_checked
from .schema_v1 import apply_schema_v1
from .taskwarrior import parse_tw_utc_to_epoch_ms, run_task_export
from .util.console import eprint
from .util.timeparse import midnight_epoch_ms
from .util.tz import normalize_tz_name
from .util.viewkey import make_view_key


def _nautical_hooks_enabled(enabled: bool | None = None) -> bool:
    if enabled is not None:
        return bool(enabled)
    raw = os.getenv("SCALPEL_ENABLE_NAUTICAL_HOOKS")
    if raw is None:
        return True
    v = (raw or "").strip().lower()
    if v in {"0", "false", "no", "off"}:
        return False
    if v in {"1", "true", "yes", "on"}:
        return True
    return True


def _raw_tasks_may_need_nautical(raw_tasks: Sequence[RawTask]) -> bool:
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            continue
        for key in ("anchor", "cp", "chain", "chainID", "chainId", "chainid"):
            v = raw.get(key)
            if isinstance(v, str) and v.strip():
                return True
    return False


def _warn_nautical_disabled_if_needed(raw_tasks: Sequence[RawTask], *, enabled: bool) -> None:
    if enabled:
        return
    if not _raw_tasks_may_need_nautical(raw_tasks):
        return
    eprint(
        "[scalpel] INFO: nautical preview hooks are disabled. "
        "Remove --no-nautical-hooks (or set SCALPEL_ENABLE_NAUTICAL_HOOKS=1) to enable nautical anchor/cp preview tasks."
    )


def _nautical_query_command() -> list[str] | None:
    command = shutil.which("nautical")
    if command:
        return [command, "query"]
    for path in (Path.home() / ".task" / "nautical", Path.home() / ".task" / "hooks" / "nautical"):
        if path.is_file() and os.access(path, os.X_OK):
            return [str(path), "query"]
    return None


def _query_nautical_occurrences(*, start_date: dt.date, end_date: dt.date) -> dict[str, list[dict[str, Any]]]:
    command = _nautical_query_command()
    if command is None:
        return {}
    argv = command + [
        "occurrences",
        "--all",
        "--from",
        start_date.isoformat(),
        "--to",
        end_date.isoformat(),
        "--omissions",
        "exclude",
    ]
    try:
        result = run_checked(argv, timeout_s=30.0)
        document = json.loads(result.stdout)
    except (CommandNotFoundError, CommandTimeoutError, CommandFailedError, json.JSONDecodeError, OSError) as exc:
        eprint(f"[scalpel] WARN: Nautical query unavailable: {exc}")
        return {}
    if not isinstance(document, dict) or document.get("status") in {"invalid", "unavailable"}:
        failure = document.get("failure") if isinstance(document, dict) else None
        detail = failure.get("message") if isinstance(failure, dict) else "invalid response"
        eprint(f"[scalpel] WARN: Nautical query unavailable: {detail}")
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for item in document.get("results", []):
        if not isinstance(item, dict):
            continue
        task = item.get("task")
        uuid = task.get("uuid") if isinstance(task, dict) else None
        occurrences = item.get("occurrences")
        if isinstance(uuid, str) and isinstance(occurrences, list):
            out[uuid] = [x for x in occurrences if isinstance(x, dict)]
    return out


def _apply_interval_fields(
    task_out: Task,
    *,
    default_duration_min: int,
    max_infer_duration_min: int,
) -> None:
    iv = infer_interval_ms(
        due_ms=task_out.get("due_ms"),
        scheduled_ms=task_out.get("scheduled_ms"),
        duration_min=task_out.get("duration_min"),
        default_duration_min=int(default_duration_min),
        max_infer_duration_min=int(max_infer_duration_min),
    )
    if iv is None:
        return
    task_out.update(
        {
            "start_calc_ms": iv.start_ms,
            "end_calc_ms": iv.end_ms,
            "dur_calc_min": iv.duration_min,
            "dur_src": iv.duration_src,
            "place_src": iv.placement_src,
            "interval_ok": iv.ok,
            "interval_warn": iv.warning,
        }
    )


def _task_identity(raw: RawTask) -> str:
    return str(raw.get("uuid") or raw.get("id") or "").strip()


def _completed_filter_for(filter_str: str) -> str | None:
    """Return a conservative completed-task companion filter.

    The default interactive filter is `status:pending`; in that common case we
    can safely fetch completed tasks with `status:completed`. Arbitrary
    Taskwarrior filter rewrites are intentionally avoided because their boolean
    semantics are easy to break.
    """

    if filter_str.strip() == "status:pending":
        return "status:completed"
    return None


def _export_tasks_for_view(filter_str: str, *, show_completed: bool) -> list[RawTask]:
    raw_tasks = run_task_export(filter_str)
    if not show_completed:
        return raw_tasks

    completed_filter = _completed_filter_for(filter_str)
    if not completed_filter:
        return raw_tasks

    seen = {_task_identity(t) for t in raw_tasks if isinstance(t, dict)}
    for task in run_task_export(completed_filter):
        if not isinstance(task, dict):
            continue
        ident = _task_identity(task)
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        raw_tasks.append(task)
    return raw_tasks


def _build_nautical_preview_tasks(
    *,
    base_tasks: Sequence[Task],
    raw_tasks: Sequence[RawTask],
    start_date: dt.date,
    days: int,
    tz_name: str,
    default_duration_min: int,
    max_infer_duration_min: int,
    nautical_hooks_enabled: bool,
) -> list[Task]:
    """Build previews through Nautical's versioned public query boundary."""
    if not nautical_hooks_enabled or not _raw_tasks_may_need_nautical(raw_tasks):
        return []
    if not any(
        str(task.get("status") or raw.get("status") or "").strip().lower() != "completed"
        for task, raw in zip(base_tasks, raw_tasks, strict=False)
    ):
        return []
    occurrence_map = _query_nautical_occurrences(
        start_date=start_date,
        end_date=start_date + dt.timedelta(days=max(1, int(days)) - 1),
    )
    if not occurrence_map:
        return []

    out: list[Task] = []
    for task_out, raw in zip(base_tasks, raw_tasks, strict=False):
        if str(task_out.get("status") or raw.get("status") or "").strip().lower() == "completed":
            continue
        source_uuid = str(task_out.get("uuid") or "").strip()
        if not source_uuid:
            continue
        anchor_expr = str(raw.get("anchor") or "").strip()
        cp_expr = str(raw.get("cp") or "").strip()
        for index, occurrence in enumerate(occurrence_map.get(source_uuid, [])):
            utc_value = occurrence.get("utc")
            due_ms = parse_tw_utc_to_epoch_ms(str(utc_value or ""))
            if not isinstance(due_ms, int):
                continue
            source = str(occurrence.get("source") or "").strip().lower()
            kind = "anchor" if "anchor" in source or (anchor_expr and not cp_expr) else "cp"
            if kind == "anchor" and not anchor_expr:
                kind = "cp"
            if kind == "cp" and not cp_expr:
                kind = "anchor"
            preview = cast(Task, dict(task_out))
            preview.update(
                {
                    "uuid": f"nautical-{kind}-{source_uuid}-{due_ms}-i{index}",
                    "id": None,
                    "nautical_preview": True,
                    "nautical_kind": kind,
                    "nautical_source_uuid": source_uuid,
                    "nautical_anchor": anchor_expr,
                    "nautical_anchor_mode": str(raw.get("anchor_mode") or "").strip() or None,
                    "nautical_cp": cp_expr,
                    "nautical_link": 0,
                    "scheduled_ms": None,
                    "due_ms": due_ms,
                }
            )
            _apply_interval_fields(
                preview,
                default_duration_min=default_duration_min,
                max_infer_duration_min=max_infer_duration_min,
            )
            out.append(preview)
    return out


def build_payload(
    *,
    filter_str: str,
    start_date: dt.date,
    days: int,
    work_start: int,
    work_end: int,
    snap: int,
    default_duration_min: int,
    max_infer_duration_min: int,
    px_per_min: float,
    goals_path: str,
    tz: Optional[str] = None,
    display_tz: Optional[str] = None,
    plan_overrides: Optional[dict[str, PlanOverride]] = None,
    nautical_hooks_enabled: Optional[bool] = None,
    show_completed: bool = False,
) -> Payload:
    """Build a SCALPEL payload from Taskwarrior export.

    Timezone contract:
      - All timestamps are stored as UTC epoch milliseconds.
      - `cfg.tz` defines *day boundaries* (bucketing; `day_key`, `indices.by_day`, `view_start_ms`).
      - `cfg.display_tz` is a display hint (default: "local").

    Default policy for interactive use:
      - tz='local' and display_tz='local'

    Deterministic fixtures/CI should pass tz='UTC'.
    """

    tz_name = normalize_tz_name(tz)
    display_tz_name = normalize_tz_name(display_tz)

    raw_tasks = _export_tasks_for_view(filter_str, show_completed=bool(show_completed))
    nautical_enabled = _nautical_hooks_enabled(nautical_hooks_enabled)
    _warn_nautical_disabled_if_needed(raw_tasks, enabled=nautical_enabled)

    tasks: list[Task] = []
    preview_pairs: list[tuple[Task, RawTask]] = []
    for t in raw_tasks:
        nt = normalize_task(t)
        if not nt:
            continue

        task_out: Task = {
            "uuid": nt.uuid,
            "id": nt.id,
            "description": nt.description,
            "status": nt.status,
            "project": nt.project,
            "tags": list(nt.tags),
            "priority": nt.priority,
            "urgency": nt.urgency,
            "scheduled_ms": nt.scheduled_ms,
            "due_ms": nt.due_ms,
            "end_ms": nt.end_ms,
            "duration": nt.duration_raw,
            "duration_min": nt.duration_min,
        }
        for uda_key in ("anchor", "cp"):
            uda_val = t.get(uda_key)
            if isinstance(uda_val, str) and uda_val.strip():
                task_out[uda_key] = uda_val.strip()
        if nt.status == "completed" and isinstance(nt.end_ms, int):
            task_out["completed_end_ms"] = nt.end_ms
            task_out["original_due_ms"] = nt.due_ms
            task_out["due_ms"] = nt.end_ms

        _apply_interval_fields(
            task_out,
            default_duration_min=default_duration_min,
            max_infer_duration_min=max_infer_duration_min,
        )

        tasks.append(task_out)
        preview_pairs.append((task_out, t))

    preview_tasks = _build_nautical_preview_tasks(
        base_tasks=[p[0] for p in preview_pairs],
        raw_tasks=[p[1] for p in preview_pairs],
        start_date=start_date,
        days=int(days),
        tz_name=tz_name,
        default_duration_min=int(default_duration_min),
        max_infer_duration_min=int(max_infer_duration_min),
        nautical_hooks_enabled=nautical_enabled,
    )
    if preview_tasks:
        tasks.extend(preview_tasks)

    view_start_ms = midnight_epoch_ms(start_date, tz=tz_name)

    cfg: CalendarConfig = {
        "tz": tz_name,
        "display_tz": display_tz_name,
        "days": int(days),
        "work_start_min": int(work_start),
        "work_end_min": int(work_end),
        "snap_min": int(snap),
        "default_duration_min": int(default_duration_min),
        "max_infer_duration_min": int(max_infer_duration_min),
        "px_per_min": float(px_per_min),
        "view_start_ms": int(view_start_ms),
        "view_key": make_view_key(
            filter_str,
            start_date,
            days,
            work_start,
            work_end,
            snap,
            tz=tz_name,
            display_tz=display_tz_name,
        ),
        "show_completed": bool(show_completed),
    }

    goals_cfg = load_goals_config(goals_path)

    payload: Payload = {"cfg": cfg, "tasks": tasks, "goals": goals_cfg}
    if plan_overrides:
        payload = apply_plan_overrides(payload, plan_overrides, normalize=False)

    # v2 is applied by callers/tools via scalpel.schema.upgrade_payload.
    return cast(Payload, apply_schema_v1(payload))
