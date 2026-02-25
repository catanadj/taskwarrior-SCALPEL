# scalpel/palette.py
from __future__ import annotations

from dataclasses import dataclass
from .model import Task


@dataclass(frozen=True)
class PaletteNode:
    name: str
    count: int
    color: str | None = None
    children: tuple["PaletteNode", ...] = ()


def build_project_tag_tree(tasks: list[Task]) -> PaletteNode:
    """
    Root
      ProjectA
        tag1
        tag2
      ProjectB
        tagX
    """


def resolve_task_color(task: Task,
                       goal_color: str | None,
                       overrides: dict[str, str]) -> str | None:
    """Apply override precedence (tag override > project override > goal color)."""

