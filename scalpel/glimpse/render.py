from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from typing import Sequence

from ..util.tz import resolve_tz
from .model import GlimpseBand, GlimpseSnapshot, GlimpseTask
from .style import AgendaStyle, project_color, style_for


def _highlight(value: str, query: str, *, ascii_only: bool = False) -> str:
    needle = query.strip()
    if not needle:
        return value
    left, right = ("[", "]") if ascii_only else ("⟦", "⟧")
    return re.sub(re.escape(needle), lambda match: f"{left}{match.group(0)}{right}", value, flags=re.IGNORECASE)


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
        if start is None:
            return task.end_ms
        return max(start, task.end_ms)
    if start is not None and type(task.duration_min) is int:
        return start + task.duration_min * 60_000
    return start


def _overlap_ids(tasks: Sequence[GlimpseTask]) -> set[str]:
    marked: set[str] = set()
    intervals = []
    for task in tasks:
        start, end = _task_start(task), _task_end(task)
        if start is None or end is None or end <= start:
            continue
        intervals.append((start, end, task.uuid))

    active: list[tuple[int, str]] = []
    for start, end, uuid in sorted(intervals):
        active = [(active_end, active_uuid) for active_end, active_uuid in active if active_end > start]
        for _, active_uuid in active:
            marked.update((uuid, active_uuid))
        active.append((end, uuid))
    return marked


def _default_bands(snapshot: GlimpseSnapshot) -> tuple[GlimpseBand, ...]:
    if snapshot.bands:
        return snapshot.bands
    start, end = snapshot.work_start_min, snapshot.work_end_min
    candidates = (
        ("Morning", start, min(end, start + 240)),
        ("Focus", start + 240, min(end, start + 480)),
        ("Afternoon", start + 480, end),
    )
    return tuple(
        GlimpseBand(label, max(start, band_start), band_end)
        for label, band_start, band_end in candidates
        if band_end > max(start, band_start)
    )


def _band_at(bands: Sequence[GlimpseBand], minute: int) -> GlimpseBand | None:
    return next((band for band in bands if band.start_min <= minute < band.end_min), None)


def _local_time(timestamp_ms: int | None, timezone: dt.tzinfo) -> str:
    if timestamp_ms is None:
        return "  --"
    return dt.datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone).strftime("%H:%M")


def _local_hour_boundary_ms(day: dt.date, hour: int, timezone: dt.tzinfo) -> int:
    boundary_day = day + dt.timedelta(days=hour // 24)
    boundary = dt.datetime.combine(boundary_day, dt.time(hour % 24), tzinfo=timezone)
    return int(boundary.timestamp() * 1000)


def _day_tasks(snapshot: GlimpseSnapshot) -> dict[str, list[GlimpseTask]]:
    groups: dict[str, list[GlimpseTask]] = defaultdict(list)
    for task in snapshot.tasks:
        groups[task.day_key or "Unscheduled"].append(task)
    for tasks in groups.values():
        tasks.sort(key=lambda item: (_task_start(item) is None, _task_start(item) or 0, item.description.lower()))
    return groups


def _marker(task: GlimpseTask, *, overlap: bool, style: AgendaStyle, ascii_only: bool = False) -> str:
    overlap_glyph, completed_glyph, nautical_glyph, regular_glyph = (
        ("!", "x", "@", "|") if ascii_only else ("⚠", "✓", "⚓", "┃")
    )
    if overlap:
        return f"{style.red}{overlap_glyph}{style.reset}"
    if task.status.lower() == "completed":
        return f"{style.green}{completed_glyph}{style.reset}"
    if task.nautical_preview:
        return f"{style.cyan}{nautical_glyph}{style.reset}"
    return f"{style.magenta}{regular_glyph}{style.reset}"


def _row(
    task: GlimpseTask,
    *,
    overlap: bool,
    timezone: dt.tzinfo,
    width: int,
    style: AgendaStyle,
    ascii_only: bool = False,
    highlight_query: str = "",
) -> str:
    time = _local_time(_task_start(task), timezone)
    marker = _marker(task, overlap=overlap, style=style, ascii_only=ascii_only)
    duration = _format_duration(task.duration_min)
    project = (
        f"  {project_color(task.project, style=style)}{task.project}{style.reset if task.project else ''}"
        if task.project
        else ""
    )
    suffix = f"{duration:>7}{project}"
    description_width = max(8, width - 14 - len(suffix))
    description = _truncate(
        _highlight(task.description or "(untitled)", highlight_query, ascii_only=ascii_only), description_width
    )
    return f"  {time} {marker} {description:<{description_width}}{suffix}".rstrip()


def render_agenda(
    snapshot: GlimpseSnapshot,
    *,
    width: int = 80,
    color: bool = False,
    now_ms: int | None = None,
    ascii_only: bool = False,
    highlight_query: str = "",
) -> str:
    """Render a deterministic, width-bounded read-only agenda."""
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
        today_marker = (
            " · today"
            if now_ms is not None and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).date() == day
            else ""
        )
        lines.append(f"{style.bold}{day.strftime('%a %d %b')}{today_marker}{style.reset}")
        if not tasks:
            lines.append(f"  {style.dim}No tasks scheduled.{style.reset}")
        else:
            for task in tasks:
                lines.append(
                    _row(
                        task,
                        overlap=task.uuid in overlap_ids,
                        timezone=timezone,
                        width=width,
                        style=style,
                        ascii_only=ascii_only,
                        highlight_query=highlight_query,
                    )
                )
                if isinstance(task.duration_min, int) and task.duration_min > 0:
                    total_minutes += task.duration_min
                conflicts += int(task.uuid in overlap_ids)
        if now_ms is not None and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).date() == day:
            current_time = dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).strftime("%H:%M")
            lines.append(f"  {style.dim}Current time: {current_time}{style.reset}")
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
    ascii_only: bool = False,
    highlight_query: str = "",
) -> str:
    """Render one day as a compact, hourly terminal timeline."""
    width = max(40, int(width))
    selected_day = day or snapshot.start_date
    timezone = resolve_tz(snapshot.timezone_name)
    style = style_for(color=color)
    day_key = selected_day.isoformat()
    tasks = [task for task in snapshot.tasks if task.day_key == day_key]
    tasks.sort(key=lambda item: (_task_start(item) is None, _task_start(item) or 0, item.description.lower()))
    overlap_ids = _overlap_ids(tasks)
    day_start = _local_hour_boundary_ms(selected_day, 0, timezone)
    is_today = now_ms is not None and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).date() == selected_day
    bands = _default_bands(snapshot)
    lines = [f"{style.bold}SCALPEL · Day · {selected_day.strftime('%a %d %b %Y')}{style.reset}", ""]
    intervals = {
        task.uuid: (_task_start(task), _task_end(task))
        for task in tasks
    }
    lane_by_uuid: dict[str, int] = {}
    lane_ends: list[int] = []
    for task in tasks:
        start, end = intervals[task.uuid]
        if start is None or end is None or end <= start:
            continue
        lane = next((index for index, lane_end in enumerate(lane_ends) if start >= lane_end), len(lane_ends))
        if lane == len(lane_ends):
            lane_ends.append(end)
        else:
            lane_ends[lane] = end
        lane_by_uuid[task.uuid] = lane
    first_visible_hour: dict[str, int] = {}
    for hour in range(24):
        slot_start = _local_hour_boundary_ms(selected_day, hour, timezone)
        slot_end = _local_hour_boundary_ms(selected_day, hour + 1, timezone)
        for task in tasks:
            start, end = intervals[task.uuid]
            if (
                start is not None
                and end is not None
                and end > slot_start
                and start < slot_end
                and task.uuid not in first_visible_hour
            ):
                first_visible_hour[task.uuid] = hour
    for hour in range(24):
        slot_start = _local_hour_boundary_ms(selected_day, hour, timezone)
        slot_end = _local_hour_boundary_ms(selected_day, hour + 1, timezone)
        active = [
            task
            for task in tasks
            if (_task_start(task) is not None and (_task_end(task) or _task_start(task) or 0) > slot_start)
            and (_task_start(task) or 0) < slot_end
        ]
        label = f"{hour:02d}:00"
        band = _band_at(bands, hour * 60 + 30)
        band_label = f" {style.dim}[{band.label}]{style.reset}" if band else ""
        current = (
            is_today and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).hour == hour
            if now_ms is not None
            else False
        )
        current_label = f" {style.red}◀ now{style.reset}" if current else ""
        if not active:
            lines.append(f"{label} {style.dim}│{style.reset}{band_label}{current_label}")
            continue
        lines.append(f"{label} {style.dim}│{style.reset}{band_label}{current_label}")
        for task in active:
            start = _task_start(task)
            end = _task_end(task)
            duration = max(15, int(((end or start or slot_end) - (start or slot_start)) / 60_000))
            bar_width = max(1, min(12, duration // 15))
            marker = _marker(task, overlap=task.uuid in overlap_ids, style=style, ascii_only=ascii_only)
            lane = lane_by_uuid.get(task.uuid, 0)
            lane_prefix = f"L{lane + 1} " if width >= 72 else ""
            if first_visible_hour.get(task.uuid) != hour:
                continuation = "  +-- continues" if ascii_only else "  └─ continues"
                lines.append(f"     {lane_prefix}{style.dim}{continuation}{style.reset}")
                continue
            outside = start is not None and (
                start < day_start + snapshot.work_start_min * 60_000
                or start >= day_start + snapshot.work_end_min * 60_000
            )
            suffix = " [outside work hours]" if outside else ""
            description = _truncate(
                _highlight((task.description or "(untitled)") + suffix, highlight_query, ascii_only=ascii_only),
                max(8, width - 22 - len(lane_prefix)),
            )
            bar = "#" if ascii_only else "█"
            lines.append(f"     {lane_prefix}{marker} {bar * bar_width} {description}")
    lines.append("")
    total_minutes = sum(task.duration_min or 0 for task in tasks if (task.duration_min or 0) > 0)
    conflicts = len(overlap_ids) // 2
    lines.append(
        f"{style.dim}{len(tasks)} task{'s' if len(tasks) != 1 else ''} · "
        f"{_format_duration(total_minutes) or '0m'} planned · "
        f"{conflicts} conflict{'s' if conflicts != 1 else ''}{style.reset}"
    )
    return "\n".join(lines)


def render_week(
    snapshot: GlimpseSnapshot,
    *,
    week_start: dt.date | None = None,
    width: int = 120,
    color: bool = False,
    ascii_only: bool = False,
    highlight_query: str = "",
    now_ms: int | None = None,
) -> str:
    """Render seven days as a compact calendar, stacking days when narrow."""
    width = max(40, int(width))
    selected_start = week_start or snapshot.start_date
    timezone = resolve_tz(snapshot.timezone_name)
    style = style_for(color=color)
    days = [selected_start + dt.timedelta(days=offset) for offset in range(7)]
    groups = _day_tasks(snapshot)
    day_tasks = [groups.get(day.isoformat(), []) for day in days]
    day_overlaps = [_overlap_ids(tasks) for tasks in day_tasks]
    lines = [f"{style.bold}SCALPEL · Week · {selected_start.isoformat()}{style.reset}", ""]
    bands = _default_bands(snapshot)
    if bands and width >= 72:
        band_summary = " · ".join(
            f"{band.label} {band.start_min // 60:02d}:{band.start_min % 60:02d}-{band.end_min // 60:02d}:{band.end_min % 60:02d}"
            for band in bands
        )
        lines.append(f"{style.dim}Bands: {band_summary}{style.reset}")
        lines.append("")

    if width < 100:
        for day, tasks, overlaps in zip(days, day_tasks, day_overlaps, strict=True):
            conflict_count = len(overlaps) // 2
            lines.append(
                f"{style.bold}{day.strftime('%a %d %b')}{' · today' if now_ms is not None and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).date() == day else ''} "
                f"{style.dim}({len(tasks)} task{'s' if len(tasks) != 1 else ''}, "
                f"{conflict_count} conflict{'s' if conflict_count != 1 else ''}){style.reset}"
            )
            if not tasks:
                lines.append(f"  {style.dim}—{style.reset}")
            else:
                for task in tasks:
                    lines.append(
                        _row(
                            task,
                            overlap=task.uuid in overlaps,
                            timezone=timezone,
                            width=width,
                            style=style,
                            ascii_only=ascii_only,
                            highlight_query=highlight_query,
                        )
                    )
            lines.append("")
        return "\n".join(lines).rstrip()

    column_width = max(4, (width - 14) // 7)
    header = "  " + "  ".join(
        _truncate(
            f"{day.strftime('%a')} {day.day:02d}{' *' if now_ms is not None and dt.datetime.fromtimestamp(now_ms / 1000, tz=timezone).date() == day else ''}",
            column_width,
        ).ljust(column_width)
        for day in days
    )
    lines.append(header.rstrip())
    lines.append("  " + "  ".join(("-" if ascii_only else "─") * column_width for _ in days))
    max_rows = max((len(tasks) for tasks in day_tasks), default=0)
    for row_index in range(max_rows or 1):
        cells: list[str] = []
        for tasks, overlaps in zip(day_tasks, day_overlaps, strict=True):
            if row_index >= len(tasks):
                cells.append("".ljust(column_width))
                continue
            task = tasks[row_index]
            marker = (
                "!"
                if task.uuid in overlaps and ascii_only
                else "⚠"
                if task.uuid in overlaps
                else "@"
                if task.nautical_preview and ascii_only
                else "⚓"
                if task.nautical_preview
                else "x"
                if task.status.lower() == "completed" and ascii_only
                else "✓"
                if task.status.lower() == "completed"
                else "."
            )
            time = _local_time(_task_start(task), timezone)
            project = f" · {task.project}" if task.project else ""
            visible_cell = _truncate(
                f"{time} {marker} {_highlight(task.description or '(untitled)', highlight_query, ascii_only=ascii_only)}{project}",
                column_width,
            )
            cell = visible_cell
            if task.project and task.project in visible_cell:
                color_code = project_color(task.project, style=style)
                cell = (
                    visible_cell.replace(task.project, f"{color_code}{task.project}{style.reset}", 1)
                    if color_code
                    else visible_cell
                )
            cells.append(cell.ljust(column_width))
        lines.append("  " + "  ".join(cells).rstrip())
    return "\n".join(lines)
