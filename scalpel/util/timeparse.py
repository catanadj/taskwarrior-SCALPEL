# scalpel/util/timeparse.py
from __future__ import annotations

import datetime as dt
import re
from typing import Tuple

from .tz import midnight_epoch_ms as _midnight_epoch_ms
from .tz import resolve_tz

_HHMM_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_hhmm(s: str) -> Tuple[int, int]:
    m = _HHMM_RE.match(s.strip())
    if not m:
        raise ValueError(f"Invalid HH:MM: {s!r}")
    hh = int(m.group(1))
    mm = int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError(f"Invalid HH:MM: {s!r}")
    return hh, mm


def parse_workhours(s: str) -> Tuple[int, int]:
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError("workhours must be like 06:00-23:00")
    sh, sm = parse_hhmm(parts[0])
    eh, em = parse_hhmm(parts[1])
    start = sh * 60 + sm
    end = eh * 60 + em
    if end <= start:
        raise ValueError("workhours end must be after start")
    return start, end


def parse_date_yyyy_mm_dd(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()


def midnight_epoch_ms(d: dt.date, tz: str | None = "local") -> int:
    """Epoch ms for midnight at date `d` in timezone `tz`.

    `tz` accepts:
      - "local" (default)
      - "UTC"
      - IANA zone name (e.g. "Europe/Bucharest")
      - fixed offset (e.g. "+02:00")
    """
    tzinfo = resolve_tz(tz)
    return _midnight_epoch_ms(d, tzinfo)


def local_midnight_epoch_ms(d: dt.date) -> int:
    """Backward-compatible alias for midnight in the system local timezone."""
    return midnight_epoch_ms(d, tz="local")
