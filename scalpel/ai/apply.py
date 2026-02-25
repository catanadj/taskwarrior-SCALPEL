"""Apply AI plan overrides to a payload in a deterministic way."""

from __future__ import annotations

from typing import Any, Dict, List

from scalpel.schema_v1 import apply_schema_v1
from scalpel.util.tz import day_key_from_ms, normalize_tz_name, resolve_tz

from .interface import AiPlanResult, PlanOverride, validate_plan_overrides

JsonDict = Dict[str, Any]


def _infer_duration_min(start_ms: int, due_ms: int) -> int:
    delta_ms = max(0, int(due_ms) - int(start_ms))
    return max(1, delta_ms // 60000)


def apply_plan_overrides(
    payload: JsonDict,
    overrides: Dict[str, PlanOverride],
    *,
    normalize: bool = True,
) -> JsonDict:
    """Return a payload with plan overrides applied to task calc fields.

    - Updates per-task: start_calc_ms, end_calc_ms, dur_calc_min, day_key.
    - Leaves original due_ms/scheduled_ms intact for traceability.
    - Optionally re-normalizes with schema v1 to rebuild indices.
    """

    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict, got {type(payload).__name__}")

    errs = validate_plan_overrides(payload, overrides)
    if errs:
        raise ValueError("Invalid plan overrides:\n" + "\n".join(f"  - {e}" for e in errs))

    out: JsonDict = dict(payload)
    tasks_in = out.get("tasks")
    tasks: List[Dict[str, Any]] = []

    cfg = out.get("cfg")
    tz_name = None
    if isinstance(cfg, dict):
        tz_raw = cfg.get("tz")
        if isinstance(tz_raw, str) and tz_raw.strip():
            tz_name = normalize_tz_name(tz_raw.strip())

    tzinfo = resolve_tz(tz_name or "local")

    if isinstance(tasks_in, list):
        for t in tasks_in:
            if not isinstance(t, dict):
                tasks.append(t)
                continue
            u = t.get("uuid")
            if not isinstance(u, str) or u not in overrides:
                tasks.append(t)
                continue

            ov = overrides[u]
            dur_min = ov.duration_min if ov.duration_min is not None else _infer_duration_min(ov.start_ms, ov.due_ms)

            t2 = dict(t)
            t2["start_calc_ms"] = int(ov.start_ms)
            t2["end_calc_ms"] = int(ov.due_ms)
            t2["dur_calc_min"] = int(dur_min)

            dk = day_key_from_ms(ov.start_ms, tzinfo)
            if dk:
                t2["day_key"] = dk

            tasks.append(t2)
    else:
        tasks = tasks_in if isinstance(tasks_in, list) else []

    out["tasks"] = tasks
    if normalize:
        out.pop("indices", None)
        return apply_schema_v1(out)
    return out


def _ensure_task_uuid(t: Dict[str, Any]) -> None:
    if not isinstance(t.get("uuid"), str) or not t["uuid"].strip():
        raise ValueError("added task must include non-empty uuid")


def _ensure_added_task_fields(t: Dict[str, Any]) -> None:
    if not isinstance(t.get("description"), str) or not t["description"].strip():
        raise ValueError("added task must include non-empty description")
    if not isinstance(t.get("status"), str) or not t["status"].strip():
        raise ValueError("added task must include non-empty status")
    tags = t.get("tags")
    if tags is None:
        return
    if not isinstance(tags, list):
        raise ValueError("added task tags must be a list when provided")


def _merge_task_update(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if k == "uuid":
            continue
        out[k] = v
    return out


def apply_plan_result(
    payload: JsonDict,
    result: AiPlanResult,
    *,
    normalize: bool = True,
) -> JsonDict:
    """Apply an AiPlanResult: add tasks, update fields, then apply overrides."""
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict, got {type(payload).__name__}")
    if not isinstance(result, AiPlanResult):
        raise TypeError("result must be AiPlanResult")

    out: JsonDict = dict(payload)
    tasks_in = out.get("tasks")
    tasks_list: List[Dict[str, Any]] = []
    if isinstance(tasks_in, list):
        for t in tasks_in:
            if isinstance(t, dict):
                tasks_list.append(dict(t))

    by_uuid = {t.get("uuid"): t for t in tasks_list if isinstance(t.get("uuid"), str)}

    # Apply updates to existing tasks.
    for uuid, patch in (result.task_updates or {}).items():
        if not isinstance(uuid, str) or not uuid:
            raise ValueError("task_updates must use non-empty uuid keys")
        if not isinstance(patch, dict):
            raise ValueError(f"task_updates[{uuid}] must be an object")
        base = by_uuid.get(uuid)
        if base is None:
            raise ValueError(f"task_updates refers to unknown uuid: {uuid}")
        merged = _merge_task_update(base, patch)
        by_uuid[uuid] = merged

    # Add new tasks.
    added = []
    for t in result.added_tasks or ():
        if not isinstance(t, dict):
            raise ValueError("added_tasks entries must be objects")
        _ensure_task_uuid(t)
        _ensure_added_task_fields(t)
        u = t.get("uuid")
        if u in by_uuid:
            raise ValueError(f"added_tasks uuid already exists: {u}")
        added.append(dict(t))
        by_uuid[u] = added[-1]

    # Preserve task order: existing tasks first, then added.
    ordered = []
    seen = set()
    for t in tasks_list:
        u = t.get("uuid")
        if u in by_uuid and u not in seen:
            ordered.append(by_uuid[u])
            seen.add(u)
    for t in added:
        u = t.get("uuid")
        if u not in seen:
            ordered.append(t)
            seen.add(u)

    out["tasks"] = ordered

    # Apply overrides on top of updated/added tasks.
    if result.overrides:
        out = apply_plan_overrides(out, result.overrides, normalize=False)

    if normalize:
        out.pop("indices", None)
        return apply_schema_v1(out)
    return out
