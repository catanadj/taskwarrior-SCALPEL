# scalpel/schema_contracts/v2.py
from __future__ import annotations

from typing import Any, Dict, List


def _require(cond: bool, msg: str, errs: List[str]) -> None:
    if not cond:
        errs.append(msg)


def validate_payload_v2(payload: Dict[str, Any]) -> List[str]:
    """Schema v2 contract validator.

    Keep error strings stable: tests and CLI output rely on them.
    Returns a list of human-readable issues (empty means OK).

    Timezone contract:
      - cfg.tz and cfg.display_tz must be non-empty strings.
      - cfg.view_start_ms must be midnight in cfg.tz.
    """
    errs: List[str] = []

    _require(payload.get("schema_version") == 2, "schema_version must be 2", errs)

    cfg = payload.get("cfg")
    tasks = payload.get("tasks")
    indices = payload.get("indices")

    _require(isinstance(cfg, dict), "cfg must be dict", errs)
    _require(isinstance(tasks, list), "tasks must be list", errs)
    _require(isinstance(indices, dict), "indices must be dict", errs)

    ga = payload.get("generated_at")
    meta = payload.get("meta")
    if not isinstance(ga, str) and isinstance(meta, dict):
        ga = meta.get("generated_at")
    _require(isinstance(ga, str) and bool(ga), "generated_at must be non-empty string", errs)

    if isinstance(cfg, dict):
        tz = cfg.get("tz")
        display_tz = cfg.get("display_tz")
        _require(isinstance(tz, str) and bool(str(tz).strip()), "cfg.tz must be non-empty string", errs)
        _require(
            isinstance(display_tz, str) and bool(str(display_tz).strip()),
            "cfg.display_tz must be non-empty string",
            errs,
        )
        if isinstance(cfg.get("view_start_ms"), int) and isinstance(tz, str) and tz.strip():
            try:
                from scalpel.util.tz import is_midnight_ms, resolve_tz

                if not is_midnight_ms(int(cfg["view_start_ms"]), resolve_tz(tz)):
                    errs.append("cfg.view_start_ms must be midnight in cfg.tz")
            except Exception:
                errs.append("cfg.view_start_ms must be midnight in cfg.tz")
        if "px_per_min" in cfg:
            px = cfg.get("px_per_min")
            _require(
                isinstance(px, (int, float)) and not isinstance(px, bool),
                "cfg.px_per_min must be number",
                errs,
            )

    if isinstance(indices, dict):
        for k in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
            _require(k in indices, f"indices missing key: {k}", errs)
        _require(isinstance(indices.get("by_uuid"), dict), "indices.by_uuid must be dict", errs)

    # Indices value types (pre-release contract):
    #  - by_uuid: {uuid: int_index}
    #  - by_status/by_project/by_tag/by_day: {key: [int_index, ...]}
    if isinstance(indices, dict):
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

    if isinstance(tasks, list):
        for i, t in enumerate(tasks):
            if not isinstance(t, dict):
                errs.append(f"tasks[{i}] must be dict")
                continue
            u = t.get("uuid")
            _require(isinstance(u, str) and u.strip(), f"tasks[{i}].uuid must be non-empty string", errs)
            st = t.get("status")
            _require(isinstance(st, str) and bool(st), f"tasks[{i}].status must be non-empty string", errs)
            tags = t.get("tags")
            _require(isinstance(tags, list), f"tasks[{i}].tags must be list", errs)

    if isinstance(tasks, list) and isinstance(indices, dict) and isinstance(indices.get("by_uuid"), dict):
        by_uuid = indices["by_uuid"]
        for u, idx in list(by_uuid.items())[:2000]:
            if not isinstance(u, str) or not u:
                errs.append("indices.by_uuid contains non-string/empty uuid key")
                break
            if not isinstance(idx, int):
                errs.append(f"indices.by_uuid[{u!r}] must be int index")
                continue
            if idx < 0 or idx >= len(tasks):
                errs.append(f"indices.by_uuid[{u!r}] out of range: {idx} (tasks={len(tasks)})")
                continue
            t = tasks[idx]
            if isinstance(t, dict) and str(t.get("uuid") or "") != u:
                errs.append(f"indices.by_uuid[{u!r}] points to tasks[{idx}] with uuid={t.get('uuid')!r}")

    return errs
