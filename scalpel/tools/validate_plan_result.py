#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from scalpel.ai import validate_plan_result


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-validate-plan-result] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"plan result must be a JSON object; got {type(obj).__name__}")
    return obj


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-validate-plan-result",
        description="Validate an AI plan result JSON file.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input plan JSON path")
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        obj = _load_json(in_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    errs = validate_plan_result(obj)
    if errs:
        for e in errs[:50]:
            print(f"[scalpel-validate-plan-result] ERROR: {e}", file=sys.stderr)
        return 3

    print("[scalpel-validate-plan-result] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
