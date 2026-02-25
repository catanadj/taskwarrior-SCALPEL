from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests/fixtures/golden_payload_v2.json"


def _canon(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)


class TestRenderReplayV2RoundTripContract(unittest.TestCase):
    def test_render_replay_html_round_trips_payload(self) -> None:
        self.assertTrue(FIXTURE.exists(), f"Missing fixture: {FIXTURE}")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            replay = td / "replay.html"

            # Render v2 payload -> replay HTML
            cmd_r = [
                sys.executable,
                "-m",
                "scalpel.tools.render_payload",
                "--in",
                str(FIXTURE),
                "--out",
                str(replay),
            ]
            p_r = subprocess.run(cmd_r, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
            combined_r = (p_r.stdout or "") + "\n" + (p_r.stderr or "")
            self.assertEqual(p_r.returncode, 0, combined_r)
            self.assertTrue(replay.exists(), "render_payload did not create replay.html")

            # Validate HTML extraction path (tool contract)
            cmd_v = [
                sys.executable,
                "-m",
                "scalpel.tools.validate_payload",
                "--from-html",
                str(replay),
            ]
            p_v = subprocess.run(cmd_v, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
            combined_v = (p_v.stdout or "") + "\n" + (p_v.stderr or "")
            self.assertEqual(p_v.returncode, 0, combined_v)

            # Library-level round trip equality (after normalization)
            # This ensures embed/extract stays stable across refactors.
            sys.path.insert(0, str(REPO_ROOT))
            from scalpel import load_payload_from_json, normalize_payload  # type: ignore
            from scalpel.html_extract import extract_payload_json_from_html_file  # type: ignore

            p0 = load_payload_from_json(FIXTURE)
            p1 = extract_payload_json_from_html_file(replay)

            n0 = normalize_payload(p0)
            n1 = normalize_payload(p1)

            self.assertEqual(_canon(n1), _canon(n0))
