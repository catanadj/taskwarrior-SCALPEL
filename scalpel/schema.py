# scalpel/schema.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from scalpel.schema_v1 import apply_schema_v1 as _apply_schema_v1

SCHEMA_NAME_V2 = "scalpel.payload"
LATEST_SCHEMA_VERSION = 2


# --- Schema appliers ----------------------------------------------------------

def apply_schema_v1(payload: Any) -> Any:
    """Upgrade payload to schema v1.

    This is a thin delegator to scalpel.schema_v1.apply_schema_v1 so we keep a
    single source of truth for v1 normalization and indexing.
    """
    return _apply_schema_v1(payload)


def apply_schema_v2(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade payload to schema v2 (additive + idempotent).

    v2 currently:
      - schema_version = 2
      - meta.schema = {name: 'scalpel.payload', version: 2}

    Note: v2 relies on v1 invariants for normalized tasks + indices.
    """
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict; got {type(payload).__name__}")

    if (
        payload.get("schema_version") == 2
        and isinstance(payload.get("meta"), dict)
        and isinstance(payload.get("meta", {}).get("schema"), dict)
        and payload.get("meta", {}).get("schema", {}).get("name") == SCHEMA_NAME_V2
        and payload.get("meta", {}).get("schema", {}).get("version") == 2
    ):
        return payload

    out = dict(payload)
    out["schema_version"] = 2

    meta_in = out.get("meta")
    meta: Dict[str, Any]
    if isinstance(meta_in, dict):
        meta = dict(meta_in)
    else:
        meta = {}

    schema_in = meta.get("schema")
    schema: Dict[str, Any]
    if isinstance(schema_in, dict):
        schema = dict(schema_in)
    else:
        schema = {}

    schema["name"] = SCHEMA_NAME_V2
    schema["version"] = 2
    meta["schema"] = schema

    out["meta"] = meta
    return out


# --- Validators (library-facing convenience) ---------------------------------

def validate_schema_v1(payload: Dict[str, Any], *, label: str) -> List[str]:
    from scalpel.schema_contracts.v1 import validate_payload_v1

    errs = validate_payload_v1(payload)
    return [f"{label}: {e}" for e in errs]


def validate_schema_v2(payload: Dict[str, Any], *, label: str) -> List[str]:
    from scalpel.schema_contracts.v2 import validate_payload_v2

    errs = validate_payload_v2(payload)
    return [f"{label}: {e}" for e in errs]


# --- Upgrader ----------------------------------------------------------------

def _coerce_version(v: Any) -> int:
    return int(v) if isinstance(v, int) else 0


def _has_tz_contract(payload: Dict[str, Any]) -> bool:
    """Return True if payload has cfg.tz/display_tz and view_start_ms is midnight in cfg.tz."""
    cfg = payload.get("cfg")
    if not isinstance(cfg, dict):
        return False
    tz = cfg.get("tz")
    disp = cfg.get("display_tz")
    if not (isinstance(tz, str) and tz.strip()):
        return False
    if not (isinstance(disp, str) and disp.strip()):
        return False
    vs = cfg.get("view_start_ms")
    if not isinstance(vs, int):
        return False

    try:
        from scalpel.util.tz import is_midnight_ms, resolve_tz

        return is_midnight_ms(vs, resolve_tz(tz))
    except Exception:
        return False


def _has_v2_envelope(payload: Dict[str, Any]) -> bool:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return False
    schema = meta.get("schema")
    if not isinstance(schema, dict):
        return False
    return (
        payload.get("schema_version") == 2
        and schema.get("name") == SCHEMA_NAME_V2
        and schema.get("version") == 2
    )


def upgrade_payload(payload: Any, target_version: Optional[int] = None) -> Any:
    """Upgrade payload to target_version (default: latest). Never downgrades.

    If input claims schema_version=2 but is missing v1 invariants (notably
    indices) or tz invariants (cfg.tz/cfg.display_tz), we repair by passing
    through v1 normalization, then re-applying v2.
    """
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict; got {type(payload).__name__}")

    req = LATEST_SCHEMA_VERSION if target_version is None else int(target_version)
    if req < 1:
        req = 1

    cur = _coerce_version(payload.get("schema_version"))

    target = max(cur, req) if cur >= 1 else req

    if target > LATEST_SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version: {target} (latest={LATEST_SCHEMA_VERSION})")
    if cur > LATEST_SCHEMA_VERSION:
        raise ValueError(f"Unsupported input schema_version: {cur} (latest={LATEST_SCHEMA_VERSION})")

    if target == 1:
        return apply_schema_v1(payload)

    # target == 2
    if cur >= 2 and isinstance(payload.get("indices"), dict) and _has_tz_contract(payload):
        if _has_v2_envelope(payload):
            return payload
        return apply_schema_v2(payload)

    out = apply_schema_v1(payload)
    if not isinstance(out, dict):
        raise TypeError("apply_schema_v1 returned non-dict")
    return apply_schema_v2(out)


if __name__ == "__main__":
    raise SystemExit("scalpel.schema is a library module")
