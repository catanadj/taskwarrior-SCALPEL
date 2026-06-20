from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from .model import Payload
from .serve_types import ServeConfig, ServeState
from .util.console import eprint


def format_http_url(host: str, port: int, path: str = "/") -> str:
    safe_host = (host or "").strip()
    if safe_host in {"", "0.0.0.0", "::"}:
        safe_host = "127.0.0.1"
    if ":" in safe_host and not safe_host.startswith("["):
        safe_host = f"[{safe_host}]"
    suffix = path if path.startswith("/") else ("/" + path)
    return f"http://{safe_host}:{port}{suffix}"


def payload_generated_at(payload: Payload) -> str | None:
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str) and generated_at:
        return generated_at
    meta = payload.get("meta")
    if isinstance(meta, dict):
        generated_at = meta.get("generated_at")
        if isinstance(generated_at, str) and generated_at:
            return generated_at
    return None


def client_state_file(out_file: Path) -> Path:
    return out_file.with_suffix(out_file.suffix + ".state.json")


def read_client_state(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items()}


def write_client_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def client_state_snapshot(state: ServeState) -> dict[str, Any]:
    return {str(key): value for key, value in state.client_state.items()}


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1].strip().lower()
    return normalized in {"", "localhost", "127.0.0.1", "::1"}


def obs_enabled() -> bool:
    raw = (os.getenv("SCALPEL_OBS_LOG", "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def obs_line(event: str, **fields: Any) -> str:
    record: dict[str, Any] = {"event": str(event)}
    for key, value in fields.items():
        if value is not None:
            record[str(key)] = value
    return "[scalpel.serve.obs] " + json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def obs_log(event: str, *, eprint_fn: Callable[[str], None] = eprint, **fields: Any) -> None:
    if not obs_enabled():
        return
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output = dict(fields)
    output.setdefault("ts", now_iso)
    eprint_fn(obs_line(event, **output))


def counter_inc(counters: dict[str, Any], key: str, *, path: str | None = None) -> None:
    normalized_key = str(key).strip()
    if not normalized_key:
        return
    counters[normalized_key] = int(counters.get(normalized_key) or 0) + 1
    if path is None:
        return
    map_key = f"{normalized_key}_by_path"
    by_path = counters.get(map_key)
    if not isinstance(by_path, dict):
        by_path = {}
        counters[map_key] = by_path
    normalized_path = str(path or "").strip() or "/"
    by_path[normalized_path] = int(by_path.get(normalized_path) or 0) + 1


def counter_snapshot(counters: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in counters.items():
        if isinstance(value, dict):
            clean: dict[str, int] = {}
            for nested_key, nested_value in value.items():
                try:
                    clean[str(nested_key)] = int(nested_value)
                except (TypeError, ValueError):
                    clean[str(nested_key)] = 0
            output[str(key)] = clean
        else:
            try:
                output[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
    return output


def build_serve_config(args: argparse.Namespace, out_path: str) -> ServeConfig:
    host = str(args.host or "127.0.0.1").strip() or "127.0.0.1"
    port = int(args.port)
    if port < 0 or port > 65535:
        raise SystemExit("--port must be between 0 and 65535")
    if not is_loopback_host(host) and not bool(getattr(args, "allow_remote", False)):
        raise SystemExit("Refusing non-loopback --host without --allow-remote.")

    required_token_raw = str(getattr(args, "serve_token", "") or "").strip()
    required_token = required_token_raw or None
    if not is_loopback_host(host) and required_token is None:
        raise SystemExit("Remote --serve requires --serve-token (or SCALPEL_SERVE_TOKEN).")

    out_file = Path(out_path)
    return ServeConfig(
        host=host,
        port=port,
        required_token=required_token,
        out_file=out_file,
        route_file="/" + out_file.name,
    )


def first_query_value(raw_path: str, name: str) -> str:
    query = parse_qs(urlsplit(raw_path).query or "", keep_blank_values=False)
    return str((query.get(name) or [""])[0]).strip()


__all__ = [
    "build_serve_config",
    "client_state_file",
    "client_state_snapshot",
    "counter_inc",
    "counter_snapshot",
    "first_query_value",
    "format_http_url",
    "is_loopback_host",
    "obs_enabled",
    "obs_line",
    "obs_log",
    "payload_generated_at",
    "read_client_state",
    "write_client_state",
]
