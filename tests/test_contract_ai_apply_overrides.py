import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scalpel.ai import PlanOverride, apply_plan_overrides
from scalpel.util.tz import day_key_from_ms, resolve_tz


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


class TestAiApplyOverridesContract(unittest.TestCase):
    def test_apply_plan_overrides_updates_calc_fields_and_indices(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        task0 = payload["tasks"][0]
        uuid = task0["uuid"]
        orig_due = task0.get("due_ms")
        orig_scheduled = task0.get("scheduled_ms")

        start_ms = int(datetime(2020, 1, 2, 9, 0, tzinfo=timezone.utc).timestamp() * 1000)
        due_ms = start_ms + (60 * 60000)
        overrides = {uuid: PlanOverride(start_ms=start_ms, due_ms=due_ms, duration_min=60)}

        out = apply_plan_overrides(payload, overrides)
        out_task = next(t for t in out["tasks"] if t.get("uuid") == uuid)

        self.assertEqual(out_task.get("start_calc_ms"), start_ms)
        self.assertEqual(out_task.get("end_calc_ms"), due_ms)
        self.assertEqual(out_task.get("dur_calc_min"), 60)
        self.assertEqual(out_task.get("due_ms"), orig_due)
        self.assertEqual(out_task.get("scheduled_ms"), orig_scheduled)

        tzinfo = resolve_tz(out["cfg"]["tz"])
        expected_day_key = day_key_from_ms(start_ms, tzinfo)
        self.assertEqual(out_task.get("day_key"), expected_day_key)
        self.assertIn(expected_day_key, out["indices"]["by_day"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
