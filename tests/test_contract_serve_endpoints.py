from __future__ import annotations

import argparse
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, Callable

from scalpel.serve_endpoints import (
    handle_apply_post,
    handle_client_state_get,
    handle_client_state_post,
    handle_refresh_endpoint,
    handle_task_endpoint,
    handle_timew_endpoint,
)
from scalpel.serve_types import ServeState


class EndpointRecorder:
    def __init__(self) -> None:
        self.responses: list[tuple[int, dict[str, Any]]] = []
        self.metrics: list[str] = []

    def send(self, status: int, body: dict[str, Any]) -> None:
        self.responses.append((status, body))

    def increment(self, metric: str) -> None:
        self.metrics.append(metric)


class ServeEndpointContractTests(unittest.TestCase):
    def test_task_endpoint_maps_lookup_outcomes(self) -> None:
        recorder = EndpointRecorder()
        handle_task_endpoint("", task_lookup=lambda _: {}, send_json=recorder.send, obs_inc=recorder.increment)  # type: ignore[arg-type]
        self.assertEqual(recorder.responses[-1][0], 400)

        lookups: tuple[tuple[Callable[[str], Any], int, str], ...] = (
            (lambda _: {"task": None, "matched": 0, "exact": False}, 404, "task_export_not_found_total"),
            (lambda _: (_ for _ in ()).throw(ValueError("bad query")), 400, "task_export_error_total"),
            (lambda _: (_ for _ in ()).throw(SystemExit("ambiguous")), 409, "task_export_error_total"),
            (lambda _: (_ for _ in ()).throw(RuntimeError("broken")), 500, "task_export_error_total"),
        )
        for lookup, status, metric in lookups:
            with self.subTest(status=status):
                handle_task_endpoint("abc", task_lookup=lookup, send_json=recorder.send, obs_inc=recorder.increment)
                self.assertEqual(recorder.responses[-1][0], status)
                self.assertEqual(recorder.metrics[-1], metric)

        handle_task_endpoint(
            "abc",
            task_lookup=lambda _: {"task": {"uuid": "abc"}, "matched": 1, "exact": True},
            send_json=recorder.send,
            obs_inc=recorder.increment,
        )
        self.assertEqual(
            recorder.responses[-1],
            (200, {"ok": True, "task": {"uuid": "abc"}, "uuid_query": "abc", "matched": 1, "exact": True}),
        )

    def test_timew_endpoint_validates_and_maps_failures(self) -> None:
        recorder = EndpointRecorder()
        handle_timew_endpoint("bad", timew_export=lambda _: {}, send_json=recorder.send, obs_inc=recorder.increment)  # type: ignore[arg-type]
        self.assertEqual(recorder.responses[-1][0], 400)

        handle_timew_endpoint(
            "2026-01-01",
            timew_export=lambda day: {"day": day, "intervals": []},
            send_json=recorder.send,
            obs_inc=recorder.increment,
        )
        self.assertEqual(recorder.responses[-1][0], 200)
        for error in (SystemExit("missing timew"), RuntimeError("broken")):
            with self.subTest(error=type(error).__name__):
                handle_timew_endpoint(
                    "2026-01-01",
                    timew_export=lambda _, error=error: (_ for _ in ()).throw(error),
                    send_json=recorder.send,
                    obs_inc=recorder.increment,
                )
                self.assertEqual(recorder.responses[-1][0], 500)

    def test_refresh_endpoint_updates_state_and_maps_failures(self) -> None:
        recorder = EndpointRecorder()
        state = ServeState(payload={}, client_state={})
        lock = threading.Lock()
        args = argparse.Namespace()
        handle_refresh_endpoint(
            args=args,
            out_path="out.html",
            route_file="/out.html",
            state=state,
            state_lock=lock,
            render_once=lambda _args, _path: {"generated_at": "now"},
            send_json=recorder.send,
            obs_inc=recorder.increment,
        )
        self.assertEqual(state.payload["generated_at"], "now")
        self.assertEqual(recorder.responses[-1][0], 200)

        for error in (SystemExit("render exit"), RuntimeError("render failed")):
            with self.subTest(error=type(error).__name__):
                handle_refresh_endpoint(
                    args=args,
                    out_path="out.html",
                    route_file="/out.html",
                    state=state,
                    state_lock=lock,
                    render_once=lambda _args, _path, error=error: (_ for _ in ()).throw(error),
                    send_json=recorder.send,
                    obs_inc=recorder.increment,
                )
                self.assertEqual(recorder.responses[-1][0], 500)

    def test_client_state_endpoints_validate_and_persist(self) -> None:
        recorder = EndpointRecorder()
        state = ServeState(payload={}, client_state={"old": 1})
        lock = threading.Lock()
        handle_client_state_get(state=state, state_lock=lock, send_json=recorder.send)
        self.assertEqual(recorder.responses[-1][1]["state"], {"old": 1})

        with tempfile.TemporaryDirectory() as td:
            state_file = Path(td) / "state.json"
            invalid = (None, {"values": []}, {"delete": "old"})
            for body in invalid:
                with self.subTest(body=body):
                    handle_client_state_post(
                        body=body,
                        state=state,
                        state_lock=lock,
                        state_file=state_file,
                        send_json=recorder.send,
                    )
                    self.assertEqual(recorder.responses[-1][0], 400)

            handle_client_state_post(
                body={"values": {"new": 2}, "delete": ["old"]},
                state=state,
                state_lock=lock,
                state_file=state_file,
                send_json=recorder.send,
            )
            self.assertEqual(state.client_state, {"new": 2})
            self.assertTrue(state_file.is_file())

    def test_apply_endpoint_validates_and_maps_results(self) -> None:
        recorder = EndpointRecorder()
        successful = {
            "ok": True,
            "applied": 1,
            "selected": 1,
            "commands": [],
            "stopped_after_index": None,
        }
        failed = {**successful, "ok": False, "applied": 0, "stopped_after_index": 0}
        invalid = (
            None,
            {},
            {"confirm": True, "commands": "bad"},
            {"confirm": True, "commands": [], "selected": "bad"},
            {"confirm": True, "commands": []},
        )
        for body in invalid:
            with self.subTest(body=body):
                handle_apply_post(
                    body=body,
                    execute_apply=lambda *_args, **_kwargs: successful,  # type: ignore[arg-type]
                    send_json=recorder.send,
                    obs_inc=recorder.increment,
                )
                self.assertEqual(recorder.responses[-1][0], 400)

        for result, metric in ((successful, "apply_success_total"), (failed, "apply_error_total")):
            handle_apply_post(
                body={"confirm": True, "commands": ["task x done"], "selected": [0]},
                execute_apply=lambda *_args, result=result, **_kwargs: result,  # type: ignore[arg-type]
                send_json=recorder.send,
                obs_inc=recorder.increment,
            )
            self.assertEqual(recorder.responses[-1][0], 200)
            self.assertEqual(recorder.metrics[-1], metric)

        handle_apply_post(
            body={"confirm": True, "commands": ["bad"]},
            execute_apply=lambda *_args, **_kwargs: (_ for _ in ()).throw(SystemExit("invalid")),
            send_json=recorder.send,
            obs_inc=recorder.increment,
        )
        self.assertEqual(recorder.responses[-1][0], 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
