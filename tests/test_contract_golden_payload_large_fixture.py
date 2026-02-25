from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests/fixtures/golden_payload_large_v1.json"
GEN = REPO_ROOT / "scripts/scalpel_fixtures_generate_large_payload_v1.py"

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

class TestGoldenLargePayloadFixtureContract(unittest.TestCase):
    def test_fixture_exists(self):
        self.assertTrue(FIXTURE.exists(), f"missing fixture: {FIXTURE}")

    def test_fixture_is_up_to_date(self):
        self.assertTrue(GEN.exists(), f"missing generator: {GEN}")
        with tempfile.TemporaryDirectory() as td:
            outp = Path(td) / "golden_payload_large_v1.json"
            cmd = ["python3", str(GEN), "--out", str(outp)]
            p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, (p.stdout or "") + "\n" + (p.stderr or ""))

            self.assertEqual(
                _sha256(FIXTURE),
                _sha256(outp),
                "golden_payload_large_v1.json differs from generator output; run generator to refresh fixture",
            )

    def test_fixture_validates_with_validate_payload_tool(self):
        cmd = ["python3", "-m", "scalpel.tools.validate_payload", "--in", str(FIXTURE)]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
