import unittest
from scalpel.schema import upgrade_payload

class TestPayloadUpgradeContract(unittest.TestCase):
    def test_upgrade_legacy_payload_to_v1(self) -> None:
        legacy = {
            "cfg": {
                "view_key": "legacy",
                "view_start_ms": 0,
                "days": 1,
                "px_per_min": 2,
                "work_start_min": 480,
                "work_end_min": 1020,
                "snap_min": 5,
                "default_duration_min": 30,
                "max_infer_duration_min": 180,
            },
            "tasks": [],
            "meta": {"generated_by": "contract"},
        }
        out = upgrade_payload(legacy)
        self.assertEqual(out.get("schema_version"), 2)
        self.assertIn("generated_at", out)
        self.assertIn("indices", out)

if __name__ == "__main__":
    unittest.main(verbosity=2)
