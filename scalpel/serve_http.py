from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, cast
from urllib.parse import urlsplit

from .serve_endpoints import (
    handle_apply_post,
    handle_client_state_get,
    handle_client_state_post,
    handle_refresh_endpoint,
    handle_task_endpoint,
    handle_timew_endpoint,
)
from .serve_support import client_state_snapshot, first_query_value, obs_log
from .serve_types import ExecuteApplyFn, RenderOnceFn, ServeConfig, ServeState, TaskLookupFn, TimewExportFn


@dataclass(frozen=True)
class HttpContext:
    args: argparse.Namespace
    out_path: str
    config: ServeConfig
    state: ServeState
    state_lock: threading.Lock
    state_file: Path
    render_once: RenderOnceFn
    task_lookup: TaskLookupFn
    timew_export: TimewExportFn
    execute_apply: ExecuteApplyFn
    inject_bootstrap: Callable[[str, dict[str, Any]], str]
    obs_inc: Callable[..., None]
    obs_metrics: Callable[[], dict[str, Any]]


def make_handler(context: HttpContext) -> type[BaseHTTPRequestHandler]:
    """Build the request handler class bound to one server instance."""
    config = context.config

    class Handler(BaseHTTPRequestHandler):
        def _query_token(self) -> str:
            return str(first_query_value(self.path, "token"))

        def _header_token(self) -> str:
            token = str(self.headers.get("X-Scalpel-Token") or "").strip()
            if token:
                return token
            authorization = str(self.headers.get("Authorization") or "").strip()
            if authorization.lower().startswith("bearer "):
                return authorization[7:].strip()
            return ""

        def _cookie_token(self) -> str:
            raw = str(self.headers.get("Cookie") or "")
            if not raw:
                return ""
            for part in raw.split(";"):
                key, _, value = part.strip().partition("=")
                if key.strip() == "scalpel_token":
                    return value.strip()
            return ""

        def _is_authorized(self) -> bool:
            if config.required_token is None:
                return True
            return any(
                token and token == config.required_token
                for token in (self._query_token(), self._header_token(), self._cookie_token())
            )

        def _deny_unauthorized(self, path: str) -> None:
            context.obs_inc("auth_failures_total", path=path)
            obs_log(
                "serve.auth_denied",
                path=path,
                method=self.command,
                client=(self.client_address[0] if self.client_address else ""),
            )
            self._send_json(401, {"ok": False, "error": "Unauthorized"})

        def _send_json(self, code: int, payload: dict[str, Any], *, set_auth_cookie: bool = False) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            if set_auth_cookie and config.required_token is not None:
                self.send_header(
                    "Set-Cookie",
                    f"scalpel_token={config.required_token}; Path=/; HttpOnly; SameSite=Lax",
                )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, code: int, html_text: str, *, set_auth_cookie: bool = False) -> None:
            body = html_text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            if set_auth_cookie and config.required_token is not None:
                self.send_header(
                    "Set-Cookie",
                    f"scalpel_token={config.required_token}; Path=/; HttpOnly; SameSite=Lax",
                )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            message = fmt % args
            message = re.sub(r"(token=)[^&\s]+", r"\1REDACTED", message, flags=re.IGNORECASE)
            print(f"[scalpel-serve] {self.address_string()} - {message}", file=sys.stderr)

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            context.obs_inc("requests_total", path=path)
            context.obs_inc("requests_get_total")
            if path in {"/", config.route_file}:
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                try:
                    with context.state_lock:
                        html = config.out_file.read_text(encoding="utf-8")
                        client_state = client_state_snapshot(context.state)
                except (OSError, UnicodeError) as ex:
                    self._send_json(500, {"ok": False, "error": f"Failed reading HTML: {ex}"})
                    return
                html = context.inject_bootstrap(html, client_state)
                set_cookie = config.required_token is not None and self._query_token() == config.required_token
                self._send_html(200, html, set_auth_cookie=set_cookie)
                return

            if path == "/payload":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                with context.state_lock:
                    payload = context.state.payload
                context.obs_inc("payload_reads_total")
                self._send_json(200, cast(dict[str, Any], payload))
                return

            if path == "/client-state":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                handle_client_state_get(
                    state=context.state,
                    state_lock=context.state_lock,
                    send_json=self._send_json,
                )
                return

            if path == "/task":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                handle_task_endpoint(
                    first_query_value(self.path, "uuid"),
                    task_lookup=context.task_lookup,
                    send_json=self._send_json,
                    obs_inc=context.obs_inc,
                )
                return

            if path == "/timew":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                handle_timew_endpoint(
                    first_query_value(self.path, "day"),
                    timew_export=context.timew_export,
                    send_json=self._send_json,
                    obs_inc=context.obs_inc,
                )
                return

            if path == "/metrics":
                if config.required_token is not None and not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                self._send_json(200, {"ok": True, "metrics": context.obs_metrics()})
                return

            if path == "/health":
                include_metrics = first_query_value(self.path, "metrics").lower() in {"1", "true", "yes", "on"}
                response: dict[str, Any] = {"ok": True}
                if include_metrics:
                    response.update(
                        auth_required=config.required_token is not None,
                        metrics=context.obs_metrics(),
                    )
                self._send_json(200, response)
                return

            self._send_json(404, {"ok": False, "error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            context.obs_inc("requests_total", path=path)
            context.obs_inc("requests_post_total")
            if path not in {"/refresh", "/client-state", "/apply"}:
                self._send_json(404, {"ok": False, "error": "Not found"})
                return
            if not self._is_authorized():
                self._deny_unauthorized(path)
                return
            if path == "/refresh":
                handle_refresh_endpoint(
                    args=context.args,
                    out_path=context.out_path,
                    route_file=config.route_file,
                    state=context.state,
                    state_lock=context.state_lock,
                    render_once=context.render_once,
                    send_json=self._send_json,
                    obs_inc=context.obs_inc,
                )
                return
            try:
                content_length = int(self.headers.get("Content-Length") or "0")
            except (TypeError, ValueError):
                content_length = 0
            try:
                raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
                body = json.loads(raw.decode("utf-8", errors="replace"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                self._send_json(400, {"ok": False, "error": "Invalid JSON body."})
                return
            if path == "/apply":
                handle_apply_post(
                    body=body,
                    execute_apply=context.execute_apply,
                    send_json=self._send_json,
                    obs_inc=context.obs_inc,
                )
                return
            handle_client_state_post(
                body=body,
                state=context.state,
                state_lock=context.state_lock,
                state_file=context.state_file,
                send_json=self._send_json,
            )

    return Handler


__all__ = ["HttpContext", "make_handler"]
