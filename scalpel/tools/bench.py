#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload
from scalpel.validate import validate_payload
from scalpel.query_lang import Query, QueryError


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-bench] ERROR: {msg}", file=sys.stderr)
    return rc


def _now_ns() -> int:
    return time.perf_counter_ns()


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _time_one(fn, *, repeats: int, warmup: int) -> Tuple[float, float, float]:
    for _ in range(max(0, warmup)):
        fn()

    samples_ms: List[float] = []
    for _ in range(max(1, repeats)):
        t0 = _now_ns()
        fn()
        t1 = _now_ns()
        samples_ms.append((t1 - t0) / 1_000_000.0)

    return (min(samples_ms), statistics.fmean(samples_ms), max(samples_ms))


def _target_schema_for_payload(payload: Dict[str, Any], requested: int) -> int:
    """Never downgrade. If input is already newer than requested, keep newer."""
    v = payload.get("schema_version")
    cur = int(v) if isinstance(v, int) else 0
    requested = int(requested) if isinstance(requested, int) else 1
    if requested < 1:
        requested = 1
    return max(cur, requested)


def _scale_payload_tasks(payload: Dict[str, Any], n: int, seed: int, schema: int) -> Dict[str, Any]:
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        tasks = []
    tasks = [t for t in tasks if isinstance(t, dict)]

    if n <= 0 or not tasks:
        p = dict(payload)
        p["tasks"] = []
        p.pop("indices", None)
        return upgrade_payload(p, target_version=schema)  # type: ignore[arg-type]

    rng = random.Random(seed)
    out_tasks: List[Dict[str, Any]] = []
    for i in range(n):
        t = dict(tasks[rng.randrange(len(tasks))])
        # Ensure uuid uniqueness so indices stay meaningful.
        u = t.get("uuid")
        u = str(u) if isinstance(u, str) and u else f"scaled-{i}"
        t["uuid"] = f"{u}-{i:06d}"
        out_tasks.append(t)

    p = dict(payload)
    p["tasks"] = out_tasks
    # Force indices rebuild in the upgrader.
    p.pop("indices", None)
    return upgrade_payload(p, target_version=schema)  # type: ignore[arg-type]


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scalpel-bench", description="Micro-benchmark SCALPEL core operations.")
    ap.add_argument("--in", dest="in_json", default="tests/fixtures/golden_payload_v1.json", help="Base payload JSON path")
    ap.add_argument("--n", type=int, default=250, help="Number of tasks to benchmark against (scaled from base fixture)")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for task scaling")
    ap.add_argument("--repeats", type=int, default=1, help="Measurement repeats (min/avg/max over repeats)")
    ap.add_argument("--warmup", type=int, default=0, help="Warmup runs per step before measuring")
    ap.add_argument(
        "--schema",
        type=int,
        default=LATEST_SCHEMA_VERSION,
        help="Target schema version (default: latest supported; never downgrades input).",
    )
    ap.add_argument("--q", default=None, help="Optional query to run (Query.parse surface)")
    ap.add_argument("--no-render", action="store_true", help="Skip render benchmark (fast-path mode)")
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
    

    base_path = Path(ns.in_json)
    if not base_path.exists():
        return _die(f"Missing input JSON: {base_path}")

    try:
        base_payload = _load_json(base_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {base_path} ({e})")

    req_schema = int(ns.schema) if ns.schema is not None else int(LATEST_SCHEMA_VERSION)
    if req_schema > int(LATEST_SCHEMA_VERSION):
        return _die(f"--schema {req_schema} is unsupported (latest={{LATEST_SCHEMA_VERSION}})")

    schema = _target_schema_for_payload(base_payload, int(ns.schema) if ns.schema is not None else int(LATEST_SCHEMA_VERSION))
    payload = _scale_payload_tasks(base_payload, int(ns.n), int(ns.seed), schema)

    print(f"[scalpel-bench] base={base_path} n={ns.n} seed={ns.seed} repeats={ns.repeats} warmup={ns.warmup} schema={schema}")

    def _normalize() -> None:
        _ = upgrade_payload(payload, target_version=schema)  # type: ignore[arg-type]

    def _validate() -> None:
        errs = validate_payload(payload)
        if errs:
            raise RuntimeError("invalid payload: " + "; ".join(errs[:5]))

    def _query() -> None:
        # If no query is provided, exercise a tiny deterministic surface.
        qs = [ns.q] if ns.q else [r"description~\\[", r"description!~\\[", "status:pending"]
        for s in qs:
            try:
                q = Query.parse(s)
                _ = q.run(payload)
            except QueryError as e:
                raise RuntimeError(f"query failed: {s!r} ({e})") from e

    mn, av, mx = _time_one(_normalize, repeats=int(ns.repeats), warmup=int(ns.warmup))
    print(f"[scalpel-bench] normalize: {mn:.2f}/{av:.2f}/{mx:.2f} ms (min/avg/max)")

    mn, av, mx = _time_one(_validate, repeats=int(ns.repeats), warmup=int(ns.warmup))
    print(f"[scalpel-bench] validate:  {mn:.2f}/{av:.2f}/{mx:.2f} ms (min/avg/max)")

    mn, av, mx = _time_one(_query, repeats=int(ns.repeats), warmup=int(ns.warmup))
    print(f"[scalpel-bench] query:     {mn:.2f}/{av:.2f}/{mx:.2f} ms (min/avg/max)")

    if bool(ns.no_render):
        print("[scalpel-bench] render:    (skipped: --no-render)")
        return 0

    # Lazy import to keep fast-path lean.
    from scalpel.render.inline import build_html  # type: ignore

    def _render() -> None:
        html = build_html(payload)
        if not isinstance(html, str) or len(html) < 10:
            raise RuntimeError("render produced unexpected output")

    mn, av, mx = _time_one(_render, repeats=int(ns.repeats), warmup=int(ns.warmup))
    print(f"[scalpel-bench] render:    {mn:.2f}/{av:.2f}/{mx:.2f} ms (min/avg/max)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())