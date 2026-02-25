#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scalpel.html_extract import extract_payload_json_from_html_file
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload

try:
    from scalpel.schema_contracts.v1 import validate_payload_v1  # type: ignore
except Exception:  # pragma: no cover
    validate_payload_v1 = None  # type: ignore

try:
    from scalpel.schema_contracts.v2 import validate_payload_v2  # type: ignore
except Exception:  # pragma: no cover
    validate_payload_v2 = None  # type: ignore


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-validate-payload] ERROR: {msg}", file=sys.stderr)
    return rc


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _load_payload_from_json(p: Path) -> Dict[str, Any]:
    obj = json.loads(_read_text(p))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _declared_schema(payload: Dict[str, Any]) -> int:
    v = payload.get("schema_version")
    return int(v) if isinstance(v, int) else 0


def _validate_schema(payload: Dict[str, Any], schema: int) -> List[str]:
    if schema == 1:
        if validate_payload_v1 is None:
            return ["schema v1 validator not available"]
        return list(validate_payload_v1(payload))
    if schema == 2:
        if validate_payload_v2 is None:
            return ["schema v2 validator not available"]
        return list(validate_payload_v2(payload))
    return [f"unsupported schema_version: {schema!r}"]


def _resolve_target_schema(payload_raw: Dict[str, Any], requested: int) -> int:
    """Resolve the schema to validate.

    requested:
      - 0 => auto
      - 1..LATEST => explicit

    Auto policy:
      - If payload declares schema_version 1/2 => validate that schema *as-is*
      - If payload declares nothing (0) => validate latest (after upgrade)

    Explicit policy:
      - Never downgrade. If input declares v2 and requested=1 => error.
      - If requested>declared => allow upgrade.
    """
    declared = _declared_schema(payload_raw)

    if declared > int(LATEST_SCHEMA_VERSION):
        raise ValueError(f"Unsupported schema_version: {declared} (latest={LATEST_SCHEMA_VERSION})")

    if requested == 0:
        return declared if declared >= 1 else int(LATEST_SCHEMA_VERSION)

    if requested < 1:
        return 1
    if requested > int(LATEST_SCHEMA_VERSION):
        raise ValueError(f"--schema {requested} unsupported (latest={LATEST_SCHEMA_VERSION})")

    if declared >= 1 and requested < declared:
        raise ValueError(f"Refusing to downgrade input schema_version={declared} to --schema {requested}")

    return requested


def _prepare_for_schema(payload_raw: Dict[str, Any], target_schema: int, *, requested: int) -> Dict[str, Any]:
    """Prepare payload for validation at target_schema."""
    declared = _declared_schema(payload_raw)

    # Auto + declared schema means "validate as-is".
    if requested == 0 and declared == target_schema and declared >= 1:
        return payload_raw

    # Explicit schema==1 means "validate raw v1" (no upgrade).
    if requested != 0 and target_schema == 1:
        return payload_raw

    # Otherwise, upgrade to requested schema.
    return upgrade_payload(payload_raw, target_version=int(target_schema))  # type: ignore[arg-type]


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-validate-payload",
        description=(
            "Validate SCALPEL payload from JSON and/or HTML.\n"
            "Default behavior is auto: validate the declared schema version as-is.\n"
            "Use --schema N to validate schema N (upgrading legacy inputs when needed).\n"
            "Never downgrades: passing --schema 1 for a v2 input is an error."
        ),
    )
    ap.add_argument("--in", dest="in_json", default=None, help="Input payload JSON path")
    ap.add_argument(
        "--from-html",
        dest="from_html",
        default=None,
        help="Extract payload from HTML path (embedded JSON script block)",
    )
    ap.add_argument(
        "--write-json",
        default=None,
        help="If using --from-html, write extracted (and possibly upgraded) payload JSON to this path",
    )
    ap.add_argument(
        "--schema",
        type=int,
        default=0,
        help="Target schema version to validate (0=auto; default).",
    )
    ns = ap.parse_args(argv)

    requested_schema = int(ns.schema) if isinstance(ns.schema, int) else 0

    if not ns.in_json and not ns.from_html:
        return _die("Provide --in and/or --from-html")

    all_errs: List[str] = []

    def _validate_one(*, src: str, payload_raw: Dict[str, Any], write_json_path: Optional[Path] = None) -> None:
        nonlocal all_errs
        target_schema = _resolve_target_schema(payload_raw, requested_schema)
        payload = _prepare_for_schema(payload_raw, target_schema, requested=requested_schema)

        if write_json_path is not None:
            write_json_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )

        errs = _validate_schema(payload, target_schema)
        all_errs.extend([f"{src}: {e}" for e in errs])

    if ns.in_json:
        p = Path(ns.in_json)
        if not p.exists():
            return _die(f"Missing JSON file: {p}")
        try:
            payload_raw = _load_payload_from_json(p)
            _validate_one(src=f"json:{p}", payload_raw=payload_raw)
        except Exception as e:
            return _die(f"Failed to load/validate JSON payload: {p} ({e})")

    if ns.from_html:
        p = Path(ns.from_html)
        if not p.exists():
            return _die(f"Missing HTML file: {p}")
        try:
            raw = extract_payload_json_from_html_file(p)
            if not isinstance(raw, dict):
                raise ValueError(f"HTML payload must be an object/dict; got {type(raw).__name__}")
            outp = Path(ns.write_json) if ns.write_json else None
            _validate_one(src=f"html:{p}", payload_raw=raw, write_json_path=outp)
        except Exception as e:
            return _die(f"Failed to extract/validate payload from HTML: {p} ({e})")

    if all_errs:
        print("[scalpel-validate-payload] FAIL", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        return 3

    print("[scalpel-validate-payload] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
