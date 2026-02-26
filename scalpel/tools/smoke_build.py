#!/usr/bin/env python3
"""
scalpel smoke build

Goals:
  - Generate a minimal scalpel HTML using scalpel.render.inline.build_html()
    without requiring Taskwarrior.
  - Run basic invariants so refactors fail fast (avoid blank page surprises).

Usage:
  PYTHONPATH=/path/to/repo python -m scalpel.tools.smoke_build --out build/scalpel_smoke.html
"""

import sys
sys.dont_write_bytecode = True
import argparse
import os
import datetime as dt
import json
from pathlib import Path
from typing import Any
from scalpel.render.inline import build_html
from scalpel.schema import upgrade_payload, LATEST_SCHEMA_VERSION
from scalpel.render.template import HTML_TEMPLATE
from scalpel.util.tz import normalize_tz_name, resolve_tz, midnight_epoch_ms, today_date

MARKER = "__DATA_JSON__"


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-smoke-build] ERROR: {msg}", file=sys.stderr)
    return rc

def _embed_payload_html(payload: dict, *, pretty: bool) -> str:
    n = HTML_TEMPLATE.count(MARKER)
    if n != 1:
        raise RuntimeError(f"HTML_TEMPLATE must contain {MARKER} exactly once (found {n})")

    if pretty:
        data_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    return HTML_TEMPLATE.replace(MARKER, data_json)


def _midnight_ms(d: dt.date, tz_name: str) -> int:
    return midnight_epoch_ms(d, resolve_tz(tz_name))


def _ymd(d: dt.date) -> str:
    return d.isoformat()


def _synthetic_tasks(view_start_ms: int) -> list[dict[str, Any]]:
    """A tiny task set that exercises planned + unplanned cases."""
    # Put one planned task inside working hours on day 0.
    s0 = view_start_ms + 9 * 60 * 60 * 1000
    d0 = s0 + 30 * 60 * 1000
    return [
        {
            "uuid": "00000000-0000-0000-0000-000000000001",
            "id": 1,
            "description": "SMOKE: Planned task",
            "project": "smoke",
            "tags": ["smoke"],
            "priority": "",
            "urgency": 1.0,
            "scheduled_ms": s0,
            "due_ms": d0,
            "duration": "PT30M",
        },
        {
            "uuid": "00000000-0000-0000-0000-000000000002",
            "id": 2,
            "description": "SMOKE: Unplanned task (no due/scheduled)",
            "project": "smoke",
            "tags": ["smoke"],
            "priority": "",
            "urgency": 1.0,
            "scheduled_ms": None,
            "due_ms": None,
            "duration": "PT10M",
        },
    ]


def _make_cfg(*, view_key: str, view_start_ms: int, days: int, px_per_min: int, work: str, snap: int, default_duration_min: int) -> dict[str, Any]:
    # work is "HH:MM-HH:MM"
    try:
        a, b = work.split("-", 1)
        h1, m1 = a.split(":", 1)
        h2, m2 = b.split(":", 1)
        work_start_min = int(h1) * 60 + int(m1)
        work_end_min = int(h2) * 60 + int(m2)
    except Exception as e:
        raise SystemExit(f"Invalid --work '{work}'. Expected HH:MM-HH:MM") from e

    if days < 1:
        raise SystemExit("--days must be >= 1")
    if work_end_min <= work_start_min:
        raise SystemExit("--work end must be after start")

    return {
        "view_key": view_key,
        "view_start_ms": int(view_start_ms),
        "days": int(days),
        "px_per_min": int(px_per_min),
        "work_start_min": int(work_start_min),
        "work_end_min": int(work_end_min),
        "snap_min": int(snap),
        "default_duration_min": int(default_duration_min),
        "max_infer_duration_min": int(default_duration_min * 6),
    }


def _basic_html_checks(html: str, *, strict: bool = False) -> None:
    # Keep these checks intentionally broad, to avoid brittleness across refactors.
    if not isinstance(html, str) or len(html) < 5000:
        raise RuntimeError(f"Smoke HTML too small ({len(html)} chars) — likely blank/failed injection.")

    # Template markers should never leak.
    for marker in ("__DATA_JSON__", "__CSS_BLOCK__", "__JS_BLOCK__", "__BODY_MARKUP__"):
        if marker in html:
            raise RuntimeError(f"Template marker {marker} still present in generated HTML.")

    # HTML should contain a DATA assignment (template convention).
    if "const DATA" not in html and "var DATA" not in html and "DATA =" not in html:
        raise RuntimeError("Generated HTML does not appear to contain DATA bootstrap.")

    # A minimal sanity check that we have at least some tasks in the payload text.
    if "SMOKE: Planned task" not in html:
        raise RuntimeError("Expected synthetic task label missing from HTML output.")

    if not strict:
        return

    # STRICT HTML invariants (golden contract)
    import json
    import re

    # Shell invariants
    if "<!doctype html>" not in html.lower():
        raise RuntimeError("Strict: missing <!doctype html>.")
    if "<title>Taskwarrior Calendar</title>" not in html:
        raise RuntimeError("Strict: missing expected <title>Taskwarrior Calendar</title>.")
    if '<meta charset="utf-8"' not in html.lower():
        raise RuntimeError("Strict: missing meta charset utf-8.")

    # Required DOM anchor IDs (public-ish UI contract)
    required_ids = [
        # data bootstrap
        "tw-data",
        # header controls
        "meta",
        "selMeta",
        "zoom",
        "zoomVal",
        "viewwin",
        "vwToday",
        "btnCopy",
        # main panels
        "calendar",
        "backlog",
        "commands",
        # overlays / add modal
        "addModal",
        "addLines",
    ]
    for id_ in required_ids:
        n = html.count(f'id="{id_}"')
        if n != 1:
            raise RuntimeError(f"Strict: expected id={id_!r} exactly once (found {n}).")

    # Extract and validate embedded JSON payload (must be parseable)
    m = re.search(
        r'<script\s+id="tw-data"\s+type="application/json">\s*(.*?)\s*</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise RuntimeError('Strict: missing <script id="tw-data" type="application/json"> payload.')

    raw = m.group(1).strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Strict: tw-data JSON not parseable: {e}") from e

    if not isinstance(payload, dict):
        raise RuntimeError("Strict: tw-data payload is not a dict.")

    for k in ("cfg", "tasks", "meta"):
        if k not in payload:
            raise RuntimeError(f"Strict: tw-data missing key: {k}")

    cfg = payload.get("cfg", {})
    if not isinstance(cfg, dict):
        raise RuntimeError("Strict: cfg is not a dict.")

    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list) or len(tasks) < 2:
        raise RuntimeError(f"Strict: expected >=2 tasks, got {len(tasks) if isinstance(tasks, list) else type(tasks)}")

    descs = [t.get("description", "") for t in tasks if isinstance(t, dict)]
    if not any("SMOKE: Planned task" in d for d in descs):
        raise RuntimeError("Strict: synthetic planned task description missing from tasks payload.")

    def _parse_dt_any(s: str):
        """Parse a datetime string in either ISO or Taskwarrior compact forms. Returns aware UTC datetime or None."""
        if not s or not isinstance(s, str):
            return None
        ss = s.strip()
        # TW compact: YYYYMMDDTHHMMSSZ
        m = __import__("re").match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$", ss)
        if m:
            y, mo, d, hh, mm, sec = map(int, m.groups())
            from datetime import datetime, timezone
            return datetime(y, mo, d, hh, mm, sec, tzinfo=timezone.utc)
        # ISO-ish with Z
        try:
            from datetime import datetime, timezone
            iso = ss.replace("Z", "+00:00") if ss.endswith("Z") else ss
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None


    def _dt_to_iso_z(dt):
        if dt is None:
            return None
        try:
            from datetime import timezone
            dt = dt.astimezone(timezone.utc)
            return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except Exception:
            return None


    def _ms(dt):
        if dt is None:
            return None
        try:
            return int(dt.timestamp() * 1000)
        except Exception:
            return None


    def _normalize_tags(v):
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if str(x)]
        if isinstance(v, str):
            vv = v.strip()
            if not vv:
                return []
            # Accept either comma or whitespace separated
            if "," in vv:
                return [x.strip() for x in vv.split(",") if x.strip()]
            return [x for x in vv.split() if x]
        return [str(v)]


    def _normalize_task_v1(t: dict) -> dict:
        """Return a normalized task dict suitable for UI consumption."""
        if not isinstance(t, dict):
            t = {"description": str(t)}

        uuid = t.get("uuid") or t.get("id") or ""
        uuid = str(uuid)

        desc = t.get("description") or ""
        desc = str(desc)

        status = t.get("status") or "pending"
        status = str(status)

        project = t.get("project")
        project = str(project) if project is not None else None

        tags = _normalize_tags(t.get("tags"))

        # Canonicalize common datetime fields
        due_dt = _parse_dt_any(t.get("due")) if isinstance(t.get("due"), str) else None
        start_dt = _parse_dt_any(t.get("start")) if isinstance(t.get("start"), str) else None
        end_dt = _parse_dt_any(t.get("end")) if isinstance(t.get("end"), str) else None

        due_iso = _dt_to_iso_z(due_dt) or (t.get("due") if isinstance(t.get("due"), str) else None)
        start_iso = _dt_to_iso_z(start_dt) or (t.get("start") if isinstance(t.get("start"), str) else None)
        end_iso = _dt_to_iso_z(end_dt) or (t.get("end") if isinstance(t.get("end"), str) else None)

        due_ts = _ms(due_dt)
        start_ts = _ms(start_dt)
        end_ts = _ms(end_dt)

        # Prefer day bucket: due -> start -> end
        day_dt = due_dt or start_dt or end_dt
        day_key = day_dt.date().isoformat() if day_dt is not None else None

        duration_min = None
        if start_ts is not None and end_ts is not None and end_ts >= start_ts:
            duration_min = int((end_ts - start_ts) / 60000)

        out = dict(t)  # preserve existing fields
        out.update(
            {
                "uuid": uuid,
                "description": desc,
                "status": status,
                "project": project,
                "tags": tags,
                "due": due_iso,
                "start": start_iso,
                "end": end_iso,
                "due_ts": due_ts,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "day_key": day_key,
                "duration_min": duration_min,
            }
        )
        return out


    def _build_indices_v1(tasks: list[dict]) -> dict:
        by_uuid: dict[str, int] = {}
        by_status: dict[str, list[int]] = {}
        by_project: dict[str, list[int]] = {}
        by_tag: dict[str, list[int]] = {}
        by_day: dict[str, list[int]] = {}

        for i, t in enumerate(tasks):
            if not isinstance(t, dict):
                continue
            u = str(t.get("uuid") or "")
            if not u:
                continue
            by_uuid[u] = i

            st = str(t.get("status") or "pending")
            by_status.setdefault(st, []).append(i)

            pr = t.get("project")
            if pr:
                by_project.setdefault(str(pr), []).append(i)

            for tag in (t.get("tags") or []):
                by_tag.setdefault(str(tag), []).append(i)

            dk = t.get("day_key")
            if dk:
                by_day.setdefault(str(dk), []).append(i)

        return {
            "by_uuid": by_uuid,
            "by_status": by_status,
            "by_project": by_project,
            "by_tag": by_tag,
            "by_day": by_day,
        }


    def _apply_schema_v1(payload: dict) -> dict:
        """Idempotently upgrade payload to schema v1 (versioned, normalized, indexed)."""
        if not isinstance(payload, dict):
            return payload
        if payload.get("schema_version") == 1 and isinstance(payload.get("indices"), dict):
            return payload

        from datetime import datetime, timezone

        out = dict(payload)
        out["schema_version"] = 1
        out["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        tasks = out.get("tasks") or []
        if not isinstance(tasks, list):
            tasks = []
        tasks_n = [_normalize_task_v1(t) for t in tasks]
        out["tasks"] = tasks_n

        out["indices"] = _build_indices_v1(tasks_n)
        return out
    # === /SCALPEL SCHEMA V1 HELPERS ===
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scalpel-smoke-build")
    p.add_argument("--out", required=True, help="Output HTML path")
    p.add_argument("--out-json", default=None, help="Optional JSON payload output path (schema v1/v2)")
    p.add_argument("--days", type=int, default=7, help="Number of future days to render")
    p.add_argument("--start", default=None, help="Start day (YYYY-MM-DD). Default: today")
    p.add_argument("--view-key", default="smoke", help="cfg.view_key")
    p.add_argument("--px-per-min", type=int, default=2, help="Vertical scale")
    p.add_argument("--work", default="08:00-17:00", help="Working window HH:MM-HH:MM")
    p.add_argument("--snap", type=int, default=5, help="Snap minutes")
    p.add_argument("--default-duration-min", type=int, default=30, help="Default duration in minutes")
    p.add_argument("--pretty", action="store_true", help="Pretty-print embedded JSON (debug; increases size)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict smoke gating (stronger HTML invariants).",
    )
# SCALPEL_SMOKE_SCHEMA_V2: allow emitting schema v1 or v2 (default v1)
    p.add_argument(
        "--schema",
        type=int,
        default=int(os.getenv("SCALPEL_SCHEMA_VERSION", str(LATEST_SCHEMA_VERSION))),
        help="Target schema version for payload.json + embedded HTML (default: latest)",
    )

    p.add_argument(
        "--tz",
        default=os.getenv("SCALPEL_TZ", "local"),
        help="Bucketing timezone for day boundaries (default: env SCALPEL_TZ or 'local')",
    )
    p.add_argument(
        "--display-tz",
        default=os.getenv("SCALPEL_DISPLAY_TZ", "local"),
        help="Display timezone hint (default: env SCALPEL_DISPLAY_TZ or 'local')",
    )

    args = p.parse_args(argv)
    # SCALPEL_SCHEMA_SELECT_4_1
    # Schema selection: default to latest; never downgrade input.
    _req_schema = getattr(args, 'schema', None)
    try:
        _req_schema_i = int(_req_schema) if _req_schema is not None else int(LATEST_SCHEMA_VERSION)
    except Exception:
        _req_schema_i = int(LATEST_SCHEMA_VERSION)
    if _req_schema_i < 1:
        _req_schema_i = 1
    if _req_schema_i > int(LATEST_SCHEMA_VERSION):
        # Keep error text consistent across tools.
        raise SystemExit(f"--schema {_req_schema_i} unsupported (latest={LATEST_SCHEMA_VERSION})")
    

    if args.start:
        try:
            y, m, d = [int(x) for x in args.start.split("-")]
            start_date = dt.date(y, m, d)
        except Exception as e:
            raise SystemExit(f"Invalid --start '{args.start}'. Expected YYYY-MM-DD") from e
    else:
        # Default: today in --tz (not process-local).
        tz_name = normalize_tz_name(getattr(args, 'tz', os.getenv('SCALPEL_TZ', 'local')))
        try:
            start_date = today_date(resolve_tz(tz_name))
        except ValueError as e:
            raise SystemExit(f"Invalid --tz value: {e}")
    tz_name = normalize_tz_name(getattr(args, 'tz', os.getenv('SCALPEL_TZ', 'local')))
    display_tz = normalize_tz_name(getattr(args, 'display_tz', os.getenv('SCALPEL_DISPLAY_TZ', 'local')))
    try:
        resolve_tz(tz_name)
        resolve_tz(display_tz)
    except ValueError as e:
        raise SystemExit(f"Invalid timezone value: {e}")



    view_start_ms = _midnight_ms(start_date, tz_name)

    cfg = _make_cfg(
        view_key=str(args.view_key),
        view_start_ms=view_start_ms,
        days=int(args.days),
        px_per_min=int(args.px_per_min),
        work=str(args.work),
        snap=int(args.snap),
        default_duration_min=int(args.default_duration_min),
    )
    cfg["tz"] = tz_name
    cfg["display_tz"] = display_tz
    tasks = _synthetic_tasks(view_start_ms)

    payload = {
        "cfg": cfg,
        "tasks": tasks,
        "meta": {
            "generated_by": "scalpel.tools.smoke_build",
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "start_ymd": _ymd(start_date),
        },
    }
    # Upgrade payload ONCE (this is the single source of truth from here on)
    schema_req = int(getattr(args, "schema", int(LATEST_SCHEMA_VERSION)))
    if schema_req < 1:
        schema_req = 1
    if schema_req > int(LATEST_SCHEMA_VERSION):
        return _die(f"--schema {schema_req} unsupported (latest={LATEST_SCHEMA_VERSION})")

    payload = upgrade_payload(payload, target_version=schema_req)  # type: ignore[arg-type]

    # Canonical JSON blob used BOTH for --out-json and HTML embedding
    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if bool(getattr(args, "pretty", False)) else None,
    ) + "\n"

    if getattr(args, "out_json", None):
        outp = Path(args.out_json)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(payload_json, encoding="utf-8")

    marker = "__DATA_JSON__"
    if HTML_TEMPLATE.count(marker) != 1:
        return _die(f"HTML template marker {marker!r} must occur exactly once")

    html = HTML_TEMPLATE.replace(marker, payload_json.rstrip("\n"))

    # Optional sanity: strict checks verify embedded payload parses and validates.
    _basic_html_checks(html, strict=bool(getattr(args, "strict", False)))

    out_html = Path(args.out)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")

    print(f"[scalpel] smoke html: {out_html}")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
