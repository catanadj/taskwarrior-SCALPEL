import json
import os
import subprocess
import unittest
import datetime as dt
from pathlib import Path
from unittest.mock import patch

from scalpel.payload import build_payload
from scalpel.schema_v1 import apply_schema_v1
from scalpel.validate import assert_valid_payload
from scalpel.validate import validate_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "payload_v1_min.json"

def _py() -> str:
    return os.environ.get("PYTHON", "python3")

class TestPublicValidateApiContract(unittest.TestCase):
    def test_library_and_tool_agree_on_fixture(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        errs = validate_payload(payload)
        self.assertEqual(errs, [], f"library errors: {errs}")

        cmd = [_py(), "-m", "scalpel.tools.validate_payload", "--in", str(FIXTURE)]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)

    def test_validate_accepts_schema_v1_payload_without_meta(self) -> None:
        payload = apply_schema_v1(
            {
                "cfg": {
                    "view_key": "k",
                    "view_start_ms": 0,
                    "days": 1,
                    "px_per_min": 2,
                    "work_start_min": 0,
                    "work_end_min": 60,
                    "snap_min": 10,
                    "default_duration_min": 10,
                    "max_infer_duration_min": 60,
                },
                "tasks": [],
            }
        )
        self.assertNotIn("meta", payload)
        self.assertEqual(validate_payload(payload), [])
        assert_valid_payload(payload)

    def test_validate_accepts_float_px_per_min(self) -> None:
        payload = apply_schema_v1(
            {
                "cfg": {
                    "view_key": "k",
                    "view_start_ms": 0,
                    "days": 1,
                    "px_per_min": 2.5,
                    "work_start_min": 0,
                    "work_end_min": 60,
                    "snap_min": 10,
                    "default_duration_min": 10,
                    "max_infer_duration_min": 60,
                },
                "tasks": [],
                "meta": {},
            }
        )
        self.assertEqual(validate_payload(payload), [])
        assert_valid_payload(payload)

    def test_build_payload_output_validates(self) -> None:
        with patch("scalpel.payload.run_task_export", return_value=[]), patch(
            "scalpel.payload._load_nautical_core", return_value=None
        ):
            payload = build_payload(
                filter_str="status:pending",
                start_date=dt.date(2026, 1, 1),
                days=1,
                work_start=480,
                work_end=1020,
                snap=10,
                default_duration_min=10,
                max_infer_duration_min=480,
                px_per_min=2.5,
                goals_path="does-not-exist.json",
                tz="UTC",
                display_tz="UTC",
            )
        self.assertEqual(validate_payload(payload), [])
        assert_valid_payload(payload)

if __name__ == "__main__":
    unittest.main(verbosity=2)
