#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from scalpel.ai import apply_plan_overrides, load_plan_overrides
from scalpel.planner import (
    apply_overrides,
    op_align_ends,
    op_align_starts,
    op_distribute,
    op_nudge,
    op_stack,
)
from scalpel.schema import upgrade_payload


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-plan-ops] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _load_selected(path: Path) -> List[str]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, list):
        raise ValueError("selected uuids must be a JSON list")
    out: List[str] = []
    for u in obj:
        if isinstance(u, str) and u.strip():
            out.append(u.strip())
    return out


def _op_func(name: str):
    name = name.lower().strip()
    if name == "align-starts":
        return op_align_starts
    if name == "align-ends":
        return op_align_ends
    if name == "stack":
        return op_stack
    if name == "distribute":
        return op_distribute
    if name == "nudge":
        return op_nudge
    raise ValueError(f"Unknown op: {name}")


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-plan-ops",
        description="Apply planner ops to a payload JSON and emit overrides.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--out", default=None, help="Write updated payload JSON to this path")
    ap.add_argument("--overrides-in", default=None, help="Existing plan overrides JSON to layer on")
    ap.add_argument("--overrides-out", default=None, help="Write merged plan overrides JSON to this path")
    ap.add_argument("--selected", required=True, help="JSON file with selected UUIDs array")
    ap.add_argument("--op", required=True, help="Operation: align-starts|align-ends|stack|distribute|nudge")
    ap.add_argument("--snap", type=int, default=10, help="Snap minutes for align/stack/distribute (default: 10)")
    ap.add_argument("--delta", type=int, default=0, help="Delta minutes for nudge (default: 0)")
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        payload_raw = _load_json(in_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    payload = upgrade_payload(payload_raw)  # normalize indices, tz, etc.

    try:
        selected = _load_selected(Path(ns.selected))
    except Exception as e:
        return _die(f"Failed to load selected uuids: {e}")

    overrides = {}
    if ns.overrides_in:
        try:
            overrides = load_plan_overrides(Path(ns.overrides_in))
        except Exception as e:
            return _die(f"Failed to load overrides: {e}")

    cfg = payload.get("cfg", {}) if isinstance(payload.get("cfg"), dict) else {}
    tz_name = cfg.get("tz") if isinstance(cfg.get("tz"), str) else "UTC"

    events = apply_overrides(payload.get("tasks", []), overrides, cfg)
    try:
        op = _op_func(ns.op)
        if op is op_nudge:
            new_overrides = op(selected, events, int(ns.delta))
        else:
            new_overrides = op(selected, events, int(ns.snap), tz_name=tz_name)
    except Exception as e:
        return _die(str(e))

    merged = dict(overrides)
    merged.update(new_overrides)

    if ns.overrides_out:
        out_path = Path(ns.overrides_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: {"start_ms": v.start_ms, "due_ms": v.due_ms, "duration_min": v.duration_min} for k, v in merged.items()}
        out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if ns.out:
        try:
            updated = apply_plan_overrides(payload, merged)
            out_path = Path(ns.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception as e:
            return _die(f"Failed to apply overrides: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
