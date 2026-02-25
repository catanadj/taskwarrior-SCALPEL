# tests/test_contract_check_preflight.py
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import scalpel.tools.check as check


class TestCheckPreflightContract(unittest.TestCase):
    def _tmp_out(self) -> str:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return os.path.join(td.name, "smoke.html")

    def test_default_runs_doctor_and_smoke_build_when_not_skipped(self) -> None:
        out = self._tmp_out()
        calls: list[tuple[str, list[str]]] = []

        def fake_call(mod: str, argv: list[str]) -> int:
            calls.append((mod, list(argv)))
            return 0

        with patch.object(check, "_call", side_effect=fake_call):
            rc = check.main(["--out", out, "--skip-validate"])
        self.assertEqual(rc, 0)

        # Contract: check preflight is doctor then smoke_build (validate is explicitly skipped here)
        self.assertEqual([c[0] for c in calls], ["doctor", "smoke_build"])
        self.assertEqual(calls[1][1], ["--out", out])

    def test_skip_flags_disable_doctor_and_smoke_build(self) -> None:
        out = self._tmp_out()
        calls: list[tuple[str, list[str]]] = []

        def fake_call(mod: str, argv: list[str]) -> int:
            calls.append((mod, list(argv)))
            return 0

        with patch.object(check, "_call", side_effect=fake_call):
            rc = check.main(
                ["--out", out, "--skip-validate", "--skip-doctor", "--skip-smoke"]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])

    def test_env_skip_flags_disable_doctor_and_smoke_build(self) -> None:
        out = self._tmp_out()
        calls: list[tuple[str, list[str]]] = []

        def fake_call(mod: str, argv: list[str]) -> int:
            calls.append((mod, list(argv)))
            return 0

        with patch.dict(os.environ, {"SCALPEL_SKIP_DOCTOR": "1", "SCALPEL_SKIP_SMOKE": "1"}, clear=False):
            with patch.object(check, "_call", side_effect=fake_call):
                rc = check.main(["--out", out, "--skip-validate"])
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])

    def test_skip_doctor_only_runs_smoke_build(self) -> None:
        out = self._tmp_out()
        calls: list[tuple[str, list[str]]] = []

        def fake_call(mod: str, argv: list[str]) -> int:
            calls.append((mod, list(argv)))
            return 0

        with patch.object(check, "_call", side_effect=fake_call):
            rc = check.main(["--out", out, "--skip-validate", "--skip-doctor"])
        self.assertEqual(rc, 0)
        self.assertEqual([c[0] for c in calls], ["smoke_build"])

    def test_skip_smoke_only_runs_doctor(self) -> None:
        out = self._tmp_out()
        calls: list[tuple[str, list[str]]] = []

        def fake_call(mod: str, argv: list[str]) -> int:
            calls.append((mod, list(argv)))
            return 0

        with patch.object(check, "_call", side_effect=fake_call):
            rc = check.main(["--out", out, "--skip-validate", "--skip-smoke"])
        self.assertEqual(rc, 0)
        self.assertEqual([c[0] for c in calls], ["doctor"])


class TestWrapperContract(unittest.TestCase):
    def test_check_strict_wrapper_passes_skip_flags_to_scalpel_check(self) -> None:
        # Static contract: strict wrapper must call scalpel_check.sh with --skip-doctor/--skip-smoke
        with open("scripts/scalpel_check_strict.sh", "r", encoding="utf-8", errors="replace") as f:
            s = f.read()

        self.assertIn("scalpel_check.sh", s)
        self.assertIn("--skip-doctor", s)
        self.assertIn("--skip-smoke", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)

