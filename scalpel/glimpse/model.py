from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class GlimpseTask:
    """Immutable terminal-facing representation of one planned task."""

    uuid: str
    description: str
    status: str
    day_key: str
    scheduled_ms: int | None
    due_ms: int | None
    duration_min: int | None
    project: str | None
    tags: tuple[str, ...]
    nautical_preview: bool


@dataclass(frozen=True, slots=True)
class GlimpseSnapshot:
    """Immutable input to all Glimpse layout and rendering code."""

    start_date: date
    days: int
    timezone_name: str
    tasks: tuple[GlimpseTask, ...]
