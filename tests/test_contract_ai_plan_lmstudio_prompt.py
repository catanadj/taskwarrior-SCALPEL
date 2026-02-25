import json
import unittest
from pathlib import Path

from scalpel.tools.ai_plan_lmstudio import _build_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "planner_core_fixture.json"


class TestAiPlanLmStudioPromptContract(unittest.TestCase):
    def test_prompt_includes_selected_tasks(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        prompt = _build_prompt(payload, ["a"], "align starts")
        obj = json.loads(prompt)
        self.assertEqual(obj["selected_uuids"], ["a"])
        self.assertEqual(len(obj["tasks"]), 1)
        self.assertEqual(obj["tasks"][0]["uuid"], "a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
