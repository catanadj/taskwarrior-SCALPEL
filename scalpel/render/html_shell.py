# scalpel/render/html_shell.py
from __future__ import annotations

FAVICON_HREF = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' rx='14' fill='%230f1318'/%3E"
    "%3Cpath d='M17 45 43 19l4 4-26 26H17z' fill='%23ff8a5b'/%3E"
    "%3Cpath d='M40 16l8 8' stroke='%23ffd7c8' stroke-width='5' stroke-linecap='round'/%3E"
    "%3Cpath d='M16 48h10' stroke='%239aa6b2' stroke-width='4' stroke-linecap='round'/%3E"
    "%3C/svg%3E"
)

HTML_SHELL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SCALPEL</title>
<link rel="icon" type="image/svg+xml" href="__FAVICON_HREF__" />
<style>
__CSS_BLOCK__
</style>
</head>
<body>
__BODY_MARKUP__
<script id="tw-data" type="application/json">
__DATA_JSON__
</script>

<script>
__JS_BLOCK__
</script>
</body>
</html>
"""

HTML_SHELL = HTML_SHELL.replace("__FAVICON_HREF__", FAVICON_HREF)
