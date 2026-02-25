# scalpel/render/template.py
from __future__ import annotations

from .html_shell import HTML_SHELL
from .html_markup import BODY_MARKUP
from .inline_css import CSS_BLOCK
from .inline_js import JS_BLOCK


# Assemble full HTML template (data is injected later by build_html)
HTML_TEMPLATE = (
    HTML_SHELL
    .replace("__CSS_BLOCK__", CSS_BLOCK)
    .replace("__JS_BLOCK__", JS_BLOCK)
    .replace("__BODY_MARKUP__", BODY_MARKUP)
)


def build_html(data: dict) -> str:
    import json

    payload = json.dumps(data, ensure_ascii=False)
    # Prevent accidental </script> termination if it ever appears in task data
    payload = payload.replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DATA_JSON__", payload)
