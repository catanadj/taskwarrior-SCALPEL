#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple

import datetime as dt

DAY_MS = 86400000
MIN_MS = 60000

DATA_RE = re.compile(
    r'<script[^>]+id="tw-data"[^>]*>\s*(.*?)\s*</script>',
    re.DOTALL | re.IGNORECASE,
)


def run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        raise SystemExit(f"Command failed ({p.returncode}): {' '.join(cmd)}")


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_payload(html: str) -> Dict[str, Any]:
    m = DATA_RE.search(html)
    if not m:
        raise ValueError("Could not locate <script id='tw-data' type='application/json'> payload block.")
    raw = m.group(1).strip()
    return json.loads(raw)


OPTIONAL_TASK_KEYS = {
    "duration_min",
    "start_calc_ms",
    "end_calc_ms",
    "dur_calc_min",
    "dur_src",
    "place_src",
    "interval_ok",
    "interval_warn",
}


def canonicalize_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(p)

    cfg = out.get("cfg") or {}
    if isinstance(cfg, dict):
        out["cfg"] = dict(cfg)

    tasks = out.get("tasks") or []
    if isinstance(tasks, list):
        norm_tasks = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            tt = dict(t)

            # Normalize tags for stable comparisons
            tags = tt.get("tags")
            if isinstance(tags, list):
                tt["tags"] = sorted([str(x) for x in tags])

            # Drop optional keys so old/new remain comparable when we intentionally extend payload
            for k in OPTIONAL_TASK_KEYS:
                tt.pop(k, None)

            norm_tasks.append(tt)

        norm_tasks.sort(key=lambda x: str(x.get("uuid") or ""))
        out["tasks"] = norm_tasks

    return out



def payload_fingerprint(p: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    cfg = p.get("cfg") if isinstance(p.get("cfg"), dict) else {}
    tasks = p.get("tasks") if isinstance(p.get("tasks"), list) else []
    keys = sorted(list(cfg.keys())) if isinstance(cfg, dict) else []
    return (len(tasks), len(keys), keys)

def fail(msg: str) -> None:
    raise ValueError(msg)


def require_type(name: str, v: Any, t: type) -> None:
    if not isinstance(v, t):
        fail(f"{name}: expected {t.__name__}, got {type(v).__name__}")


def require_keys(name: str, d: Dict[str, Any], keys: List[str]) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        fail(f"{name}: missing keys {missing}")


def check_cfg_invariants(cfg: Dict[str, Any]) -> None:
    require_keys("cfg", cfg, [
        "days",
        "work_start_min",
        "work_end_min",
        "snap_min",
        "default_duration_min",
        "max_infer_duration_min",
        "px_per_min",
        "view_start_ms",
        "view_key",
    ])

    # Type checks
    for k in ["days", "work_start_min", "work_end_min", "snap_min",
              "default_duration_min", "max_infer_duration_min", "view_start_ms"]:
        if not isinstance(cfg.get(k), int):
            fail(f"cfg.{k}: expected int, got {type(cfg.get(k)).__name__}")

    if not isinstance(cfg.get("px_per_min"), (int, float)):
        fail(f"cfg.px_per_min: expected number, got {type(cfg.get('px_per_min')).__name__}")

    if not isinstance(cfg.get("view_key"), str) or not cfg["view_key"].strip():
        fail("cfg.view_key: expected non-empty string")

    # Value sanity
    if cfg["days"] <= 0:
        fail("cfg.days: must be > 0")
    if cfg["work_end_min"] <= cfg["work_start_min"]:
        fail("cfg.workhours: work_end_min must be > work_start_min")
    if cfg["snap_min"] <= 0:
        fail("cfg.snap_min: must be > 0")
    if cfg["default_duration_min"] <= 0:
        fail("cfg.default_duration_min: must be > 0")
    if cfg["max_infer_duration_min"] <= 0:
        fail("cfg.max_infer_duration_min: must be > 0")
    if cfg["px_per_min"] <= 0:
        fail("cfg.px_per_min: must be > 0")


def check_task_invariants(tasks: List[Dict[str, Any]]) -> None:
    # Required keys used by UI
    required = [
        "uuid", "id", "description", "project", "tags",
        "priority", "urgency", "scheduled_ms", "due_ms", "duration"
    ]
    seen = set()
    for i, t in enumerate(tasks):
        name = f"tasks[{i}]"
        require_type(name, t, dict)
        require_keys(name, t, required)

        uuid = t.get("uuid")
        if not isinstance(uuid, str) or not uuid.strip():
            fail(f"{name}.uuid: expected non-empty string")
        if uuid in seen:
            fail(f"{name}.uuid: duplicate uuid {uuid}")
        seen.add(uuid)

        # tags must be list of strings (empty ok)
        tags = t.get("tags")
        if not isinstance(tags, list):
            fail(f"{name}.tags: expected list, got {type(tags).__name__}")
        for j, tag in enumerate(tags):
            if not isinstance(tag, str):
                fail(f"{name}.tags[{j}]: expected str, got {type(tag).__name__}")

        # project/description are strings (empty project ok; description should usually exist)
        if not isinstance(t.get("description"), str):
            fail(f"{name}.description: expected str")
        if not isinstance(t.get("project"), str):
            fail(f"{name}.project: expected str")

        # scheduled_ms / due_ms: int or None
        for k in ["scheduled_ms", "due_ms"]:
            v = t.get(k)
            if v is not None and not isinstance(v, int):
                fail(f"{name}.{k}: expected int or null, got {type(v).__name__}")

        # id: int or None
        if t.get("id") is not None and not isinstance(t.get("id"), int):
            fail(f"{name}.id: expected int or null, got {type(t.get('id')).__name__}")

        # urgency: number or None
        urg = t.get("urgency")
        if urg is not None and not isinstance(urg, (int, float)):
            fail(f"{name}.urgency: expected number or null, got {type(urg).__name__}")

        # duration_min: optional int or null
        if "duration_min" in t:
            dm = t.get("duration_min")
            if dm is not None and not isinstance(dm, int):
                fail(f"{name}.duration_min: expected int or null, got {type(dm).__name__}")
            if isinstance(dm, int) and dm <= 0:
                fail(f"{name}.duration_min: expected > 0, got {dm}")

        # Optional consistency check: if duration exists, duration_min should usually parse
        # (TW duration UDA should be ISO; if parse fails, this flags a mismatch in expectations)
        if t.get("duration") is not None and "duration_min" in t:
            if t.get("duration_min") is None:
                fail(f"{name}: duration present but duration_min is null (unexpected for TW duration UDA)")

        # Computed interval invariants (optional)
        if "start_calc_ms" in t or "end_calc_ms" in t:
            sc = t.get("start_calc_ms")
            ec = t.get("end_calc_ms")
            dm = t.get("dur_calc_min")

            if sc is not None and not isinstance(sc, int):
                fail(f"{name}.start_calc_ms: expected int or null")
            if ec is not None and not isinstance(ec, int):
                fail(f"{name}.end_calc_ms: expected int or null")
            if dm is not None and not isinstance(dm, int):
                fail(f"{name}.dur_calc_min: expected int or null")

            if isinstance(sc, int) and isinstance(ec, int) and isinstance(dm, int):
                if dm <= 0:
                    fail(f"{name}.dur_calc_min: expected >0, got {dm}")
                if ec <= sc:
                    fail(f"{name}: end_calc_ms <= start_calc_ms")
                if ec - sc != dm * 60000:
                    fail(f"{name}: (end-start) != dur_calc_min minutes")

                # In your semantics end_calc_ms should equal due_ms when due exists
                if t.get("due_ms") is not None and ec != t.get("due_ms"):
                    fail(f"{name}: end_calc_ms != due_ms (expected due-dominant end)")




def check_goals_invariants(goals: Any) -> None:
    # goals may be None if missing file
    if goals is None:
        return

    require_type("goals", goals, dict)
    if goals.get("version") != 1:
        fail(f"goals.version: expected 1, got {goals.get('version')!r}")

    gl = goals.get("goals")
    if not isinstance(gl, list):
        fail("goals.goals: expected list")

    for i, g in enumerate(gl):
        name = f"goals.goals[{i}]"
        require_type(name, g, dict)
        require_keys(name, g, ["id", "name", "color", "projects", "tags", "tags_all", "mode"])

        if not isinstance(g["id"], str) or not g["id"].strip():
            fail(f"{name}.id: expected non-empty string")
        if not isinstance(g["name"], str) or not g["name"].strip():
            fail(f"{name}.name: expected non-empty string")
        if not isinstance(g["color"], str) or not g["color"].strip():
            fail(f"{name}.color: expected non-empty string")

        for k in ["projects", "tags", "tags_all"]:
            if not isinstance(g[k], list):
                fail(f"{name}.{k}: expected list")
            for j, v in enumerate(g[k]):
                if not isinstance(v, str):
                    fail(f"{name}.{k}[{j}]: expected str, got {type(v).__name__}")

        if g["mode"] not in ("any", "all"):
            fail(f"{name}.mode: expected 'any' or 'all', got {g['mode']!r}")


def check_payload_invariants(payload: Dict[str, Any]) -> None:
    require_type("payload", payload, dict)
    require_keys("payload", payload, ["cfg", "tasks", "goals"])

    cfg = payload["cfg"]
    tasks = payload["tasks"]
    goals = payload["goals"]

    require_type("payload.cfg", cfg, dict)
    require_type("payload.tasks", tasks, list)

    check_cfg_invariants(cfg)
    check_cfg_time_sanity(cfg)          # <-- add
    check_task_invariants(tasks)
    check_task_time_sanity(tasks, cfg)  # <-- add
    check_goals_invariants(goals)


def is_plausible_epoch_ms(x: int) -> bool:
    # Very permissive range: 2000-01-01 .. 2100-01-01 (UTC)
    # Helps catch accidental seconds-vs-ms bugs, negative values, etc.
    return 946684800000 <= x <= 4102444800000


def check_cfg_time_sanity(cfg: Dict[str, Any]) -> None:
    # Minutes in day bounds
    for k in ["work_start_min", "work_end_min"]:
        v = cfg.get(k)
        if not (0 <= v <= 1440):
            fail(f"cfg.{k}: expected 0..1440, got {v}")

    if cfg["snap_min"] > 360:
        fail(f"cfg.snap_min: suspiciously large ({cfg['snap_min']} min)")
    if cfg["default_duration_min"] > 1440:
        fail(f"cfg.default_duration_min: suspiciously large ({cfg['default_duration_min']} min)")
    if cfg["max_infer_duration_min"] > 10080:
        fail(f"cfg.max_infer_duration_min: suspiciously large ({cfg['max_infer_duration_min']} min)")

    vsm = cfg.get("view_start_ms")
    if not is_plausible_epoch_ms(vsm):
        fail(f"cfg.view_start_ms: not a plausible epoch-ms timestamp: {vsm}")

    # Check "near midnight" in LOCAL time (not epoch modulo day).
    local_tz = dt.datetime.now().astimezone().tzinfo
    dloc = dt.datetime.fromtimestamp(vsm / 1000.0, tz=local_tz)

    # Allow up to 2 minutes drift (extra safety)
    if not (dloc.hour == 0 and dloc.minute in (0, 1) and dloc.second == 0):
        fail(
            "cfg.view_start_ms: expected near local midnight; "
            f"got local time {dloc.strftime('%Y-%m-%d %H:%M:%S %z')}"
        )


def check_task_time_sanity(tasks: List[Dict[str, Any]], cfg: Dict[str, Any]) -> None:
    max_infer = int(cfg.get("max_infer_duration_min", 480))
    max_infer_ms = max_infer * MIN_MS

    for i, t in enumerate(tasks):
        name = f"tasks[{i}]"
        sched = t.get("scheduled_ms")
        due = t.get("due_ms")

        if sched is not None and not is_plausible_epoch_ms(int(sched)):
            fail(f"{name}.scheduled_ms: not plausible epoch-ms: {sched}")
        if due is not None and not is_plausible_epoch_ms(int(due)):
            fail(f"{name}.due_ms: not plausible epoch-ms: {due}")

        if sched is not None and due is not None:
            if int(due) < int(sched):
                fail(f"{name}: due_ms < scheduled_ms (due={due}, scheduled={sched})")

            span = int(due) - int(sched)

            # Hard-fail only on absurd spans (unit bugs / corrupt parse)
            if span > (365 * DAY_MS):
                fail(f"{name}: due-scheduled span > 1 year ({span} ms)")

            # Note: long scheduled→due spans are valid; do not fail them.
            # (Optional warning is handled outside this function.)

        # Your due-dominant placement cannot place scheduled-only tasks
        if sched is not None and due is None:
            fail(f"{name}: scheduled_ms present but due_ms is null (task cannot be placed due-dominant)")

        # both missing is fine (backlog)



def stable_json(p: Dict[str, Any]) -> str:
    return json.dumps(p, ensure_ascii=False, sort_keys=True, indent=2)


def first_diff(a: Any, b: Any, path: str = "") -> str | None:
    # Minimal “where did it diverge?” helper
    if type(a) != type(b):
        return f"{path}: type differs: {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        ak = set(a.keys())
        bk = set(b.keys())
        if ak != bk:
            only_a = sorted(list(ak - bk))[:20]
            only_b = sorted(list(bk - ak))[:20]
            return f"{path}: keys differ. only_a={only_a} only_b={only_b}"
        for k in sorted(a.keys()):
            d = first_diff(a[k], b[k], f"{path}.{k}" if path else str(k))
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: list length differs: {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: value differs: {a!r} vs {b!r}"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate split + monolith HTML, extract embedded payload JSON, canonicalize, and compare."
    )
    ap.add_argument("--new", required=True, help="Path to the NEW (split) generator script, e.g. scalpel_run.py")
    ap.add_argument("--old", required=True, help="Path to the OLD (monolith) generator script, e.g. scalpel_monolith.py")
    ap.add_argument("--args", default="", help="Args passed to both scripts (string, e.g. \"--days 7 --filter status:pending\")")
    ap.add_argument("--keep", action="store_true", help="Keep generated HTML files (prints their paths).")
    ap.add_argument("--python", default=sys.executable, help="Python executable to use (default: current).")
    ns = ap.parse_args()

    common_args = ns.args.strip().split() if ns.args.strip() else []

    with tempfile.TemporaryDirectory() as td:
        out_new = os.path.join(td, "new.html")
        out_old = os.path.join(td, "old.html")

        run([ns.python, ns.new, "--out", out_new, "--no-open", *common_args])
        run([ns.python, ns.old, "--out", out_old, "--no-open", *common_args])

        html_new = read_text(out_new)
        html_old = read_text(out_old)

        p_new = canonicalize_payload(extract_payload(html_new))
        p_old = canonicalize_payload(extract_payload(html_old))

        # Invariant checks (validate both independently)
        try:
            check_payload_invariants(p_new)
        except Exception as ex:
            raise SystemExit(f"NEW payload invariant failure: {ex}")

        try:
            check_payload_invariants(p_old)
        except Exception as ex:
            raise SystemExit(f"OLD payload invariant failure: {ex}")


        fp_new = payload_fingerprint(p_new)
        fp_old = payload_fingerprint(p_old)

        if p_new == p_old:
            print("OK: payloads are equivalent after canonicalization.")
            print(f"tasks={fp_new[0]} cfg_keys={fp_new[1]}")
            if ns.keep:
                keep_new = os.path.abspath("verify_new.html")
                keep_old = os.path.abspath("verify_old.html")
                with open(keep_new, "w", encoding="utf-8") as f:
                    f.write(html_new)
                with open(keep_old, "w", encoding="utf-8") as f:
                    f.write(html_old)
                print("Wrote:")
                print(keep_new)
                print(keep_old)
            return

        # Not equal: print quick diagnostics + write stable json snapshots
        print("FAIL: payloads differ.")
        print(f"NEW tasks={fp_new[0]} cfg_keys={fp_new[1]}")
        print(f"OLD tasks={fp_old[0]} cfg_keys={fp_old[1]}")

        where = first_diff(p_new, p_old)
        if where:
            print("First difference:", where)

        snap_new = os.path.abspath("payload_new.json")
        snap_old = os.path.abspath("payload_old.json")
        with open(snap_new, "w", encoding="utf-8") as f:
            f.write(stable_json(p_new))
        with open(snap_old, "w", encoding="utf-8") as f:
            f.write(stable_json(p_old))
        print("Wrote payload snapshots:")
        print(snap_new)
        print(snap_old)

        if ns.keep:
            keep_new = os.path.abspath("verify_new.html")
            keep_old = os.path.abspath("verify_old.html")
            with open(keep_new, "w", encoding="utf-8") as f:
                f.write(html_new)
            with open(keep_old, "w", encoding="utf-8") as f:
                f.write(html_old)
            print("Wrote HTML outputs:")
            print(keep_new)
            print(keep_old)

        raise SystemExit(2)


if __name__ == "__main__":
    main()

