from __future__ import annotations

import argparse
import json
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from scalpel import serve


def _request_json(opener: Any, url: str, *, method: str = "GET", body: object | None = None, headers: dict[str, str] | None = None):
    payload = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=payload, method=method, headers=req_headers)
    return opener.open(req, timeout=5)


@dataclass
class _ServeHarness:
    root: Path
    token: str | None = None
    out_file: Path = field(init=False)
    payload_count: int = field(default=0, init=False)
    holder: dict[str, ThreadingHTTPServer] = field(default_factory=dict, init=False)
    thread: threading.Thread | None = field(default=None, init=False)
    server_error: BaseException | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.out_file = self.root / "serve.html"
        self.out_file.write_text("<!doctype html><html><head></head><body>initial</body></html>", encoding="utf-8")

    def _args(self) -> argparse.Namespace:
        return argparse.Namespace(
            host="127.0.0.1",
            port=0,
            serve_token=self.token or "",
            allow_remote=False,
            no_open=True,
        )

    def _render_once(self, _args: argparse.Namespace, out_path: str):
        self.payload_count += 1
        payload = {
            "cfg": {"view_key": "serve-e2e", "view_start_ms": 0, "days": 7},
            "tasks": [],
            "meta": {"generated_at": f"gen-{self.payload_count}"},
        }
        Path(out_path).write_text(
            f"<!doctype html><html><head></head><body>refresh-{self.payload_count}</body></html>",
            encoding="utf-8",
        )
        return payload

    def _task_lookup(self, uuid_query: str):
        return {
            "task": {"uuid": "12345678-1111-2222-3333-abcdefabcdef", "description": f"Task {uuid_query}"},
            "matched": 1,
            "exact": True,
        }

    def _timew_export(self, day: str):
        return {
            "day": day,
            "intervals": [
                {
                    "start_ms": 1767225600000,
                    "end_ms": 1767229200000,
                    "tags": ["focus"],
                    "annotation": "Deep work",
                }
            ],
        }

    def _server_factory(self, addr: tuple[str, int], handler: type):
        server = ThreadingHTTPServer(addr, handler)
        self.holder["server"] = server
        return server

    def start(self) -> "_ServeHarness":
        initial_payload = {
            "cfg": {"view_key": "serve-e2e", "view_start_ms": 0, "days": 7},
            "tasks": [],
            "meta": {"generated_at": "gen-0"},
        }

        def runner() -> None:
            try:
                serve.serve(
                    self._args(),
                    str(self.out_file),
                    initial_payload,
                    render_once=self._render_once,
                    task_lookup=self._task_lookup,
                    timew_export=self._timew_export,
                    server_factory=self._server_factory,
                    browser_open=None,
                )
            except BaseException as ex:
                self.server_error = ex

        self.thread = threading.Thread(target=runner, daemon=True)
        self.thread.start()
        deadline = time.time() + 5.0
        while "server" not in self.holder:
            if self.server_error is not None:
                if isinstance(self.server_error, PermissionError):
                    raise unittest.SkipTest("local HTTP bind not permitted in this environment")
                raise RuntimeError(f"serve thread failed to start: {self.server_error}")
            if time.time() >= deadline:
                raise RuntimeError("serve thread did not start in time")
            time.sleep(0.01)
        return self

    def stop(self) -> None:
        server = self.holder.get("server")
        if server is not None:
            server.shutdown()
        if self.thread is not None:
            self.thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        server = self.holder["server"]
        host, port = server.server_address[:2]
        return f"http://{host}:{int(port)}"


class TestServeEndToEndContract(unittest.TestCase):
    def test_live_endpoints_auth_refresh_and_persisted_client_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))

            harness = _ServeHarness(root, token="abc123").start()
            try:
                with self.assertRaises(HTTPError) as ctx:
                    _request_json(opener, harness.base_url + "/payload")
                self.assertEqual(ctx.exception.code, 401)

                with opener.open(harness.base_url + "/?token=abc123", timeout=5) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                    self.assertEqual(resp.status, 200)
                    self.assertIn("Set-Cookie", str(resp.headers))
                    self.assertIn("__scalpel_kvGet", html)
                    self.assertIn("/client-state", html)
                    self.assertIn("navigator.sendBeacon", html)
                    self.assertIn("pagehide", html)

                with _request_json(opener, harness.base_url + "/payload") as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(payload["meta"]["generated_at"], "gen-0")

                with _request_json(opener, harness.base_url + "/task?uuid=12345678") as resp:
                    task_body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(task_body["ok"])
                self.assertEqual(task_body["task"]["description"], "Task 12345678")

                with _request_json(opener, harness.base_url + "/timew?day=2026-01-01") as resp:
                    timew_body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(timew_body["ok"])
                self.assertEqual(timew_body["intervals"][0]["annotation"], "Deep work")

                with _request_json(
                    opener,
                    harness.base_url + "/client-state",
                    method="POST",
                    body={"values": {"scalpel.viewwin.global": {"startYmd": "2026-03-10", "futureDays": 9}}},
                ) as resp:
                    state_body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(state_body["ok"])
                self.assertEqual(state_body["state"]["scalpel.viewwin.global"]["futureDays"], 9)

                with _request_json(opener, harness.base_url + "/refresh", method="POST", body={}) as resp:
                    refresh_body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(refresh_body["ok"])
                self.assertEqual(refresh_body["generated_at"], "gen-1")

                with _request_json(opener, harness.base_url + "/payload") as resp:
                    payload_after = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(payload_after["meta"]["generated_at"], "gen-1")

                with opener.open(harness.base_url + "/", timeout=5) as resp:
                    refreshed_html = resp.read().decode("utf-8", errors="replace")
                self.assertIn("refresh-1", refreshed_html)
                self.assertIn('"futureDays":9', refreshed_html)

                with _request_json(opener, harness.base_url + "/metrics") as resp:
                    metrics_body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(metrics_body["ok"])
                self.assertGreaterEqual(metrics_body["metrics"].get("requests_total", 0), 1)
            finally:
                harness.stop()

            # Serve-backed state survives restarts from the sidecar store.
            harness2 = _ServeHarness(root, token="abc123").start()
            try:
                opener2 = build_opener(HTTPCookieProcessor(CookieJar()))
                with opener2.open(harness2.base_url + "/?token=abc123", timeout=5) as resp:
                    html2 = resp.read().decode("utf-8", errors="replace")
                self.assertIn('"futureDays":9', html2)

                with _request_json(opener2, harness2.base_url + "/client-state") as resp:
                    state_again = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(state_again["state"]["scalpel.viewwin.global"]["futureDays"], 9)
            finally:
                harness2.stop()

    def test_apply_endpoint_executes_selected_commands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))
            harness = _ServeHarness(root, token="abc123").start()
            try:
                with opener.open(harness.base_url + "/?token=abc123", timeout=5):
                    pass

                def fake_apply(commands: list[object], *, selected: list[object] | None = None) -> dict[str, Any]:
                    self.assertEqual(commands, ["task 12345678 done", "task 12345678 delete"])
                    self.assertEqual(selected, [1])
                    return {
                        "ok": True,
                        "applied": 1,
                        "selected": 1,
                        "stopped_after_index": None,
                        "commands": [
                            {
                                "index": 1,
                                "kind": "delete",
                                "line": "task 12345678 delete",
                                "argv": ["task", "12345678", "delete"],
                                "ok": True,
                                "returncode": 0,
                                "stdout": "",
                                "stderr": "",
                                "error": None,
                            }
                        ],
                    }

                with patch("scalpel.serve.execute_apply_commands", side_effect=fake_apply):
                    with _request_json(
                        opener,
                        harness.base_url + "/apply",
                        method="POST",
                        body={
                            "commands": ["task 12345678 done", "task 12345678 delete"],
                            "selected": [1],
                            "confirm": True,
                        },
                    ) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(body["ok"])
                self.assertEqual(body["applied"], 1)
                self.assertEqual(body["commands"][0]["kind"], "delete")
            finally:
                harness.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
