"""Payload validation helpers (library-facing)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scalpel.schema import LATEST_SCHEMA_VERSION as _LATEST_SCHEMA_VERSION


class PayloadValidationError(ValueError):
    """Raised when a payload fails validation."""


LATEST_SCHEMA_VERSION = _LATEST_SCHEMA_VERSION


def _require(cond: bool, msg: str, errs: List[str]) -> None:
    if not cond:
        errs.append(msg)


def _get_generated_at(payload: Dict[str, Any]) -> Optional[str]:
    # Prefer meta.generated_at; tolerate legacy top-level generated_at.
    meta = payload.get("meta")
    if isinstance(meta, dict):
        ga = meta.get("generated_at")
        if isinstance(ga, str) and ga.strip():
            return ga.strip()
    ga2 = payload.get("generated_at")
    if isinstance(ga2, str) and ga2.strip():
        return ga2.strip()
    return None


def _validate_common(payload: Dict[str, Any], *, label: str, expect_version: int) -> List[str]:
    errs: List[str] = []

    _require(payload.get("schema_version") == expect_version, f"{label}: schema_version must be {expect_version}", errs)

    ga = _get_generated_at(payload)
    _require(isinstance(ga, str) and bool(ga), f"{label}: meta.generated_at must be non-empty string", errs)

    cfg = payload.get("cfg")
    tasks = payload.get("tasks")
    indices = payload.get("indices")
    meta = payload.get("meta")

    _require(isinstance(cfg, dict), f"{label}: cfg must be dict", errs)
    _require(isinstance(tasks, list), f"{label}: tasks must be list", errs)
    _require(isinstance(indices, dict), f"{label}: indices must be dict", errs)
    if meta is not None:
        _require(isinstance(meta, dict), f"{label}: meta must be dict", errs)

    if isinstance(indices, dict):
        for k in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
            _require(k in indices, f"{label}: indices missing key: {k}", errs)
        _require(isinstance(indices.get("by_uuid"), dict), f"{label}: indices.by_uuid must be dict", errs)

    if isinstance(tasks, list):
        for i, t in enumerate(tasks):
            if not isinstance(t, dict):
                errs.append(f"{label}: tasks[{i}] must be dict")
                continue
            u = t.get("uuid")
            _require(isinstance(u, str) and u.strip(), f"{label}: tasks[{i}].uuid must be non-empty string", errs)
            _require(
                isinstance(t.get("status"), str) and bool(t.get("status")),
                f"{label}: tasks[{i}].status must be non-empty string",
                errs,
            )
            tags = t.get("tags")
            _require(isinstance(tags, list), f"{label}: tasks[{i}].tags must be list", errs)

    # Cross-check indices.by_uuid -> valid task index
    if isinstance(tasks, list) and isinstance(indices, dict) and isinstance(indices.get("by_uuid"), dict):
        by_uuid = indices["by_uuid"]
        for u, idx in list(by_uuid.items())[:2000]:  # keep cheap
            if not isinstance(u, str) or not u:
                errs.append(f"{label}: indices.by_uuid contains non-string/empty uuid key")
                break
            if not isinstance(idx, int):
                errs.append(f"{label}: indices.by_uuid[{u!r}] must be int index")
                continue
            if idx < 0 or idx >= len(tasks):
                errs.append(f"{label}: indices.by_uuid[{u!r}] out of range: {idx} (tasks={len(tasks)})")
                continue
            t = tasks[idx]
            if isinstance(t, dict) and str(t.get("uuid") or "") != u:
                errs.append(f"{label}: indices.by_uuid[{u!r}] points to tasks[{idx}] with uuid={t.get('uuid')!r}")

    return errs


def validate_schema_v1(payload: Dict[str, Any], *, label: str = "payload") -> List[str]:
    return _validate_common(payload, label=label, expect_version=1)


def validate_schema_v2(payload: Dict[str, Any], *, label: str = "payload") -> List[str]:
    # For now v2 is structurally compatible with v1 invariants (cfg/tasks/indices/meta).
    return _validate_common(payload, label=label, expect_version=2)


def validate_payload(payload: Dict[str, Any], *, label: str = "payload") -> List[str]:
    if not isinstance(payload, dict):
        return [f"{label}: payload must be a dict/object"]
    sv = payload.get("schema_version")
    if sv == 1:
        return validate_schema_v1(payload, label=label)
    if sv == 2:
        return validate_schema_v2(payload, label=label)
    if isinstance(sv, int):
        return [f"Unsupported schema_version: {sv} (latest={LATEST_SCHEMA_VERSION})"]
    return [f"{label}: schema_version must be an int"]


def assert_valid_payload(payload: Dict[str, Any]) -> None:
    # Keep the exact unsupported-schema wording relied upon by tools/tests.
    if not isinstance(payload, dict):
        raise PayloadValidationError("payload must be a JSON object")
    sv = payload.get("schema_version")
    if isinstance(sv, int) and sv not in (1, 2):
        raise PayloadValidationError(f"Unsupported schema_version: {sv} (latest={LATEST_SCHEMA_VERSION})")
    errs = validate_payload(payload, label="payload")
    if errs:
        raise PayloadValidationError(errs[0])


__all__ = [
    "LATEST_SCHEMA_VERSION",
    "PayloadValidationError",
    "assert_valid_payload",
    "validate_payload",
    "validate_schema_v1",
    "validate_schema_v2",
]
