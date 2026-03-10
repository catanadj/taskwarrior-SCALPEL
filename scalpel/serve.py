from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, TypedDict, cast
from urllib.parse import parse_qs, quote, urlsplit

from .model import Payload, RawTask
from .util.console import eprint


class TimewInterval(TypedDict):
    start_ms: int
    end_ms: int
    tags: list[str]
    annotation: str


class TimewExportResult(TypedDict):
    day: str
    intervals: list[TimewInterval]


class TaskExportLookupResult(TypedDict):
    task: RawTask | None
    matched: int
    exact: bool


@dataclass(frozen=True)
class ServeConfig:
    host: str
    port: int
    required_token: str | None
    out_file: Path
    route_file: str


@dataclass
class ServeState:
    payload: Payload
    client_state: dict[str, Any]


RenderOnceFn = Callable[[argparse.Namespace, str], Payload]
TaskLookupFn = Callable[[str], TaskExportLookupResult]
TimewExportFn = Callable[[str], TimewExportResult]
BrowserOpenFn = Callable[[str], Any]
ServerFactoryFn = Callable[[tuple[str, int], type[BaseHTTPRequestHandler]], ThreadingHTTPServer]

_YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _format_http_url(host: str, port: int, path: str = "/") -> str:
    safe_host = (host or "").strip()
    if safe_host in {"", "0.0.0.0", "::"}:
        safe_host = "127.0.0.1"
    if ":" in safe_host and not safe_host.startswith("["):
        safe_host = f"[{safe_host}]"
    suffix = path if path.startswith("/") else ("/" + path)
    return f"http://{safe_host}:{port}{suffix}"


def _payload_generated_at(payload: Payload) -> str | None:
    ga = payload.get("generated_at")
    if isinstance(ga, str) and ga:
        return ga
    meta = payload.get("meta")
    if isinstance(meta, dict):
        m = meta.get("generated_at")
        if isinstance(m, str) and m:
            return m
    return None


def _client_state_file(out_file: Path) -> Path:
    return out_file.with_suffix(out_file.suffix + ".state.json")


def _read_client_state(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items()}


def _write_client_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _client_state_snapshot(state: ServeState) -> dict[str, Any]:
    return {str(k): v for k, v in state.client_state.items()}


def _escape_script_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")


def _serve_bootstrap_script(client_state: dict[str, Any]) -> str:
    boot_json = _escape_script_json(client_state)
    return (
        "<script>\n"
        "(() => {\n"
        '  "use strict";\n'
        "  const g = (typeof globalThis !== 'undefined') ? globalThis : window;\n"
        "  if (!g) return;\n"
        f"  const boot = {boot_json};\n"
        "  const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);\n"
        "  const store = (g.__scalpel_serverKvStore && typeof g.__scalpel_serverKvStore === 'object') ? g.__scalpel_serverKvStore : Object.assign({}, boot);\n"
        "  g.__scalpel_serverKvStore = store;\n"
        "  let pendingValues = {};\n"
        "  let pendingDelete = new Set();\n"
        "  let flushTimer = 0;\n"
        "  function scheduleFlush(){\n"
        "    if (flushTimer) return;\n"
        "    flushTimer = setTimeout(flushNow, 60);\n"
        "  }\n"
        "  async function flushNow(){\n"
        "    if (flushTimer){ clearTimeout(flushTimer); flushTimer = 0; }\n"
        "    const values = pendingValues;\n"
        "    const del = Array.from(pendingDelete);\n"
        "    pendingValues = {};\n"
        "    pendingDelete = new Set();\n"
        "    if (!Object.keys(values).length && !del.length) return;\n"
        "    try {\n"
        "      await fetch('/client-state', {\n"
        "        method: 'POST',\n"
        "        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },\n"
        "        credentials: 'same-origin',\n"
        "        cache: 'no-store',\n"
        "        body: JSON.stringify({ values, delete: del }),\n"
        "      });\n"
        "    } catch (_) {}\n"
        "  }\n"
        "  function safeLsSet(key, value){ try { localStorage.setItem(String(key), String(value)); } catch (_) {} }\n"
        "  function safeLsDel(key){ try { localStorage.removeItem(String(key)); } catch (_) {} }\n"
        "  g.__scalpel_kvGet = function(key, fb){\n"
        "    const k = String(key);\n"
        "    return hasOwn(store, k) ? store[k] : fb;\n"
        "  };\n"
        "  g.__scalpel_kvSet = function(key, value){\n"
        "    const k = String(key);\n"
        "    const v = String(value);\n"
        "    store[k] = v;\n"
        "    pendingValues[k] = v;\n"
        "    pendingDelete.delete(k);\n"
        "    safeLsSet(k, v);\n"
        "    scheduleFlush();\n"
        "  };\n"
        "  g.__scalpel_kvDel = function(key){\n"
        "    const k = String(key);\n"
        "    delete store[k];\n"
        "    delete pendingValues[k];\n"
        "    pendingDelete.add(k);\n"
        "    safeLsDel(k);\n"
        "    scheduleFlush();\n"
        "  };\n"
        "  g.__scalpel_kvGetJSON = function(key, fb){\n"
        "    const v = g.__scalpel_kvGet(String(key), null);\n"
        "    if (v == null) return fb;\n"
        "    if (typeof v === 'object') return v;\n"
        "    try { return JSON.parse(String(v)); } catch (_) { return fb; }\n"
        "  };\n"
        "  g.__scalpel_kvSetJSON = function(key, obj){\n"
        "    const k = String(key);\n"
        "    store[k] = obj;\n"
        "    pendingValues[k] = obj;\n"
        "    pendingDelete.delete(k);\n"
        "    try { safeLsSet(k, JSON.stringify(obj)); } catch (_) {}\n"
        "    scheduleFlush();\n"
        "  };\n"
        "})();\n"
        "</script>\n"
    )


def _inject_serve_bootstrap(html_text: str, client_state: dict[str, Any]) -> str:
    bootstrap = _serve_bootstrap_script(client_state)
    marker = '<script id="tw-data" type="application/json">'
    if marker in html_text:
        return html_text.replace(marker, bootstrap + marker, 1)
    if "</body>" in html_text:
        return html_text.replace("</body>", bootstrap + "</body>", 1)
    return bootstrap + html_text


def _is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1].strip().lower()
    return h in {"", "localhost", "127.0.0.1", "::1"}


def _obs_enabled() -> bool:
    raw = (os.getenv("SCALPEL_OBS_LOG", "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _obs_line(event: str, **fields: Any) -> str:
    rec: dict[str, Any] = {"event": str(event)}
    for k, v in fields.items():
        if v is None:
            continue
        rec[str(k)] = v
    return "[scalpel.serve.obs] " + json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _obs_log(event: str, *, eprint_fn: Callable[[str], None] = eprint, **fields: Any) -> None:
    if not _obs_enabled():
        return
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out = dict(fields)
    out.setdefault("ts", now_iso)
    eprint_fn(_obs_line(event, **out))


def _counter_inc(counters: dict[str, Any], key: str, *, path: str | None = None) -> None:
    k = str(key).strip()
    if not k:
        return
    counters[k] = int(counters.get(k) or 0) + 1
    if path is None:
        return
    mk = f"{k}_by_path"
    m = counters.get(mk)
    if not isinstance(m, dict):
        m = {}
        counters[mk] = m
    p = str(path or "").strip() or "/"
    m[p] = int(m.get(p) or 0) + 1


def _counter_snapshot(counters: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in counters.items():
        if isinstance(v, dict):
            clean: dict[str, int] = {}
            for kk, vv in v.items():
                try:
                    clean[str(kk)] = int(vv)
                except Exception:
                    clean[str(kk)] = 0
            out[str(k)] = clean
        else:
            try:
                out[str(k)] = int(v)
            except Exception:
                continue
    return out


def _build_serve_config(args: argparse.Namespace, out_path: str) -> ServeConfig:
    host = str(args.host or "127.0.0.1").strip() or "127.0.0.1"
    port = int(args.port)
    if port < 0 or port > 65535:
        raise SystemExit("--port must be between 0 and 65535")
    if (not _is_loopback_host(host)) and (not bool(getattr(args, "allow_remote", False))):
        raise SystemExit("Refusing non-loopback --host without --allow-remote.")

    required_token_raw = str(getattr(args, "serve_token", "") or "").strip()
    required_token = required_token_raw or None
    if (not _is_loopback_host(host)) and required_token is None:
        raise SystemExit("Remote --serve requires --serve-token (or SCALPEL_SERVE_TOKEN).")

    out_file = Path(out_path)
    return ServeConfig(
        host=host,
        port=port,
        required_token=required_token,
        out_file=out_file,
        route_file="/" + out_file.name,
    )


def _first_query_value(raw_path: str, name: str) -> str:
    qs = parse_qs(urlsplit(raw_path).query or "", keep_blank_values=False)
    return str((qs.get(name) or [""])[0]).strip()


def _handle_task_endpoint(
    uuid_q: str,
    *,
    task_lookup: TaskLookupFn,
    send_json: Callable[[int, dict[str, Any]], None],
    obs_inc: Callable[[str], None],
) -> None:
    if not uuid_q:
        send_json(400, {"ok": False, "error": "Query param 'uuid' is required."})
        return
    try:
        task_res = task_lookup(uuid_q)
        task_obj = task_res.get("task")
        if not isinstance(task_obj, dict):
            obs_inc("task_export_not_found_total")
            send_json(404, {"ok": False, "error": f"Task not found for uuid:{uuid_q}"})
            return
        obs_inc("task_export_success_total")
        _obs_log(
            "serve.task_export_ok",
            uuid_query=uuid_q,
            matched=int(task_res.get("matched") or 0),
            exact=bool(task_res.get("exact")),
        )
        send_json(
            200,
            {
                "ok": True,
                "task": task_obj,
                "uuid_query": uuid_q,
                "matched": int(task_res.get("matched") or 0),
                "exact": bool(task_res.get("exact")),
            },
        )
    except ValueError as e:
        obs_inc("task_export_error_total")
        send_json(400, {"ok": False, "error": str(e)})
    except SystemExit as e:
        obs_inc("task_export_error_total")
        _obs_log("serve.task_export_error", uuid_query=uuid_q, error=str(e))
        send_json(409, {"ok": False, "error": str(e)})
    except Exception as e:
        obs_inc("task_export_error_total")
        _obs_log("serve.task_export_error", uuid_query=uuid_q, error=f"{type(e).__name__}: {e}")
        send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


def _handle_timew_endpoint(
    day: str,
    *,
    timew_export: TimewExportFn,
    send_json: Callable[[int, dict[str, Any]], None],
    obs_inc: Callable[[str], None],
) -> None:
    if not _YMD_RE.match(day):
        send_json(400, {"ok": False, "error": "Query param 'day' must be YYYY-MM-DD."})
        return
    try:
        timew_res = timew_export(day)
        obs_inc("timew_export_success_total")
        _obs_log("serve.timew_export_ok", day=day, intervals=len(timew_res["intervals"]))
        send_json(200, {"ok": True, "day": timew_res["day"], "intervals": timew_res["intervals"]})
    except SystemExit as e:
        obs_inc("timew_export_error_total")
        _obs_log("serve.timew_export_error", day=day, error=str(e))
        send_json(500, {"ok": False, "error": str(e)})
    except Exception as e:
        obs_inc("timew_export_error_total")
        _obs_log("serve.timew_export_error", day=day, error=f"{type(e).__name__}: {e}")
        send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


def _handle_refresh_endpoint(
    *,
    args: argparse.Namespace,
    out_path: str,
    route_file: str,
    state: ServeState,
    state_lock: threading.Lock,
    render_once: RenderOnceFn,
    send_json: Callable[[int, dict[str, Any]], None],
    obs_inc: Callable[[str], None],
) -> None:
    t0 = dt.datetime.now(dt.timezone.utc)
    try:
        with state_lock:
            payload = render_once(args, out_path)
            state.payload = payload
        elapsed_ms = int((dt.datetime.now(dt.timezone.utc) - t0).total_seconds() * 1000)
        obs_inc("refresh_success_total")
        _obs_log(
            "serve.refresh_ok",
            ms=elapsed_ms,
            generated_at=_payload_generated_at(payload),
        )
        send_json(
            200,
            {
                "ok": True,
                "generated_at": _payload_generated_at(payload),
                "path": route_file,
            },
        )
    except SystemExit as e:
        obs_inc("refresh_error_total")
        _obs_log("serve.refresh_error", error=str(e))
        send_json(500, {"ok": False, "error": str(e)})
    except Exception as e:
        obs_inc("refresh_error_total")
        _obs_log("serve.refresh_error", error=f"{type(e).__name__}: {e}")
        send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


def _handle_client_state_get(
    *,
    state: ServeState,
    state_lock: threading.Lock,
    send_json: Callable[[int, dict[str, Any]], None],
) -> None:
    with state_lock:
        snapshot = _client_state_snapshot(state)
    send_json(200, {"ok": True, "state": snapshot})


def _handle_client_state_post(
    *,
    body: object,
    state: ServeState,
    state_lock: threading.Lock,
    state_file: Path,
    send_json: Callable[[int, dict[str, Any]], None],
) -> None:
    if not isinstance(body, dict):
        send_json(400, {"ok": False, "error": "JSON body must be an object."})
        return
    values = body.get("values")
    delete_raw = body.get("delete")
    if values is None:
        values = {}
    if not isinstance(values, dict):
        send_json(400, {"ok": False, "error": "Field 'values' must be an object."})
        return
    delete_keys: list[str] = []
    if delete_raw is None:
        delete_raw = []
    if not isinstance(delete_raw, list):
        send_json(400, {"ok": False, "error": "Field 'delete' must be an array."})
        return
    for item in delete_raw:
        delete_keys.append(str(item))
    with state_lock:
        for key, value in values.items():
            state.client_state[str(key)] = value
        for key in delete_keys:
            state.client_state.pop(str(key), None)
        snapshot = _client_state_snapshot(state)
        _write_client_state(state_file, snapshot)
    send_json(200, {"ok": True, "state": snapshot})


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

    _obs_log("serve.started", host=cfg.host, port=cfg.port, auth_required=cfg.required_token is not None)

    class Handler(BaseHTTPRequestHandler):
        def _query_token(self) -> str:
            return _first_query_value(self.path, "token")

        def _header_token(self) -> str:
            x_token = str(self.headers.get("X-Scalpel-Token") or "").strip()
            if x_token:
                return x_token
            auth = str(self.headers.get("Authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                return auth[7:].strip()
            return ""

        def _cookie_token(self) -> str:
            raw = str(self.headers.get("Cookie") or "")
            if not raw:
                return ""
            for part in raw.split(";"):
                key, _, val = part.strip().partition("=")
                if key.strip() == "scalpel_token":
                    return val.strip()
            return ""

        def _is_authorized(self) -> bool:
            if cfg.required_token is None:
                return True
            for tok in (self._query_token(), self._header_token(), self._cookie_token()):
                if tok and tok == cfg.required_token:
                    return True
            return False

        def _deny_unauthorized(self, path: str) -> None:
            _obs_inc("auth_failures_total", path=path)
            _obs_log(
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
            if set_auth_cookie and cfg.required_token is not None:
                self.send_header("Set-Cookie", f"scalpel_token={cfg.required_token}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, code: int, html_text: str, *, set_auth_cookie: bool = False) -> None:
            body = html_text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            if set_auth_cookie and cfg.required_token is not None:
                self.send_header("Set-Cookie", f"scalpel_token={cfg.required_token}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *a: Any) -> None:
            msg = fmt % a
            msg = re.sub(r"(token=)[^&\s]+", r"\1REDACTED", msg, flags=re.IGNORECASE)
            print(f"[scalpel-serve] {self.address_string()} - {msg}", file=sys.stderr)

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            _obs_inc("requests_total", path=path)
            _obs_inc("requests_get_total")
            if path in {"/", cfg.route_file}:
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                try:
                    with state_lock:
                        html = cfg.out_file.read_text(encoding="utf-8")
                        client_state = _client_state_snapshot(state)
                except Exception as e:
                    self._send_json(500, {"ok": False, "error": f"Failed reading HTML: {e}"})
                    return
                html = _inject_serve_bootstrap(html, client_state)
                set_cookie = cfg.required_token is not None and self._query_token() == cfg.required_token
                self._send_html(200, html, set_auth_cookie=set_cookie)
                return

            if path == "/payload":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                with state_lock:
                    payload = state.payload
                _obs_inc("payload_reads_total")
                self._send_json(200, cast(dict[str, Any], payload))
                return

            if path == "/client-state":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                _handle_client_state_get(
                    state=state,
                    state_lock=state_lock,
                    send_json=self._send_json,
                )
                return

            if path == "/task":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                _handle_task_endpoint(
                    _first_query_value(self.path, "uuid"),
                    task_lookup=task_lookup,
                    send_json=self._send_json,
                    obs_inc=_obs_inc,
                )
                return

            if path == "/timew":
                if not self._is_authorized():
                    self._deny_unauthorized(path)
                    return
                _handle_timew_endpoint(
                    _first_query_value(self.path, "day"),
                    timew_export=timew_export,
                    send_json=self._send_json,
                    obs_inc=_obs_inc,
                )
                return

            if path == "/metrics":
                if cfg.required_token is not None and (not self._is_authorized()):
                    self._deny_unauthorized(path)
                    return
                self._send_json(200, {"ok": True, "metrics": _obs_metrics()})
                return

            if path == "/health":
                include_metrics = _first_query_value(self.path, "metrics").lower() in {"1", "true", "yes", "on"}
                if include_metrics:
                    self._send_json(
                        200,
                        {"ok": True, "auth_required": cfg.required_token is not None, "metrics": _obs_metrics()},
                    )
                else:
                    self._send_json(200, {"ok": True})
                return

            self._send_json(404, {"ok": False, "error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            _obs_inc("requests_total", path=path)
            _obs_inc("requests_post_total")
            if path not in {"/refresh", "/client-state"}:
                self._send_json(404, {"ok": False, "error": "Not found"})
                return
            if not self._is_authorized():
                self._deny_unauthorized(path)
                return
            if path == "/refresh":
                _handle_refresh_endpoint(
                    args=args,
                    out_path=out_path,
                    route_file=cfg.route_file,
                    state=state,
                    state_lock=state_lock,
                    render_once=render_once,
                    send_json=self._send_json,
                    obs_inc=_obs_inc,
                )
                return
            try:
                content_len = int(self.headers.get("Content-Length") or "0")
            except Exception:
                content_len = 0
            try:
                raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
                body = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                self._send_json(400, {"ok": False, "error": "Invalid JSON body."})
                return
            _handle_client_state_post(
                body=body,
                state=state,
                state_lock=state_lock,
                state_file=state_file,
                send_json=self._send_json,
            )

    server = server_factory((cfg.host, cfg.port), Handler)
    actual_host, actual_port = server.server_address[:2]
    if cfg.required_token is None:
        serve_url = _format_http_url(str(actual_host), int(actual_port), "/")
    else:
        serve_url = _format_http_url(str(actual_host), int(actual_port), f"/?token={quote(cfg.required_token, safe='')}")
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
