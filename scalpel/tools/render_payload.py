#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from scalpel.ai import apply_plan_overrides, apply_plan_result, load_plan_overrides, load_plan_result
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload
from scalpel.validate import validate_payload


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-render] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _declared_schema(payload: Dict[str, Any]) -> int:
    v = payload.get("schema_version")
    return int(v) if isinstance(v, int) else 0


def _pick_target_schema(payload: Dict[str, Any], requested: int) -> int:
    declared = _declared_schema(payload)

    if declared > int(LATEST_SCHEMA_VERSION):
        raise ValueError(f"Unsupported schema_version: {declared} (latest={LATEST_SCHEMA_VERSION})")

    req = int(requested)
    if req < 1:
        req = 1
    if req > int(LATEST_SCHEMA_VERSION):
        raise ValueError(f"--schema {req} unsupported (latest={LATEST_SCHEMA_VERSION})")

    # Never downgrade: explicit and loud.
    if declared >= 1 and req < declared:
        raise ValueError(f"Refusing to downgrade input schema_version={declared} to --schema {req}")

    # Also never downgrade implicitly.
    return max(declared, req)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-render-payload",
        description="Render a payload JSON to an HTML replay page.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--out", required=True, help="Output HTML path")
    ap.add_argument("--strict", action="store_true", help="Enable strict HTML checks (if available)")
    ap.add_argument("--plan-overrides", default=None, help="JSON file of plan overrides to apply")
    ap.add_argument("--plan-result", default=None, help="JSON file of AI plan result to apply")
    ap.add_argument(
        "--schema",
        type=int,
        default=int(LATEST_SCHEMA_VERSION),
        help="Target schema to upgrade to before rendering (default: latest). Never downgrades.",
    )
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        payload_raw = _load_json(in_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    try:
        target = _pick_target_schema(payload_raw, int(ns.schema))
    except Exception as e:
        return _die(str(e))

    # Default behavior: upgrade to v2 (latest). This is the v2-default lock.
    payload = payload_raw
    if _declared_schema(payload_raw) != target or _declared_schema(payload_raw) < 1:
        payload = upgrade_payload(payload_raw, target_version=int(target))  # type: ignore[arg-type]

    if ns.plan_overrides:
        try:
            overrides = load_plan_overrides(Path(ns.plan_overrides))
            payload = apply_plan_overrides(payload, overrides)
        except Exception as e:
            return _die(f"Failed to apply plan overrides: {e}")
    if ns.plan_result:
        try:
            plan = load_plan_result(Path(ns.plan_result))
            payload = apply_plan_result(payload, plan)
        except Exception as e:
            return _die(f"Failed to apply plan result: {e}")

    # Validate (on a deep copy to avoid accidental mutation).
    errs = validate_payload(copy.deepcopy(payload))
    if errs:
        msg = "; ".join(errs[:10])
        return _die(f"Invalid payload: {msg}", rc=3)

    # Render by embedding JSON directly into the HTML template marker.
    # This guarantees extract_payload_json_from_html_file(replay.html) == embedded payload (dict-equal).
    try:
        from scalpel.render.template import HTML_TEMPLATE  # type: ignore
    except Exception as e:
        return _die(f"Failed to import HTML_TEMPLATE: {e}")

    marker = "__DATA_JSON__"
    n = HTML_TEMPLATE.count(marker)
    if n != 1:
        return _die(f"HTML_TEMPLATE must contain {marker} exactly once (found {n})")

    data_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    html = HTML_TEMPLATE.replace(marker, data_json)

    if bool(ns.strict):
        # Best-effort: strict checks are optional for the tool.
        try:
            from scalpel.html_checks import basic_html_checks  # type: ignore
        except Exception:
            basic_html_checks = None
        if basic_html_checks is not None:
            try:
                basic_html_checks(html, strict=True)  # type: ignore[misc]
            except Exception as e:
                return _die(f"Strict HTML checks failed: {e}", rc=4)

    out = Path(ns.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")

    print(f"[scalpel-render] OK: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
