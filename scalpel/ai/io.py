"""AI planning I/O helpers (internal)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .interface import PlanOverride


def _as_int(v: Any) -> Optional[int]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


def load_plan_overrides(path: Path) -> Dict[str, PlanOverride]:
    """Load plan overrides from JSON.

    Expected format:
      { "<uuid>": {"start_ms": 123, "due_ms": 456, "duration_min": 60}, ... }
    """

    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("plan overrides must be a JSON object mapping uuid -> override")

    out: Dict[str, PlanOverride] = {}
    for uuid, raw in obj.items():
        if not isinstance(uuid, str) or not uuid.strip():
            raise ValueError("plan overrides must use non-empty string UUID keys")
        if not isinstance(raw, dict):
            raise ValueError(f"override for {uuid} must be an object")

        start_ms = _as_int(raw.get("start_ms"))
        due_ms = _as_int(raw.get("due_ms"))
        dur_min = _as_int(raw.get("duration_min"))

        if start_ms is None or due_ms is None:
            raise ValueError(f"override for {uuid} must include int start_ms and due_ms")
        if due_ms <= start_ms:
            raise ValueError(f"override for {uuid} must have due_ms > start_ms")
        if dur_min is not None and dur_min <= 0:
            raise ValueError(f"override for {uuid} duration_min must be positive")

        out[uuid] = PlanOverride(start_ms=int(start_ms), due_ms=int(due_ms), duration_min=dur_min)

    return out
