# scalpel/taskwarrior.py
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

from .util.console import eprint

TW_UTC_RE = re.compile(r"^(\d{8})T(\d{6})Z$")  # e.g. 20251217T083000Z


def _task_export_timeout_s() -> float:
    raw = (os.getenv("SCALPEL_TASK_TIMEOUT_S", "30") or "").strip()
    try:
        v = float(raw)
        if v > 0:
            return v
    except Exception:
        pass
    return 30.0


def _obs_enabled() -> bool:
    v = (os.getenv("SCALPEL_OBS_LOG", "") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}

def parse_tw_utc_to_epoch_ms(s: str) -> Optional[int]:
    if not s:
        return None

    m = TW_UTC_RE.match(s)
    if not m:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return int(d.timestamp() * 1000)
        except Exception:
            return None

    try:
        ymd = m.group(1)
        hms = m.group(2)
        y = int(ymd[0:4])
        mo = int(ymd[4:6])
        d0 = int(ymd[6:8])
        hh = int(hms[0:2])
        mm = int(hms[2:4])
        ss = int(hms[4:6])
        aware = dt.datetime(y, mo, d0, hh, mm, ss, tzinfo=dt.timezone.utc)
        return int(aware.timestamp() * 1000)
    except Exception:
        return None

def run_task_export(filter_str: str) -> List[Dict[str, Any]]:
    cmd = ["task"]
    if filter_str.strip():
        try:
            cmd += shlex.split(filter_str.strip(), posix=True)
        except ValueError as ex:
            raise SystemExit(f"Invalid Taskwarrior filter expression: {ex}")
    cmd += ["export"]

    timeout_s = _task_export_timeout_s()
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_s,
        )
    except FileNotFoundError:
        raise SystemExit("Taskwarrior binary 'task' not found on PATH.")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"Taskwarrior export timed out after {timeout_s:.1f}s.")

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if proc.returncode != 0:
        out_err = b""
        if proc.stdout:
            out_err += proc.stdout
        if proc.stdout and proc.stderr:
            out_err += b"\n"
        if proc.stderr:
            out_err += proc.stderr
        if out_err:
            eprint(out_err.decode("utf-8", errors="replace"))
        raise SystemExit(f"Taskwarrior export failed (exit {proc.returncode}, {elapsed_ms}ms).")

    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        if _obs_enabled():
            eprint(f"[scalpel.taskwarrior] export.ok ms={elapsed_ms} tasks=0")
        return []
    try:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("task export did not return a JSON list")
        if _obs_enabled():
            eprint(f"[scalpel.taskwarrior] export.ok ms={elapsed_ms} tasks={len(data)}")
        return data
    except Exception as ex:
        raise SystemExit(f"Failed to parse `task export` JSON after {elapsed_ms}ms: {ex}")
