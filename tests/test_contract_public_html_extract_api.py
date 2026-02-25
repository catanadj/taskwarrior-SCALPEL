import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from scalpel.schema import LATEST_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]

class TestPublicHtmlExtractApiContract(unittest.TestCase):
    def test_extract_payload_json_from_html_file(self):
        env = dict(os.environ)
        env["SCALPEL_SKIP_DOCTOR"] = "1"

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out = td / "smoke.html"

            cmd = [os.environ.get("PYTHON", "python3"), "-m", "scalpel.tools.smoke_build", "--out", str(out), "--strict"]
            subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=True)

            from scalpel.html_extract import extract_payload_json_from_html_file

            payload = extract_payload_json_from_html_file(out)
            self.assertIsInstance(payload, dict)
            self.assertEqual(payload.get("schema_version"), LATEST_SCHEMA_VERSION)
            self.assertIn("tasks", payload)
            self.assertIn("cfg", payload)
            self.assertIn("indices", payload)

if __name__ == "__main__":
    unittest.main(verbosity=2)
