from __future__ import annotations

import curses
import datetime as dt
from dataclasses import dataclass, replace
from typing import Callable, Literal

from ..util.tz import resolve_tz
from .details import task_details
from .model import GlimpseSnapshot
from .render import render_agenda, render_day, render_week
from .search import search_snapshot

ViewName = Literal["agenda", "day", "week"]


@dataclass(frozen=True, slots=True)
class GlimpseState:
    view: ViewName = "agenda"
    day_offset: int = 0
    selected: int = 0
    help_visible: bool = False
    details_visible: bool = False
    query: str = ""
    refresh_requested: bool = False
    should_quit: bool = False


def update_state(state: GlimpseState, key: str) -> GlimpseState:
    """Apply one key without requiring a terminal, making interaction testable."""
    if key in {"q", "Q"}:
        return replace(state, should_quit=True)
    if key in {"r", "R"}:
        return replace(state, refresh_requested=True, details_visible=False)
    if key in {"\n", "KEY_ENTER"}:
        return replace(state, details_visible=not state.details_visible)
    if key in {"\x1b", "KEY_EXIT"}:
        return replace(state, details_visible=False, help_visible=False)
    if key in {"a", "A"}:
        return replace(state, view="agenda")
    if key in {"d", "D"}:
        return replace(state, view="day")
    if key in {"w", "W"}:
        return replace(state, view="week")
    if key in {"h", "KEY_LEFT"}:
        return replace(state, day_offset=state.day_offset - 1, selected=0)
    if key in {"l", "KEY_RIGHT"}:
        return replace(state, day_offset=state.day_offset + 1, selected=0)
    if key in {"j", "KEY_DOWN"}:
        return replace(state, selected=state.selected + 1)
    if key in {"k", "KEY_UP"}:
        return replace(state, selected=max(0, state.selected - 1))
    if key == "t":
        return replace(state, day_offset=0, selected=0)
    if key == "?":
        return replace(state, help_visible=not state.help_visible)
    return state


def _content(snapshot: GlimpseSnapshot, state: GlimpseState, width: int) -> str:
    snapshot = search_snapshot(snapshot, state.query)
    day = snapshot.start_date + dt.timedelta(days=state.day_offset)
    if state.view == "day":
        return render_day(snapshot, day=day, width=width, color=False, highlight_query=state.query)
    if state.view == "week":
        return render_week(snapshot, week_start=day, width=width, color=False, highlight_query=state.query)
    return render_agenda(snapshot, width=width, color=False, highlight_query=state.query)


def _detail_annotations(snapshot: GlimpseSnapshot, task_index: int) -> tuple[str, ...]:
    task = snapshot.tasks[task_index]
    start = task.start_ms
    end = task.end_ms or (start + (task.duration_min or 0) * 60_000 if start is not None else None)
    conflict = any(
        other.uuid != task.uuid and other.start_ms is not None and other.end_ms is not None and start is not None and end is not None
        and start < other.end_ms and other.start_ms < end
        for other in snapshot.tasks
    )
    notes = ["Overlaps another task." if conflict else "No overlap detected."]
    if start is not None:
        day_start = int(dt.datetime.fromtimestamp(start / 1000, tz=resolve_tz(snapshot.timezone_name)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        minute = int((start - day_start) / 60_000)
        if minute < snapshot.work_start_min or minute >= snapshot.work_end_min:
            notes.append("Starts outside configured work hours.")
    return tuple(notes)


def _read_search_query(window: curses.window, height: int, width: int) -> str:
    """Read a search query while guaranteeing terminal echo restoration."""
    curses.echo()
    try:
        window.addstr(height - 1, 0, "Search: ")
        return window.getstr(height - 1, 8, max(1, width - 9)).decode("utf-8", errors="replace").strip()
    finally:
        curses.noecho()


def run_interactive(snapshot: GlimpseSnapshot | None = None, refresh: Callable[[], GlimpseSnapshot] | None = None, loader: Callable[[], GlimpseSnapshot] | None = None) -> None:
    """Run the read-only curses shell and always restore the terminal on exit."""

    def loop(screen: object) -> None:
        nonlocal snapshot
        window = screen  # curses.wrapper supplies a curses window at runtime.
        assert isinstance(window, curses.window)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        window.keypad(True)
        state = GlimpseState()
        status = ""
        if snapshot is None and loader is not None:
            window.erase()
            loading_width = max(0, window.getmaxyx()[1] - 1)
            window.addnstr(0, 0, "SCALPEL Glimpse", loading_width)
            window.addnstr(2, 0, "Loading Taskwarrior data…", loading_width)
            window.refresh()
            try:
                snapshot = loader()
            except Exception as exc:  # pragma: no cover - terminal-only failure path
                status = f"Load failed: {exc} · press r to retry · q to quit"
        while not state.should_quit:
            height, width = window.getmaxyx()
            window.erase()
            body = status or "? for help · q to quit"
            if state.help_visible:
                body = "a agenda · d day · w week · h/l day · j/k select · r refresh · q quit"
            content = ["Loading Taskwarrior data…"] if snapshot is None else _content(snapshot, state, max(40, width - 1)).splitlines()
            if state.details_visible and snapshot is not None:
                filtered = search_snapshot(snapshot, state.query)
                if filtered.tasks:
                    detail_index = min(state.selected, len(filtered.tasks) - 1)
                    selected_task = filtered.tasks[detail_index]
                    original_index = next(index for index, item in enumerate(snapshot.tasks) if item.uuid == selected_task.uuid)
                    content = task_details(selected_task, width=max(32, width - 4), timezone_name=snapshot.timezone_name, annotations=_detail_annotations(snapshot, original_index)).splitlines()
                else:
                    content = ["No matching task selected."]
            elif state.help_visible:
                content = [body]
            for row, line in enumerate(content[: max(0, height - 2)]):
                try:
                    window.addnstr(row, 0, line, max(0, width - 1))
                except curses.error:
                    pass
            try:
                window.addnstr(height - 1, 0, body, max(0, width - 1), curses.A_REVERSE)
            except curses.error:
                pass
            key = window.get_wch()
            if isinstance(key, str):
                if key == "/":
                    query = _read_search_query(window, height, width)
                    state = replace(state, query=query.strip(), selected=0)
                    continue
                state = update_state(state, key)
            else:
                state = update_state(state, str(key))
            if state.refresh_requested:
                callback = refresh or loader
                if callback is None:
                    status = "Refresh unavailable in payload mode"
                else:
                    try:
                        status = "Loading Taskwarrior data…"
                        snapshot = callback()
                        status = "Refreshed · ? for help · q to quit"
                    except Exception as exc:  # pragma: no cover - terminal-only failure path
                        status = f"Refresh failed: {exc}"
                state = replace(state, refresh_requested=False, selected=0)

    curses.wrapper(loop)
