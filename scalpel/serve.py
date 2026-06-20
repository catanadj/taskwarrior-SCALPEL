from __future__ import annotations

import argparse
import threading
from http.server import ThreadingHTTPServer
from typing import Any, Collection
from urllib.parse import quote

from . import serve_support as _support
from .model import Payload
from .serve_apply import ApplyExecutionResult, execute_apply_commands
from .serve_bootstrap import _escape_script_json, _inject_serve_bootstrap, _serve_bootstrap_script
from .serve_endpoints import handle_apply_post as _handle_apply_post_impl
from .serve_http import HttpContext, make_handler
from .serve_types import (
    BrowserOpenFn,
    ObsIncFn,
    RenderOnceFn,
    SendJsonFn,
    ServeConfig,
    ServerFactoryFn,
    ServeState,
    TaskExportLookupResult,
    TaskLookupFn,
    TimewExportFn,
    TimewExportResult,
    TimewInterval,
)

_build_serve_config = _support.build_serve_config
_client_state_file = _support.client_state_file
_client_state_snapshot = _support.client_state_snapshot
_counter_inc = _support.counter_inc
_counter_snapshot = _support.counter_snapshot
_first_query_value = _support.first_query_value
_format_http_url = _support.format_http_url
_is_loopback_host = _support.is_loopback_host
_obs_enabled = _support.obs_enabled
_obs_line = _support.obs_line
_obs_log = _support.obs_log
_payload_generated_at = _support.payload_generated_at
_read_client_state = _support.read_client_state
_write_client_state = _support.write_client_state

__all__ = [
    "ServeConfig",
    "ServeState",
    "TaskExportLookupResult",
    "TimewExportResult",
    "TimewInterval",
    "_build_serve_config",
    "_client_state_file",
    "_client_state_snapshot",
    "_counter_inc",
    "_counter_snapshot",
    "_escape_script_json",
    "_first_query_value",
    "_format_http_url",
    "_is_loopback_host",
    "_inject_serve_bootstrap",
    "_obs_enabled",
    "_obs_line",
    "_obs_log",
    "_payload_generated_at",
    "_serve_bootstrap_script",
    "_write_client_state",
    "serve",
]


def _handle_apply_post(*, body: object, send_json: SendJsonFn, obs_inc: ObsIncFn) -> None:
    """Compatibility wrapper retaining the historical patch point."""
    _handle_apply_post_impl(
        body=body,
        execute_apply=execute_apply_commands,
        send_json=send_json,
        obs_inc=obs_inc,
    )


def serve(
    args: argparse.Namespace,
    out_path: str,
    initial_payload: Payload,
    *,
    render_once: RenderOnceFn,
    task_lookup: TaskLookupFn,
    timew_export: TimewExportFn,
    server_factory: ServerFactoryFn = ThreadingHTTPServer,
    browser_open: BrowserOpenFn | None = None,
) -> None:
    cfg = _build_serve_config(args, out_path)
    state = ServeState(
        payload=initial_payload,
        client_state=_read_client_state(_client_state_file(cfg.out_file)),
    )
    state_lock = threading.Lock()
    obs_lock = threading.Lock()
    obs_counters: dict[str, Any] = {}
    state_file = _client_state_file(cfg.out_file)

    def _obs_inc(key: str, *, path: str | None = None) -> None:
        with obs_lock:
            _counter_inc(obs_counters, key, path=path)

    def _obs_metrics() -> dict[str, Any]:
        with obs_lock:
            return _counter_snapshot(obs_counters)

    def _execute_apply(
        lines: Collection[object],
        *,
        selected: Collection[object] | None = None,
    ) -> ApplyExecutionResult:
        return execute_apply_commands(lines, selected=selected)

    _obs_log("serve.started", host=cfg.host, port=cfg.port, auth_required=cfg.required_token is not None)

    handler = make_handler(
        HttpContext(
            args=args,
            out_path=out_path,
            config=cfg,
            state=state,
            state_lock=state_lock,
            state_file=state_file,
            render_once=render_once,
            task_lookup=task_lookup,
            timew_export=timew_export,
            execute_apply=_execute_apply,
            inject_bootstrap=_inject_serve_bootstrap,
            obs_inc=_obs_inc,
            obs_metrics=_obs_metrics,
        )
    )

    server = server_factory((cfg.host, cfg.port), handler)
    actual_host, actual_port = server.server_address[:2]
    if cfg.required_token is None:
        serve_url = _format_http_url(str(actual_host), int(actual_port), "/")
    else:
        serve_url = _format_http_url(
            str(actual_host), int(actual_port), f"/?token={quote(cfg.required_token, safe='')}"
        )
    print(serve_url)

    if not getattr(args, "no_open", False) and browser_open is not None:
        try:
            browser_open(serve_url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
