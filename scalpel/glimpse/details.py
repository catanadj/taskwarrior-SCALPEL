from __future__ import annotations

from .model import GlimpseTask


def task_details(task: GlimpseTask, *, width: int = 72) -> str:
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
        f"Scheduled    {task.scheduled_ms if task.scheduled_ms is not None else '—'}",
        f"Due          {task.due_ms if task.due_ms is not None else '—'}",
        f"Duration     {task.duration_min if task.duration_min is not None else '—'} min",
        f"Nautical     {'preview' if task.nautical_preview else '—'}",
    ]
    return "\n".join(line if len(line) <= width else line[: width - 1] + "…" for line in lines)
