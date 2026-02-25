import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestFilterPayloadApiContract(unittest.TestCase):
    def test_filter_payload_filters_and_remaps_indices(self) -> None:
        from scalpel.api import filter_payload
        from scalpel.api import load_payload_from_json  # existing public helper

        payload = load_payload_from_json(REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json")
        tasks = payload.get("tasks") or []
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)

        # Pick a "real" uuid if present (avoid synthetic 000... fixtures when possible)
        synthetic = {
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        }
        pick = None
        for t in tasks:
            if isinstance(t, dict):
                u = t.get("uuid")
                if isinstance(u, str) and u and u not in synthetic:
                    pick = u
                    break
        if pick is None:
            pick = tasks[0].get("uuid") if isinstance(tasks[0], dict) else None
        self.assertIsInstance(pick, str)
        self.assertTrue(pick)

        out = filter_payload(payload, f"uuid:{pick}")
        out_tasks = out.get("tasks") or []
        self.assertEqual(len(out_tasks), 1)
        self.assertEqual(out_tasks[0].get("uuid"), pick)

        idx = out.get("indices") or {}
        self.assertIsInstance(idx, dict)
        by_uuid = idx.get("by_uuid") or {}
        self.assertIsInstance(by_uuid, dict)
        self.assertEqual(by_uuid.get(pick), 0)

        # cfg/meta preserved by default when present
        if "cfg" in payload:
            self.assertEqual(out.get("cfg"), payload.get("cfg"))
        if "meta" in payload:
            self.assertEqual(out.get("meta"), payload.get("meta"))

    def test_filter_payload_empty_query_is_noop(self) -> None:
        from scalpel.api import filter_payload
        from scalpel.api import load_payload_from_json

        payload = load_payload_from_json(REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json")
        out = filter_payload(payload, "")
        self.assertEqual(len(out.get("tasks") or []), len(payload.get("tasks") or []))

    def test_filter_payload_keep_meta_false_drops_meta(self) -> None:
        from scalpel.api import filter_payload
        from scalpel.api import load_payload_from_json

        payload = load_payload_from_json(REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json")
        self.assertIn("meta", payload)

        out = filter_payload(payload, "", keep_meta=False)
        self.assertNotIn("meta", out)


if __name__ == "__main__":
    unittest.main()
