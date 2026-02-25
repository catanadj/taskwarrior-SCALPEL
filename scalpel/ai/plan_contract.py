"""Plan result contract validation.

Supports:
  - scalpel.plan.v1 (legacy overrides/added_tasks/task_updates)
  - scalpel.plan.v2 (op-based, ISO-friendly; engine resolves slots)
"""

from __future__ import annotations

from typing import Any, Dict, List


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _validate_common_fields(obj: Dict[str, Any], errs: List[str]) -> None:
    warnings = obj.get("warnings", [])
    if not isinstance(warnings, list) or not all(isinstance(x, str) for x in warnings):
        errs.append("warnings must be a list of strings")

    notes = obj.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        errs.append("notes must be a list of strings")

    model_id = obj.get("model_id")
    if model_id is not None and not isinstance(model_id, str):
        errs.append("model_id must be a string")


def _validate_v2_slot_catalog(cat: Any, errs: List[str]) -> None:
    if cat is None:
        return
    if not isinstance(cat, dict):
        errs.append("slot_catalog must be an object when provided")
        return
    for slot_id, raw in list(cat.items())[:5000]:
        if not _is_nonempty_str(slot_id):
            errs.append("slot_catalog keys must be non-empty strings")
            break
        if not isinstance(raw, dict):
            errs.append(f"slot_catalog[{slot_id}] must be an object")
            continue
        # For portability, only enforce ms fields if present.
        if "start_ms" in raw and not isinstance(raw.get("start_ms"), int):
            errs.append(f"slot_catalog[{slot_id}].start_ms must be int when provided")
        if "due_ms" in raw and not isinstance(raw.get("due_ms"), int):
            errs.append(f"slot_catalog[{slot_id}].due_ms must be int when provided")
        if "start_ms" in raw and "due_ms" in raw:
            s = raw.get("start_ms")
            e = raw.get("due_ms")
            if isinstance(s, int) and isinstance(e, int) and e <= s:
                errs.append(f"slot_catalog[{slot_id}] must have due_ms > start_ms")


def _validate_v2_ops(ops: Any, slot_catalog: Any, errs: List[str]) -> None:
    if not isinstance(ops, list):
        errs.append("ops must be a list")
        return

    for op in ops[:5000]:
        if not isinstance(op, dict):
            errs.append("ops entries must be objects")
            break
        kind = op.get("op")
        if not _is_nonempty_str(kind):
            errs.append("each op must include non-empty string 'op'")
            continue

        if kind == "create_task":
            if not _is_nonempty_str(op.get("temp_id")):
                errs.append("create_task must include non-empty temp_id")
            if not _is_nonempty_str(op.get("description")):
                errs.append("create_task must include non-empty description")
            if "duration_min" in op and op.get("duration_min") is not None and not isinstance(op.get("duration_min"), int):
                errs.append("create_task duration_min must be int when provided")
            if isinstance(op.get("duration_min"), int) and int(op.get("duration_min")) <= 0:
                errs.append("create_task duration_min must be positive when provided")
        elif kind == "split_task":
            if not _is_nonempty_str(op.get("uuid")):
                errs.append("split_task must include non-empty uuid")
            subs = op.get("subtasks")
            if not isinstance(subs, list) or not subs:
                errs.append("split_task must include non-empty subtasks list")
            else:
                for st in subs[:5000]:
                    if not isinstance(st, dict):
                        errs.append("split_task subtasks entries must be objects")
                        break
                    if not _is_nonempty_str(st.get("temp_id")):
                        errs.append("split_task subtasks must include non-empty temp_id")
                    if not _is_nonempty_str(st.get("description")):
                        errs.append("split_task subtasks must include non-empty description")
                    if not isinstance(st.get("duration_min"), int):
                        errs.append("split_task subtasks must include int duration_min")
                    elif int(st.get("duration_min")) <= 0:
                        errs.append("split_task subtasks duration_min must be positive")
        elif kind == "place":
            if not _is_nonempty_str(op.get("target")):
                errs.append("place must include non-empty target")
            has_slot = _is_nonempty_str(op.get("slot_id"))
            has_iso = _is_nonempty_str(op.get("start_iso")) and _is_nonempty_str(op.get("due_iso"))
            if not (has_slot or has_iso):
                errs.append("place must include slot_id or (start_iso and due_iso)")
            if has_slot:
                if not isinstance(slot_catalog, dict):
                    errs.append("place slot_id requires slot_catalog")
                else:
                    slot_id = str(op.get("slot_id")).strip()
                    slot = slot_catalog.get(slot_id)
                    if not isinstance(slot, dict):
                        errs.append(f"slot_catalog missing slot_id: {slot_id}")
                    else:
                        s = slot.get("start_ms")
                        e = slot.get("due_ms")
                        if not isinstance(s, int) or not isinstance(e, int):
                            errs.append(f"slot_catalog[{slot_id}] must include int start_ms/due_ms")
                        elif int(e) <= int(s):
                            errs.append(f"slot_catalog[{slot_id}] must have due_ms > start_ms")
        elif kind == "update_task":
            if not _is_nonempty_str(op.get("target")) and not _is_nonempty_str(op.get("uuid")):
                errs.append("update_task must include uuid or target")
            if not isinstance(op.get("patch"), dict):
                errs.append("update_task must include patch object")
        elif kind in {"complete_task", "delete_task"}:
            if not _is_nonempty_str(op.get("uuid")) and not _is_nonempty_str(op.get("target")):
                errs.append(f"{kind} must include uuid or target")
        else:
            # Forward-compatible: accept unknown ops.
            continue


def validate_plan_result(obj: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(obj, dict):
        return ["plan result must be an object"]

    schema = obj.get("schema")
    if schema is not None and schema not in {"scalpel.plan.v1", "scalpel.plan.v2"}:
        errs.append("schema must be 'scalpel.plan.v1' or 'scalpel.plan.v2' when provided")

    if schema == "scalpel.plan.v2":
        _validate_v2_ops(obj.get("ops"), obj.get("slot_catalog"), errs)
        _validate_v2_slot_catalog(obj.get("slot_catalog"), errs)
        _validate_common_fields(obj, errs)
        return errs

    # Default: v1 validation (schema omitted => v1 for backwards compatibility)
    overrides = obj.get("overrides", {})
    if not isinstance(overrides, dict):
        errs.append("overrides must be an object")
    else:
        for uuid, raw in list(overrides.items())[:5000]:
            if not isinstance(uuid, str) or not uuid.strip():
                errs.append("override keys must be non-empty strings")
                break
            if not isinstance(raw, dict):
                errs.append(f"override for {uuid} must be an object")
                continue
            if not isinstance(raw.get("start_ms"), int) or not isinstance(raw.get("due_ms"), int):
                errs.append(f"override for {uuid} must include int start_ms and due_ms")

    added_tasks = obj.get("added_tasks", [])
    if not isinstance(added_tasks, list):
        errs.append("added_tasks must be a list")
    else:
        for t in added_tasks[:5000]:
            if not isinstance(t, dict):
                errs.append("added_tasks entries must be objects")
                break
            u = t.get("uuid")
            if not isinstance(u, str) or not u.strip():
                errs.append("added_tasks entries must include non-empty uuid")
                break
            d = t.get("description")
            if not isinstance(d, str) or not d.strip():
                errs.append("added_tasks entries must include non-empty description")
                break
            s = t.get("status")
            if not isinstance(s, str) or not s.strip():
                errs.append("added_tasks entries must include non-empty status")
                break
            tags = t.get("tags")
            if tags is not None and not isinstance(tags, list):
                errs.append("added_tasks tags must be a list when provided")
                break

    task_updates = obj.get("task_updates", {})
    if not isinstance(task_updates, dict):
        errs.append("task_updates must be an object")
    else:
        for uuid, patch in list(task_updates.items())[:5000]:
            if not isinstance(uuid, str) or not uuid.strip():
                errs.append("task_updates keys must be non-empty strings")
                break
            if not isinstance(patch, dict):
                errs.append(f"task_updates[{uuid}] must be an object")
                continue

    _validate_common_fields(obj, errs)

    return errs
