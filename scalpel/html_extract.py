# Public helper API: extract SCALPEL payload JSON from rendered HTML
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HtmlPayloadExtractError(RuntimeError):
    message: str
    def __str__(self) -> str:
        return self.message


_SCRIPT_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>\s*(?P<body>.*?)\s*</script>",
    flags=re.IGNORECASE | re.DOTALL,
)

_TYPE_RE = re.compile(
    r'\btype\s*=\s*(?:"(?P<dq>[^"]+)"|\'(?P<sq>[^\']+)\'|(?P<bare>[^\s>]+))',
    flags=re.IGNORECASE,
)


def _attr_type(attrs: str) -> str | None:
    m = _TYPE_RE.search(attrs or "")
    if not m:
        return None
    return (m.group("dq") or m.group("sq") or m.group("bare") or "").strip()


def _extract_payload_json_from_data_assignment(html_text: str):
    """
    Fallback extractor for payload embedded as:
      const DATA = {...};
      var DATA = {...};
      DATA = {...};
      window.DATA = {...};
    Uses a balanced-brace scan to isolate the JSON object/array.
    """
    import html as _html
    import re

    m = re.search(r'\b(?:const|var)?\s*(?:window\.)?DATA\s*=\s*', html_text)
    if not m:
        raise ValueError("Could not find DATA assignment in HTML.")
    i = m.end()

    n = len(html_text)
    while i < n and html_text[i].isspace():
        i += 1
    if i >= n or html_text[i] not in "{[":
        raise ValueError("DATA assignment does not appear to start with '{' or '['.")

    start = i
    stack: list[str] = []
    in_str = False
    esc = False

    while i < n:
        ch = html_text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    break
                top = stack.pop()
                if (top == "{" and ch != "}") or (top == "[" and ch != "]"):
                    raise ValueError("Unbalanced braces while extracting DATA JSON.")
                if not stack:
                    i += 1
                    break
        i += 1

    blob = html_text[start:i].strip()
    blob = _html.unescape(blob)
    return json.loads(blob)


def extract_payload_json_from_html_text(html_text: str):
    """
    Extract SCALPEL payload JSON from HTML.

    Supported embeddings:
      1) Preferred: <script id="tw-data"> ...json... </script>   (type may be absent/variant)
      2) Also:      <script type="application/json[;...]" ...> ...json... </script>
      3) Fallback:  DATA = {...}  assignment
    """
    import html as _html
    import re

    # 1) script#tw-data (type-agnostic)
    pat_id = r'<script\b[^>]*\bid=["\']tw-data["\'][^>]*>(?P<body>.*?)</script>'
    for m in re.finditer(pat_id, html_text, flags=re.IGNORECASE | re.DOTALL):
        body = (m.group("body") or "").strip()
        if not body:
            continue
        try:
            payload = json.loads(_html.unescape(body))
        except Exception:
            continue
        return payload

    # 2) any <script type="application/json..."> (allow params like charset)
    pat_type = r'<script\b[^>]*\btype=["\']application/json(?:\s*;[^"\']*)?["\'][^>]*>(?P<body>.*?)</script>'
    for m in re.finditer(pat_type, html_text, flags=re.IGNORECASE | re.DOTALL):
        body = (m.group("body") or "").strip()
        if not body:
            continue
        try:
            payload = json.loads(_html.unescape(body))
        except Exception:
            continue
        return payload

    # 3) fallback DATA assignment
    try:
        return _extract_payload_json_from_data_assignment(html_text)
    except Exception as e:
        # Keep legacy-ish wording to avoid fragile expectations elsewhere.
        raise HtmlPayloadExtractError("No <script type='application/json'> payload block found in HTML.") from e

def extract_payload_json_from_html_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    html = p.read_text(encoding="utf-8")
    return extract_payload_json_from_html_text(html)
