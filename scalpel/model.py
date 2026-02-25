# scalpel/model.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from scalpel.ai.interface import PlanOverride


@dataclass(frozen=True)
class TaskLite:
    uuid: str
    id: Optional[int]
    description: str
    project: str
    tags: Tuple[str, ...]
    priority: str
    urgency: Optional[float]

    scheduled_ms: Optional[int]
    due_ms: Optional[int]

    duration_raw: Optional[str]
    duration_min: Optional[int]

    raw: dict[str, Any]


# Planner-facing types (lightweight)
Task = Dict[str, Any]
CalendarConfig = Dict[str, Any]


@dataclass(frozen=True)
class ConflictSegment:
    start_ms: int
    end_ms: int
    uuids: Tuple[str, ...]
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
    "Task",
    "CalendarConfig",
    "PlanOverride",
    "ConflictSegment",
    "SelectionMetrics",
]
