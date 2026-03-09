# scalpel/model.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TypedDict


@dataclass(frozen=True)
class TaskLite:
    uuid: str
    id: Optional[int]
    description: str
    project: str
    tags: tuple[str, ...]
    priority: str
    urgency: Optional[float]

    scheduled_ms: Optional[int]
    due_ms: Optional[int]

    duration_raw: Optional[str]
    duration_min: Optional[int]

    raw: dict[str, Any]


RawTask = dict[str, Any]
EventTuple = tuple[int, int, int]
EventMap = dict[str, EventTuple]


class Task(TypedDict, total=False):
    uuid: str
    id: int | None
    description: str
    project: str | None
    status: str
    tags: list[str]
    priority: str
    urgency: float | None
    scheduled_ms: int | None
    due_ms: int | None
    duration: str | None
    duration_min: int | None
    start_calc_ms: int
    end_calc_ms: int
    dur_calc_min: int
    dur_src: str
    place_src: str
    interval_ok: bool
    interval_warn: str | None
    day_key: str | None
    nautical_preview: bool
    nautical_kind: str
    nautical_source_uuid: str
    nautical_anchor: str
    nautical_anchor_mode: str | None
    nautical_cp: str
    nautical_link: int


class CalendarConfig(TypedDict, total=False):
    tz: str
    display_tz: str
    days: int
    work_start_min: int
    work_end_min: int
    snap_min: int
    default_duration_min: int
    max_infer_duration_min: int
    px_per_min: float
    view_start_ms: int
    view_key: str


class Payload(TypedDict, total=False):
    schema_version: int
    generated_at: str
    cfg: CalendarConfig
    tasks: list[Task]
    goals: dict[str, Any] | None
    indices: dict[str, Any]
    meta: dict[str, Any]


@dataclass(frozen=True)
class ConflictSegment:
    start_ms: int
    end_ms: int
    uuids: tuple[str, ...]
    key: str
    kind: str = "overlap"  # "overlap" | "out_of_hours"


@dataclass(frozen=True)
class SelectionMetrics:
    count: int
    duration_min: int
    span_min: int
    gap_min: int


__all__ = [
    "TaskLite",
    "RawTask",
    "Task",
    "CalendarConfig",
    "Payload",
    "EventTuple",
    "EventMap",
    "ConflictSegment",
    "SelectionMetrics",
]
