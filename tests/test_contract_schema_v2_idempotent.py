from __future__ import annotations

import copy
import json
from pathlib import Path

from scalpel.schema import upgrade_payload, LATEST_SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v2.json"


def test_upgrade_v2_is_strict_noop_and_non_mutating() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)

    before = copy.deepcopy(payload)

    out = upgrade_payload(payload, target_version=LATEST_SCHEMA_VERSION)

    # Must not mutate input.
    assert payload == before

    # Must be semantically identical.
    assert out == before

    # Must remain a no-op on repeated calls.
    out2 = upgrade_payload(out, target_version=LATEST_SCHEMA_VERSION)
    assert out2 == before

