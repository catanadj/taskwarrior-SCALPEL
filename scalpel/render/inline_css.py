# scalpel/render/inline_css.py
from __future__ import annotations

from .css.part01_tokens_theme import CSS_PART as CSS_01
from .css.part02_base import CSS_PART as CSS_02
from .css.part03_header_layout import CSS_PART as CSS_03
from .css.part04_panels_palette import CSS_PART as CSS_04
from .css.part05_calendar import CSS_PART as CSS_05
from .css.part07_modals_misc import CSS_PART as CSS_06

CSS_BLOCK = "\n".join([
  CSS_01, CSS_02, CSS_03, CSS_04, CSS_05, CSS_06
])
