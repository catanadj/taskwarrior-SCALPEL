"""AI scheduling interface (internal, forward-compatible).

This module defines a stable boundary between the calendar payload and any AI
planner. It deliberately avoids dependencies on UI or Taskwarrior details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

JsonDict = Dict[str, Any]


@dataclass(frozen=True)
class AiConstraints:
    """Optional constraints for AI planning; None means "use payload defaults"."""

    horizon_start_ms: Optional[int] = None
    horizon_end_ms: Optional[int] = None
    work_start_min: Optional[int] = None
    work_end_min: Optional[int] = None
    snap_min: Optional[int] = None


@dataclass(frozen=True)
class AiPlanRequest:
    """Inputs to an AI planner.

    payload: normalized scalpel payload (schema v1+).
    selected_uuids: optional target subset for planning.
    mode: hint for the planner (e.g. "suggest", "optimize", "resolve_conflicts").
    """

    payload: JsonDict
    selected_uuids: Tuple[str, ...] = ()
    mode: str = "suggest"
    constraints: AiConstraints = field(default_factory=AiConstraints)
    model_id: Optional[str] = None
    seed: Optional[int] = None


@dataclass(frozen=True)
class PlanOverride:
    """Proposed schedule for a task (UTC epoch milliseconds)."""

    start_ms: int
    due_ms: int
    duration_min: Optional[int] = None


@dataclass(frozen=True)
class AiPlanResult:
    """Outputs of an AI planner."""

    overrides: Dict[str, PlanOverride]
    added_tasks: Tuple[Dict[str, Any], ...] = ()
    task_updates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    warnings: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()
    model_id: Optional[str] = None


class AiPlanner(Protocol):
    def plan(self, req: AiPlanRequest) -> AiPlanResult:
        """Return a plan proposal for the given request."""


class NoopPlanner:
    """Baseline planner that proposes no changes."""

    def plan(self, req: AiPlanRequest) -> AiPlanResult:
        return AiPlanResult(overrides={}, model_id=req.model_id)


NOOP_PLANNER = NoopPlanner()


def _iter_payload_uuids(payload: JsonDict) -> Iterable[str]:
    idx = payload.get("indices")
    if isinstance(idx, dict):
        by_uuid = idx.get("by_uuid")
        if isinstance(by_uuid, dict):
            for u in by_uuid.keys():
                if isinstance(u, str) and u:
                    yield u
            return
    tasks = payload.get("tasks")
    if isinstance(tasks, list):
        for t in tasks:
            if isinstance(t, dict):
                u = t.get("uuid")
                if isinstance(u, str) and u:
                    yield u


def validate_plan_overrides(payload: JsonDict, overrides: Dict[str, PlanOverride]) -> List[str]:
    """Validate overrides against payload tasks and basic timing invariants."""

    errs: List[str] = []
    uuid_set = set(_iter_payload_uuids(payload))

    if not isinstance(overrides, dict):
        return ["overrides must be a dict[str, PlanOverride]"]

    for uuid, ov in overrides.items():
        if uuid not in uuid_set:
            errs.append(f"unknown uuid in overrides: {uuid}")
            continue
        if not isinstance(ov, PlanOverride):
            errs.append(f"override for {uuid} must be PlanOverride")
            continue
        if not isinstance(ov.start_ms, int) or not isinstance(ov.due_ms, int):
            errs.append(f"override for {uuid} must use int start_ms/due_ms")
            continue
        if ov.due_ms <= ov.start_ms:
            errs.append(f"override for {uuid} must have due_ms > start_ms")
            continue

        delta_ms = ov.due_ms - ov.start_ms
        if delta_ms % 60000 != 0:
            errs.append(f"override for {uuid} must align to minutes (delta_ms % 60000 == 0)")
        if ov.duration_min is not None:
            if not isinstance(ov.duration_min, int) or ov.duration_min <= 0:
                errs.append(f"override for {uuid} duration_min must be positive int")
            elif ov.duration_min * 60000 != delta_ms:
                errs.append(f"override for {uuid} duration_min != (due_ms - start_ms)")

    return errs
