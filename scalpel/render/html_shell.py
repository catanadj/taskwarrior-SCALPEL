# scalpel/render/html_shell.py
from __future__ import annotations

HTML_SHELL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Taskwarrior Calendar</title>
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
