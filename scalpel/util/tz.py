# scalpel/util/tz.py
from __future__ import annotations

import datetime as dt
import re
from typing import Optional

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")


def normalize_tz_name(name: Optional[str]) -> str:
    """Normalize a timezone identifier.

    Supported forms:
      - None/"" -> "local"
      - "local" / "system" -> "local" (resolve to the machine's local timezone)
      - "UTC" / "Z" / "GMT" -> "UTC"
      - IANA names, e.g. "Europe/Bucharest"
      - Fixed offsets: "+02:00", "+0200", "-05:00"

    Returned value is a stable canonical string for storage in cfg.
    """
    if name is None:
        return "local"
    s = str(name).strip()
    if not s:
        return "local"

    low = s.lower()
    if low in {"local", "system", "native"}:
        return "local"
    if low in {"utc", "z", "gmt", "utc0", "utc+0"}:
        return "UTC"

    # Preserve explicit identifiers (IANA, offsets, etc.) as given.
    return s


def resolve_tz(name: Optional[str]) -> dt.tzinfo:
    """Resolve a timezone name into a tzinfo.

    For "local", resolves to the system local tzinfo.
    For "UTC", resolves to dt.timezone.utc.
    For IANA zone names, resolves via zoneinfo.ZoneInfo when available.
    For fixed offsets, resolves to dt.timezone(offset).

    Raises ValueError for invalid timezone identifiers.
    """
    tz_name = normalize_tz_name(name)

    if tz_name == "UTC":
        return dt.timezone.utc

    if tz_name == "local":
        tz = dt.datetime.now().astimezone().tzinfo
        return tz or dt.timezone.utc

    # Fixed offsets: +HH:MM, +HHMM, -HH:MM, -HHMM
    m = _OFFSET_RE.match(tz_name)
    if m:
        sign_s, hh_s, mm_s = m.groups()
        hh = int(hh_s)
        mm = int(mm_s)
        if hh > 23 or mm > 59:
            raise ValueError(f"Invalid timezone offset: {tz_name!r}")
        sign = 1 if sign_s == "+" else -1
        off_min = sign * (hh * 60 + mm)
        return dt.timezone(dt.timedelta(minutes=off_min))

    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)  # type: ignore[misc]
        except Exception as ex:
            raise ValueError(f"Invalid timezone identifier: {tz_name!r}") from ex

    raise ValueError(f"Invalid timezone identifier: {tz_name!r} (zoneinfo unavailable)")


def today_date(tz: dt.tzinfo) -> dt.date:
    return dt.datetime.now(tz=tz).date()


def midnight_epoch_ms(d: dt.date, tz: dt.tzinfo) -> int:
    aware = dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
    return int(aware.timestamp() * 1000)


def day_key_from_ms(ms: Optional[int], tz: dt.tzinfo) -> Optional[str]:
    if ms is None:
        return None
    try:
        d = dt.datetime.fromtimestamp(int(ms) / 1000.0, tz=tz).date()
        return d.isoformat()
    except Exception:
        return None


def is_midnight_ms(ms: Optional[int], tz: dt.tzinfo) -> bool:
    if ms is None:
        return False
    try:
        t = dt.datetime.fromtimestamp(int(ms) / 1000.0, tz=tz)
        return t.hour == 0 and t.minute == 0 and t.second == 0
    except Exception:
        return False
