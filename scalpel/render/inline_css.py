# scalpel/render/inline_css.py
from __future__ import annotations

from .assets import read_render_asset

CSS_ASSET_PATHS = (
    "css/part01_tokens_theme.css",
    "css/part02_base.css",
    "css/part03_header_layout.css",
    "css/part04_panels_palette.css",
    "css/part05_calendar.css",
    "css/part07_modals_misc.css",
)

CSS_BLOCK = "\n".join(read_render_asset(path) for path in CSS_ASSET_PATHS)
