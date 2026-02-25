# scalpel/metrics.py
from __future__ import annotations

from datetime import date
from .model import Goal, Task


def compute_day_balance(day: date,
                        tasks: list[Task],
                        events: dict[str, tuple[int,int,int]],
                        goals: list[Goal]) -> dict[str, int]:
    """
    Return minutes per goal name plus:
      - "Other"
      - "Free"
    """


def compute_next_up(now_ms: int,
                    events: dict[str, tuple[int,int,int]]) -> tuple[str | None, str | None]:
    """Return (current_uuid, next_uuid)."""

