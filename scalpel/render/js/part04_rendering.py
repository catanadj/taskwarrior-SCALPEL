# scalpel/render/js/part04_rendering.py
from __future__ import annotations

from pathlib import Path

_JS_PATH = Path(__file__).with_suffix('.js')

try:
    JS_PART = _JS_PATH.read_text(encoding='utf-8')
except OSError as ex:
    raise RuntimeError(f"Failed to load JS source from {_JS_PATH}") from ex
