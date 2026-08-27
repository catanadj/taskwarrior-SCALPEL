from __future__ import annotations

from datetime import date

from ..model import Payload
from .model import GlimpseBand, GlimpseSnapshot, GlimpseTask


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
                priority=_optional_text(task.get("priority")),
                completed_ms=_first_int(task.get("completed_end_ms"), task.get("completion_ms")),
                anchor=_optional_text(task.get("anchor")),
                cp=_optional_text(task.get("cp")),
            )
        )
    cfg = payload.get("cfg", {})
    cfg = cfg if isinstance(cfg, dict) else {}
    work_start = max(0, min(1439, int(cfg.get("work_start_min", 0) or 0)))
    work_end = max(work_start + 1, min(1440, int(cfg.get("work_end_min", 1440) or 1440)))
    bands: list[GlimpseBand] = []
    raw_bands = cfg.get("time_bands", [])
    if isinstance(raw_bands, list):
        for raw_band in raw_bands:
            if not isinstance(raw_band, dict):
                continue
            label = _optional_text(raw_band.get("label"))
            start = raw_band.get("start")
            end = raw_band.get("end")
            if label and isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= 1440:
                bands.append(GlimpseBand(label, start, end))
    return GlimpseSnapshot(
        start_date=start_date,
        days=max(1, int(days)),
        timezone_name=timezone_name,
        tasks=tuple(tasks),
        work_start_min=work_start,
        work_end_min=work_end,
        bands=tuple(bands),
    )
