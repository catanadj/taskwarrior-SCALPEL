from __future__ import annotations

import json
import os
import time
import unittest
from pathlib import Path

from scalpel.bench import make_large_payload_v1
from scalpel.query_lang import Query
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


def _load_large_payload(n_tasks: int = 20000, seed: int = 1) -> dict:
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    large = make_large_payload_v1(base, n_tasks=n_tasks, seed=seed)
    return upgrade_payload(large, target_version=int(LATEST_SCHEMA_VERSION))


class TestQueryPerfBudgetContract(unittest.TestCase):
    def test_query_run_budget_large_payload(self) -> None:
        if os.environ.get("SCALPEL_SKIP_PERF_TESTS", "").strip() == "1":
            self.skipTest("SCALPEL_SKIP_PERF_TESTS=1")

        payload = _load_large_payload()
        q = Query.parse(r"status:pending description~\\[ tag:bench")

        # Ensure the benchmark query actually does useful work.
        got = q.run(payload)
        self.assertGreater(len(got), 0, "perf benchmark query unexpectedly matched no tasks")

        warmup = 5
        loops = 60
        budget_ms = float(os.environ.get("SCALPEL_QUERY_PERF_BUDGET_MS", "300"))

        for _ in range(warmup):
            q.run(payload)

        t0 = time.perf_counter()
        for _ in range(loops):
            q.run(payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLessEqual(
            elapsed_ms,
            budget_ms,
            f"Query perf budget exceeded: {elapsed_ms:.2f} ms > {budget_ms:.2f} ms "
            f"(loops={loops}, n_tasks=20000)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
