from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class GlimpseBand:
    label: str
    start_min: int
    end_min: int


@dataclass(frozen=True, slots=True)
class GlimpseTask:
    """Immutable terminal-facing representation of one planned task."""

    uuid: str
    description: str
    status: str
    day_key: str
    scheduled_ms: int | None
    due_ms: int | None
    start_ms: int | None
    end_ms: int | None
    duration_min: int | None
    project: str | None
    tags: tuple[str, ...]
    nautical_preview: bool
    priority: str | None = None
    completed_ms: int | None = None
    anchor: str | None = None
    cp: str | None = None


@dataclass(frozen=True, slots=True)
class GlimpseSnapshot:
    """Immutable input to all Glimpse layout and rendering code."""

    start_date: date
    days: int
    timezone_name: str
    tasks: tuple[GlimpseTask, ...]
    work_start_min: int = 0
    work_end_min: int = 1440
    bands: tuple[GlimpseBand, ...] = ()
