#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configuration
HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parents[1]

# Resource limits
MAX_SESSIONS = 10
SESSION_TIMEOUT = 300  # 5 minutes
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB
QUEUE_MAX_SIZE = 1000

# Constants
MAX_TAGS_PER_TASK = 20
MAX_PROJECTS_IN_SUMMARY = 5
STREAM_TIMEOUT = 0.2

# Allowed command-line arguments (for security)
ALLOWED_ARG_PREFIXES = {
    '--print-payload',
    '--filter',
    '--project',
    '--tag',
    '--tags',
    '--dry-run',
    '--help',
    '--version',
    '--limit',
    '--sort',
    '--debug',
}

# Session storage
SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSIONS_LOCK = threading.Lock()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _validate_args(args: List[str]) -> tuple[bool, Optional[str]]:
    """Validate command-line arguments for security."""
    for arg in args:
        if arg.startswith('--'):
            # Extract the base argument (before '=')
            base_arg = arg.split('=')[0]
            if base_arg not in ALLOWED_ARG_PREFIXES:
                return False, f"Argument not allowed: {base_arg}"
        elif arg.startswith('-'):
            # Single dash arguments (like -h) - be more restrictive
            if arg not in ['-h', '-v']:
                return False, f"Short argument not allowed: {arg}"
        # Non-flag arguments are generally okay (values for flags)
    return True, None


def _json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: int = 200) -> None:
    """Send JSON response with proper headers."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _error_response(handler: BaseHTTPRequestHandler, message: str, code: str, status: int) -> None:
    """Send standardized error response."""
    _json_response(handler, {
        "error": {
            "message": message,
            "code": code
        }
    }, status)


def _selection_summary_from_payload(payload_text: str) -> str:
    """Generate summary statistics from task selection payload."""
    if not payload_text:
        return ""
    try:
        obj = json.loads(payload_text)
    except Exception as e:
        logger.warning(f"Failed to parse payload for summary: {e}")
        return ""
    
    tasks = obj.get("tasks")
    if not isinstance(tasks, list):
        return ""
    
    total = len(tasks)
    by_project: Dict[str, int] = {}
    by_tag: Dict[str, int] = {}
    
    for t in tasks:
        if not isinstance(t, dict):
            continue
        proj = str(t.get("project") or "").strip() or "(none)"
        by_project[proj] = by_project.get(proj, 0) + 1
        tags = t.get("tags") if isinstance(t.get("tags"), list) else []
        for tag in tags[:MAX_TAGS_PER_TASK]:
            tag_s = str(tag).strip()
            if tag_s:
                by_tag[tag_s] = by_tag.get(tag_s, 0) + 1
    
    top_projects = ", ".join(
        f"{k}:{v}" for k, v in sorted(by_project.items(), key=lambda x: -x[1])[:MAX_PROJECTS_IN_SUMMARY]
    )
    top_tags = ", ".join(
        f"{k}:{v}" for k, v in sorted(by_tag.items(), key=lambda x: -x[1])[:MAX_PROJECTS_IN_SUMMARY]
    )
    return f"total: {total}\nprojects: {top_projects or 'n/a'}\ntags: {top_tags or 'n/a'}"


def _start_process(args: List[str]) -> str:
    """Start a new subprocess session."""
    session_id = uuid.uuid4().hex
    cmd = ["python3", "-u", "-m", "scalpel.tools.ai_plan_tasks"] + args
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    
    logger.info(f"Starting session {session_id[:8]} with args: {args}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            env=env,
        )
    except Exception as e:
        logger.error(f"Failed to start process: {e}")
        raise
    
    q: "queue.Queue[str]" = queue.Queue(maxsize=QUEUE_MAX_SIZE)

    def _reader(stream, prefix: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                try:
                    q.put(prefix + line.rstrip("\n"), timeout=1.0)
                except queue.Full:
                    logger.warning(f"Queue full for session {session_id[:8]}, dropping output")
        except Exception as e:
            logger.error(f"Reader error for session {session_id[:8]}: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    threading.Thread(target=_reader, args=(proc.stdout, ""), daemon=True).start()
    threading.Thread(target=_reader, args=(proc.stderr, "[stderr] "), daemon=True).start()

    with SESSIONS_LOCK:
        SESSIONS[session_id] = {
            "proc": proc,
            "queue": q,
            "cmd": cmd,
            "created": time.time()
        }
    
    return session_id


def _get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID."""
    with SESSIONS_LOCK:
        return SESSIONS.get(session_id)


def _cleanup_session(session_id: str) -> None:
    """Cleanup and remove a session."""
    with SESSIONS_LOCK:
        sess = SESSIONS.pop(session_id, None)
        if sess:
            proc = sess.get("proc")
            if proc and proc.poll() is None:
                logger.info(f"Terminating process for session {session_id[:8]}")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing process for session {session_id[:8]}")
                    proc.kill()


def _cleanup_stale_sessions() -> None:
    """Remove sessions that have exceeded timeout."""
    with SESSIONS_LOCK:
        now = time.time()
        stale = []
        for sid, sess in SESSIONS.items():
            age = now - sess.get('created', now)
            proc = sess.get('proc')
            # Clean up if timed out or process is dead
            if age > SESSION_TIMEOUT or (proc and proc.poll() is not None):
                stale.append(sid)
        
        for sid in stale:
            logger.info(f"Cleaning up stale session {sid[:8]}")
            sess = SESSIONS.pop(sid, None)
            if sess:
                proc = sess.get('proc')
                if proc and proc.poll() is None:
                    proc.terminate()


def _shutdown_handler(signum, frame) -> None:
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, cleaning up...")
    with SESSIONS_LOCK:
        for sid, sess in list(SESSIONS.items()):
            proc = sess.get('proc')
            if proc and proc.poll() is None:
                logger.info(f"Terminating session {sid[:8]}")
                proc.terminate()
        SESSIONS.clear()
    logger.info("Shutdown complete")
    sys.exit(0)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", "0"))
            
            # Check payload size
            if length > MAX_PAYLOAD_SIZE:
                _error_response(self, "Payload too large", "PAYLOAD_TOO_LARGE", 413)
                return
            
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception as e:
                logger.warning(f"Invalid JSON in /run: {e}")
                _error_response(self, "Invalid JSON", "INVALID_JSON", 400)
                return

            args = body.get("args")
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
                _error_response(self, "args must be list[str]", "INVALID_ARGS_TYPE", 400)
                return

            # Validate arguments for security
            valid, error_msg = _validate_args(args)
            if not valid:
                logger.warning(f"Invalid arguments rejected: {error_msg}")
                _error_response(self, error_msg or "Invalid arguments", "INVALID_ARGUMENTS", 400)
                return

            # Check session limit
            with SESSIONS_LOCK:
                if len(SESSIONS) >= MAX_SESSIONS:
                    _error_response(self, "Too many active sessions", "SESSION_LIMIT", 429)
                    return

            # Get payload preview
            payload = ""
            try:
                payload_cmd = ["python3", "-u", "-m", "scalpel.tools.ai_plan_tasks"] + args + ["--print-payload"]
                payload = subprocess.check_output(
                    payload_cmd,
                    cwd=str(ROOT),
                    text=True,
                    stderr=subprocess.STDOUT,
                    timeout=10
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Payload command failed: {e.output}")
                payload = ""
            except subprocess.TimeoutExpired:
                logger.error("Payload command timed out")
                payload = ""
            except Exception as e:
                logger.error(f"Unexpected error getting payload: {e}")
                payload = ""

            try:
                session_id = _start_process(args)
            except Exception as e:
                logger.error(f"Failed to start process: {e}")
                _error_response(self, "Failed to start process", "PROCESS_START_FAILED", 500)
                return

            sess = _get_session(session_id)
            _json_response(
                self,
                {
                    "session_id": session_id,
                    "cmd": sess["cmd"] if sess else [],
                    "payload": payload,
                    "selection_summary": _selection_summary_from_payload(payload),
                },
                status=200,
            )
            return

        if self.path == "/input":
            length = int(self.headers.get("Content-Length", "0"))
            
            if length > MAX_PAYLOAD_SIZE:
                _error_response(self, "Payload too large", "PAYLOAD_TOO_LARGE", 413)
                return
            
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception as e:
                logger.warning(f"Invalid JSON in /input: {e}")
                _error_response(self, "Invalid JSON", "INVALID_JSON", 400)
                return
            
            session_id = body.get("session_id")
            text = body.get("text", "")
            
            if not isinstance(session_id, str) or not session_id:
                _error_response(self, "Missing session_id", "MISSING_SESSION_ID", 400)
                return
            
            sess = _get_session(session_id)
            if not sess:
                _error_response(self, "Unknown session_id", "UNKNOWN_SESSION", 404)
                return
            
            proc = sess.get("proc")
            if proc and proc.stdin and proc.poll() is None:
                try:
                    proc.stdin.write(str(text) + "\n")
                    proc.stdin.flush()
                except Exception as e:
                    logger.error(f"Failed to write to stdin for session {session_id[:8]}: {e}")
                    _error_response(self, "Failed to write to stdin", "STDIN_WRITE_FAILED", 500)
                    return
            else:
                _error_response(self, "Process not running", "PROCESS_NOT_RUNNING", 400)
                return
            
            _json_response(self, {"ok": True}, status=200)
            return

        if self.path == "/stop":
            length = int(self.headers.get("Content-Length", "0"))
            
            if length > MAX_PAYLOAD_SIZE:
                _error_response(self, "Payload too large", "PAYLOAD_TOO_LARGE", 413)
                return
            
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception as e:
                logger.warning(f"Invalid JSON in /stop: {e}")
                _error_response(self, "Invalid JSON", "INVALID_JSON", 400)
                return
            
            session_id = body.get("session_id")
            if not isinstance(session_id, str) or not session_id:
                _error_response(self, "Missing session_id", "MISSING_SESSION_ID", 400)
                return
            
            sess = _get_session(session_id)
            if not sess:
                _error_response(self, "Unknown session_id", "UNKNOWN_SESSION", 404)
                return
            
            _cleanup_session(session_id)
            _json_response(self, {"ok": True}, status=200)
            return

        _error_response(self, "Not found", "NOT_FOUND", 404)

    def do_GET(self) -> None:
        if not self.path.startswith("/stream"):
            _error_response(self, "Not found", "NOT_FOUND", 404)
            return
        
        query = self.path.split("?", 1)[-1] if "?" in self.path else ""
        params = {}
        for part in query.split("&"):
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        
        session_id = params.get("id")
        if not session_id:
            _error_response(self, "Missing id parameter", "MISSING_ID", 400)
            return
        
        sess = _get_session(session_id)
        if not sess:
            _error_response(self, "Unknown session_id", "UNKNOWN_SESSION", 404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        q: "queue.Queue[str]" = sess["queue"]
        proc = sess["proc"]
        
        try:
            while True:
                try:
                    line = q.get(timeout=STREAM_TIMEOUT)
                    data = line.replace("\r", "")
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    if proc.poll() is not None:
                        break
                except Exception as e:
                    logger.error(f"Stream error for session {session_id[:8]}: {e}")
                    break
            
            self.wfile.write(b"event: done\ndata: done\n\n")
            self.wfile.flush()
        except Exception as e:
            logger.error(f"Failed to send completion event: {e}")
        finally:
            _cleanup_session(session_id)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Suppress default HTTP logging, we use structured logging
        return


def _cleanup_loop() -> None:
    """Background thread to periodically clean up stale sessions."""
    while True:
        time.sleep(60)  # Run every minute
        try:
            _cleanup_stale_sessions()
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")


def main() -> None:
    # Setup signal handlers
    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
    cleanup_thread.start()
    
    # Start server
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    logger.info(f"Server listening on http://{HOST}:{PORT}")
    logger.info(f"Resource limits: max_sessions={MAX_SESSIONS}, session_timeout={SESSION_TIMEOUT}s")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        _shutdown_handler(None, None)


if __name__ == "__main__":
    main()