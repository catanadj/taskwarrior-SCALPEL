#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload


class DdminError(RuntimeError):
    pass


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-ddmin] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise DdminError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _infer_schema(payload: Dict[str, Any], requested: Optional[int]) -> int:
    cur = payload.get("schema_version")
    cur_i = int(cur) if isinstance(cur, int) else 0
    if requested is None:
        req = cur_i if cur_i >= 1 else 1
    else:
        req = int(requested)
        if req < 1:
            req = 1
    return max(cur_i, req)  # never downgrade


def _get_tasks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return []
    out: List[Dict[str, Any]] = []
    for t in tasks:
        if isinstance(t, dict):
            out.append(t)
    return out


def _with_tasks(payload: Dict[str, Any], tasks: List[Dict[str, Any]], schema: int) -> Dict[str, Any]:
    p = dict(payload)
    p["tasks"] = tasks
    p.pop("indices", None)  # force rebuild
    return upgrade_payload(p, target_version=schema)  # type: ignore[arg-type]


def _cmd_replace(cmd: str, in_path: Path) -> List[str]:
    # Supports "{in}" placeholder; if absent, appends the path.
    if "{in}" in cmd:
        cmd = cmd.replace("{in}", str(in_path))
        return ["bash", "-lc", cmd]
    return ["bash", "-lc", f"{cmd} {str(in_path)}"]


def _fails(cmd: str, payload: Dict[str, Any], schema: int, timeout_s: int) -> bool:
    # Write candidate payload to a temp file and run command.
    with tempfile.TemporaryDirectory(prefix="scalpel-ddmin-") as td:
        p = Path(td) / "payload.json"
        # NOTE: payload already prepared by caller; just dump it.
        p.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

        argv = _cmd_replace(cmd, p)
        try:
            r = subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=float(timeout_s))
        except subprocess.TimeoutExpired:
            return False  # treat timeout as non-failure persistence
        return r.returncode != 0


@dataclass
class DdminCfg:
    cmd: str
    timeout_s: int
    max_tests: int


def ddmin_tasks(base_payload: Dict[str, Any], tasks: List[Dict[str, Any]], *, cfg: DdminCfg, schema: int) -> List[Dict[str, Any]]:
    # Classic ddmin over list elements.
    cur = list(tasks)
    if not cur:
        return cur

    tests = 0

    def test(candidate: List[Dict[str, Any]]) -> bool:
        nonlocal tests
        if tests >= cfg.max_tests:
            return False
        tests += 1
        p = _with_tasks(base_payload, candidate, schema=schema)
        return _fails(cfg.cmd, p, schema=schema, timeout_s=cfg.timeout_s)

    # Ensure the starting payload actually fails; otherwise no shrink possible.
    if not test(cur):
        return cur

    n = 2
    while len(cur) >= 2:
        if tests >= cfg.max_tests:
            break

        # Partition into n chunks
        chunks: List[List[Dict[str, Any]]] = []
        size = (len(cur) + n - 1) // n
        for i in range(0, len(cur), size):
            chunks.append(cur[i : i + size])

        reduced = False

        # Try each chunk alone
        for c in chunks:
            if tests >= cfg.max_tests:
                break
            if test(c):
                cur = c
                n = 2
                reduced = True
                break

        if reduced:
            continue

        # Try complements (remove one chunk)
        for c in chunks:
            if tests >= cfg.max_tests:
                break
            comp = [x for x in cur if x not in c]
            if not comp:
                continue
            if test(comp):
                cur = comp
                n = max(n - 1, 2)
                reduced = True
                break

        if reduced:
            continue

        if n >= len(cur):
            break
        n = min(len(cur), n * 2)

    return cur


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scalpel-ddmin-shrink", description="Delta-debug shrink a payload to a minimal task set that preserves a failure.")
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON")
    ap.add_argument("--out", required=True, help="Output minimized payload JSON")
    ap.add_argument("--cmd", required=True, help="Command to run; must fail (non-zero) to be considered reproducing. Use {in} placeholder.")
    ap.add_argument("--timeout", type=int, default=20, help="Timeout (seconds) per test run")
    ap.add_argument("--max-tests", type=int, default=200, help="Maximum number of test invocations")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print output")
    ap.add_argument(
        "--schema",
        type=int,
        default=LATEST_SCHEMA_VERSION,
        help="Target schema version (default: latest supported; never downgrades input).",
    )
    
    ns = ap.parse_args(argv)
    # SCALPEL_SCHEMA_SELECT_4_1
    # Schema selection: default to latest; never downgrade input.
    _req_schema = getattr(ns, 'schema', None)
    try:
        _req_schema_i = int(_req_schema) if _req_schema is not None else int(LATEST_SCHEMA_VERSION)
    except Exception:
        _req_schema_i = int(LATEST_SCHEMA_VERSION)
    if _req_schema_i < 1:
        _req_schema_i = 1
    if _req_schema_i > int(LATEST_SCHEMA_VERSION):
        # Keep error text consistent across tools.
        raise SystemExit(f"--schema {_req_schema_i} unsupported (latest={LATEST_SCHEMA_VERSION})")
    

    inp = Path(ns.in_json)
    if not inp.exists():
        return _die(f"Missing input: {inp}")

    try:
        raw = _load_json(inp)
    except Exception as e:
        return _die(f"Failed to parse JSON: {inp} ({e})")

    req_schema = int(ns.schema) if ns.schema is not None else int(LATEST_SCHEMA_VERSION)
    if req_schema > int(LATEST_SCHEMA_VERSION):
        return _die(f"--schema {req_schema} is unsupported (latest={{LATEST_SCHEMA_VERSION}})")

    schema = _infer_schema(raw, ns.schema)
    base = upgrade_payload(raw, target_version=schema)  # type: ignore[arg-type]
    tasks = _get_tasks(base)

    cfg = DdminCfg(cmd=str(ns.cmd), timeout_s=int(ns.timeout), max_tests=int(ns.max_tests))
    kept = ddmin_tasks(base, tasks, cfg=cfg, schema=schema)

    out_payload = _with_tasks(base, kept, schema=schema)

    outp = Path(ns.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    if ns.pretty:
        txt = json.dumps(out_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        txt = json.dumps(out_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"

    outp.write_text(txt, encoding="utf-8")
    print(f"[scalpel-ddmin] OK: {outp} (tasks={len(kept)} schema={out_payload.get('schema_version')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
