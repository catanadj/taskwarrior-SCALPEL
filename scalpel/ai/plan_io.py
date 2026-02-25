"""Load/save AiPlanResult JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .interface import AiPlanResult, PlanOverride
from .plan_contract import validate_plan_result
from .plan_v2 import compile_plan_v2


def _as_int(v: Any) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


def load_plan_result(path: Path) -> AiPlanResult:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("plan result must be a JSON object")

    errs = validate_plan_result(obj)
    if errs:
        raise ValueError("Invalid plan result:\n" + "\n".join(f"  - {e}" for e in errs))

    schema = obj.get("schema")
    if schema == "scalpel.plan.v2":
        # Compile op-based plan into the stable AiPlanResult shape.
        return compile_plan_v2(obj)

    overrides_raw = obj.get("overrides") or {}
    if not isinstance(overrides_raw, dict):
        raise ValueError("plan result overrides must be an object")
    overrides: Dict[str, PlanOverride] = {}
    for uuid, raw in overrides_raw.items():
        if not isinstance(uuid, str) or not uuid.strip():
            raise ValueError("override keys must be non-empty strings")
        if not isinstance(raw, dict):
            raise ValueError(f"override for {uuid} must be an object")
        start_ms = _as_int(raw.get("start_ms"))
        due_ms = _as_int(raw.get("due_ms"))
        dur_min = _as_int(raw.get("duration_min"))
        if start_ms is None or due_ms is None:
            raise ValueError(f"override for {uuid} must include int start_ms and due_ms")
        overrides[uuid] = PlanOverride(start_ms=int(start_ms), due_ms=int(due_ms), duration_min=dur_min)

    added_tasks = obj.get("added_tasks") or []
    if not isinstance(added_tasks, list):
        raise ValueError("plan result added_tasks must be a list")
    added_tuple: Tuple[Dict[str, Any], ...] = tuple(
        t for t in added_tasks if isinstance(t, dict)
    )

    task_updates = obj.get("task_updates") or {}
    if not isinstance(task_updates, dict):
        raise ValueError("plan result task_updates must be an object")
    updates: Dict[str, Dict[str, Any]] = {}
    for uuid, patch in task_updates.items():
        if not isinstance(uuid, str) or not uuid.strip():
            raise ValueError("task_updates keys must be non-empty strings")
        if not isinstance(patch, dict):
            raise ValueError(f"task_updates[{uuid}] must be an object")
        updates[uuid] = patch

    warnings = obj.get("warnings") or []
    notes = obj.get("notes") or []
    model_id = obj.get("model_id")

    if not isinstance(warnings, list) or not all(isinstance(x, str) for x in warnings):
        raise ValueError("plan result warnings must be a list of strings")
    if not isinstance(notes, list) or not all(isinstance(x, str) for x in notes):
        raise ValueError("plan result notes must be a list of strings")
    if model_id is not None and not isinstance(model_id, str):
        raise ValueError("plan result model_id must be a string")

    return AiPlanResult(
        overrides=overrides,
        added_tasks=added_tuple,
        task_updates=updates,
        warnings=tuple(warnings),
        notes=tuple(notes),
        model_id=model_id,
    )
