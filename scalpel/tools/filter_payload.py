#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scalpel.api import filter_payload
from scalpel.html_extract import extract_payload_json_from_html_file
from scalpel.validate import assert_valid_payload


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-filter-payload] ERROR: {msg}", file=sys.stderr)
    return rc


def _read_json(p: Path) -> dict:
    obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError(f"payload must be an object/dict; got {type(obj).__name__}")
    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scalpel-filter-payload", description="Filter a SCALPEL payload using scalpel query language.")
    ap.add_argument("--in", dest="in_json", default=None, help="Input payload JSON path")
    ap.add_argument("--from-html", dest="from_html", default=None, help="Extract payload from HTML path (script#tw-data or DATA=...)")
    ap.add_argument("--q", required=True, help="Query string (scalpel/query_lang)")
    ap.add_argument("--out", required=True, help="Output payload JSON path")
    ap.add_argument("--pretty", action="store_true", help="Pretty JSON output")
    ns = ap.parse_args(argv)

    if not ns.in_json and not ns.from_html:
        return _die("Provide --in and/or --from-html")

    # Load (JSON takes precedence if both provided)
    payload: dict
    if ns.in_json:
        p = Path(ns.in_json)
        if not p.exists():
            return _die(f"Missing JSON file: {p}")
        try:
            payload = _read_json(p)
        except Exception as e:
            return _die(f"Failed to parse JSON payload: {p} ({e})")
    else:
        p = Path(ns.from_html)
        if not p.exists():
            return _die(f"Missing HTML file: {p}")
        try:
            payload = extract_payload_json_from_html_file(p)
            if not isinstance(payload, dict):
                return _die(f"HTML payload must be an object/dict; got {type(payload).__name__}")
        except Exception as e:
            return _die(f"Failed to extract payload from HTML: {p} ({e})")

    # Filter and validate
    try:
        outp = filter_payload(payload, ns.q)
        assert_valid_payload(outp)
    except Exception as e:
        return _die(f"Filter/validate failed: {e}", rc=3)

    out_path = Path(ns.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(outp, ensure_ascii=False, indent=2 if ns.pretty else None)
    out_path.write_text(txt + "\n", encoding="utf-8", newline="\n")

    print(f"[scalpel-filter-payload] OK: wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
