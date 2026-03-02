from __future__ import annotations

import json
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

    def test_serve_mode_starts_http_server(self) -> None:
        events: list[str] = []

        class FakeServer:
            def __init__(self, addr, _handler):  # type: ignore[no-untyped-def]
                self.server_address = ("127.0.0.1", 8765 if int(addr[1]) == 0 else int(addr[1]))
                events.append("init")

            def serve_forever(self):  # type: ignore[no-untyped-def]
                events.append("serve_forever")
                raise KeyboardInterrupt

            def server_close(self):  # type: ignore[no-untyped-def]
                events.append("server_close")

        with tempfile.TemporaryDirectory() as td:
            outp = Path(td) / "serve.html"
            with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
                "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
            ), patch("scalpel.cli.ThreadingHTTPServer", FakeServer):
                cli.main(["--serve", "--no-open", "--start", "2026-01-01", "--port", "0", "--out", str(outp)])

            self.assertTrue(outp.exists())
            self.assertEqual(events, ["init", "serve_forever", "server_close"])

    def test_timew_export_day_parses_and_clamps_intervals(self) -> None:
        payload = [
            {"start": "2025-12-31T23:30:00Z", "end": "2026-01-01T00:10:00Z", "tags": ["commute"]},
            {"start": "2026-01-01T10:00:00Z", "end": "2026-01-01T11:30:00Z", "annotation": "Deep work"},
            {"start": "2026-01-01T23:50:00Z", "end": "2026-01-02T00:30:00Z", "tags": ["wrap"]},
        ]

        class Proc:
            returncode = 0
            stdout = json.dumps(payload).encode("utf-8")
            stderr = b""

        seen_cmd: list[str] = []

        def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
            seen_cmd[:] = list(cmd)
            return Proc()

        with patch("scalpel.cli.subprocess.run", side_effect=fake_run):
            out = cli._run_timew_export_for_day(day_ymd="2026-01-01", tz_name="UTC")

        self.assertEqual(seen_cmd, ["timew", "2026-01-01", "export"])
        self.assertEqual(out["day"], "2026-01-01")
        self.assertEqual(len(out["intervals"]), 3)

        first = out["intervals"][0]
        second = out["intervals"][1]
        third = out["intervals"][2]

        self.assertEqual(first["start_ms"], 1767225600000)  # 2026-01-01T00:00:00Z (clamped)
        self.assertEqual(first["end_ms"], 1767226200000)
        self.assertEqual(first["tags"], ["commute"])

        self.assertEqual(second["start_ms"], 1767261600000)
        self.assertEqual(second["end_ms"], 1767267000000)
        self.assertEqual(second["annotation"], "Deep work")

        self.assertEqual(third["start_ms"], 1767311400000)
        self.assertEqual(third["end_ms"], 1767312000000)  # 2026-01-02T00:00:00Z (clamped)


if __name__ == "__main__":
    unittest.main(verbosity=2)
