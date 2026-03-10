from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel import cli


class TestCliDefaultOutContract(unittest.TestCase):
    def test_obs_log_emits_structured_line_when_enabled(self) -> None:
        with patch.dict(os.environ, {"SCALPEL_OBS_LOG": "1"}, clear=False), patch("scalpel.cli.eprint") as ep:
            cli._obs_log("serve.auth_denied", path="/payload", method="GET", client="127.0.0.1")
        self.assertTrue(ep.called)
        line = str(ep.call_args.args[0]) if ep.call_args and ep.call_args.args else ""
        self.assertTrue(line.startswith("[scalpel.serve.obs] "))
        blob = line.split(" ", 1)[1]
        obj = json.loads(blob)
        self.assertEqual(obj.get("event"), "serve.auth_denied")
        self.assertEqual(obj.get("path"), "/payload")
        self.assertIn("ts", obj)

    def test_obs_log_is_silent_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch("scalpel.cli.eprint") as ep:
            cli._obs_log("serve.auth_denied", path="/payload")
        self.assertFalse(ep.called)

    def test_counter_helpers_track_total_and_by_path(self) -> None:
        counters = {}
        cli._counter_inc(counters, "auth_failures_total", path="/payload")
        cli._counter_inc(counters, "auth_failures_total", path="/payload")
        cli._counter_inc(counters, "auth_failures_total", path="/refresh")
        snap = cli._counter_snapshot(counters)
        self.assertEqual(snap.get("auth_failures_total"), 3)
        by_path = snap.get("auth_failures_total_by_path")
        self.assertIsInstance(by_path, dict)
        self.assertEqual(by_path.get("/payload"), 2)
        self.assertEqual(by_path.get("/refresh"), 1)

    def test_default_out_is_build_relative_to_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
                    "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
                ):
                    cli.main(["--once", "--no-open", "--start", "2026-01-01"])
            finally:
                os.chdir(old_cwd)

            self.assertTrue((tmp / "build" / "scalpel_schedule.html").exists())

    def test_invalid_tz_reports_user_error(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["--once", "--no-open", "--tz", "No/Such_Zone"])
        self.assertIn("Invalid --tz value", str(ctx.exception))

    def test_nautical_hooks_enabled_by_default(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}) as bp, patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            cli.main(["--once", "--no-open", "--start", "2026-01-01"])
        self.assertTrue(bp.call_args.kwargs.get("nautical_hooks_enabled"))

    def test_no_nautical_hooks_flag_disables_preview_expansion(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}) as bp, patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            cli.main(["--once", "--no-open", "--start", "2026-01-01", "--no-nautical-hooks"])
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
                cli.main(["--once", "--no-open", "--start", "2026-01-01"])

            self.assertTrue((home / ".scalpel" / "build" / "scalpel_schedule.html").exists())

    def test_live_mode_is_default(self) -> None:
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
                cli.main(["--no-open", "--start", "2026-01-01", "--port", "0", "--out", str(outp)])

            self.assertTrue(outp.exists())
            self.assertEqual(events, ["init", "serve_forever", "server_close"])

    def test_once_flag_renders_without_starting_http_server(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            outp = Path(td) / "once.html"
            with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
                "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
            ), patch("scalpel.cli.ThreadingHTTPServer", side_effect=AssertionError("server should not start")):
                cli.main(["--once", "--no-open", "--start", "2026-01-01", "--out", str(outp)])

            self.assertTrue(outp.exists())

    def test_serve_remote_host_requires_allow_remote_flag(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["--serve", "--no-open", "--start", "2026-01-01", "--host", "0.0.0.0"])
        self.assertIn("without --allow-remote", str(ctx.exception))

    def test_serve_remote_host_requires_token(self) -> None:
        with patch("scalpel.cli.build_payload", return_value={"cfg": {}, "tasks": []}), patch(
            "scalpel.cli.build_html", return_value="<!doctype html><html><body>ok</body></html>"
        ):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(
                    [
                        "--serve",
                        "--no-open",
                        "--start",
                        "2026-01-01",
                        "--host",
                        "0.0.0.0",
                        "--allow-remote",
                    ]
                )
        self.assertIn("requires --serve-token", str(ctx.exception))

    def test_serve_remote_with_token_and_allow_remote_starts_server(self) -> None:
        events: list[str] = []

        class FakeServer:
            def __init__(self, addr, _handler):  # type: ignore[no-untyped-def]
                self.server_address = ("0.0.0.0", 8765 if int(addr[1]) == 0 else int(addr[1]))
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
                cli.main(
                    [
                        "--serve",
                        "--no-open",
                        "--start",
                        "2026-01-01",
                        "--port",
                        "0",
                        "--host",
                        "0.0.0.0",
                        "--allow-remote",
                        "--serve-token",
                        "abc123",
                        "--out",
                        str(outp),
                    ]
                )

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

    def test_task_export_uuid_query_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            cli._run_task_export_for_uuid("not-a-valid-uuid query")

    def test_task_export_uuid_query_not_found(self) -> None:
        with patch("scalpel.cli.run_task_export", return_value=[]):
            out = cli._run_task_export_for_uuid("1234abcd")
        self.assertEqual(out, {"task": None, "matched": 0, "exact": False})

    def test_task_export_uuid_query_prefers_exact_match(self) -> None:
        t1 = {"uuid": "aaaaaaaa-1111-1111-1111-111111111111", "description": "A"}
        t2 = {"uuid": "aaaaaaaa-2222-2222-2222-222222222222", "description": "B"}
        with patch("scalpel.cli.run_task_export", return_value=[t1, t2]):
            out = cli._run_task_export_for_uuid("aaaaaaaa-2222-2222-2222-222222222222")
        self.assertIs(out["task"], t2)
        self.assertEqual(out["matched"], 2)
        self.assertTrue(out["exact"])

    def test_task_export_uuid_query_ambiguous_prefix_fails(self) -> None:
        t1 = {"uuid": "aaaaaaaa-1111-1111-1111-111111111111", "description": "A"}
        t2 = {"uuid": "aaaaaaaa-2222-2222-2222-222222222222", "description": "B"}
        with patch("scalpel.cli.run_task_export", return_value=[t1, t2]):
            with self.assertRaises(SystemExit):
                cli._run_task_export_for_uuid("aaaaaaaa")


if __name__ == "__main__":
    unittest.main(verbosity=2)
