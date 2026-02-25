from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestRenderPayloadToolContract(unittest.TestCase):
    def test_render_payload_from_smoke_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            smoke_html = td / "smoke.html"
            payload_json = td / "payload.json"
            replay_html = td / "replay.html"

            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT)

            # Build schema payload JSON via smoke_build (no Taskwarrior).
            cmd1 = [
                sys.executable,
                "-m",
                "scalpel.tools.smoke_build",
                "--out",
                str(smoke_html),
                "--strict",
                "--out-json",
                str(payload_json),
            ]
            subprocess.run(cmd1, cwd=str(REPO_ROOT), env=env, check=True)

            self.assertTrue(payload_json.exists(), "smoke_build did not produce --out-json payload")

            # Render from JSON (record/replay path).
            cmd2 = [
                sys.executable,
                "-m",
                "scalpel.tools.render_payload",
                "--in",
                str(payload_json),
                "--out",
                str(replay_html),
                "--strict",
            ]
            subprocess.run(cmd2, cwd=str(REPO_ROOT), env=env, check=True)

            txt = replay_html.read_text(encoding="utf-8")
            self.assertIn("SMOKE: Planned task", txt)
            self.assertNotIn("__DATA_JSON__", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
