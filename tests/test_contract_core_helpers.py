from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scalpel import payload, serve


class PayloadHelperContractTests(unittest.TestCase):
    def test_nautical_hook_policy_and_detection(self) -> None:
        self.assertTrue(payload._nautical_hooks_enabled(True))
        self.assertFalse(payload._nautical_hooks_enabled(False))
        for raw, expected in (("0", False), ("off", False), ("yes", True), ("unexpected", True)):
            with self.subTest(raw=raw), patch.dict("os.environ", {"SCALPEL_ENABLE_NAUTICAL_HOOKS": raw}):
                self.assertEqual(payload._nautical_hooks_enabled(), expected)
        self.assertTrue(payload._raw_tasks_may_need_nautical([{"anchor": " daily "}]))
        self.assertFalse(payload._raw_tasks_may_need_nautical([{}, {"anchor": " "}]))

    def test_time_helpers_handle_valid_and_invalid_values(self) -> None:
        self.assertEqual(payload._parse_hhmm_str("09:30"), (9, 30))
        self.assertIsNone(payload._parse_hhmm_str("24:00"))
        self.assertIsNone(payload._parse_hhmm_str("bad"))
        self.assertEqual(payload._local_hhmm_from_ms(0, dt.timezone.utc), (0, 0))
        self.assertIsNone(payload._local_hhmm_from_ms(None, dt.timezone.utc))

        hour = dt.timedelta(hours=1)
        self.assertEqual(
            payload._cp_next_due_ms(base_end_ms=0, base_due_ms=None, td=hour, tzinfo=dt.timezone.utc),
            3_600_000,
        )
        self.assertIsNone(payload._cp_next_due_ms(base_end_ms=None, base_due_ms=None, td=hour, tzinfo=dt.timezone.utc))


class ServeHelperContractTests(unittest.TestCase):
    def test_url_host_and_query_helpers(self) -> None:
        self.assertEqual(serve._format_http_url("0.0.0.0", 8080, "status"), "http://127.0.0.1:8080/status")
        self.assertEqual(serve._format_http_url("::1", 8080), "http://[::1]:8080/")
        self.assertTrue(serve._is_loopback_host("[::1]"))
        self.assertFalse(serve._is_loopback_host("example.com"))
        self.assertEqual(serve._first_query_value("/task?uuid=abc%20123", "uuid"), "abc 123")

    def test_payload_timestamp_and_script_injection_fallbacks(self) -> None:
        self.assertEqual(serve._payload_generated_at({"generated_at": "now"}), "now")
        self.assertEqual(serve._payload_generated_at({"meta": {"generated_at": "then"}}), "then")
        self.assertIsNone(serve._payload_generated_at({}))
        escaped = serve._escape_script_json({"value": "</script>"})
        self.assertNotIn("</script>", escaped)
        self.assertIn("__scalpel_serverKvStore", serve._inject_serve_bootstrap("<body></body>", {}))
        self.assertTrue(serve._inject_serve_bootstrap("plain", {}).endswith("plain"))

    def test_client_state_round_trip_and_invalid_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "nested" / "state.json"
            self.assertEqual(serve._read_client_state(state_path), {})
            serve._write_client_state(state_path, {"b": 2, "a": 1})
            self.assertEqual(serve._read_client_state(state_path), {"a": 1, "b": 2})
            self.assertTrue(state_path.read_text(encoding="utf-8").endswith("\n"))
            state_path.write_text(json.dumps([]), encoding="utf-8")
            self.assertEqual(serve._read_client_state(state_path), {})
            state_path.write_text("{", encoding="utf-8")
            self.assertEqual(serve._read_client_state(state_path), {})

    def test_counter_helpers_normalize_values(self) -> None:
        counters: dict[str, object] = {"requests": "2", "bad": object(), "paths": {"/ok": "3", "/bad": object()}}
        serve._counter_inc(counters, "requests", path="")
        serve._counter_inc(counters, "", path="ignored")
        self.assertEqual(counters["requests"], 3)
        snapshot = serve._counter_snapshot(counters)
        self.assertEqual(snapshot["requests"], 3)
        self.assertEqual(snapshot["requests_by_path"], {"/": 1})
        self.assertEqual(snapshot["paths"], {"/ok": 3, "/bad": 0})
        self.assertNotIn("bad", snapshot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
