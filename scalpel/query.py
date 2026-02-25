from __future__ import annotations

"""scalpel.query

Schema-aware query helpers for SCALPEL payloads.

Design goals:
- Treat schema v1 payload as the public contract.
- Prefer indices for O(1)/O(k) lookups.
- Be defensive: never crash the UI path due to a single bad index entry.
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

JsonDict = Dict[str, Any]
Task = Dict[str, Any]


def _tasks(payload: JsonDict) -> List[Task]:
    t = payload.get("tasks")
    return t if isinstance(t, list) else []


def _indices(payload: JsonDict) -> Mapping[str, Any]:
    idx = payload.get("indices")
    return idx if isinstance(idx, dict) else {}


def _safe_task_at(tasks: Sequence[Task], idx: Any) -> Optional[Task]:
    if not isinstance(idx, int):
        return None
    if idx < 0 or idx >= len(tasks):
        return None
    t = tasks[idx]
    return t if isinstance(t, dict) else None


def iter_tasks(payload: JsonDict) -> Iterable[Task]:
    """Iterate tasks in payload order."""
    for t in _tasks(payload):
        if isinstance(t, dict):
            yield t


def task_by_uuid(payload: JsonDict, uuid: str, *, default: Optional[Task] = None) -> Optional[Task]:
    """Return the task dict for uuid or default (None by default).

    Uses indices.by_uuid when present; falls back to linear scan as a safety net.
    """
    if not isinstance(uuid, str) or not uuid:
        return default

    tasks = _tasks(payload)
    idxs = _indices(payload)
    by_uuid = idxs.get("by_uuid") if isinstance(idxs, dict) else None
    if isinstance(by_uuid, dict):
        t = _safe_task_at(tasks, by_uuid.get(uuid))
        if t is not None:
            # Ensure index is consistent (paranoia); otherwise fall back
            if str(t.get("uuid") or "") == uuid:
                return t

    # Safety net: linear scan (kept intentionally simple)
    for t in tasks:
        if isinstance(t, dict) and str(t.get("uuid") or "") == uuid:
            return t

    return default


def require_task_by_uuid(payload: JsonDict, uuid: str) -> Task:
    """Like task_by_uuid but raises KeyError when missing."""
    t = task_by_uuid(payload, uuid, default=None)
    if t is None:
        raise KeyError(uuid)
    return t


def _indices_to_tasks(payload: JsonDict, idx_list: Any) -> List[Task]:
    """Convert an index list to tasks, ignoring bad indices."""
    tasks = _tasks(payload)
    out: List[Task] = []
    if not isinstance(idx_list, list):
        return out
    for idx in idx_list:
        t = _safe_task_at(tasks, idx)
        if t is not None:
            out.append(t)
    return out


def tasks_by_status(payload: JsonDict, status: str) -> List[Task]:
    idxs = _indices(payload)
    by_status = idxs.get("by_status") if isinstance(idxs, dict) else None
    if not isinstance(by_status, dict):
        return []
    return _indices_to_tasks(payload, by_status.get(status))


def tasks_by_project(payload: JsonDict, project: str) -> List[Task]:
    idxs = _indices(payload)
    by_project = idxs.get("by_project") if isinstance(idxs, dict) else None
    if not isinstance(by_project, dict):
        return []
    return _indices_to_tasks(payload, by_project.get(project))


def tasks_by_tag(payload: JsonDict, tag: str) -> List[Task]:
    idxs = _indices(payload)
    by_tag = idxs.get("by_tag") if isinstance(idxs, dict) else None
    if not isinstance(by_tag, dict):
        return []
    return _indices_to_tasks(payload, by_tag.get(tag))


def tasks_by_day(payload: JsonDict, ymd: str) -> List[Task]:
    """Return tasks indexed under indices.by_day[YYYY-MM-DD]."""
    idxs = _indices(payload)
    by_day = idxs.get("by_day") if isinstance(idxs, dict) else None
    if not isinstance(by_day, dict):
        return []
    return _indices_to_tasks(payload, by_day.get(ymd))


__all__ = [
    "iter_tasks",
    "task_by_uuid",
    "require_task_by_uuid",
    "tasks_by_status",
    "tasks_by_project",
    "tasks_by_tag",
    "tasks_by_day",
]
