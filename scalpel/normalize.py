# scalpel/normalize.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .model import TaskLite
from .taskwarrior import parse_tw_utc_to_epoch_ms
from .util.duration import parse_duration_to_minutes
from .util.console import eprint


def _obs_enabled() -> bool:
    v = (os.getenv("SCALPEL_OBS_LOG", "") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}

def normalize_task(t: Dict[str, Any]) -> Optional[TaskLite]:
    uuid = str(t.get("uuid") or "").strip()
    if not uuid:
        return None

    tags = t.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    dur_raw = t.get("duration")
    dur_raw_s = None if dur_raw is None else str(dur_raw).strip()
    dur_min = parse_duration_to_minutes(dur_raw_s)
    scheduled_raw = str(t.get("scheduled") or "")
    due_raw = str(t.get("due") or "")
    scheduled_ms = parse_tw_utc_to_epoch_ms(scheduled_raw)
    due_ms = parse_tw_utc_to_epoch_ms(due_raw)
    if _obs_enabled():
        if scheduled_raw and scheduled_ms is None:
            eprint(f"[scalpel.normalize] WARN: invalid scheduled timestamp uuid={uuid!r} value={scheduled_raw!r}")
        if due_raw and due_ms is None:
            eprint(f"[scalpel.normalize] WARN: invalid due timestamp uuid={uuid!r} value={due_raw!r}")

    return TaskLite(
        uuid=uuid,
        id=t.get("id") if isinstance(t.get("id"), int) else None,
        description=str(t.get("description") or ""),
        project=str(t.get("project") or ""),
        tags=tuple(str(x) for x in tags if isinstance(x, str)),
        priority=str(t.get("priority") or ""),
        urgency=t.get("urgency") if isinstance(t.get("urgency"), (int, float)) else None,
        scheduled_ms=scheduled_ms,
        due_ms=due_ms,
        duration_raw=dur_raw_s,
        duration_min=dur_min,
        raw=dict(t),
    )
