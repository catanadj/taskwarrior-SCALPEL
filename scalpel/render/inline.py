# scalpel/render/inline.py
from __future__ import annotations

import json
from .template import HTML_TEMPLATE

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover
    orjson = None  # type: ignore

_DATA_MARKER = "__DATA_JSON__"
_DATA_MARKER_COUNT = HTML_TEMPLATE.count(_DATA_MARKER)


def build_html(payload: dict) -> str:
    # Inject DATA JSON into the HTML template.
    # Hardening:
    #   - Template must contain the __DATA_JSON__ placeholder exactly once.
    #   - Generated HTML must not contain the placeholder after injection.
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict, got {type(payload).__name__}")

    if _DATA_MARKER_COUNT != 1:
        raise RuntimeError(f"HTML_TEMPLATE must contain {_DATA_MARKER} exactly once (found {_DATA_MARKER_COUNT})")

    if orjson is not None:
        data_json = orjson.dumps(payload).decode("utf-8")
    else:
        data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    data_json = data_json.replace("</", r"<\/")  # script-safe injection
    html = HTML_TEMPLATE.replace(_DATA_MARKER, data_json)

    if _DATA_MARKER in html:
        raise RuntimeError("HTML generation failed: marker still present after injection")

    return html
