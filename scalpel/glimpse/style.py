from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgendaStyle:
    """Small ANSI palette kept separate from layout and content."""

    reset: str = "\033[0m"
    dim: str = "\033[2m"
    bold: str = "\033[1m"
    cyan: str = "\033[36m"
    yellow: str = "\033[33m"
    green: str = "\033[32m"
    magenta: str = "\033[35m"
    red: str = "\033[31m"


PLAIN_STYLE = AgendaStyle(*("" for _ in range(8)))


def color_enabled(*, requested: bool | None = None, stream: object = sys.stdout) -> bool:
    if requested is False or "NO_COLOR" in os.environ:
        return False
    if os.environ.get("TERM", "").strip().lower() in {"", "dumb", "unknown"}:
        return False
    if requested is True:
        return True
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def style_for(*, color: bool) -> AgendaStyle:
    return AgendaStyle() if color else PLAIN_STYLE


def project_color(project: str | None, *, style: AgendaStyle) -> str:
    """Return a stable ANSI color for a project, or no color in plain mode."""
    if not project or not style.reset:
        return ""
    palette = (style.cyan, style.yellow, style.green, style.magenta, style.red)
    return palette[sum(ord(char) for char in project) % len(palette)]
