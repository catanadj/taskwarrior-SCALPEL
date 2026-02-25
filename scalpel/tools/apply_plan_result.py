#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from scalpel.ai import apply_plan_result, load_plan_result
from scalpel.schema import upgrade_payload


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-apply-plan-result] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-apply-plan-result",
        description="Apply an AI plan result JSON to a payload JSON.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--plan", required=True, help="AI plan result JSON path")
    ap.add_argument("--out", required=True, help="Output payload JSON path")
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        payload_raw = _load_json(in_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    try:
        plan = load_plan_result(Path(ns.plan))
    except Exception as e:
        return _die(f"Failed to load plan result: {e}")

    payload = upgrade_payload(payload_raw)
    try:
        out_payload = apply_plan_result(payload, plan)
    except Exception as e:
        return _die(f"Failed to apply plan result: {e}")

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
