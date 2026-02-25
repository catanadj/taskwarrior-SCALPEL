from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestPublicApiEntrypointContract(unittest.TestCase):
    def test_import_and_load_golden_payload(self) -> None:
        import scalpel
        from scalpel import normalize_payload, load_payload_from_json

        fixture = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"
        self.assertTrue(fixture.exists(), f"missing fixture: {fixture}")

        payload = load_payload_from_json(fixture)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("schema_version"), 2)
        self.assertIn("tasks", payload)
        self.assertIn("indices", payload)

        # normalize is idempotent on already-normal payload
        payload2 = normalize_payload(payload)
        self.assertEqual(payload2.get("schema_version"), 2)

        # smoke check re-export (module attribute)
        self.assertTrue(hasattr(scalpel, "load_payload_from_json"))
        self.assertTrue(hasattr(scalpel, "normalize_payload"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
