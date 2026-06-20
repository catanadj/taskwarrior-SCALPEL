from __future__ import annotations

import argparse
import datetime as dt
import re
import threading
from pathlib import Path
from typing import Any, cast

from .serve_support import client_state_snapshot, obs_log, payload_generated_at, write_client_state
from .serve_types import ExecuteApplyFn, ObsIncFn, RenderOnceFn, SendJsonFn, ServeState, TaskLookupFn, TimewExportFn

_YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def handle_task_endpoint(
    uuid_query: str,
    *,
    task_lookup: TaskLookupFn,
    send_json: SendJsonFn,
    obs_inc: ObsIncFn,
) -> None:
    if not uuid_query:
        send_json(400, {"ok": False, "error": "Query param 'uuid' is required."})
        return
    try:
        task_result = task_lookup(uuid_query)
        task = task_result.get("task")
        if not isinstance(task, dict):
            obs_inc("task_export_not_found_total")
            send_json(404, {"ok": False, "error": f"Task not found for uuid:{uuid_query}"})
            return
        obs_inc("task_export_success_total")
        obs_log(
            "serve.task_export_ok",
            uuid_query=uuid_query,
            matched=int(task_result.get("matched") or 0),
            exact=bool(task_result.get("exact")),
        )
        send_json(
            200,
            {
                "ok": True,
                "task": task,
                "uuid_query": uuid_query,
                "matched": int(task_result.get("matched") or 0),
                "exact": bool(task_result.get("exact")),
            },
        )
    except ValueError as ex:
        obs_inc("task_export_error_total")
        send_json(400, {"ok": False, "error": str(ex)})
    except SystemExit as ex:
        obs_inc("task_export_error_total")
        obs_log("serve.task_export_error", uuid_query=uuid_query, error=str(ex))
        send_json(409, {"ok": False, "error": str(ex)})
    except Exception as ex:
        obs_inc("task_export_error_total")
        obs_log("serve.task_export_error", uuid_query=uuid_query, error=f"{type(ex).__name__}: {ex}")
        send_json(500, {"ok": False, "error": f"{type(ex).__name__}: {ex}"})


def handle_timew_endpoint(
    day: str,
    *,
    timew_export: TimewExportFn,
    send_json: SendJsonFn,
    obs_inc: ObsIncFn,
) -> None:
    if not _YMD_RE.match(day):
        send_json(400, {"ok": False, "error": "Query param 'day' must be YYYY-MM-DD."})
        return
    try:
        result = timew_export(day)
        obs_inc("timew_export_success_total")
        obs_log("serve.timew_export_ok", day=day, intervals=len(result["intervals"]))
        send_json(200, {"ok": True, "day": result["day"], "intervals": result["intervals"]})
    except SystemExit as ex:
        obs_inc("timew_export_error_total")
        obs_log("serve.timew_export_error", day=day, error=str(ex))
        send_json(500, {"ok": False, "error": str(ex)})
    except Exception as ex:
        obs_inc("timew_export_error_total")
        obs_log("serve.timew_export_error", day=day, error=f"{type(ex).__name__}: {ex}")
        send_json(500, {"ok": False, "error": f"{type(ex).__name__}: {ex}"})


def handle_refresh_endpoint(
    *,
    args: argparse.Namespace,
    out_path: str,
    route_file: str,
    state: ServeState,
    state_lock: threading.Lock,
    render_once: RenderOnceFn,
    send_json: SendJsonFn,
    obs_inc: ObsIncFn,
) -> None:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        with state_lock:
            payload = render_once(args, out_path)
            state.payload = payload
        elapsed_ms = int((dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000)
        obs_inc("refresh_success_total")
        obs_log("serve.refresh_ok", ms=elapsed_ms, generated_at=payload_generated_at(payload))
        send_json(
            200,
            {"ok": True, "generated_at": payload_generated_at(payload), "path": route_file},
        )
    except SystemExit as ex:
        obs_inc("refresh_error_total")
        obs_log("serve.refresh_error", error=str(ex))
        send_json(500, {"ok": False, "error": str(ex)})
    except Exception as ex:
        obs_inc("refresh_error_total")
        obs_log("serve.refresh_error", error=f"{type(ex).__name__}: {ex}")
        send_json(500, {"ok": False, "error": f"{type(ex).__name__}: {ex}"})


def handle_client_state_get(*, state: ServeState, state_lock: threading.Lock, send_json: SendJsonFn) -> None:
    with state_lock:
        snapshot = client_state_snapshot(state)
    send_json(200, {"ok": True, "state": snapshot})


def handle_client_state_post(
    *,
    body: object,
    state: ServeState,
    state_lock: threading.Lock,
    state_file: Path,
    send_json: SendJsonFn,
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
    if delete_raw is None:
        delete_raw = []
    if not isinstance(delete_raw, list):
        send_json(400, {"ok": False, "error": "Field 'delete' must be an array."})
        return
    delete_keys = [str(item) for item in delete_raw]
    with state_lock:
        for key, value in values.items():
            state.client_state[str(key)] = value
        for key in delete_keys:
            state.client_state.pop(key, None)
        snapshot = client_state_snapshot(state)
        write_client_state(state_file, snapshot)
    send_json(200, {"ok": True, "state": snapshot})


def handle_apply_post(
    *,
    body: object,
    execute_apply: ExecuteApplyFn,
    send_json: SendJsonFn,
    obs_inc: ObsIncFn,
) -> None:
    if not isinstance(body, dict):
        send_json(400, {"ok": False, "error": "JSON body must be an object."})
        return
    commands = body.get("commands")
    selected = body.get("selected")
    if not bool(body.get("confirm")):
        send_json(400, {"ok": False, "error": "Field 'confirm' must be true."})
        return
    if not isinstance(commands, list):
        send_json(400, {"ok": False, "error": "Field 'commands' must be an array."})
        return
    if selected is not None and not isinstance(selected, list):
        send_json(400, {"ok": False, "error": "Field 'selected' must be an array."})
        return
    if not commands:
        send_json(400, {"ok": False, "error": "No commands supplied for apply."})
        return
    try:
        result = execute_apply(commands, selected=cast(list[object] | None, selected))
    except SystemExit as ex:
        obs_inc("apply_error_total")
        obs_log("serve.apply_error", error=str(ex))
        send_json(400, {"ok": False, "error": str(ex)})
        return
    if result["ok"]:
        obs_inc("apply_success_total")
        obs_log("serve.apply_ok", applied=result["applied"], selected=result["selected"])
        send_json(200, cast(dict[str, Any], result))
        return
    obs_inc("apply_error_total")
    obs_log(
        "serve.apply_error",
        applied=result["applied"],
        selected=result["selected"],
        stopped_after_index=result["stopped_after_index"],
    )
    send_json(200, cast(dict[str, Any], result))


__all__ = [
    "handle_apply_post",
    "handle_client_state_get",
    "handle_client_state_post",
    "handle_refresh_endpoint",
    "handle_task_endpoint",
    "handle_timew_endpoint",
]
