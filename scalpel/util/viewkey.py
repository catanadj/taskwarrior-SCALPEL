# scalpel/util/viewkey.py
from __future__ import annotations

import datetime as dt


def make_view_key(
    filter_str: str,
    start_date: dt.date,
    days: int,
    work_start: int,
    work_end: int,
    snap: int,
    tz: str = "local",
    display_tz: str = "local",
) -> str:
    """Return a stable view key used for caching and UI-state correlation.

    The view key is intentionally cheap and deterministic.
    It includes timezone knobs so changing bucketing/display does not accidentally
    reuse stale cached state.
    """
    raw = f"{filter_str}|{start_date.isoformat()}|{days}|{work_start}|{work_end}|{snap}|{tz}|{display_tz}"
    h = 0
    for ch in raw:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"
