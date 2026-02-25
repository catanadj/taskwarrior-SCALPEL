#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is on sys.path when executed as a script.
# (Unit tests invoke this generator via `python3 scripts/...py`.)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from scalpel.bench import make_large_payload_v1

def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-fixtures] ERROR: {msg}", file=sys.stderr)
    return rc

def _read_json(p: Path) -> Dict[str, Any]:
    obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be dict; got {type(obj).__name__}")
    return obj

def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scalpel-fixtures-generate-large", description="Generate deterministic large schema v1 payload fixture.")
    ap.add_argument("--base", default="tests/fixtures/golden_payload_v1.json", help="Base fixture JSON path")
    ap.add_argument("--out", default="tests/fixtures/golden_payload_large_v1.json", help="Output fixture JSON path")
    ap.add_argument("--n", type=int, default=1000, help="Number of tasks to generate")
    ap.add_argument("--seed", type=int, default=1, help="Deterministic expansion seed")
    ns = ap.parse_args(argv)

    base = Path(ns.base)
    if not base.exists():
        return _die(f"Missing base fixture: {base}")
    try:
        p = _read_json(base)
    except Exception as e:
        return _die(f"Failed to parse base fixture: {base} ({e})")

    out_payload = make_large_payload_v1(p, n_tasks=int(ns.n), seed=int(ns.seed))

    outp = Path(ns.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[scalpel-fixtures] OK: wrote: {outp} (n={ns.n}, seed={ns.seed})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
