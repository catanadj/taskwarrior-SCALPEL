# scalpel/render/inline_js.py
from __future__ import annotations

from .js.part01_core import JS_PART as JS_01
from .js.part02_palette_goals import JS_PART as JS_02
from .js.part03_selection_ops import JS_PART as JS_03
from .js.part04_rendering import JS_PART as JS_04
from .js.part05_commands import JS_PART as JS_05
from .js.part06_drag_resize import JS_PART as JS_06
from .js.part08_notes import JS_PART as JS_08
from .js.part07_init import JS_PART as JS_07

JS_BLOCK = "\n".join([
  JS_01, JS_02, JS_03, JS_04, JS_05, JS_06, JS_08, JS_07
])
