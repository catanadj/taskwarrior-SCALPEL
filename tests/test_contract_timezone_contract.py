import json
import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PY = os.environ.get("PYTHON", "python3")


def _run_py(code: str, *, env: dict) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e.update(env)
    e.setdefault("PYTHONPATH", str(REPO_ROOT))
    return subprocess.run(
        [PY, "-c", code],
        cwd=str(REPO_ROOT),
        env=e,
        text=True,
        capture_output=True,
    )


class TestTimezoneContract(unittest.TestCase):
    def test_cfg_tz_utc_is_invariant_across_process_tz(self):
        payload = {
            "cfg": {
                "tz": "UTC",
                "display_tz": "local",
                "view_key": "tztest",
                "view_start_ms": 1577836800000,  # 2020-01-01T00:00:00Z
                "days": 1,
                "px_per_min": 2,
                "work_start_min": 0,
                "work_end_min": 1440,
                "snap_min": 5,
                "default_duration_min": 30,
                "max_infer_duration_min": 180,
            },
            "tasks": [
                {
                    "uuid": "u1",
                    "status": "pending",
                    "tags": [],
                    "due_ms": 1577836800000 + 30 * 60 * 1000,
                },
                {
                    "uuid": "u2",
                    "status": "pending",
                    "tags": [],
                    "due_ms": 1577836800000 + 23 * 60 * 60 * 1000 + 30 * 60 * 1000,
                },
                {
                    "uuid": "u0",
                    "status": "pending",
                    "tags": [],
                    "due_ms": 1577836800000 - 30 * 60 * 1000,
                },
            ],
        }

        code = r'''
import json, os, time
from scalpel.schema import upgrade_payload
p = json.loads(os.environ["PAYLOAD_JSON"])
# Ensure process TZ applies (should NOT affect cfg.tz='UTC')
if hasattr(time, "tzset"):
    time.tzset()
out = upgrade_payload(p, target_version=2)
res = {
  "view_start_ms": out["cfg"]["view_start_ms"],
  "tz": out["cfg"].get("tz"),
  "day_keys": [t.get("day_key") for t in out.get("tasks", [])],
  "by_day_keys": sorted((out.get("indices") or {}).get("by_day", {}).keys()),
}
print(json.dumps(res, sort_keys=True))
'''

        env_base = {"PAYLOAD_JSON": json.dumps(payload)}

        p1 = _run_py(code, env={**env_base, "TZ": "UTC"})
        self.assertEqual(p1.returncode, 0, p1.stdout + "\n" + p1.stderr)

        p2 = _run_py(code, env={**env_base, "TZ": "America/Los_Angeles"})
        self.assertEqual(p2.returncode, 0, p2.stdout + "\n" + p2.stderr)

        self.assertEqual(p1.stdout.strip(), p2.stdout.strip())

    def test_contract_rejects_non_midnight_view_start_ms(self):
        payload_v2 = {
            "schema_version": 2,
            "generated_at": "x",
            "cfg": {
                "tz": "UTC",
                "display_tz": "local",
                "view_start_ms": 1577836800000 + 3600 * 1000,
            },
            "tasks": [{"uuid": "u1", "status": "pending", "tags": []}],
            "indices": {
                "by_uuid": {"u1": 0},
                "by_status": {"pending": [0]},
                "by_project": {},
                "by_tag": {},
                "by_day": {},
            },
            "meta": {"schema": {"name": "scalpel.payload", "version": 2}},
        }

        from scalpel.schema_contracts.v2 import validate_payload_v2

        errs = validate_payload_v2(payload_v2)
        self.assertIn("cfg.view_start_ms must be midnight in cfg.tz", errs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
