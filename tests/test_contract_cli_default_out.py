from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel import cli


class TestCliDefaultOutContract(unittest.TestCase):
    def test_default_out_is_build_relative_to_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
                    "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
                ):
                    cli.main(["--no-open", "--start", "2026-01-01"])
            finally:
                os.chdir(old_cwd)

            self.assertTrue((tmp / "build" / "scalpel_schedule.html").exists())

    def test_invalid_tz_reports_user_error(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["--no-open", "--tz", "No/Such_Zone"])
        self.assertIn("Invalid --tz value", str(ctx.exception))

    def test_nautical_hooks_enabled_by_default(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}) as bp, patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            cli.main(["--no-open", "--start", "2026-01-01"])
        self.assertTrue(bp.call_args.kwargs.get("nautical_hooks_enabled"))

    def test_no_nautical_hooks_flag_disables_preview_expansion(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}) as bp, patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            cli.main(["--no-open", "--start", "2026-01-01", "--no-nautical-hooks"])
        self.assertFalse(bp.call_args.kwargs.get("nautical_hooks_enabled"))

    def test_default_out_falls_back_when_unwritable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            home.mkdir(parents=True, exist_ok=True)

            blocked_dir = Path("/home/build")
            blocked_out = str(blocked_dir / "scalpel_schedule.html")

            orig_mkdir = Path.mkdir

            def fake_mkdir(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                if self == blocked_dir:
                    raise PermissionError(13, "Permission denied", str(self))
                return orig_mkdir(self, *args, **kwargs)

            with patch.dict(os.environ, {"HOME": str(home)}), patch(
                "scalpel.cli.os.path.abspath", return_value=blocked_out
            ), patch("pathlib.Path.mkdir", new=fake_mkdir), patch(
                "scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}
            ), patch("scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"):
                cli.main(["--no-open", "--start", "2026-01-01"])

            self.assertTrue((home / ".scalpel" / "build" / "scalpel_schedule.html").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
