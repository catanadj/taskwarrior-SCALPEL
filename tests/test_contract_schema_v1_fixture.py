import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "payload_v1_min.json"

def _py() -> str:
    return os.environ.get("PYTHON", "python3")

class TestSchemaV1FixtureContract(unittest.TestCase):
    def test_fixture_validates_with_validate_payload_tool(self) -> None:
        self.assertTrue(FIXTURE.exists(), f"missing fixture: {FIXTURE}")
        cmd = [_py(), "-m", "scalpel.tools.validate_payload", "--in", str(FIXTURE)]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
