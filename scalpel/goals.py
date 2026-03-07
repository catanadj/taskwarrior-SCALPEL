

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FUNC_COLOR_RE = re.compile(r"^(?:rgb|hsl)a?\(\s*[-+0-9.%\s,]+\)$", re.IGNORECASE)
_NAMED_COLOR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,31}$")


def _normalize_css_color(value: str) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    if _HEX_COLOR_RE.fullmatch(s):
        return s
    if _FUNC_COLOR_RE.fullmatch(s):
        return s
    if _NAMED_COLOR_RE.fullmatch(s):
        return s.lower()
    return ""


def load_goals_config(path: str) -> Optional[Dict[str, Any]]:
    """Load goals config JSON.

    Accepted formats:
      - { "goals": [ {..}, ... ] }
      - [ {..}, ... ]

    Goal fields (v1):
      name (required)
      id (optional; auto-derived from name)
      color (required; any CSS color, typically #RRGGBB)
      projects (optional; list of project prefixes)
      tags (optional; list of tags)
      tags_all (optional; list of tags that must all be present)
      mode (optional; "any" (default) or "all")
    """
    if not path:
        return None
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return None

    if isinstance(raw, dict) and isinstance(raw.get("goals"), list):
        goals = raw.get("goals")
    elif isinstance(raw, list):
        goals = raw
    else:
        return None

    out = []
    for g in goals:
        if not isinstance(g, dict):
            continue
        name = str(g.get("name") or "").strip()
        if not name:
            continue
        gid = str(g.get("id") or "").strip()
        if not gid:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            gid = slug or f"goal-{len(out)+1}"
        color = _normalize_css_color(g.get("color") or "")
        if not color:
            continue

        projects = g.get("projects") or g.get("projects_prefix") or []
        tags_any = g.get("tags") or g.get("tags_any") or []
        tags_all = g.get("tags_all") or []
        mode = str(g.get("mode") or "any").strip().lower()
        if mode not in ("any", "all"):
            mode = "any"

        out.append(
            {
                "id": gid,
                "name": name,
                "color": color,
                "projects": [
                    str(x).strip()
                    for x in (projects if isinstance(projects, list) else [])
                    if str(x).strip()
                ],
                "tags": [
                    str(x).strip()
                    for x in (tags_any if isinstance(tags_any, list) else [])
                    if str(x).strip()
                ],
                "tags_all": [
                    str(x).strip()
                    for x in (tags_all if isinstance(tags_all, list) else [])
                    if str(x).strip()
                ],
                "mode": mode,
            }
        )

    return {"version": 1, "goals": out}
