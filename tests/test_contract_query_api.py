from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestQueryApiContract(unittest.TestCase):
    def test_query_helpers_work_on_golden_payload(self) -> None:
        from scalpel.api import load_payload_from_json
        from scalpel.api import (
            iter_tasks,
            task_by_uuid,
            tasks_by_status,
            tasks_by_project,
            tasks_by_tag,
            tasks_by_day,
        )

        fixture = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"
        self.assertTrue(fixture.exists(), f"missing fixture: {fixture}")

        payload = load_payload_from_json(fixture)
        self.assertEqual(payload.get("schema_version"), 2)

        tasks = payload.get("tasks") or []
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0, "golden payload must contain at least 1 task")

        # uuid lookup round-trip for a few tasks
        for t in tasks[:10]:
            if not isinstance(t, dict):
                continue
            u = t.get("uuid")
            if isinstance(u, str) and u:
                t2 = task_by_uuid(payload, u)
                self.assertIsNotNone(t2)
                self.assertEqual(t2.get("uuid"), u)

        # indices-driven group lookups should be consistent with indices lists
        idx = payload.get("indices") or {}
        self.assertIsInstance(idx, dict)

        for key, fn in [
            ("by_status", tasks_by_status),
            ("by_project", tasks_by_project),
            ("by_tag", tasks_by_tag),
            ("by_day", tasks_by_day),
        ]:
            m = idx.get(key)
            if not isinstance(m, dict) or not m:
                continue
            k0 = next(iter(m.keys()))
            got = fn(payload, k0, include_smoke=True)
            self.assertIsInstance(got, list)

            idx_list = m.get(k0)
            if isinstance(idx_list, list):
                # Compare uuid sets to avoid ordering assumptions
                expected = set()
                for i in idx_list:
                    if isinstance(i, int) and 0 <= i < len(tasks) and isinstance(tasks[i], dict):
                        u = tasks[i].get("uuid")
                        if isinstance(u, str) and u:
                            expected.add(u)
                actual = set()
                for t in got:
                    if isinstance(t, dict):
                        u = t.get("uuid")
                        if isinstance(u, str) and u:
                            actual.add(u)
                self.assertEqual(actual, expected)

        # iter_tasks should yield dicts
        for t in iter_tasks(payload, include_smoke=True):
            self.assertIsInstance(t, dict)
            break


if __name__ == "__main__":
    unittest.main(verbosity=2)
