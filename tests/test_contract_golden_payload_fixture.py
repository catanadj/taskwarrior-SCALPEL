from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / 'tests/fixtures/golden_payload_v1.json'

class TestGoldenPayloadFixtureContract(unittest.TestCase):
    def test_fixture_exists(self) -> None:
        self.assertTrue(FIXTURE.exists(), f"missing fixture: {FIXTURE}")

    def test_fixture_is_up_to_date(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, "-m", "scalpel.tools.gen_fixtures", "--check"]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        self.assertEqual(p.returncode, 0, combined)

    def test_fixture_validates_and_renders(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        # Validate
        cmd_v = [sys.executable, "-m", "scalpel.tools.validate_payload", "--in", str(FIXTURE)]
        subprocess.run(cmd_v, cwd=str(REPO_ROOT), env=env, check=True)

        # Render (record/replay)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out_html = td / "replay.html"
            cmd_r = [
                sys.executable,
                "-m",
                "scalpel.tools.render_payload",
                "--in",
                str(FIXTURE),
                "--out",
                str(out_html),
                "--strict",
            ]
            subprocess.run(cmd_r, cwd=str(REPO_ROOT), env=env, check=True)
            txt = out_html.read_text(encoding="utf-8")
            self.assertIn("SMOKE: Planned task", txt)

if __name__ == "__main__":
    unittest.main(verbosity=2)
