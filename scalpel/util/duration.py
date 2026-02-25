# scalpel/util/duration.py
from __future__ import annotations

import re
from typing import Optional

# Taskwarrior duration UDA typically stores ISO-8601: PT10M, PT1H30M, etc.
_ISO_RE = re.compile(r"^P(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)$", re.IGNORECASE)

def parse_duration_to_minutes(s: str | None) -> Optional[int]:
    if not s:
        return None
    ss = str(s).strip()
    if not ss:
        return None

    m = _ISO_RE.match(ss)
    if not m:
        return None

    h = int(m.group(1) or 0)
    mn = int(m.group(2) or 0)
    sec = int(m.group(3) or 0)

    total = h * 60 + mn
    # Round seconds to nearest minute only if you ever see seconds; TW durations usually won’t.
    if sec >= 30:
        total += 1

    return total if total > 0 else None

