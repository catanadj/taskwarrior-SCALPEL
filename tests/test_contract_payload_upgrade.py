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

    def test_upgrade_v1_missing_generated_at_is_repaired(self) -> None:
        payload = {
            "schema_version": 1,
            "cfg": {"tz": "UTC", "display_tz": "UTC"},
            "tasks": [{"uuid": "u1", "status": "pending", "tags": []}],
            "indices": {
                "by_uuid": {"u1": 0},
                "by_status": {"pending": [0]},
                "by_project": {},
                "by_tag": {},
                "by_day": {},
            },
        }
        out = upgrade_payload(payload, target_version=1)
        self.assertEqual(out.get("schema_version"), 1)
        self.assertIsInstance(out.get("generated_at"), str)
        self.assertTrue(bool(str(out.get("generated_at")).strip()))

    def test_upgrade_to_v2_repairs_missing_generated_at_from_v1_payload(self) -> None:
        payload = {
            "schema_version": 1,
            "cfg": {"tz": "UTC", "display_tz": "UTC"},
            "tasks": [{"uuid": "u1", "status": "pending", "tags": []}],
            "indices": {
                "by_uuid": {"u1": 0},
                "by_status": {"pending": [0]},
                "by_project": {},
                "by_tag": {},
                "by_day": {},
            },
        }
        out = upgrade_payload(payload, target_version=2)
        self.assertEqual(out.get("schema_version"), 2)
        self.assertIsInstance(out.get("generated_at"), str)
        self.assertTrue(bool(str(out.get("generated_at")).strip()))

if __name__ == "__main__":
    unittest.main(verbosity=2)
