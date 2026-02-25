from __future__ import annotations

from typing import Any, Dict, Optional

from scalpel.schema import LATEST_SCHEMA_VERSION


def pick_target_schema(payload: Dict[str, Any], requested: Optional[int]) -> int:
    """
    Decide the schema to upgrade to.

    Rules:
      - Default is latest.
      - Never downgrade (if input is already newer than requested, keep input version).
      - Reject requests newer than latest.
    """
    cur = payload.get("schema_version")
    cur_i = int(cur) if isinstance(cur, int) else 0

    if requested is None:
        req = int(LATEST_SCHEMA_VERSION)
    else:
        req = int(requested)
        if req < 1:
            req = 1

    if req > int(LATEST_SCHEMA_VERSION):
        raise ValueError(f"--schema {req} unsupported (latest={LATEST_SCHEMA_VERSION})")

    return max(cur_i, req)

