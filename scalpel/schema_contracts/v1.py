# scalpel/schema_contracts/v1.py
from __future__ import annotations

from typing import Any


def validate_payload_v1(p: dict[str, Any]) -> list[str]:
    """Central, reusable contract for schema_version=1 payloads.

    Return: list of human-readable error strings (empty means OK).
    Keep this strict on keys/types; keep error strings stable.

    Timezone contract:
      - cfg.tz and cfg.display_tz must be non-empty strings.
      - cfg.view_start_ms must be midnight in cfg.tz.
    """
    errs: list[str] = []

    if not isinstance(p, dict):
        return [f"payload must be dict (got {type(p).__name__})"]

    if p.get("schema_version") != 1:
        errs.append("schema_version must be 1")

    if not isinstance(p.get("generated_at"), str) or not p.get("generated_at"):
        errs.append("generated_at must be a non-empty string")

    cfg = p.get("cfg")
    if not isinstance(cfg, dict):
        errs.append("cfg must be dict")
        cfg = {}
    else:
        req_int = [
            "view_start_ms",
            "days",
            "work_start_min",
            "work_end_min",
            "snap_min",
            "default_duration_min",
        ]
        if not isinstance(cfg.get("view_key"), str) or not cfg.get("view_key"):
            errs.append("cfg.view_key must be a non-empty string")
        for k in req_int:
            if k not in cfg:
                errs.append(f"cfg missing key: {k}")
                continue
            if not isinstance(cfg.get(k), int):
                errs.append(f"cfg.{k} must be int")
        if "px_per_min" in cfg:
            px = cfg.get("px_per_min")
            if not isinstance(px, (int, float)) or isinstance(px, bool):
                errs.append("cfg.px_per_min must be number")

    # TZ contract
    tz = cfg.get("tz")
    display_tz = cfg.get("display_tz")
    if not (isinstance(tz, str) and tz.strip()):
        errs.append("cfg.tz must be non-empty string")
    if not (isinstance(display_tz, str) and display_tz.strip()):
        errs.append("cfg.display_tz must be non-empty string")

    if isinstance(cfg.get("view_start_ms"), int) and isinstance(tz, str) and tz.strip():
        try:
            from scalpel.util.tz import is_midnight_ms, resolve_tz

            if not is_midnight_ms(int(cfg["view_start_ms"]), resolve_tz(tz)):
                errs.append("cfg.view_start_ms must be midnight in cfg.tz")
        except Exception:
            # If tz can't be resolved, validator should still flag as contract breach.
            errs.append("cfg.view_start_ms must be midnight in cfg.tz")

    tasks = p.get("tasks")
    if not isinstance(tasks, list):
        errs.append("tasks must be list")
    else:
        for i, t in enumerate(tasks[:200]):
            if not isinstance(t, dict):
                errs.append(f"tasks[{i}] must be dict")
                continue
            if "uuid" not in t:
                errs.append(f"tasks[{i}] missing uuid")

    indices = p.get("indices")
    if not isinstance(indices, dict):
        errs.append("indices must be dict")
        indices = {}

    for k in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
        if k not in indices:
            errs.append(f"indices missing key: {k}")

    if isinstance(indices, dict):
        if not isinstance(indices.get("by_uuid"), dict):
            errs.append("indices.by_uuid must be dict")
        for name in ("by_status", "by_project", "by_tag", "by_day"):
            m = indices.get(name)
            if not isinstance(m, dict):
                errs.append(f"indices.{name} must be dict")
                continue
            for k, v in list(m.items())[:50]:
                if not isinstance(v, list):
                    errs.append(f"indices.{name}[{k!r}] must be list")
                    break
                for idx in v[:200]:
                    if not isinstance(idx, int):
                        errs.append(f"indices.{name}[{k!r}] must be list[int]")
                        break
                else:
                    continue
                break

    meta = p.get("meta")
    if meta is not None and not isinstance(meta, dict):
        errs.append("meta must be dict when present")

    return errs
