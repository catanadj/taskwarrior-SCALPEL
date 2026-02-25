#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from scalpel.ai import AiPlanResult, PlanOverride
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
    print(f"[scalpel-ai-plan-stub] ERROR: {msg}", file=sys.stderr)
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


def _pick_op(prompt: str) -> str:
    p = (prompt or "").lower()
    if "align end" in p or "align ends" in p:
        return "align-ends"
    if "align start" in p or "align starts" in p:
        return "align-starts"
    if "distribute" in p:
        return "distribute"
    if "stack" in p:
        return "stack"
    if "nudge" in p or "shift" in p or "move" in p:
        return "nudge"
    return "nudge"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-ai-plan-stub",
        description="Stub AI planner: turns prompt + selection into a deterministic plan result JSON.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--selected", required=True, help="JSON file with selected UUIDs array")
    ap.add_argument("--prompt", default="", help="User prompt (used for op selection and notes)")
    ap.add_argument("--out", required=True, help="Output plan result JSON path")
    ap.add_argument("--snap", type=int, default=10, help="Snap minutes for align/stack/distribute (default: 10)")
    ap.add_argument("--delta", type=int, default=30, help="Delta minutes for nudge (default: 30)")
    ap.add_argument(
        "--plan-schema",
        choices=["v1", "v2"],
        default="v1",
        help="Plan schema to write (default: v1)",
    )
    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json)
    if not in_path.exists():
        return _die(f"Missing input JSON: {in_path}")

    try:
        payload_raw = _load_json(in_path)
        payload = upgrade_payload(payload_raw)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    try:
        selected = _load_selected(Path(ns.selected))
    except Exception as e:
        return _die(f"Failed to load selected uuids: {e}")

    cfg = payload.get("cfg", {}) if isinstance(payload.get("cfg"), dict) else {}
    tz_name = cfg.get("tz") if isinstance(cfg.get("tz"), str) else "UTC"

    events = apply_overrides(payload.get("tasks", []), {}, cfg)
    op_name = _pick_op(ns.prompt)

    if op_name == "align-starts":
        overrides = op_align_starts(selected, events, int(ns.snap), tz_name=tz_name)
    elif op_name == "align-ends":
        overrides = op_align_ends(selected, events, int(ns.snap), tz_name=tz_name)
    elif op_name == "stack":
        overrides = op_stack(selected, events, int(ns.snap), tz_name=tz_name)
    elif op_name == "distribute":
        overrides = op_distribute(selected, events, int(ns.snap), tz_name=tz_name)
    else:
        overrides = op_nudge(selected, events, int(ns.delta))

    result = AiPlanResult(
        overrides=overrides,
        added_tasks=(),
        task_updates={},
        warnings=(),
        notes=(f"stub-op:{op_name}", ns.prompt.strip()) if ns.prompt.strip() else (f"stub-op:{op_name}",),
        model_id="stub-v1",
    )

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    def _base36(n: int) -> str:
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        if n == 0:
            return "0"
        sign = ""
        if n < 0:
            sign = "-"
            n = -n
        out = []
        while n:
            n, r = divmod(n, 36)
            out.append(alphabet[r])
        return sign + "".join(reversed(out))

    if ns.plan_schema == "v2":
        slot_catalog = {}
        ops = []
        for k, v in result.overrides.items():
            sid = f"S{_base36(int(v.start_ms))}"
            slot_catalog[sid] = {"start_ms": int(v.start_ms), "due_ms": int(v.due_ms)}
            ops.append({"op": "place", "target": k, "slot_id": sid})

        data = {
            "schema": "scalpel.plan.v2",
            "ops": ops,
            "slot_catalog": slot_catalog,
            "warnings": list(result.warnings),
            "notes": list(result.notes),
            "model_id": result.model_id,
        }
    else:
        data = {
            "schema": "scalpel.plan.v1",
            "overrides": {
                k: {"start_ms": v.start_ms, "due_ms": v.due_ms, "duration_min": v.duration_min}
                for k, v in result.overrides.items()
            },
            "added_tasks": list(result.added_tasks),
            "task_updates": result.task_updates,
            "warnings": list(result.warnings),
            "notes": list(result.notes),
            "model_id": result.model_id,
        }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
