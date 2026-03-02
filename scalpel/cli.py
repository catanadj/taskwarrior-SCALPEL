from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .ai import apply_plan_result, load_plan_overrides, load_plan_result
from .payload import build_payload
from .render.inline import build_html
from .taskwarrior import parse_tw_utc_to_epoch_ms
from .util.timeparse import parse_date_yyyy_mm_dd, parse_workhours
from .util.tz import resolve_tz, today_date, normalize_tz_name


def _build_parser(default_out: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Generate an interactive Taskwarrior calendar HTML (custom time-grid)."
    )
    ap.add_argument("--filter", default="status:pending", help="Taskwarrior filter for export (default: status:pending)")
    ap.add_argument("--start", default=None, help="View start date YYYY-MM-DD (default: today in --tz)")
    ap.add_argument("--days", type=int, default=7, help="Number of days to show (default: 7)")
    ap.add_argument("--workhours", default="06:00-23:00", help="Work hours window, e.g. 06:00-23:00")
    ap.add_argument("--snap", type=int, default=10, help="Snap minutes for drag/resize (default: 10)")
    ap.add_argument("--default-duration", type=int, default=10, help="Default minutes when duration is missing (default: 10)")
    ap.add_argument("--max-infer-duration", type=int, default=480, help="Max minutes to infer duration from due-scheduled (default: 480)")
    ap.add_argument("--px-per-min", type=float, default=2.0, help="Initial vertical scale in pixels per minute (default: 2.0)")

    ap.add_argument(
        "--tz",
        default=os.getenv("SCALPEL_TZ", "local"),
        help="Bucketing timezone for day boundaries (default: env SCALPEL_TZ or 'local')",
    )
    ap.add_argument(
        "--display-tz",
        default=os.getenv("SCALPEL_DISPLAY_TZ", "local"),
        help="Display timezone hint (default: env SCALPEL_DISPLAY_TZ or 'local')",
    )

    ap.add_argument(
        "--out",
        default=default_out,
        help="Output HTML path (default: ./build/scalpel_schedule.html)",
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument(
        "--goals",
        default=os.path.join(script_dir, "goals.json"),
        help="Goals config JSON (default: script folder /goals.json). If missing, goals are disabled.",
    )

    ap.add_argument("--plan-overrides", default=None, help="JSON file of plan overrides to apply")
    ap.add_argument("--plan-result", default=None, help="JSON file of AI plan result to apply")
    ap.add_argument(
        "--no-nautical-hooks",
        action="store_true",
        help="Disable nautical anchor/cp preview task expansion for this run",
    )
    ap.add_argument(
        "--serve",
        action="store_true",
        help="Run a local HTTP server with POST /refresh to rebuild data and reload in-browser.",
    )
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for --serve mode (default: 127.0.0.1).",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for --serve mode (default: 8765, use 0 for auto).",
    )
    ap.add_argument("--no-open", action="store_true", help="Do not open the generated HTML in a browser")
    return ap


def _resolve_out_path(out_arg: str, default_out: str) -> str:
    out_path = os.path.abspath(out_arg)
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        # If caller used the default relative path from an unwritable CWD,
        # transparently fall back to a user-writable location.
        if out_arg == default_out:
            fallback = Path.home() / ".scalpel" / "build" / "scalpel_schedule.html"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            out_path = str(fallback)
            print(
                f"[scalpel] WARN: default output directory is not writable; using {out_path}",
                file=sys.stderr,
            )
        else:
            raise SystemExit(f"Cannot create output directory '{Path(out_path).parent}': {e}")
    return out_path


def _resolve_start_date(start_arg: str | None, tz_name: str) -> dt.date:
    if start_arg:
        return parse_date_yyyy_mm_dd(start_arg)
    try:
        return today_date(resolve_tz(tz_name))
    except ValueError as e:
        raise SystemExit(f"Invalid --tz value: {e}")


def _load_plan_inputs(args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    plan_overrides = None
    plan_result = None
    if args.plan_overrides:
        try:
            plan_overrides = load_plan_overrides(Path(args.plan_overrides))
        except Exception as e:
            raise SystemExit(f"Failed to load plan overrides: {e}")
    if args.plan_result:
        try:
            plan_result = load_plan_result(Path(args.plan_result))
        except Exception as e:
            raise SystemExit(f"Failed to load plan result: {e}")
    return plan_overrides, plan_result


def _build_data(args: argparse.Namespace) -> dict[str, Any]:
    tz_name = normalize_tz_name(args.tz)
    display_tz = normalize_tz_name(args.display_tz)
    start_date = _resolve_start_date(args.start, tz_name)

    work_start, work_end = parse_workhours(args.workhours)
    plan_overrides, plan_result = _load_plan_inputs(args)

    data = build_payload(
        filter_str=args.filter,
        start_date=start_date,
        days=int(args.days),
        work_start=int(work_start),
        work_end=int(work_end),
        snap=int(args.snap),
        default_duration_min=int(args.default_duration),
        max_infer_duration_min=int(args.max_infer_duration),
        px_per_min=float(args.px_per_min),
        goals_path=str(args.goals),
        tz=tz_name,
        display_tz=display_tz,
        plan_overrides=plan_overrides,
        nautical_hooks_enabled=not bool(args.no_nautical_hooks),
    )
    if plan_result:
        data = apply_plan_result(data, plan_result)
    return data


def _render_once(args: argparse.Namespace, out_path: str) -> dict[str, Any]:
    data = _build_data(args)
    html = build_html(data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return data


def _format_http_url(host: str, port: int, path: str = "/") -> str:
    safe_host = (host or "").strip()
    if safe_host in {"", "0.0.0.0", "::"}:
        safe_host = "127.0.0.1"
    if ":" in safe_host and not safe_host.startswith("["):
        safe_host = f"[{safe_host}]"
    suffix = path if path.startswith("/") else ("/" + path)
    return f"http://{safe_host}:{port}{suffix}"


def _payload_generated_at(payload: dict[str, Any]) -> str | None:
    ga = payload.get("generated_at")
    if isinstance(ga, str) and ga:
        return ga
    meta = payload.get("meta")
    if isinstance(meta, dict):
        m = meta.get("generated_at")
        if isinstance(m, str) and m:
            return m
    return None


_YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _timew_timeout_s() -> float:
    raw = (os.getenv("SCALPEL_TIMEW_TIMEOUT_S", "25") or "").strip()
    try:
        v = float(raw)
        if v > 0:
            return v
    except Exception:
        pass
    return 25.0


def _day_window_utc_ms(day_ymd: str, tz_name: str) -> tuple[int, int]:
    if not _YMD_RE.match(str(day_ymd or "")):
        raise ValueError("day must be YYYY-MM-DD")
    d = parse_date_yyyy_mm_dd(day_ymd)
    tzinfo = resolve_tz(normalize_tz_name(tz_name))
    local_start = dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tzinfo)
    local_end = local_start + dt.timedelta(days=1)
    start_ms = int(local_start.astimezone(dt.timezone.utc).timestamp() * 1000)
    end_ms = int(local_end.astimezone(dt.timezone.utc).timestamp() * 1000)
    return start_ms, end_ms


def _run_timew_export_for_day(*, day_ymd: str, tz_name: str) -> dict[str, Any]:
    start_ms, end_ms = _day_window_utc_ms(day_ymd, tz_name)
    cmd = ["timew", day_ymd, "export"]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=_timew_timeout_s(),
        )
    except FileNotFoundError:
        raise SystemExit("Timewarrior binary 'timew' not found on PATH.")
    except subprocess.TimeoutExpired:
        raise SystemExit("Timewarrior export timed out.")

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace").strip()
        msg = f"Timewarrior export failed (exit {proc.returncode})."
        if err:
            msg = f"{msg} {err}"
        raise SystemExit(msg)

    text = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text:
        return {"day": day_ymd, "intervals": []}

    try:
        raw = json.loads(text)
    except Exception as e:
        raise SystemExit(f"Failed to parse `timew export` JSON: {e}")
    if not isinstance(raw, list):
        raise SystemExit("`timew export` did not return a JSON list.")

    out: list[dict[str, Any]] = []
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    for it in raw:
        if not isinstance(it, dict):
            continue
        s_ms = parse_tw_utc_to_epoch_ms(str(it.get("start") or ""))
        e_ms = parse_tw_utc_to_epoch_ms(str(it.get("end") or ""))
        if not isinstance(s_ms, int):
            continue
        if not isinstance(e_ms, int):
            e_ms = now_ms
        if e_ms <= s_ms:
            continue

        # Clamp to requested day window.
        s_ms = max(s_ms, start_ms)
        e_ms = min(e_ms, end_ms)
        if e_ms <= s_ms:
            continue

        tags = it.get("tags")
        tags_out = []
        if isinstance(tags, list):
            for t in tags:
                ts = str(t or "").strip()
                if ts:
                    tags_out.append(ts)
        annotation = str(it.get("annotation") or "").strip()
        out.append(
            {
                "start_ms": s_ms,
                "end_ms": e_ms,
                "tags": tags_out,
                "annotation": annotation,
            }
        )

    out.sort(key=lambda x: (int(x.get("start_ms") or 0), int(x.get("end_ms") or 0)))
    return {"day": day_ymd, "intervals": out}


def _serve(args: argparse.Namespace, out_path: str, initial_payload: dict[str, Any]) -> None:
    host = str(args.host or "127.0.0.1").strip() or "127.0.0.1"
    port = int(args.port)
    if port < 0 or port > 65535:
        raise SystemExit("--port must be between 0 and 65535")

    out_file = Path(out_path)
    route_file = "/" + out_file.name
    state: dict[str, Any] = {"payload": initial_payload}
    state_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, code: int, html_text: str) -> None:
            body = html_text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *a: Any) -> None:
            print(f"[scalpel-serve] {self.address_string()} - {fmt % a}", file=sys.stderr)

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path in {"/", route_file}:
                try:
                    with state_lock:
                        html = out_file.read_text(encoding="utf-8")
                except Exception as e:
                    self._send_json(500, {"ok": False, "error": f"Failed reading HTML: {e}"})
                    return
                self._send_html(200, html)
                return

            if path == "/payload":
                with state_lock:
                    payload = state.get("payload")
                if not isinstance(payload, dict):
                    self._send_json(404, {"ok": False, "error": "No payload loaded"})
                    return
                self._send_json(200, payload)
                return

            if path == "/timew":
                qs = parse_qs(urlsplit(self.path).query or "", keep_blank_values=False)
                day = str((qs.get("day") or [""])[0]).strip()
                if not _YMD_RE.match(day):
                    self._send_json(400, {"ok": False, "error": "Query param 'day' must be YYYY-MM-DD."})
                    return
                try:
                    res = _run_timew_export_for_day(day_ymd=day, tz_name=str(args.tz or "local"))
                    self._send_json(200, {"ok": True, "day": res["day"], "intervals": res["intervals"]})
                except SystemExit as e:
                    self._send_json(500, {"ok": False, "error": str(e)})
                except Exception as e:
                    self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
                return

            if path == "/health":
                self._send_json(200, {"ok": True})
                return

            self._send_json(404, {"ok": False, "error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path != "/refresh":
                self._send_json(404, {"ok": False, "error": "Not found"})
                return
            try:
                with state_lock:
                    payload = _render_once(args, out_path)
                    state["payload"] = payload
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "generated_at": _payload_generated_at(payload),
                        "path": route_file,
                    },
                )
            except SystemExit as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    server = ThreadingHTTPServer((host, port), Handler)
    actual_host, actual_port = server.server_address[:2]
    serve_url = _format_http_url(str(actual_host), int(actual_port), "/")
    print(serve_url)

    if not getattr(args, "no_open", False):
        try:
            webbrowser.open(serve_url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> None:
    default_out = os.path.join("build", "scalpel_schedule.html")
    ap = _build_parser(default_out)
    args = ap.parse_args(argv)
    out_path = _resolve_out_path(args.out, default_out)
    payload = _render_once(args, out_path)

    print(out_path)

    if bool(getattr(args, "serve", False)):
        _serve(args, out_path, payload)
        return

    if not getattr(args, "no_open", False):
        try:
            webbrowser.open("file://" + out_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
