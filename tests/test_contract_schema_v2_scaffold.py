from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_upgrade_v1_to_v2_scaffold_is_stable() -> None:
    p = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(obj, dict)

    from scalpel.schema import upgrade_payload, validate_schema_v2

    v2 = upgrade_payload(obj, target_version=2)
    assert isinstance(v2, dict)
    assert v2.get("schema_version") == 2

    meta = v2.get("meta")
    assert isinstance(meta, dict)
    sch = meta.get("schema")
    assert isinstance(sch, dict)
    assert sch.get("name") == "scalpel.payload"
    assert sch.get("version") == 2

    errs = validate_schema_v2(v2, label="v2")
    assert errs == [], f"unexpected v2 validation errors: {errs}"
