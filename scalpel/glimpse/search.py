from __future__ import annotations

from .model import GlimpseSnapshot, GlimpseTask


def search_tasks(tasks: tuple[GlimpseTask, ...], query: str) -> tuple[GlimpseTask, ...]:
    needle = query.strip().lower()
    if not needle:
        return tasks
    return tuple(
        task
        for task in tasks
        if needle in " ".join((task.description, task.uuid, task.project or "", *task.tags)).lower()
    )


def search_snapshot(snapshot: GlimpseSnapshot, query: str) -> GlimpseSnapshot:
    return GlimpseSnapshot(snapshot.start_date, snapshot.days, snapshot.timezone_name, search_tasks(snapshot.tasks, query))
