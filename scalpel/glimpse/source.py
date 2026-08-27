from __future__ import annotations

from datetime import date

from ..model import Payload
from .model import GlimpseSnapshot, GlimpseTask


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _first_int(*values: object) -> int | None:
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None:
            return parsed
    return None


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _tags(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(tag) for tag in value if isinstance(tag, str) and tag.strip())


def snapshot_from_payload(
    payload: Payload,
    *,
    start_date: date,
    days: int,
    timezone_name: str,
) -> GlimpseSnapshot:
    """Create the stable Glimpse input model from a validated SCALPEL payload."""
    tasks: list[GlimpseTask] = []
    for raw_task in payload.get("tasks", []):
        task = raw_task
        uuid = _optional_text(task.get("uuid"))
        if uuid is None:
            continue
        tasks.append(
            GlimpseTask(
                uuid=uuid,
                description=str(task.get("description") or ""),
                status=str(task.get("status") or ""),
                day_key=str(task.get("day_key") or ""),
                scheduled_ms=_optional_int(task.get("scheduled_ms")),
                due_ms=_optional_int(task.get("due_ms")),
                start_ms=_first_int(task.get("start_calc_ms"), task.get("scheduled_ms"), task.get("due_ms")),
                end_ms=_first_int(task.get("end_calc_ms"), task.get("end_ms")),
                duration_min=_optional_int(task.get("duration_min")),
                project=_optional_text(task.get("project")),
                tags=_tags(task.get("tags")),
                nautical_preview=bool(task.get("nautical_preview")),
            )
        )
    return GlimpseSnapshot(
        start_date=start_date,
        days=max(1, int(days)),
        timezone_name=timezone_name,
        tasks=tuple(tasks),
    )
