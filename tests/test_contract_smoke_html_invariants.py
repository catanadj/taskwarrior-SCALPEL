import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scalpel.schema import LATEST_SCHEMA_VERSION
REPO_ROOT = Path(__file__).resolve().parents[1]

class TestSmokeHtmlInvariantsContract(unittest.TestCase):
    def _build_smoke_strict(self, out_path: Path) -> None:
        env = os.environ.copy()
        # Ensure module import works when running from repo checkout
        env["PYTHONPATH"] = str(REPO_ROOT)

        cmd = [
            sys.executable,
            "-m",
            "scalpel.tools.smoke_build",
            "--out",
            str(out_path),
            "--strict",
        ]
        subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=True)

    def test_smoke_html_has_golden_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "smoke.html"
            self._build_smoke_strict(out)

            self.assertTrue(out.exists(), f"missing output: {out}")
            html = out.read_text(encoding="utf-8", errors="replace")
            self.assertGreater(len(html), 5000)

            # Shell invariants
            self.assertIn("<!doctype html>", html.lower())
            self.assertIn("<title>Taskwarrior Calendar</title>", html)
            self.assertIn('meta charset="utf-8"', html.lower())

            # No template markers
            for marker in ("__DATA_JSON__", "__CSS_BLOCK__", "__JS_BLOCK__", "__BODY_MARKUP__"):
                self.assertNotIn(marker, html)

            # Required IDs appear exactly once (public-ish UI contract)
            required_ids = [
                "tw-data",
                "meta",
                "selMeta",
                "pendingMeta",
                "zoom",
                "zoomVal",
                "viewwin",
                "vwToday",
                "btnCopy",
                "btnCommand",
                "btnHelp",
                "calendar",
                "backlog",
                "commands",
                "cmdGuide",
                "toast",
                "helpModal",
                "commandModal",
                "commandQ",
                "addModal",
                "addLines",
            ]
            for id_ in required_ids:
                n = html.count(f'id="{id_}"')
                self.assertEqual(n, 1, f"expected id={id_!r} once, found {n}")

            # Extract and validate embedded JSON payload
            m = re.search(
                r'<script\s+id="tw-data"\s+type="application/json">\s*(.*?)\s*</script>',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            self.assertIsNotNone(m, "missing tw-data JSON script block")
            payload = json.loads(m.group(1).strip())

            self.assertIsInstance(payload, dict)
            for k in ("cfg", "tasks", "meta"):
                self.assertIn(k, payload)


            # Schema v1 contract
            self.assertIn("schema_version", payload)
            self.assertEqual(payload["schema_version"], LATEST_SCHEMA_VERSION)
            
            self.assertIn("generated_at", payload)

            self.assertIn("indices", payload)
            indices = payload["indices"]
            self.assertIsInstance(indices, dict)
            for ik in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
                self.assertIn(ik, indices)

            by_uuid = indices["by_uuid"]
            self.assertIsInstance(by_uuid, dict)
            self.assertGreaterEqual(len(by_uuid), 1)

            # Normalized tasks
            for t in payload["tasks"]:
                self.assertIsInstance(t, dict)
                self.assertIn("uuid", t)
                self.assertTrue(t["uuid"])
                self.assertIn("description", t)
                self.assertIn("status", t)
                self.assertIn("tags", t)
                self.assertIsInstance(t["tags"], list)
            tasks = payload["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertGreaterEqual(len(tasks), 2)
            self.assertTrue(any("SMOKE: Planned task" in (t.get("description", "") if isinstance(t, dict) else "") for t in tasks))

if __name__ == "__main__":
    unittest.main(verbosity=2)
