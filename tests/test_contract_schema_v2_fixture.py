from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests/fixtures/golden_payload_v2.json"


class TestSchemaV2FixtureContract(unittest.TestCase):
    def test_fixture_validates_with_validate_payload_tool(self) -> None:
        self.assertTrue(FIXTURE.exists(), f"Missing fixture: {FIXTURE}")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        cmd = [
            sys.executable,
            "-m",
            "scalpel.tools.validate_payload",
            "--in",
            str(FIXTURE),
        ]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)
