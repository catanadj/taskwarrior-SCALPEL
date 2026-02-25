"""scalpel.plan.v2 compiler.

Plan v2 is an op-based, ISO-friendly format intended for local models.
The engine resolves all time arithmetic.

This module compiles a v2 JSON object into an AiPlanResult.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Tuple

from .interface import AiPlanResult, PlanOverride


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _temp_uuid(temp_id: str) -> str:
    # Deterministic, readable pseudo UUID for draft tasks.
    core = _normalize_temp_id(temp_id)
    return f"tmp:{core}"


def _normalize_temp_id(raw: str) -> str:
    s = raw.strip()
    if s.startswith("tmp:"):
        s = s[4:].strip()
    return s


def _parse_iso_to_ms(s: str) -> int:
    """Parse an ISO 8601 string into epoch ms.

    Requires timezone info (offset or Z). We intentionally do not accept
    naive datetimes because v2 is meant to be deterministic across machines.
    """
    raw = s.strip().replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(raw)
    if d.tzinfo is None:
        raise ValueError(f"ISO time must include timezone offset: {s!r}")
    return int(d.timestamp() * 1000)


def compile_plan_v2(obj: Dict[str, Any]) -> AiPlanResult:
    """Compile a scalpel.plan.v2 JSON object into AiPlanResult."""

    if not isinstance(obj, dict):
        raise ValueError("plan v2 must be an object")
    if obj.get("schema") != "scalpel.plan.v2":
        raise ValueError("plan v2 schema must be 'scalpel.plan.v2'")

    ops = obj.get("ops")
    if not isinstance(ops, list):
        raise ValueError("plan v2 must include ops list")

    slot_catalog = obj.get("slot_catalog")
    if slot_catalog is None:
        slot_catalog = {}
    if not isinstance(slot_catalog, dict):
        raise ValueError("plan v2 slot_catalog must be an object when provided")

    # Map temp_id -> uuid.
    temp_map: Dict[str, str] = {}
    added_tasks: List[Dict[str, Any]] = []
    task_updates: Dict[str, Dict[str, Any]] = {}
    overrides: Dict[str, PlanOverride] = {}

    def resolve_target_id(raw: Any) -> str:
        if not _is_nonempty_str(raw):
            raise ValueError("op target must be a non-empty string")
        s = str(raw).strip()
        if s.startswith("tmp:"):
            core = _normalize_temp_id(s)
            return temp_map.get(core) or _temp_uuid(core)
        core = _normalize_temp_id(s)
        if core in temp_map:
            return temp_map[core]
        return s

    # First pass: allocate temp ids for created tasks, so later ops can reference them.
    for op in ops:
        if not isinstance(op, dict):
            continue
        if op.get("op") != "create_task":
            continue
        tid = op.get("temp_id")
        if not _is_nonempty_str(tid):
            continue
        tid_s = _normalize_temp_id(str(tid))
        if not tid_s:
            continue
        if tid_s in temp_map:
            continue
        temp_map[tid_s] = _temp_uuid(tid_s)

    # Split subtasks also create temp ids.
    for op in ops:
        if not isinstance(op, dict):
            continue
        if op.get("op") != "split_task":
            continue
        subs = op.get("subtasks")
        if not isinstance(subs, list):
            continue
        for st in subs:
            if not isinstance(st, dict):
                continue
            tid = st.get("temp_id")
            if not _is_nonempty_str(tid):
                continue
            tid_s = _normalize_temp_id(str(tid))
            if not tid_s:
                continue
            if tid_s in temp_map:
                continue
            temp_map[tid_s] = _temp_uuid(tid_s)

    # Second pass: compile ops.
    for op in ops:
        if not isinstance(op, dict):
            raise ValueError("ops entries must be objects")
        kind = op.get("op")
        if not _is_nonempty_str(kind):
            raise ValueError("each op must include non-empty string 'op'")
        kind = str(kind).strip()

        if kind == "create_task":
            tid = op.get("temp_id")
            desc = op.get("description")
            if not _is_nonempty_str(tid) or not _is_nonempty_str(desc):
                raise ValueError("create_task must include temp_id and description")
            tid_s = _normalize_temp_id(str(tid))
            uuid = temp_map.get(tid_s) or _temp_uuid(tid_s)
            temp_map[tid_s] = uuid

            t: Dict[str, Any] = {
                "uuid": uuid,
                "description": str(desc).strip(),
                "status": str(op.get("status") or "pending"),
            }
            if _is_nonempty_str(op.get("project")):
                t["project"] = str(op.get("project")).strip()
            tags = op.get("tags")
            if isinstance(tags, list):
                t["tags"] = [str(x) for x in tags if str(x).strip()]
            elif isinstance(tags, str) and tags.strip():
                t["tags"] = [x for x in tags.split() if x]
            if isinstance(op.get("duration_min"), int) and int(op.get("duration_min")) > 0:
                t["duration_min"] = int(op.get("duration_min"))
            added_tasks.append(t)

        elif kind == "split_task":
            parent = op.get("uuid")
            if not _is_nonempty_str(parent):
                raise ValueError("split_task must include uuid")
            subs = op.get("subtasks")
            if not isinstance(subs, list) or not subs:
                raise ValueError("split_task must include non-empty subtasks list")
            for st in subs:
                if not isinstance(st, dict):
                    raise ValueError("split_task subtasks entries must be objects")
                tid = st.get("temp_id")
                desc = st.get("description")
                dur = st.get("duration_min")
                if not _is_nonempty_str(tid) or not _is_nonempty_str(desc) or not isinstance(dur, int) or dur <= 0:
                    raise ValueError("split_task subtasks require temp_id, description, duration_min")
                tid_s = _normalize_temp_id(str(tid))
                uuid = temp_map.get(tid_s) or _temp_uuid(tid_s)
                temp_map[tid_s] = uuid
                t2: Dict[str, Any] = {
                    "uuid": uuid,
                    "description": str(desc).strip(),
                    "status": "pending",
                    "duration_min": int(dur),
                    "split_of": str(parent).strip(),
                }
                # Optional inheritance hints.
                if _is_nonempty_str(st.get("project")):
                    t2["project"] = str(st.get("project")).strip()
                tags = st.get("tags")
                if isinstance(tags, list):
                    t2["tags"] = [str(x) for x in tags if str(x).strip()]
                added_tasks.append(t2)

        elif kind == "place":
            target = resolve_target_id(op.get("target"))
            slot_id = op.get("slot_id")
            start_ms = None
            due_ms = None

            if _is_nonempty_str(slot_id):
                slot = slot_catalog.get(str(slot_id).strip())
                if not isinstance(slot, dict):
                    raise ValueError(f"unknown slot_id: {slot_id}")
                s = slot.get("start_ms")
                e = slot.get("due_ms")
                if not isinstance(s, int) or not isinstance(e, int) or e <= s:
                    raise ValueError(f"slot_catalog[{slot_id}] must include int start_ms/due_ms")
                start_ms = int(s)
                due_ms = int(e)
            else:
                # Fallback: allow direct ISO placement, but require timezone offsets.
                if not _is_nonempty_str(op.get("start_iso")) or not _is_nonempty_str(op.get("due_iso")):
                    raise ValueError("place must include slot_id or (start_iso and due_iso)")
                start_ms = _parse_iso_to_ms(str(op.get("start_iso")))
                due_ms = _parse_iso_to_ms(str(op.get("due_iso")))
                if due_ms <= start_ms:
                    raise ValueError("place must have due_iso after start_iso")

            duration_min = max(1, int((int(due_ms) - int(start_ms)) // 60000))
            overrides[target] = PlanOverride(start_ms=int(start_ms), due_ms=int(due_ms), duration_min=duration_min)

        elif kind == "update_task":
            target = op.get("uuid") if _is_nonempty_str(op.get("uuid")) else op.get("target")
            uuid = resolve_target_id(target)
            patch = op.get("patch")
            if not isinstance(patch, dict):
                raise ValueError("update_task must include patch object")
            task_updates[uuid] = dict(patch)

        elif kind == "complete_task":
            uuid = resolve_target_id(op.get("uuid") or op.get("target"))
            task_updates.setdefault(uuid, {})["status"] = "completed"

        elif kind == "delete_task":
            uuid = resolve_target_id(op.get("uuid") or op.get("target"))
            task_updates.setdefault(uuid, {})["status"] = "deleted"

        else:
            # Ignore unknown ops for forward compatibility.
            continue

    warnings = obj.get("warnings") or []
    notes = obj.get("notes") or []
    model_id = obj.get("model_id")
    if not isinstance(warnings, list) or not all(isinstance(x, str) for x in warnings):
        raise ValueError("plan v2 warnings must be a list of strings")
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        raise ValueError("plan v2 notes must be a list of strings")
    if model_id is not None and not isinstance(model_id, str):
        raise ValueError("plan v2 model_id must be a string")

    return AiPlanResult(
        overrides=overrides,
        added_tasks=tuple(added_tasks),
        task_updates=task_updates,
        warnings=tuple(warnings),
        notes=tuple(notes),
        model_id=model_id,
    )
