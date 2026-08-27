from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Sequence

from ..util.tz import resolve_tz
from .model import GlimpseSnapshot, GlimpseTask
from .style import AgendaStyle, style_for


def _truncate(value: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(value) <= width:
        return value
    if width == 1:
        return "…"
    return value[: width - 1] + "…"


def _format_duration(minutes: int | None) -> str:
    if not isinstance(minutes, int) or minutes <= 0:
        return ""
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins:02d}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def _task_start(task: GlimpseTask) -> int | None:
    return next((value for value in (task.start_ms, task.scheduled_ms, task.due_ms) if value is not None), None)


def _task_end(task: GlimpseTask) -> int | None:
    start = _task_start(task)
    if task.end_ms is not None:
        return task.end_ms
    if start is not None and isinstance(task.duration_min, int):
        return start + task.duration_min * 60_000
    return start


def _overlap_ids(tasks: Sequence[GlimpseTask]) -> set[str]:
    marked: set[str] = set()
    for index, current in enumerate(tasks):
        current_start, current_end = _task_start(current), _task_end(current)
        if current_start is None or current_end is None:
            continue
        for other in tasks[index + 1 :]:
            other_start, other_end = _task_start(other), _task_end(other)
            if other_start is None or other_end is None:
                continue
            if current_start < other_end and other_start < current_end:
                marked.update((current.uuid, other.uuid))
    return marked


def _local_time(timestamp_ms: int | None, timezone: dt.tzinfo) -> str:
    if timestamp_ms is None:
        return "  --"
    return dt.datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone).strftime("%H:%M")


def _day_tasks(snapshot: GlimpseSnapshot) -> dict[str, list[GlimpseTask]]:
    groups: dict[str, list[GlimpseTask]] = defaultdict(list)
    for task in snapshot.tasks:
        groups[task.day_key or "Unscheduled"].append(task)
    for tasks in groups.values():
        tasks.sort(key=lambda item: (_task_start(item) is None, _task_start(item) or 0, item.description.lower()))
    return groups


def _marker(task: GlimpseTask, *, overlap: bool, style: AgendaStyle) -> str:
    if overlap:
        return f"{style.red}⚠{style.reset}"
    if task.status.lower() == "completed":
        return f"{style.green}✓{style.reset}"
    if task.nautical_preview:
        return f"{style.cyan}⚓{style.reset}"
    return f"{style.magenta}┃{style.reset}"


def _row(task: GlimpseTask, *, overlap: bool, timezone: dt.tzinfo, width: int, style: AgendaStyle) -> str:
    time = _local_time(_task_start(task), timezone)
    marker = _marker(task, overlap=overlap, style=style)
    duration = _format_duration(task.duration_min)
    project = f"  {task.project}" if task.project else ""
    suffix = f"{duration:>7}{project}"
    description_width = max(8, width - 14 - len(suffix))
    description = _truncate(task.description or "(untitled)", description_width)
    return f"  {time} {marker} {description:<{description_width}}{suffix}".rstrip()


def render_agenda(
    snapshot: GlimpseSnapshot,
    *,
    width: int = 80,
    color: bool = False,
    now_ms: int | None = None,
) -> str:
    """Render a deterministic, width-bounded read-only agenda."""
    del now_ms  # Reserved for the current-time marker in the day-view pass.
    width = max(40, int(width))
    timezone = resolve_tz(snapshot.timezone_name)
    style = style_for(color=color)
    groups = _day_tasks(snapshot)
    lines = [f"{style.bold}SCALPEL · Agenda · {snapshot.start_date.isoformat()}{style.reset}", ""]
    overlap_ids = _overlap_ids(snapshot.tasks)
    total_minutes = 0
    conflicts = 0
    for offset in range(snapshot.days):
        day = snapshot.start_date + dt.timedelta(days=offset)
        day_key = day.isoformat()
        tasks = groups.get(day_key, [])
        lines.append(f"{style.bold}{day.strftime('%a %d %b')}{style.reset}")
        if not tasks:
            lines.append(f"  {style.dim}No tasks scheduled.{style.reset}")
        else:
            for task in tasks:
                lines.append(_row(task, overlap=task.uuid in overlap_ids, timezone=timezone, width=width, style=style))
                if isinstance(task.duration_min, int) and task.duration_min > 0:
                    total_minutes += task.duration_min
                conflicts += int(task.uuid in overlap_ids)
        lines.append("")
    lines.append(
        f"{style.dim}Planned {_format_duration(total_minutes) or '0m'} · "
        f"{conflicts // 2} conflict{'s' if conflicts // 2 != 1 else ''} · "
        f"{len(snapshot.tasks)} task{'s' if len(snapshot.tasks) != 1 else ''}{style.reset}"
    )
    return "\n".join(lines)


def render_day(
    snapshot: GlimpseSnapshot,
    *,
    day: dt.date | None = None,
    width: int = 80,
    color: bool = False,
    now_ms: int | None = None,
) -> str:
    """Render one day as a compact, hourly terminal timeline."""
    del now_ms  # Reserved for the current-time marker once interactive mode exists.
    width = max(40, int(width))
    selected_day = day or snapshot.start_date
    timezone = resolve_tz(snapshot.timezone_name)
    style = style_for(color=color)
    day_key = selected_day.isoformat()
    tasks = [task for task in snapshot.tasks if task.day_key == day_key]
    tasks.sort(key=lambda item: (_task_start(item) is None, _task_start(item) or 0, item.description.lower()))
    overlap_ids = _overlap_ids(tasks)
    day_start = int(dt.datetime.combine(selected_day, dt.time(), tzinfo=timezone).timestamp() * 1000)
    hour_ms = 60 * 60_000
    lines = [f"{style.bold}SCALPEL · Day · {selected_day.strftime('%a %d %b %Y')}{style.reset}", ""]
    for hour in range(24):
        slot_start = day_start + hour * hour_ms
        slot_end = slot_start + hour_ms
        active = [
            task
            for task in tasks
            if (_task_start(task) is not None and (_task_end(task) or _task_start(task) or 0) > slot_start)
            and (_task_start(task) or 0) < slot_end
        ]
        label = f"{hour:02d}:00"
        if not active:
            lines.append(f"{label} {style.dim}│{style.reset}")
            continue
        lines.append(f"{label} {style.dim}│{style.reset}")
        for task in active:
            start = _task_start(task)
            end = _task_end(task)
            duration = max(15, int(((end or start or slot_end) - (start or slot_start)) / 60_000))
            bar_width = max(1, min(12, duration // 15))
            marker = _marker(task, overlap=task.uuid in overlap_ids, style=style)
            description = _truncate(task.description or "(untitled)", max(8, width - 22))
            lines.append(f"     {marker} {'█' * bar_width} {description}")
    lines.append("")
    total_minutes = sum(task.duration_min or 0 for task in tasks if (task.duration_min or 0) > 0)
    conflicts = len(overlap_ids) // 2
    lines.append(
        f"{style.dim}{len(tasks)} task{'s' if len(tasks) != 1 else ''} · "
        f"{_format_duration(total_minutes) or '0m'} planned · "
        f"{conflicts} conflict{'s' if conflicts != 1 else ''}{style.reset}"
    )
    return "\n".join(lines)
