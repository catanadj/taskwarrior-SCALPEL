from __future__ import annotations

import importlib
import unittest


class TestAiPlanTasksImportContract(unittest.TestCase):
    def test_module_imports_and_exposes_main(self) -> None:
        mod = importlib.import_module("scalpel.tools.ai_plan_tasks")
        self.assertTrue(callable(getattr(mod, "main", None)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
