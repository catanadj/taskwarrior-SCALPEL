from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGoldenPayloadV2FixtureContract(unittest.TestCase):
    def test_fixture_is_up_to_date(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        cmd = [
            sys.executable,
            "-m",
            "scalpel.tools.gen_fixtures",
            "--schema",
            "2",
            "--check",
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
