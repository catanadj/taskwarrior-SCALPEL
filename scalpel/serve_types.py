from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, TypedDict

from .model import Payload, RawTask
from .serve_apply import ApplyExecutionResult


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
ExecuteApplyFn = Callable[..., ApplyExecutionResult]
SendJsonFn = Callable[[int, dict[str, Any]], None]
ObsIncFn = Callable[..., None]


__all__ = [
    "BrowserOpenFn",
    "ExecuteApplyFn",
    "ObsIncFn",
    "RenderOnceFn",
    "SendJsonFn",
    "ServeConfig",
    "ServeState",
    "ServerFactoryFn",
    "TaskExportLookupResult",
    "TaskLookupFn",
    "TimewExportFn",
    "TimewExportResult",
    "TimewInterval",
]
