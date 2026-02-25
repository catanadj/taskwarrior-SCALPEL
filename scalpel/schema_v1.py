# scalpel/schema_v1.py
from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List, Optional

from scalpel.util.tz import (
    day_key_from_ms,
    is_midnight_ms,
    midnight_epoch_ms,
    normalize_tz_name,
    resolve_tz,
)


def _utc_iso_z_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_tags(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x)]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if "," in s:
            return [x.strip() for x in s.split(",") if x.strip()]
        return [x for x in s.split() if x]
    return [str(v)]


def _parse_duration_to_minutes(raw: Any) -> Optional[int]:
    # Prefer existing normalized minutes if already present
    try:
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
    except Exception:
        return None

    try:
        from .util.duration import parse_duration_to_minutes

        return parse_duration_to_minutes(s)
    except Exception:
        return None


def normalize_task_v1(t: Any, *, tz: dt.tzinfo) -> Dict[str, Any]:
    """Normalize a single task dict for schema v1 indices/query semantics.

    Timezone contract:
      - `day_key` is derived in the payload's `cfg.tz` timezone.
    """
    if not isinstance(t, dict):
        t = {"description": "" if t is None else str(t)}

    out: Dict[str, Any] = dict(t)

    def _as_str(v: Any, default: str = "") -> str:
        if v is None:
            return default
        if isinstance(v, str):
            return v
        try:
            return str(v)
        except Exception:
            return default

    def _as_opt_str(v: Any) -> str | None:
        s = _as_str(v, "").strip()
        return s or None

    def _coerce_int(v: Any) -> int | None:
        if v is None or isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            if v != v or v in (float("inf"), float("-inf")):
                return None
            return int(v)
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                if any(ch in s for ch in ".eE"):
                    return int(float(s))
                return int(s)
            except Exception:
                return None
        return None

    uuid_val = out.get("uuid") or out.get("id") or ""
    out["uuid"] = _as_str(uuid_val, "").strip()

    out["description"] = _as_str(out.get("description"), "")
    st = _as_str(out.get("status"), "pending").strip().lower()
    out["status"] = st or "pending"
    out["project"] = _as_opt_str(out.get("project"))

    out["tags"] = _normalize_tags(out.get("tags"))

    for k in ("due_ms", "scheduled_ms", "start_calc_ms", "end_calc_ms"):
        if k in out:
            out[k] = _coerce_int(out.get(k))

    dm_i = _coerce_int(out.get("duration_min"))
    if dm_i is not None:
        out["duration_min"] = dm_i
    else:
        if out.get("duration_min") is None:
            parsed = _parse_duration_to_minutes(out.get("duration"))
            if parsed is not None:
                out["duration_min"] = int(parsed)

    dk = out.get("day_key")
    if isinstance(dk, str) and dk.strip():
        out["day_key"] = dk.strip()
    else:
        # Prefer day bucket: due -> scheduled -> start_calc -> end_calc
        out["day_key"] = (
            day_key_from_ms(out.get("due_ms"), tz)
            or day_key_from_ms(out.get("scheduled_ms"), tz)
            or day_key_from_ms(out.get("start_calc_ms"), tz)
            or day_key_from_ms(out.get("end_calc_ms"), tz)
        )

    return out


def build_indices_v1(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_uuid: Dict[str, int] = {}
    by_status: Dict[str, List[int]] = {}
    by_project: Dict[str, List[int]] = {}
    by_tag: Dict[str, List[int]] = {}
    by_day: Dict[str, List[int]] = {}

    for i, t in enumerate(tasks):
        u = str(t.get("uuid") or "")
        if not u:
            continue
        by_uuid[u] = i

        st = str(t.get("status") or "pending")
        by_status.setdefault(st, []).append(i)

        pr = t.get("project")
        if pr:
            by_project.setdefault(str(pr), []).append(i)

        for tag in (t.get("tags") or []):
            by_tag.setdefault(str(tag), []).append(i)

        dk = t.get("day_key")
        if dk:
            by_day.setdefault(str(dk), []).append(i)

    return {
        "by_uuid": by_uuid,
        "by_status": by_status,
        "by_project": by_project,
        "by_tag": by_tag,
        "by_day": by_day,
    }


def _indices_look_like_int_indices(indices: Any) -> bool:
    """Best-effort check whether indices maps are list[int] (not legacy UUID lists)."""
    if not isinstance(indices, dict):
        return False
    if not isinstance(indices.get("by_uuid"), dict):
        return False
    for name in ("by_status", "by_project", "by_tag", "by_day"):
        m = indices.get(name)
        if not isinstance(m, dict):
            return False
        for _, v in list(m.items())[:25]:
            if not isinstance(v, list):
                return False
            for idx in v[:50]:
                if not isinstance(idx, int):
                    return False
    return True


def _ensure_cfg_tz(cfg: dict) -> tuple[str, str, dt.tzinfo]:
    """Ensure cfg has tz fields and return (tz_name, display_tz, tzinfo).

    Policy:
      - If cfg.tz is explicitly provided, respect it.
      - Otherwise, default from env SCALPEL_TZ (if set) or "local".
      - If cfg.display_tz is explicitly provided, respect it.
      - Otherwise, default from env SCALPEL_DISPLAY_TZ (if set) or "local".

    This keeps interactive UX intuitive (local bucketing) while allowing
    deterministic builds/fixtures by pinning SCALPEL_TZ=UTC.
    """

    tz_explicit = isinstance(cfg.get("tz"), str) and bool(str(cfg.get("tz")).strip())
    disp_explicit = isinstance(cfg.get("display_tz"), str) and bool(str(cfg.get("display_tz")).strip())

    tz_name = normalize_tz_name(str(cfg.get("tz")).strip() if tz_explicit else os.getenv("SCALPEL_TZ", "local"))
    display_tz = normalize_tz_name(
        str(cfg.get("display_tz")).strip() if disp_explicit else os.getenv("SCALPEL_DISPLAY_TZ", "local")
    )

    tzinfo = resolve_tz(tz_name)

    cfg["tz"] = tz_name
    cfg["display_tz"] = display_tz
    return tz_name, display_tz, tzinfo


def _repair_view_start_ms(cfg: dict, *, tz: dt.tzinfo) -> None:
    vs = cfg.get("view_start_ms")
    if not isinstance(vs, int):
        return
    if is_midnight_ms(vs, tz):
        return

    # Snap to midnight in cfg.tz of the view_start_ms's day in cfg.tz.
    try:
        d = dt.datetime.fromtimestamp(vs / 1000.0, tz=tz).date()
        cfg["view_start_ms"] = midnight_epoch_ms(d, tz)
    except Exception:
        # Leave as-is; contract validator will flag.
        return


def apply_schema_v1(payload: Any) -> Any:
    """Upgrade payload to schema v1 (additive + idempotent).

    Adds (or rebuilds if missing/invalid):
      - schema_version = 1
      - generated_at (top-level UTC ISO Z)  [preserved if already present + valid]
      - cfg.tz / cfg.display_tz (timezone contract)
      - normalized tasks (uuid/status/tags/day_key/duration_min + ms coercions)
      - indices (by_uuid/by_status/by_project/by_tag/by_day)
    """
    if not isinstance(payload, dict):
        return payload

    out = dict(payload)

    cfg_in = out.get("cfg")
    cfg = dict(cfg_in) if isinstance(cfg_in, dict) else {}
    _, _, tzinfo = _ensure_cfg_tz(cfg)
    _repair_view_start_ms(cfg, tz=tzinfo)
    out["cfg"] = cfg

    # Fast-path: only if schema is v1, indices look correct, and tz contract is present.
    if (
        out.get("schema_version") == 1
        and _indices_look_like_int_indices(out.get("indices"))
        and isinstance(cfg.get("tz"), str)
        and isinstance(cfg.get("display_tz"), str)
    ):
        return out

    out["schema_version"] = 1

    ga = out.get("generated_at")
    if not (isinstance(ga, str) and ga.strip()):
        out["generated_at"] = _utc_iso_z_now()

    tasks_raw = out.get("tasks")
    if not isinstance(tasks_raw, list):
        tasks_raw = []

    tasks = [normalize_task_v1(t, tz=tzinfo) for t in tasks_raw]
    out["tasks"] = tasks
    out["indices"] = build_indices_v1(tasks)

    return out
