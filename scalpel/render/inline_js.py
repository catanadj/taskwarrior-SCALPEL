# scalpel/render/inline_js.py
from __future__ import annotations

from .assets import read_render_asset

JS_ASSET_PATHS = (
    "js/part01_core.js",
    "js/part02_palette_goals.js",
    "js/part03_selection_ops.js",
    "js/part04_rendering.js",
    "js/part05_commands.js",
    "js/part06_drag_resize.js",
    "js/part08_notes.js",
    "js/part07_init.js",
)

JS_BLOCK = "\n".join(read_render_asset(path) for path in JS_ASSET_PATHS)
