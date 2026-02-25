# scalpel/render/html_markup.py
from __future__ import annotations

from .markup.overlays import MARKUP as OVERLAYS
from .markup.header import MARKUP as HEADER
from .markup.layout_open import MARKUP as LAYOUT_OPEN
from .markup.left_panel import MARKUP as LEFT_PANEL
from .markup.calendar_panel import MARKUP as CALENDAR_PANEL
from .markup.right_panel import MARKUP as RIGHT_PANEL
from .markup.layout_close import MARKUP as LAYOUT_CLOSE

# Assembled body markup (kept as exact concatenation, no extra newlines inserted here)
BODY_MARKUP = (
    OVERLAYS
    + HEADER
    + LAYOUT_OPEN
    + LEFT_PANEL
    + CALENDAR_PANEL
    + RIGHT_PANEL
    + LAYOUT_CLOSE
)
