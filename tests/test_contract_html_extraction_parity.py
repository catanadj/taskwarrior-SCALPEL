# Contract: HTML extraction parity (smoke HTML vs replay/render HTML)
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)


def _extract_embedded_json_from_html_text(html: str) -> dict:
    """
    Extract the first <script ... type="application/json">...</script> block
    and parse it as JSON.

    This enforces that both smoke HTML and replay HTML embed data the same way.
    """
    m = re.search(
        r'<script\b[^>]*type="application/json"[^>]*>\s*(.*?)\s*</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise AssertionError("No <script type='application/json'> block found.")

    raw = m.group(1).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Embedded JSON could not be parsed: {e}") from e

    if not isinstance(obj, dict):
        raise AssertionError("Embedded JSON must be a top-level object/dict.")
    return obj


class TestHtmlExtractionParityContract(unittest.TestCase):
    def test_smoke_and_replay_html_embed_identical_payload(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            smoke_html = td / "smoke.html"
            payload_json = td / "payload.json"
            replay_html = td / "replay.html"

            # 1) Generate smoke HTML + raw JSON (same run)
            cmd_smoke = [
                sys.executable, "-m", "scalpel.tools.smoke_build",
                "--out", str(smoke_html),
                "--out-json", str(payload_json),
                "--strict",
                "--start", "2020-01-01",
                "--days", "7",
            ]
            p = _run(cmd_smoke, cwd=REPO_ROOT, env=env)
            self.assertEqual(
                p.returncode, 0,
                f"smoke_build failed\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
            )

            # 2) Render replay HTML from the produced payload.json
            cmd_replay = [
                sys.executable, "-m", "scalpel.tools.render_payload",
                "--in", str(payload_json),
                "--out", str(replay_html),
                "--strict",
            ]
            p2 = _run(cmd_replay, cwd=REPO_ROOT, env=env)
            self.assertEqual(
                p2.returncode, 0,
                f"render_payload failed\nstdout:\n{p2.stdout}\nstderr:\n{p2.stderr}"
            )

            # 3) Validate tool must accept BOTH HTMLs + JSON
            # (If validate_payload internally compares, great; if not, we still compare ourselves below.)
            cmd_val_smoke = [
                sys.executable, "-m", "scalpel.tools.validate_payload",
                "--from-html", str(smoke_html),
                "--in", str(payload_json),
            ]
            pv1 = _run(cmd_val_smoke, cwd=REPO_ROOT, env=env)
            self.assertEqual(
                pv1.returncode, 0,
                f"validate_payload(smoke) failed\nstdout:\n{pv1.stdout}\nstderr:\n{pv1.stderr}"
            )

            cmd_val_replay = [
                sys.executable, "-m", "scalpel.tools.validate_payload",
                "--from-html", str(replay_html),
                "--in", str(payload_json),
            ]
            pv2 = _run(cmd_val_replay, cwd=REPO_ROOT, env=env)
            self.assertEqual(
                pv2.returncode, 0,
                f"validate_payload(replay) failed\nstdout:\n{pv2.stdout}\nstderr:\n{pv2.stderr}"
            )

            # 4) Parity: extracted payload from smoke HTML equals payload.json
            src = json.loads(payload_json.read_text(encoding="utf-8"))
            self.assertIsInstance(src, dict)

            smoke_obj = _extract_embedded_json_from_html_text(smoke_html.read_text(encoding="utf-8"))
            replay_obj = _extract_embedded_json_from_html_text(replay_html.read_text(encoding="utf-8"))
            from scalpel.schema import LATEST_SCHEMA_VERSION
            self.assertEqual(smoke_obj, src, "Smoke HTML embedded payload != payload.json from same run.")
            expected = upgrade_payload(src, target_version=LATEST_SCHEMA_VERSION)
            self.assertEqual(replay_obj, expected, "Replay HTML embedded payload != upgraded payload.json input.")
            self.assertEqual(replay_obj, smoke_obj, "Replay HTML embedded payload != Smoke HTML embedded payload.")

            # Small invariant: must remain schema v1 once produced.

            self.assertEqual(src.get("schema_version"), LATEST_SCHEMA_VERSION)
            self.assertEqual(smoke_obj.get("schema_version"), LATEST_SCHEMA_VERSION)
            self.assertEqual(replay_obj.get("schema_version"), LATEST_SCHEMA_VERSION)

if __name__ == "__main__":
    unittest.main(verbosity=2)
