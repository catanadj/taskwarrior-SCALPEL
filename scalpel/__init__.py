"""SCALPEL Python package.

Public API:
  - import from `scalpel.api` (preferred) or `import scalpel` (re-export)
"""

from __future__ import annotations

from .api import *  # noqa: F401,F403
from . import api as _api

__all__ = list(_api.__all__)

from .api import (
    Query,
    iter_tasks,
    load_payload_from_html,
    load_payload_from_json,
    normalize_payload,
    select_tasks,
    task_by_uuid,
    tasks_by_status,
    tasks_by_project,
    tasks_by_tag,
    tasks_by_day,





)

