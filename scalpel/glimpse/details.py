from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from .model import GlimpseTask


def _format_time(timestamp_ms: int | None, timezone_name: str) -> str:
    if timestamp_ms is None:
        return "—"
    try:
        from ..util.tz import resolve_tz
        return dt.datetime.fromtimestamp(timestamp_ms / 1000, tz=resolve_tz(timezone_name)).strftime("%Y-%m-%d %H:%M %Z")
    except (OverflowError, OSError, ValueError):
        return "invalid time"


def task_details(task: GlimpseTask, *, width: int = 72, timezone_name: str = "UTC", annotations: Sequence[str] = ()) -> str:
    """Return a readable, width-bounded detail panel for one task."""
    width = max(32, int(width))
    lines = [
        "Task details",
        "",
        f"Description  {task.description or '(untitled)'}",
        f"Status       {task.status or 'unknown'}",
        f"Project      {task.project or '—'}",
        f"Tags         {', '.join(task.tags) or '—'}",
        f"UUID         {task.uuid}",
        f"Priority     {task.priority or '—'}",
        f"Scheduled    {_format_time(task.scheduled_ms, timezone_name)}",
        f"Due          {_format_time(task.due_ms, timezone_name)}",
        f"Completed    {_format_time(task.completed_ms, timezone_name)}",
        f"Duration     {task.duration_min if task.duration_min is not None else '—'} min",
        f"Nautical     {'preview' if task.nautical_preview else '—'}",
        f"Anchor       {task.anchor or '—'}",
        f"CP           {task.cp or '—'}",
    ]
    lines.extend(f"Note         {annotation}" for annotation in annotations)
    return "\n".join(line if len(line) <= width else line[: width - 1] + "…" for line in lines)
