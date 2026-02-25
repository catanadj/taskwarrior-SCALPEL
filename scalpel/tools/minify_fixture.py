#!/usr/bin/env python3
# SCALPEL_MINIFY_FIXTURE_V5_REWRITE
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from scalpel.query_lang import Query, QueryError
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload
from scalpel.validate import validate_payload


class MinifyError(RuntimeError):
    pass


def _die(msg: str, rc: int = 2) -> int:
    print(f"[scalpel-minify] ERROR: {msg}", file=sys.stderr)
    return rc


def _load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise MinifyError(f"payload must be a JSON object; got {type(obj).__name__}")
    return obj


def _dump_json(obj: Dict[str, Any], *, pretty: bool) -> bytes:
    # Deterministic encoding.
    if pretty:
        s = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return (s + "\n").encode("utf-8")


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _normalize_schema_request(payload: Dict[str, Any], requested: Optional[int]) -> int:
    """
    Default: latest schema.
    Never downgrade below input schema_version (if present).
    """
    cur = payload.get("schema_version")
    cur_i = int(cur) if isinstance(cur, int) else 0

    if requested is None:
        req = int(LATEST_SCHEMA_VERSION)
    else:
        req = int(requested)

    if req < 1:
        req = 1

    # Never downgrade input.
    out = max(cur_i, req)

    if out > int(LATEST_SCHEMA_VERSION):
        raise MinifyError(f"--schema {out} unsupported (latest={LATEST_SCHEMA_VERSION})")

    return out


def _build_indices(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Indices contract (matches Query implementation expectations):
      - by_uuid: {uuid: int_index}
      - by_status/by_project/by_tag/by_day: {key: [int_index, ...]}
    """
    by_uuid: Dict[str, int] = {}
    by_status: Dict[str, List[int]] = {}
    by_project: Dict[str, List[int]] = {}
    by_tag: Dict[str, List[int]] = {}
    by_day: Dict[str, List[int]] = {}

    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue

        u = t.get("uuid")
        if isinstance(u, str):
            u = u.strip()
        else:
            u = str(u).strip() if u is not None else ""
        if u and u not in by_uuid:
            by_uuid[u] = i

        st = t.get("status")
        st_s = st.strip() if isinstance(st, str) else str(st).strip() if st is not None else ""
        if st_s:
            by_status.setdefault(st_s, []).append(i)

        proj = t.get("project")
        proj_s = proj.strip() if isinstance(proj, str) else ""
        if proj_s:
            by_project.setdefault(proj_s, []).append(i)

        tags = t.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                tag_s = tag.strip() if isinstance(tag, str) else ""
                if tag_s:
                    by_tag.setdefault(tag_s, []).append(i)

        day = t.get("day_key")
        day_s = day.strip() if isinstance(day, str) else ""
        if day_s:
            by_day.setdefault(day_s, []).append(i)

    return {
        "by_uuid": by_uuid,
        "by_status": by_status,
        "by_project": by_project,
        "by_tag": by_tag,
        "by_day": by_day,
    }


def _ensure_indices(payload: Dict[str, Any]) -> Dict[str, Any]:
    tasks = payload.get("tasks")
    tasks_list: List[Dict[str, Any]] = []
    if isinstance(tasks, list):
        tasks_list = [t for t in tasks if isinstance(t, dict)]
    out = dict(payload)
    out["tasks"] = tasks_list
    out["indices"] = _build_indices(tasks_list)
    return out


def _manifest_upsert(
    manifest_path: Path,
    *,
    name: str,
    out_path: Path,
    payload: Dict[str, Any],
    blob: bytes,
) -> None:
    """
    Deterministic manifest upsert.

    Manifest shape (LIST for contract stability):
      [
        {"name": "...", "path": "...", "sha256": "...", "schema_version": 2, "tasks": 1},
        ...
      ]
    """
    entries: List[Dict[str, Any]] = []

    if manifest_path.exists():
        raw = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(raw, list):
            entries = [e for e in raw if isinstance(e, dict)]

    try:
        rel = str(out_path.relative_to(manifest_path.parent))
    except Exception:
        rel = str(out_path)

    tasks = payload.get("tasks")
    n_tasks = len(tasks) if isinstance(tasks, list) else 0
    v = payload.get("schema_version")
    v_i = int(v) if isinstance(v, int) else 0

    new_entry = {
        "name": str(name),
        "path": rel,
        "sha256": _sha256(blob),
        "schema_version": v_i,
        "tasks": n_tasks,
    }

    kept: List[Dict[str, Any]] = []
    for e in entries:
        if str(e.get("name", "")) != str(name):
            kept.append(e)
    kept.append(new_entry)

    # Deterministic order.
    kept.sort(key=lambda d: str(d.get("name", "")))

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-minify-fixture",
        description="Create a minimized payload fixture from an input payload + query.",
    )
    ap.add_argument("--in", dest="in_json", required=True, help="Input payload JSON path")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--q", required=True, help="Query expression (see scalpel.query_lang)")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print output JSON")
    ap.add_argument(
        "--schema",
        type=int,
        default=None,
        help=f"Target schema version (default: latest={LATEST_SCHEMA_VERSION}; never downgrades input)",
    )

    ap.add_argument("--manifest", default=None, help="Optional manifest JSON path to upsert into")
    ap.add_argument("--name", default=None, help="Fixture name for manifest upsert")
    ap.add_argument("--update-manifest", action="store_true", help="Write/update manifest (requires --manifest and --name)")

    ns = ap.parse_args(argv)

    in_path = Path(ns.in_json).expanduser()
    out_path = Path(ns.out).expanduser()

    if not in_path.exists():
        return _die(f"Missing --in file: {in_path}")

    try:
        payload_in = _load_json(in_path)
    except Exception as e:
        return _die(f"Failed to load JSON: {in_path} ({e})")

    try:
        schema = _normalize_schema_request(payload_in, ns.schema)
    except Exception as e:
        return _die(str(e))

    # Upgrade once to target schema, then force indices to exist for Query + contracts.
    try:
        payload_up = upgrade_payload(payload_in, target_version=int(schema))  # type: ignore[arg-type]
        if not isinstance(payload_up, dict):
            raise MinifyError("upgrade_payload() did not return a dict")
        payload_up = _ensure_indices(payload_up)
    except Exception as e:
        return _die(f"Failed to upgrade/normalize payload: {e}")

    try:
        q = Query.parse(str(ns.q))
        selected = q.run(payload_up)
    except QueryError as e:
        return _die(f"Query parse/run failed: {e}")

    keep: set[str] = set()
    for t in selected:
        if isinstance(t, dict):
            u = t.get("uuid")
            if isinstance(u, str) and u.strip():
                keep.add(u.strip())

    tasks_up = payload_up.get("tasks")
    tasks_list = tasks_up if isinstance(tasks_up, list) else []
    min_tasks: List[Dict[str, Any]] = []
    for t in tasks_list:
        if not isinstance(t, dict):
            continue
        u = t.get("uuid")
        if isinstance(u, str) and u.strip() in keep:
            min_tasks.append(t)

    out_payload = dict(payload_up)
    out_payload["tasks"] = min_tasks
    out_payload = _ensure_indices(out_payload)

    # Validate (tool-level expectations depend on indices existing).
    errs = validate_payload(out_payload)
    if errs:
        msg = "; ".join(str(e) for e in errs[:8])
        return _die(f"Minified payload does not validate: {msg}", rc=3)

    blob = _dump_json(out_payload, pretty=bool(ns.pretty))
    _write(out_path, blob)

    if bool(ns.update_manifest):
        if not ns.manifest or not ns.name:
            return _die("--update-manifest requires --manifest and --name")
        manifest_path = Path(ns.manifest).expanduser()
        _manifest_upsert(
            manifest_path,
            name=str(ns.name),
            out_path=out_path,
            payload=out_payload,
            blob=blob,
        )

    print(f"[scalpel-minify] OK: {out_path} (tasks={len(min_tasks)} schema={out_payload.get('schema_version')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())