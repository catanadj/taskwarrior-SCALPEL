from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from ..api import load_payload_from_json
from .render import render_agenda
from .source import snapshot_from_payload
from .style import color_enabled


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scalpel-glimpse",
        description="Read-only terminal calendar view for SCALPEL.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="scalpel-glimpse (agenda)",
    )
    parser.add_argument("--payload", type=Path, required=True, help="SCALPEL payload JSON to render")
    parser.add_argument("--width", type=int, default=80, help="Maximum output width (default: 80)")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = load_payload_from_json(args.payload)
        cfg = payload.get("cfg", {})
        view_start_ms = cfg.get("view_start_ms") if isinstance(cfg, dict) else None
        timezone_name = str(cfg.get("display_tz") or cfg.get("tz") or "UTC") if isinstance(cfg, dict) else "UTC"
        start_date = dt.date.fromisoformat(str(cfg.get("view_key")).split("/")[0]) if isinstance(cfg, dict) and isinstance(cfg.get("view_key"), str) and len(str(cfg.get("view_key")).split("/")[0]) == 10 else dt.date.today()
        if isinstance(view_start_ms, int):
            start_date = dt.datetime.fromtimestamp(view_start_ms / 1000, tz=dt.timezone.utc).date()
        snapshot = snapshot_from_payload(
            payload,
            start_date=start_date,
            days=int(cfg.get("days", 1)) if isinstance(cfg, dict) else 1,
            timezone_name=timezone_name,
        )
        print(render_agenda(snapshot, width=args.width, color=color_enabled(requested=not args.no_color)))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"scalpel-glimpse: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
