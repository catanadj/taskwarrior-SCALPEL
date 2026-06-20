# scalpel/render/js/core.py
from __future__ import annotations

from ..assets import read_render_asset

_CORE = read_render_asset("js/part01_core.js")
_PERSIST = read_render_asset("js/persist.js")


def _inject_after_use_strict(js: str, inject: str) -> str:
    needle = '"use strict";'
    idx = js.find(needle)
    if idx == -1:
        # Fallback: just prepend (safe even if it ends up outside, but should not happen)
        return inject + "\n" + js
    insert_at = idx + len(needle)
    return js[:insert_at] + "\n\n" + inject + "\n" + js[insert_at:]


JS_PART = _inject_after_use_strict(_CORE, _PERSIST)
