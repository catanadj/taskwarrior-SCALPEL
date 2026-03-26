from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence, cast

from .goals import load_goals_config
from .model import CalendarConfig, Payload, RawTask, Task
from .taskwarrior import run_task_export, parse_tw_utc_to_epoch_ms
from .util.timeparse import midnight_epoch_ms
from .util.tz import normalize_tz_name, resolve_tz
from .util.viewkey import make_view_key
from .normalize import normalize_task
from .interval import infer_interval_ms
from .schema_v1 import apply_schema_v1
from .ai import PlanOverride, apply_plan_overrides
from .util.console import eprint


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


def _load_nautical_core(*, enabled: bool) -> Any | None:
    if not enabled:
        return None

    candidates: list[tuple[str, Path]] = []
    for base in (Path.home() / ".task", Path.home() / ".task" / "hooks"):
        candidates.append(("package", base / "nautical_core" / "__init__.py"))
        candidates.append(("module", base / "nautical_core.py"))

    for kind, path in candidates:
        if not path.is_file():
            continue
        if kind == "package":
            eprint(f"[scalpel] INFO: loading nautical_core package from {path.parent}")
            try:
                spec = importlib.util.spec_from_file_location(
                    "nautical_core",
                    str(path),
                    submodule_search_locations=[str(path.parent)],
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["nautical_core"] = mod
                    spec.loader.exec_module(mod)
                    return mod
            except Exception as ex:
                sys.modules.pop("nautical_core", None)
                eprint(f"[scalpel] WARN: failed loading nautical_core package from {path.parent}: {ex}")
            continue
        eprint(f"[scalpel] INFO: loading nautical_core from {path}")
        try:
            spec = importlib.util.spec_from_file_location("nautical_core", str(path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["nautical_core"] = mod
                spec.loader.exec_module(mod)
                return mod
        except Exception as ex:
            sys.modules.pop("nautical_core", None)
            eprint(f"[scalpel] WARN: failed loading nautical_core from {path}: {ex}")

    try:
        return importlib.import_module("nautical_core")
    except Exception:
        pass
    return None


def _parse_hhmm_str(s: str) -> tuple[int, int] | None:
    try:
        hh_s, mm_s = s.split(":", 1)
        hh = int(hh_s)
        mm = int(mm_s)
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return (hh, mm)
    except Exception:
        return None
    return None


def _local_hhmm_from_ms(ms: int | None, tzinfo: dt.tzinfo) -> tuple[int, int] | None:
    if not isinstance(ms, int):
        return None
    try:
        d = dt.datetime.fromtimestamp(ms / 1000.0, tz=tzinfo)
        return (d.hour, d.minute)
    except Exception:
        return None


def _cp_next_due_ms(
    *,
    base_end_ms: Optional[int],
    base_due_ms: Optional[int],
    td: dt.timedelta,
    tzinfo: dt.tzinfo,
) -> int | None:
    base_ms = base_end_ms if isinstance(base_end_ms, int) else base_due_ms
    if not isinstance(base_ms, int):
        return None

    base_dt = dt.datetime.fromtimestamp(base_ms / 1000.0, tz=dt.timezone.utc)
    cand = (base_dt + td).replace(microsecond=0)
    td_secs = int(td.total_seconds())
    if td_secs % 86400 != 0:
        return int(cand.timestamp() * 1000)

    src_ms = base_due_ms if isinstance(base_due_ms, int) else base_ms
    src_local = dt.datetime.fromtimestamp(src_ms / 1000.0, tz=tzinfo)
    cand_local = cand.astimezone(tzinfo)
    due_local = cand_local.replace(hour=src_local.hour, minute=src_local.minute, second=0, microsecond=0)
    return int(due_local.astimezone(dt.timezone.utc).timestamp() * 1000)


def _anchor_times_for_date(nautical: Any, dnf: Any, target: dt.date, seed_date: dt.date) -> list[str]:
    times: list[str] = []
    seen = set()
    for term in dnf:
        try:
            if not all(nautical.atom_matches_on(a, target, seed_date) for a in term):
                continue
        except Exception:
            continue
        for a in term:
            mods = a.get("mods") or {}
            tval = mods.get("t")
            if not tval:
                continue
            vals: list[str] = []
            if isinstance(tval, tuple) and len(tval) == 2:
                vals = [f"{int(tval[0]):02d}:{int(tval[1]):02d}"]
            elif isinstance(tval, list):
                for x in tval:
                    if isinstance(x, tuple) and len(x) == 2:
                        vals.append(f"{int(x[0]):02d}:{int(x[1]):02d}")
                    else:
                        vals.append(str(x))
            else:
                vals = [str(tval)]
            for v in vals:
                if v and v not in seen:
                    seen.add(v)
                    times.append(v)
    return times


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
    if not _raw_tasks_may_need_nautical(raw_tasks):
        return []

    nautical = _load_nautical_core(enabled=nautical_hooks_enabled)
    if not nautical:
        return []

    tzinfo = resolve_tz(tz_name)
    start_excl = start_date - dt.timedelta(days=1)
    end_excl = start_date + dt.timedelta(days=max(1, int(days)))
    out: list[Task] = []

    for task_out, raw in zip(base_tasks, raw_tasks):
        anchor_expr = str(raw.get("anchor") or "").strip()

        anchor_mode = str(raw.get("anchor_mode") or "").strip()

        if anchor_expr:
            try:
                dnf = nautical.validate_anchor_expr_strict(anchor_expr)
            except Exception:
                dnf = None

            if dnf:
                seed_ms = task_out.get("due_ms") if isinstance(task_out.get("due_ms"), int) else None
                if seed_ms is None:
                    seed_ms = task_out.get("scheduled_ms") if isinstance(task_out.get("scheduled_ms"), int) else None

                seed_date = (
                    dt.datetime.fromtimestamp(seed_ms / 1000.0, tz=tzinfo).date()
                    if isinstance(seed_ms, int)
                    else start_date
                )

                chain_id = raw.get("chainID") or raw.get("chainId") or raw.get("chainid") or ""
                seed_base = f"preview:{chain_id or task_out.get('uuid')}"

                dates = nautical.anchors_between_expr(
                    dnf,
                    start_excl,
                    end_excl,
                    default_seed=seed_date,
                    seed_base=seed_base,
                )

                for d in dates:
                    source_uuid = str(task_out.get("uuid") or "").strip()
                    if not source_uuid:
                        continue
                    times = _anchor_times_for_date(nautical, dnf, d, seed_date)
                    if not times:
                        hhmm = nautical.pick_hhmm_from_dnf_for_date(dnf, d, seed_date)
                        if hhmm:
                            times = [hhmm]

                    hm_fallback = _local_hhmm_from_ms(seed_ms, tzinfo)
                    if hm_fallback is None:
                        hm_fallback = (int(getattr(nautical, "DEFAULT_DUE_HOUR", 11)), 0)

                    if not times:
                        times = [f"{hm_fallback[0]:02d}:{hm_fallback[1]:02d}"]

                    for tstr in times:
                        hm = _parse_hhmm_str(tstr)
                        if hm is None:
                            hm = hm_fallback

                        due_dt = dt.datetime(d.year, d.month, d.day, hm[0], hm[1], 0, tzinfo=tzinfo)
                        due_ms = int(due_dt.timestamp() * 1000)
                        if isinstance(seed_ms, int) and due_ms == seed_ms:
                            continue

                        preview_uuid = f"nautical-{source_uuid}-{d.isoformat()}-t{hm[0]:02d}{hm[1]:02d}"

                        preview = cast(Task, dict(task_out))
                        preview.update(
                            {
                                "uuid": preview_uuid,
                                "id": None,
                                "nautical_preview": True,
                                "nautical_kind": "anchor",
                                "nautical_source_uuid": source_uuid,
                                "nautical_anchor": anchor_expr,
                                "nautical_anchor_mode": anchor_mode or None,
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

        cp_str = str(raw.get("cp") or "").strip()
        if cp_str:
            source_uuid = str(task_out.get("uuid") or "").strip()
            if not source_uuid:
                continue
            chain_val = str(raw.get("chain") or "").strip().lower()
            if chain_val in {"off", "0", "false", "no"}:
                continue

            td = nautical.parse_cp_duration(cp_str)
            if not td:
                continue

            chain_max = nautical.coerce_int(raw.get("chainMax"), 0)
            link_no = nautical.coerce_int(raw.get("link"), 1)
            if chain_max and link_no >= chain_max:
                continue

            until_dt = nautical.parse_dt_any(str(raw.get("chainUntil") or "").strip())

            due_ms_val = task_out.get("due_ms") if isinstance(task_out.get("due_ms"), int) else None
            if due_ms_val is None:
                due_ms_val = task_out.get("scheduled_ms") if isinstance(task_out.get("scheduled_ms"), int) else None

            end_ms = parse_tw_utc_to_epoch_ms(str(raw.get("end") or ""))
            base_end_ms = end_ms if isinstance(end_ms, int) else due_ms_val
            base_due_ms = due_ms_val
            if not isinstance(base_end_ms, int):
                continue

            next_link = link_no + 1
            guard = 0
            while guard < 200:
                guard += 1
                if chain_max and next_link > chain_max:
                    break

                next_due_ms = _cp_next_due_ms(
                    base_end_ms=base_end_ms,
                    base_due_ms=base_due_ms,
                    td=td,
                    tzinfo=tzinfo,
                )
                if not isinstance(next_due_ms, int):
                    break

                if isinstance(until_dt, dt.datetime):
                    if next_due_ms > int(until_dt.timestamp() * 1000):
                        break

                due_local_date = dt.datetime.fromtimestamp(next_due_ms / 1000.0, tz=tzinfo).date()
                if due_local_date >= end_excl:
                    break

                if due_local_date >= start_date:
                    preview_uuid = f"nautical-cp-{source_uuid}-{due_local_date.isoformat()}"

                    preview = cast(Task, dict(task_out))
                    preview.update(
                        {
                            "uuid": preview_uuid,
                            "id": None,
                            "nautical_preview": True,
                            "nautical_kind": "cp",
                            "nautical_source_uuid": source_uuid,
                            "nautical_cp": cp_str,
                            "nautical_link": next_link,
                            "scheduled_ms": None,
                            "due_ms": next_due_ms,
                        }
                    )

                    _apply_interval_fields(
                        preview,
                        default_duration_min=default_duration_min,
                        max_infer_duration_min=max_infer_duration_min,
                    )

                    out.append(preview)

                base_end_ms = next_due_ms
                base_due_ms = next_due_ms
                next_link += 1

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

    raw_tasks = run_task_export(filter_str)
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
            "project": nt.project,
            "tags": list(nt.tags),
            "priority": nt.priority,
            "urgency": nt.urgency,
            "scheduled_ms": nt.scheduled_ms,
            "due_ms": nt.due_ms,
            "duration": nt.duration_raw,
            "duration_min": nt.duration_min,
        }

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
    }

    goals_cfg = load_goals_config(goals_path)

    payload: Payload = {"cfg": cfg, "tasks": tasks, "goals": goals_cfg}
    if plan_overrides:
        payload = cast(
            Payload,
            apply_plan_overrides(cast(dict[str, Any], payload), plan_overrides, normalize=False),
        )

    # v2 is applied by callers/tools via scalpel.schema.upgrade_payload.
    return cast(Payload, apply_schema_v1(payload))
