import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PY = os.environ.get("PYTHON", "python3")


class TestValidatePayloadToolContract(unittest.TestCase):
    def _run(self, cmd, **kwargs):
        return subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True, **kwargs)

    def test_validate_payload_accepts_html_and_json(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out_html = td / "smoke.html"
            out_json = td / "payload.json"

            cmd = [PY, "-m", "scalpel.tools.smoke_build", "--out", str(out_html), "--strict", "--out-json", str(out_json)]
            p = self._run(cmd)
            self.assertEqual(p.returncode, 0, f"stdout:\n{p.stdout}\nstderr:\n{p.stderr}")

            cmd2 = [PY, "-m", "scalpel.tools.validate_payload", "--from-html", str(out_html), "--in", str(out_json)]
            p2 = self._run(cmd2)
            combined = (p2.stdout or "") + "\n" + (p2.stderr or "")
            self.assertEqual(p2.returncode, 0, combined)
            self.assertIn("[scalpel-validate-payload] OK", combined)

    def test_validate_payload_fails_on_corrupt_json(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            bad = td / "bad.json"
            bad.write_text('{"schema_version":1,"generated_at":"x","cfg":{},"tasks":[],"indices":{}}\n', encoding="utf-8")

            cmd = [PY, "-m", "scalpel.tools.validate_payload", "--in", str(bad)]
            p = self._run(cmd)
            self.assertNotEqual(p.returncode, 0)
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertIn("indices missing key", combined)


class TestCILiteRunsValidatePayloadContract(unittest.TestCase):
    def _run(self, cmd, **kwargs):
        return subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, capture_output=True, **kwargs)

    def test_ci_lite_runs_validate_payload_step(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out_html = td / "ci_smoke.html"

            cmd = [
                str(REPO_ROOT / "scripts" / "scalpel_ci_lite.sh"),
                "--allow-dirty",
                "--no-doctor",
                "--no-check",
                "--clean-logs",
                "--out",
                str(out_html),
            ]
            p = self._run(cmd)
            combined = (p.stdout or "") + "\n" + (p.stderr or "")
            self.assertEqual(p.returncode, 0, combined)
            self.assertIn("=== validate(payload) ===", combined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
