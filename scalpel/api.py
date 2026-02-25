"""scalpel.api

Stable *library* entrypoint for SCALPEL.

Policy:
  - Only names listed in __all__ are considered public API.
  - Everything else is internal and may change without notice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from scalpel.html_extract import extract_payload_json_from_html_file
from scalpel.query_lang import Query
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload
from scalpel.validate import assert_valid_payload

JsonPath = Union[str, Path]
Payload = Dict[str, Any]


# --- Public API: smoke-synthetic filtering ------------------------------------
# Some payloads (notably strict smoke fixtures) include synthetic tasks to
# guarantee invariants. Those should not leak into the public query surface
# by default.
_SMOKE_SYNTHETIC_UUIDS = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
]


def _is_smoke_synthetic(task: dict) -> bool:
    """Return True only for reserved smoke scaffolding tasks (and explicit synthetic flags).

    Important: do NOT use heuristics like description prefixes here, because golden fixtures
    can contain tasks with "SMOKE:" descriptions that are still part of the stable surface.
    """
    try:
        u = str(task.get("uuid") or "")
    except Exception:
        u = ""

    if u in _SMOKE_SYNTHETIC_UUIDS:
        return True

    # Future-proof: explicit markers (if schema starts setting them)
    if task.get("synthetic") is True or task.get("_synthetic") is True:
        return True
    if str(task.get("source") or "").lower() in ("synthetic",):
        return True

    return False


def _tasks_list(payload: dict) -> list:
    t = payload.get("tasks") or []
    return t if isinstance(t, list) else []


def _indices(payload: dict) -> dict:
    idx = payload.get("indices") or {}
    return idx if isinstance(idx, dict) else {}


def _pluck_by_indices(payload: dict, idxs: object, *, include_smoke: bool) -> list[dict]:
    tasks = _tasks_list(payload)
    if not isinstance(idxs, list):
        return []
    out: list[dict] = []
    for i in idxs:
        if not isinstance(i, int):
            continue
        if i < 0 or i >= len(tasks):
            continue
        t = tasks[i]
        if not isinstance(t, dict):
            continue
        if (not include_smoke) and _is_smoke_synthetic(t):
            continue
        out.append(t)
    return out


# --- /Public API: smoke-synthetic filtering -----------------------------------


def _coerce_target_version(payload: Dict[str, Any], target_version: Optional[int]) -> int:
    """Choose target schema version.

    Default: LATEST_SCHEMA_VERSION.
    Rule: never downgrade the input (max(current, requested)).
    """
    cur = payload.get("schema_version")
    cur_i = int(cur) if isinstance(cur, int) else 0

    req_i = int(target_version) if isinstance(target_version, int) else int(LATEST_SCHEMA_VERSION)
    if req_i < 1:
        req_i = 1

    latest_i = int(LATEST_SCHEMA_VERSION)
    if req_i > latest_i:
        raise ValueError(f"Unsupported schema_version: {req_i} (latest={LATEST_SCHEMA_VERSION})")

    if cur_i > latest_i:
        raise ValueError(f"Unsupported schema_version: {cur_i} (latest={LATEST_SCHEMA_VERSION})")

    return max(cur_i, req_i)


def load_payload_from_json(
    path: JsonPath,
    *,
    upgrade: bool = True,
    validate: bool = True,
    target_version: int | None = None,
) -> Dict[str, Any]:
    """Load a payload from a JSON file.

    Defaults:
      - upgrade=True upgrades to the latest schema by default (LATEST_SCHEMA_VERSION).
      - validate=True validates the (possibly upgraded) payload against the latest schema.

    Rules:
      - Never downgrades: if input is already newer than target_version, keep the newer version.
    """
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object/dict; got {type(payload).__name__}")

    if upgrade:
        tv = _coerce_target_version(payload, target_version)
        payload = upgrade_payload(payload, target_version=tv)  # type: ignore[arg-type]

    if validate:
        assert_valid_payload(payload)

    return payload


def normalize_payload(
    payload: Dict[str, Any],
    *,
    validate: bool = True,
    target_version: int | None = None,
) -> Dict[str, Any]:
    """Normalize an in-memory payload to the latest schema by default."""
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be a dict/object; got {type(payload).__name__}")

    tv = _coerce_target_version(payload, target_version)
    out = upgrade_payload(payload, target_version=tv)  # type: ignore[arg-type]

    if validate:
        assert_valid_payload(out)

    return out


def load_payload_from_html(path: JsonPath, *, validate: bool = True, target_version: int | None = None) -> Payload:
    """Extract payload JSON from HTML file and normalize."""
    p = Path(path)
    obj = extract_payload_json_from_html_file(p)
    if not isinstance(obj, dict):
        raise ValueError(f"HTML payload must be an object/dict; got {type(obj).__name__}")
    return normalize_payload(obj, validate=validate, target_version=target_version)


def task_by_uuid(payload: dict, uuid: str) -> dict | None:
    """Return the task dict for `uuid` if present.

    Note: this is a *direct* lookup and must not apply synthetic filtering.
    Filtering is the responsibility of iterators (iter_tasks / tasks_by_*).
    """
    if not uuid:
        return None

    tasks = payload.get("tasks") or []
    if not isinstance(tasks, list):
        return None

    indices = payload.get("indices") or {}
    if isinstance(indices, dict):
        by_uuid = indices.get("by_uuid") or {}
        if isinstance(by_uuid, dict):
            idx = by_uuid.get(uuid)
            if isinstance(idx, int) and 0 <= idx < len(tasks):
                t = tasks[idx]
                if isinstance(t, dict):
                    # Defensive: ensure match (indices could be stale in dev)
                    if str(t.get("uuid") or "") == uuid:
                        return t

    # Fallback: raw linear scan (UNFILTERED)
    for t in tasks:
        if isinstance(t, dict) and str(t.get("uuid") or "") == uuid:
            return t

    return None


def tasks_by_status(payload: dict, status: str, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks by status using indices. Default excludes smoke-synthetic tasks."""
    by_status = _indices(payload).get("by_status") or {}
    if not isinstance(by_status, dict):
        return []
    return _pluck_by_indices(payload, by_status.get(status) or [], include_smoke=include_smoke)


def tasks_by_project(payload: dict, project: str, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks by project using indices. Default excludes smoke-synthetic tasks."""
    by_project = _indices(payload).get("by_project") or {}
    if not isinstance(by_project, dict):
        return []
    return _pluck_by_indices(payload, by_project.get(project) or [], include_smoke=include_smoke)


def tasks_by_tag(payload: dict, tag: str, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks by tag using indices. Default excludes smoke-synthetic tasks."""
    by_tag = _indices(payload).get("by_tag") or {}
    if not isinstance(by_tag, dict):
        return []
    return _pluck_by_indices(payload, by_tag.get(tag) or [], include_smoke=include_smoke)


def tasks_by_day(payload: dict, ymd: str, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks by day (YYYY-MM-DD) using indices. Default excludes smoke-synthetic tasks."""
    by_day = _indices(payload).get("by_day") or {}
    if not isinstance(by_day, dict):
        return []
    return _pluck_by_indices(payload, by_day.get(ymd) or [], include_smoke=include_smoke)


def iter_tasks(payload: dict, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks as a list of dicts.

    By default, excludes strict-smoke synthetic tasks. Use include_smoke=True to include them.
    """
    tasks = _tasks_list(payload)
    out: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if (not include_smoke) and _is_smoke_synthetic(t):
            continue
        out.append(t)
    return out


def select_tasks(payload: dict, q: Optional[Union[str, Query]] = None, *, include_smoke: bool = False) -> list[dict]:
    """Return tasks optionally filtered by query.

    Notes:
      - Query execution uses indices on the full payload.
      - We apply smoke-synthetic filtering *after* the query selection by default.
    """
    if q is None:
        return iter_tasks(payload, include_smoke=include_smoke)

    qq = Query.parse(q) if isinstance(q, str) else q
    got = qq.run(payload)
    out: list[dict] = []
    for t in got:
        if not isinstance(t, dict):
            continue
        if (not include_smoke) and _is_smoke_synthetic(t):
            continue
        out.append(t)
    return out


def filter_payload(payload: dict, query, *, keep_cfg: bool = True, keep_meta: bool = True) -> dict:
    """Filter a payload to only tasks matching `query` and rebuild indices.

    Design goals:
      - Preserve raw regex strings in queries (Query.parse handles that; we do not reinterpret them here).
      - Preserve cfg/meta by default.
      - Rebuild indices by *subsetting/remapping existing indices*.
      - Stable ordering: tasks keep original relative order from the input payload.

    `query` may be a string (parsed via Query.parse) or a Query object.
    """
    _meta_in = payload.get("meta")

    if payload is None or not isinstance(payload, dict):
        return {}

    # Normalize/upgrade so indices exist and are consistent.
    p = payload
    try:
        p = normalize_payload(payload, validate=False)
    except (TypeError, ValueError):
        p = payload

    tasks = p.get("tasks") or []
    if not isinstance(tasks, list):
        tasks = []

    idx = p.get("indices") or {}
    if not isinstance(idx, dict):
        idx = {}
    by_uuid = idx.get("by_uuid") or {}
    if not isinstance(by_uuid, dict):
        by_uuid = {}

    q = Query.parse(query) if isinstance(query, str) else query

    keep_old: set[int] = set()
    if hasattr(q, "run_indices"):
        keep_old = set(q.run_indices(p))  # type: ignore[attr-defined]
    else:
        kept_tasks = q.run(p)  # type: ignore[call-arg]
        kept_uuids: list[str] = []
        for t in kept_tasks:
            if isinstance(t, dict):
                u = t.get("uuid")
                if isinstance(u, str) and u:
                    kept_uuids.append(u)
        for u in kept_uuids:
            oi = by_uuid.get(u)
            if isinstance(oi, int):
                keep_old.add(oi)

    keep_sorted = sorted(i for i in keep_old if isinstance(i, int) and 0 <= i < len(tasks))
    old_to_new = {old: new for new, old in enumerate(keep_sorted)}

    new_tasks = [tasks[i] for i in keep_sorted]

    def _remap_list(v):
        if not isinstance(v, list):
            return []
        out = []
        for x in v:
            if isinstance(x, int) and x in old_to_new:
                out.append(old_to_new[x])
        return out

    def _remap_map(m):
        if not isinstance(m, dict):
            return {}
        out = {}
        for k, v in m.items():
            if isinstance(v, int):
                if v in old_to_new:
                    out[k] = old_to_new[v]
            else:
                out[k] = _remap_list(v)
        return out

    new_indices = {}
    for k in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
        new_indices[k] = _remap_map(idx.get(k))

    out: dict[str, Any] = {}
    if keep_cfg and "cfg" in p:
        out["cfg"] = p["cfg"]
    if keep_meta and "meta" in p:
        out["meta"] = p["meta"]

    # Preserve other top-level keys that are part of the payload surface
    for k in ("schema_version", "generated_at"):
        if k in p and k not in out:
            out[k] = p[k]

    out["tasks"] = new_tasks
    out["indices"] = new_indices

    # Preserve meta exactly as provided by the input payload (contract-stable).
    if keep_meta:
        if "meta" in payload:
            out["meta"] = _meta_in
        else:
            out.pop("meta", None)
    else:
        out.pop("meta", None)

    return out


# --- Public API exports (locked by contract tests) ------------------------
# Keep changes intentional and reviewable.
# Prefer append-only unless you are intentionally reshaping the public surface.
_PUBLIC_EXPORTS = (
    "filter_payload",
    "iter_tasks",
    "load_payload_from_html",
    "load_payload_from_json",
    "normalize_payload",
    "task_by_uuid",
    "tasks_by_day",
    "tasks_by_project",
    "tasks_by_status",
    "tasks_by_tag",
)

__all__ = [n for n in _PUBLIC_EXPORTS if n in globals()]
# --- /Public API exports --------------------------------------------------
