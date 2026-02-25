# scalpel/interval.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

MIN_MS = 60_000


@dataclass(frozen=True)
class IntervalComputed:
    start_ms: int          # computed scheduled (for placement/commands)
    end_ms: int            # due
    duration_min: int      # effective duration used

    duration_src: str      # "duration_min" | "infer_due_minus_scheduled" | "default"
    placement_src: str     # "due_minus_duration" (for now)

    ok: bool = True
    warning: Optional[str] = None


def _round_ms_to_min(ms: int) -> int:
    # Round to nearest minute (handles seconds if ever present)
    if ms >= 0:
        return (ms + (MIN_MS // 2)) // MIN_MS
    return -((-ms + (MIN_MS // 2)) // MIN_MS)


def infer_interval_ms(
    *,
    due_ms: Optional[int],
    scheduled_ms: Optional[int],
    duration_min: Optional[int],
    default_duration_min: int,
    max_infer_duration_min: int,
) -> Optional[IntervalComputed]:
    """
    Due-dominant inference:
      - If no due -> None (cannot place)
      - duration precedence:
          1) duration_min if present
          2) infer from due-scheduled if both present and sane (<= max_infer_duration_min)
          3) default_duration_min
      - placement: start = due - duration
        (we do NOT use scheduled_ms for placement; scheduled is derived)
    """
    if due_ms is None:
        return None

    warn = None
    dur_src = "default"
    dur = None

    # 1) explicit duration_min
    if isinstance(duration_min, int) and duration_min > 0:
        dur = duration_min
        dur_src = "duration_min"

    # 2) infer from due-scheduled if duration missing
    if dur is None and scheduled_ms is not None:
        if scheduled_ms <= due_ms:
            span_min = int(_round_ms_to_min(due_ms - scheduled_ms))
            if 1 <= span_min <= int(max_infer_duration_min):
                dur = span_min
                dur_src = "infer_due_minus_scheduled"
            else:
                # scheduled far away: valid in TW, but not used for duration inference
                dur = int(default_duration_min)
                dur_src = "default"
                warn = (
                    f"duration inferred span {span_min}min outside cap "
                    f"(max_infer_duration_min={max_infer_duration_min}); using default {default_duration_min}min"
                )
        else:
            dur = int(default_duration_min)
            dur_src = "default"
            warn = "scheduled_ms > due_ms; using default duration"

    # 3) default
    if dur is None:
        dur = int(default_duration_min)
        dur_src = "default"

    start_ms = int(due_ms) - int(dur) * MIN_MS
    end_ms = int(due_ms)

    ok = True
    if dur <= 0 or start_ms >= end_ms:
        ok = False
        warn = warn or "invalid interval (non-positive duration or start>=end)"

    return IntervalComputed(
        start_ms=start_ms,
        end_ms=end_ms,
        duration_min=int(dur),
        duration_src=dur_src,
        placement_src="due_minus_duration",
        ok=ok,
        warning=warn,
    )

