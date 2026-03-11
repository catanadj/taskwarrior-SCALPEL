from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass, field
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.request import Request, urlopen

from scalpel import serve
from scalpel.render.inline import build_html


def _free_port() -> int:
    try:
        sock = socket.socket()
    except PermissionError as ex:
        raise unittest.SkipTest("local socket bind not permitted in this environment") from ex
    with sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json_request(url: str, *, method: str = "GET", body: object | None = None) -> dict[str, Any]:
    payload = None
    headers = {"Accept": "application/json"}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=payload, method=method, headers=headers)
    with urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_until(pred: Any, *, timeout: float = 5.0, interval: float = 0.05) -> Any:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = pred()
        except Exception as ex:  # pragma: no cover - retry loop
            last = ex
            time.sleep(interval)
            continue
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"condition not met before timeout; last={last!r}")


def _make_payload(generated_at: str) -> dict[str, Any]:
    return {
        "cfg": {
            "view_key": "serve-browser-e2e",
            "view_start_ms": 1767225600000,
            "days": 7,
            "px_per_min": 2,
            "work_start_min": 360,
            "work_end_min": 1380,
            "snap_min": 10,
            "default_duration_min": 10,
            "max_infer_duration_min": 480,
            "tz": "UTC",
            "display_tz": "UTC",
        },
        "tasks": [],
        "meta": {"generated_at": generated_at},
    }


def _make_task_editor_payload(generated_at: str) -> dict[str, Any]:
    payload = _make_payload(generated_at)
    payload["tasks"] = [
        {
            "id": 42,
            "uuid": "12345678-1111-2222-3333-abcdefabcdef",
            "description": "Editor task",
            "status": "pending",
            "project": "work",
            "tags": ["deep"],
            "priority": "M",
            "scheduled_ms": 1767258000000,
            "due_ms": 1767261600000,
            "duration_min": 60,
        }
    ]
    return payload


@dataclass
class _BrowserServeHarness:
    root: Path
    token: str = "abc123"
    out_file: Path = field(init=False)
    payload_count: int = field(default=0, init=False)
    holder: dict[str, ThreadingHTTPServer] = field(default_factory=dict, init=False)
    thread: threading.Thread | None = field(default=None, init=False)
    server_error: BaseException | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.out_file = self.root / "serve.html"
        self.out_file.write_text(build_html(self._payload_for(0)), encoding="utf-8")

    def _args(self) -> argparse.Namespace:
        return argparse.Namespace(
            host="127.0.0.1",
            port=0,
            serve_token=self.token,
            allow_remote=False,
            no_open=True,
        )

    def _render_once(self, _args: argparse.Namespace, out_path: str) -> dict[str, Any]:
        self.payload_count += 1
        payload = self._payload_for(self.payload_count)
        Path(out_path).write_text(build_html(payload), encoding="utf-8")
        return payload

    @staticmethod
    def _task_lookup(uuid_query: str) -> dict[str, Any]:
        return {
            "task": {"uuid": "12345678-1111-2222-3333-abcdefabcdef", "description": f"Task {uuid_query}"},
            "matched": 1,
            "exact": True,
        }

    @staticmethod
    def _timew_export(day: str) -> dict[str, Any]:
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

    def _server_factory(self, addr: tuple[str, int], handler: type) -> ThreadingHTTPServer:
        server_obj = ThreadingHTTPServer(addr, handler)
        self.holder["server"] = server_obj
        return server_obj

    def _payload_for(self, count: int) -> dict[str, Any]:
        return _make_payload(f"gen-{count}")

    def start(self) -> "_BrowserServeHarness":
        initial_payload = self._payload_for(0)

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
            except BaseException as ex:  # pragma: no cover - surfaced through polling
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
        server_obj = self.holder.get("server")
        if server_obj is not None:
            server_obj.shutdown()
        if self.thread is not None:
            self.thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        host, port = self.holder["server"].server_address[:2]
        return f"http://{host}:{int(port)}"


class _HeadlessChromium:
    def __init__(self, chromium_bin: str) -> None:
        self.chromium_bin = chromium_bin
        self.port = _free_port()
        self.proc: subprocess.Popen[str] | None = None
        self.base = f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "_HeadlessChromium":
        self.proc = subprocess.Popen(
            [
                self.chromium_bin,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--remote-debugging-port={self.port}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            _wait_until(lambda: _json_request(self.base + "/json/version").get("webSocketDebuggerUrl"), timeout=5.0)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


def _run_cdp_node_script(*, node_bin: str, devtools_port: int, page_url: str, script: str) -> None:
    env = dict(os.environ)
    env["SCALPEL_CDP_PORT"] = str(devtools_port)
    env["SCALPEL_PAGE_URL"] = page_url
    proc = subprocess.run(
        [node_bin, "-e", script],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"browser contract failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def _run_cdp_browser_contract(*, node_bin: str, devtools_port: int, page_url: str) -> None:
    script = r"""
const port = String(process.env.SCALPEL_CDP_PORT || "");
const pageUrl = String(process.env.SCALPEL_PAGE_URL || "");

async function httpJson(path, init = {}) {
  const resp = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`HTTP ${resp.status} for ${path}: ${txt}`);
  }
  return await resp.json();
}

async function openPageTarget(url) {
  return await httpJson(`/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
}

async function main() {
  const target = await openPageTarget(pageUrl);
  if (!target.webSocketDebuggerUrl) throw new Error("missing webSocketDebuggerUrl");

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let seq = 0;
  const pending = new Map();

  ws.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data || ""));
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else p.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const out = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (out.exceptionDetails) return null;
    return out.result ? out.result.value : null;
  };

  const waitFor = async (label, fn, timeoutMs = 10000) => {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await fn();
      } catch (_) {
        last = null;
      }
      if (last) return last;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
  };

  await send("Page.enable");
  await send("Runtime.enable");

  await waitFor("initial UI", () =>
    evaluate("document.readyState === 'complete' && !!document.getElementById('btnRefresh')")
  );

  await evaluate(`
    (() => {
      const more = document.getElementById('btnMoreActions');
      if (more) more.click();
      const btn = document.getElementById('btnNotes');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("notes open", () =>
    evaluate(`
      (() => {
        const wrap = document.getElementById('notesWrap');
        const root = document.querySelector('.rsec[data-rsec="actions"]');
        const hdr = root ? root.querySelector('[data-rsec-toggle="actions"]') : null;
        return !!(
          wrap && wrap.style.display === 'block' &&
          root && root.classList.contains('open') &&
          hdr && hdr.getAttribute('aria-expanded') === 'true'
        );
      })()
    `)
  );

  const before = await evaluate(`
    (() => JSON.parse(document.getElementById('tw-data').textContent).meta.generated_at)()
  `);
  if (before !== "gen-0") throw new Error(`expected gen-0 before refresh, got ${before}`);

  await new Promise((r) => setTimeout(r, 180));

  await evaluate(`
    (() => {
      const more = document.getElementById('btnMoreActions');
      if (more) more.click();
      const btn = document.getElementById('btnRefresh');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("refreshed payload", () =>
    evaluate(`
      (() => {
        try {
          return JSON.parse(document.getElementById('tw-data').textContent).meta.generated_at === 'gen-1';
        } catch (_) {
          return false;
        }
      })()
    `)
  );

  await waitFor("notes persisted", () =>
    evaluate(`
      (() => {
        const wrap = document.getElementById('notesWrap');
        const btn = document.getElementById('btnNotes');
        const root = document.querySelector('.rsec[data-rsec="actions"]');
        return !!(
          wrap && wrap.style.display === 'block' &&
          btn && btn.classList.contains('on') &&
          root && root.classList.contains('open')
        );
      })()
    `)
  );

  try { ws.close(); } catch (_) {}
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
"""
    _run_cdp_node_script(node_bin=node_bin, devtools_port=devtools_port, page_url=page_url, script=script)


def _run_cdp_task_editor_contract(*, node_bin: str, devtools_port: int, page_url: str) -> None:
    script = r"""
const port = String(process.env.SCALPEL_CDP_PORT || "");
const pageUrl = String(process.env.SCALPEL_PAGE_URL || "");

async function httpJson(path, init = {}) {
  const resp = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`HTTP ${resp.status} for ${path}: ${txt}`);
  }
  return await resp.json();
}

async function openPageTarget(url) {
  return await httpJson(`/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
}

async function main() {
  const target = await openPageTarget(pageUrl);
  if (!target.webSocketDebuggerUrl) throw new Error("missing webSocketDebuggerUrl");

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let seq = 0;
  const pending = new Map();

  ws.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data || ""));
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else p.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const out = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (out.exceptionDetails) return null;
    return out.result ? out.result.value : null;
  };

  const waitFor = async (label, fn, timeoutMs = 10000) => {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await fn();
      } catch (_) {
        last = null;
      }
      if (last) return last;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
  };

  await send("Page.enable");
  await send("Runtime.enable");

  await waitFor("task event", () =>
    evaluate(`
      (() => document.readyState === 'complete'
        && !!document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]'))()
    `)
  );

  await evaluate(`
    (() => {
      const el = document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]');
      if (!el) return false;
      el.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
      return true;
    })()
  `);

  await waitFor("task editor modal", () =>
    evaluate(`
      (() => {
        const modal = document.getElementById('taskEditModal');
        const meta = document.getElementById('taskEditMeta');
        const udaField = document.querySelector('#taskEditGrid [data-field-key="review_status"]');
        return !!(
          modal && modal.style.display === 'flex' &&
          meta && meta.textContent.includes('fresh task export') &&
          udaField && udaField.value === 'draft'
        );
      })()
    `)
  );

  await evaluate(`
    (() => {
      const proj = document.querySelector('#taskEditGrid [data-field-key="project"]');
      const review = document.querySelector('#taskEditGrid [data-field-key="review_status"]');
      if (proj) proj.value = 'ops';
      if (review) review.value = 'approved';
      const addBtn = document.getElementById('taskEditAddCustom');
      if (addBtn) addBtn.click();
      const key = document.querySelector('#taskEditCustomRows [data-custom-idx="1"][data-custom-kind="key"]');
      const val = document.querySelector('#taskEditCustomRows [data-custom-idx="1"][data-custom-kind="val"]');
      if (key) key.value = 'custom_flag';
      if (val) val.value = 'yes';
      const save = document.getElementById('taskEditSave');
      if (save) save.click();
      return true;
    })()
  `);

  await waitFor("queued modify command", () =>
    evaluate(`
      (() => {
        const modal = document.getElementById('taskEditModal');
        const commands = String((document.getElementById('commands') || {}).textContent || '');
        return !!(
          modal && modal.style.display === 'none' &&
          commands.includes('task 12345678 modify') &&
          commands.includes('project:ops') &&
          commands.includes('review_status:approved') &&
          commands.includes('custom_flag:yes')
        );
      })()
    `)
  );

  try { ws.close(); } catch (_) {}
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
    """
    _run_cdp_node_script(node_bin=node_bin, devtools_port=devtools_port, page_url=page_url, script=script)


def _run_cdp_apply_contract(*, node_bin: str, devtools_port: int, page_url: str) -> None:
    script = r"""
const port = String(process.env.SCALPEL_CDP_PORT || "");
const pageUrl = String(process.env.SCALPEL_PAGE_URL || "");

async function httpJson(path, init = {}) {
  const resp = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`HTTP ${resp.status} for ${path}: ${txt}`);
  }
  return await resp.json();
}

async function openPageTarget(url) {
  return await httpJson(`/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
}

async function main() {
  const target = await openPageTarget(pageUrl);
  if (!target.webSocketDebuggerUrl) throw new Error("missing webSocketDebuggerUrl");

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let seq = 0;
  const pending = new Map();

  ws.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data || ""));
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else p.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const out = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (out.exceptionDetails) return null;
    return out.result ? out.result.value : null;
  };

  const waitFor = async (label, fn, timeoutMs = 12000) => {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await fn();
      } catch (_) {
        last = null;
      }
      if (last) return last;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
  };

  await send("Page.enable");
  await send("Runtime.enable");

  await waitFor("task event", () =>
    evaluate(`
      (() => document.readyState === 'complete'
        && !!document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]'))()
    `)
  );

  await evaluate(`
    (() => {
      window.confirm = () => true;
      return true;
    })()
  `);

  await evaluate(`
    (() => {
      const el = document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]');
      if (!el) return false;
      el.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
      return true;
    })()
  `);

  await waitFor("task editor modal", () =>
    evaluate(`(() => {
      const modal = document.getElementById('taskEditModal');
      return !!(modal && modal.style.display === 'flex');
    })()`)
  );

  await evaluate(`
    (() => {
      const proj = document.querySelector('#taskEditGrid [data-field-key="project"]');
      if (proj) proj.value = 'ops';
      const save = document.getElementById('taskEditSave');
      if (save) save.click();
      return true;
    })()
  `);

  await waitFor("queued modify command", () =>
    evaluate(`(() => String((document.getElementById('commands') || {}).textContent || '').includes('task 12345678 modify project:ops'))()`)
  );

  await evaluate(`
    (() => {
      const btn = document.getElementById('btnApplyChanges');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("apply modal", () =>
    evaluate(`(() => {
      const modal = document.getElementById('applyModal');
      const summary = document.getElementById('applySummary');
      return !!(modal && modal.style.display === 'flex' && summary && summary.textContent.includes('1 command'));
    })()`)
  );

  await evaluate(`
    (() => {
      const btn = document.getElementById('applyConfirm');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("commands cleared after apply reload", () =>
    evaluate(`(() => {
      const count = String((document.getElementById('cmdCount') || {}).textContent || '');
      const commands = String((document.getElementById('commands') || {}).textContent || '');
      return !!(count.includes('0 total') && commands.includes('# None'));
    })()`)
  );

  try { ws.close(); } catch (_) {}
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
"""
    _run_cdp_node_script(node_bin=node_bin, devtools_port=devtools_port, page_url=page_url, script=script)


def _run_cdp_apply_failure_badge_contract(*, node_bin: str, devtools_port: int, page_url: str) -> None:
    script = r"""
const port = String(process.env.SCALPEL_CDP_PORT || "");
const pageUrl = String(process.env.SCALPEL_PAGE_URL || "");

async function httpJson(path, init = {}) {
  const resp = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`HTTP ${resp.status} for ${path}: ${txt}`);
  }
  return await resp.json();
}

async function openPageTarget(url) {
  return await httpJson(`/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
}

async function main() {
  const target = await openPageTarget(pageUrl);
  if (!target.webSocketDebuggerUrl) throw new Error("missing webSocketDebuggerUrl");

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let seq = 0;
  const pending = new Map();

  ws.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data || ""));
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else p.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const out = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (out.exceptionDetails) return null;
    return out.result ? out.result.value : null;
  };

  const waitFor = async (label, fn, timeoutMs = 12000) => {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await fn();
      } catch (_) {
        last = null;
      }
      if (last) return last;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
  };

  await send("Page.enable");
  await send("Runtime.enable");

  await waitFor("task event", () =>
    evaluate(`
      (() => document.readyState === 'complete'
        && !!document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]'))()
    `)
  );

  await evaluate(`
    (() => {
      window.confirm = () => true;
      const el = document.querySelector('.evt[data-uuid="12345678-1111-2222-3333-abcdefabcdef"]');
      if (!el) return false;
      el.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
      return true;
    })()
  `);

  await waitFor("task editor modal", () =>
    evaluate(`(() => {
      const modal = document.getElementById('taskEditModal');
      return !!(modal && modal.style.display === 'flex');
    })()`)
  );

  await evaluate(`
    (() => {
      const proj = document.querySelector('#taskEditGrid [data-field-key="project"]');
      if (proj) proj.value = 'ops';
      const save = document.getElementById('taskEditSave');
      if (save) save.click();
      return true;
    })()
  `);

  await waitFor("queued modify command", () =>
    evaluate(`(() => String((document.getElementById('commands') || {}).textContent || '').includes('task 12345678 modify project:ops'))()`)
  );

  await evaluate(`
    (() => {
      const btn = document.getElementById('btnApplyChanges');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("apply modal", () =>
    evaluate(`(() => {
      const modal = document.getElementById('applyModal');
      return !!(modal && modal.style.display === 'flex');
    })()`)
  );

  await evaluate(`
    (() => {
      const btn = document.getElementById('applyConfirm');
      if (btn) btn.click();
      return true;
    })()
  `);

  await waitFor("error badge", () =>
    evaluate(`(() => {
      const badge = document.querySelector('.apply-badge.is-err');
      const summary = String((document.getElementById('applySummary') || {}).textContent || '');
      const log = String((document.getElementById('applyResult') || {}).textContent || '');
      return !!(
        badge &&
        badge.textContent.includes('ERR') &&
        summary.includes('Applied 0/1') &&
        summary.includes('1 failed') &&
        summary.includes('stopped at #1') &&
        log.includes('failed')
      );
    })()`)
  );

  try { ws.close(); } catch (_) {}
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
"""
    _run_cdp_node_script(node_bin=node_bin, devtools_port=devtools_port, page_url=page_url, script=script)


def _run_cdp_timew_day_actions_contract(*, node_bin: str, devtools_port: int, page_url: str) -> None:
    script = r"""
const port = String(process.env.SCALPEL_CDP_PORT || "");
const pageUrl = String(process.env.SCALPEL_PAGE_URL || "");

async function httpJson(path, init = {}) {
  const resp = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`HTTP ${resp.status} for ${path}: ${txt}`);
  }
  return await resp.json();
}

async function openPageTarget(url) {
  return await httpJson(`/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
}

async function main() {
  const target = await openPageTarget(pageUrl);
  if (!target.webSocketDebuggerUrl) throw new Error("missing webSocketDebuggerUrl");

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let seq = 0;
  const pending = new Map();

  ws.onmessage = (ev) => {
    const msg = JSON.parse(String(ev.data || ""));
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else p.resolve(msg.result);
    }
  };

  await new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const out = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (out.exceptionDetails) return null;
    return out.result ? out.result.value : null;
  };

  const waitFor = async (label, fn, timeoutMs = 10000) => {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await fn();
      } catch (_) {
        last = null;
      }
      if (last) return last;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error(`timeout waiting for ${label}; last=${JSON.stringify(last)}`);
  };

  await send("Page.enable");
  await send("Runtime.enable");

  await waitFor("calendar day header", () =>
    evaluate(`
      (() => document.readyState === 'complete'
        && !!document.querySelector('.day-h[data-day-index="0"]'))()
    `)
  );

  await evaluate(`
    (() => {
      const header = document.querySelector('.day-h[data-day-index="0"]');
      if (!header) return false;
      header.dispatchEvent(new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: 120,
        clientY: 120
      }));
      return true;
    })()
  `);

  await waitFor("day actions menu", () =>
    evaluate(`
      (() => {
        const btn = document.querySelector('.day-ctx-menu button[data-act="show"]');
        return !!(btn && !btn.closest('[hidden]'));
      })()
    `)
  );

  await evaluate(`
    (() => {
      const btn = document.querySelector('.day-ctx-menu button[data-act="show"]');
      if (!btn) return false;
      btn.click();
      return true;
    })()
  `);

  await waitFor("timew note visible", () =>
    evaluate(`
      (() => {
        const note = document.querySelector('.day-col[data-day-index="0"] .note .ntxt');
        const status = String((document.getElementById('status') || {}).textContent || '');
        return !!(
          note &&
          note.textContent.includes('[timew] Deep work') &&
          note.textContent.includes('#focus') &&
          status.includes('Timewarrior notes updated for 2026-01-01')
        );
      })()
    `)
  );

  const beforeReload = await evaluate(`
    (() => {
      const note = document.querySelector('.day-col[data-day-index="0"] .note .ntxt');
      return note ? note.textContent : '';
    })()
  `);
  if (!String(beforeReload || "").includes('[timew] Deep work')) {
    throw new Error(`expected imported timew note before reload, got ${beforeReload}`);
  }

  await evaluate(`(() => { location.reload(); return true; })()`);

  await waitFor("timew note after reload", () =>
    evaluate(`
      (() => {
        const note = document.querySelector('.day-col[data-day-index="0"] .note .ntxt');
        return !!(note && note.textContent.includes('[timew] Deep work') && note.textContent.includes('#focus'));
      })()
    `)
  );

  try { ws.close(); } catch (_) {}
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
"""
    _run_cdp_node_script(node_bin=node_bin, devtools_port=devtools_port, page_url=page_url, script=script)


@dataclass
class _TaskEditorServeHarness(_BrowserServeHarness):
    def _payload_for(self, count: int) -> dict[str, Any]:
        return _make_task_editor_payload(f"gen-{count}")

    @staticmethod
    def _task_lookup(uuid_query: str) -> dict[str, Any]:
        return {
            "task": {
                "id": 42,
                "uuid": "12345678-1111-2222-3333-abcdefabcdef",
                "description": f"Editor task {uuid_query}",
                "status": "pending",
                "project": "work",
                "tags": ["deep"],
                "priority": "M",
                "review_status": "draft",
                "scheduled_ms": 1767258000000,
                "due_ms": 1767261600000,
                "duration_min": 60,
            },
            "matched": 1,
            "exact": True,
        }


class TestServeBrowserLiveContract(unittest.TestCase):
    def test_live_browser_refresh_preserves_notes_visibility(self) -> None:
        chromium_bin = shutil.which("chromium")
        node_bin = shutil.which("node")
        if not chromium_bin or not node_bin:
            raise unittest.SkipTest("chromium/node not available")

        with tempfile.TemporaryDirectory() as td:
            harness = _BrowserServeHarness(Path(td)).start()
            try:
                with _HeadlessChromium(chromium_bin) as browser:
                    _run_cdp_browser_contract(
                        node_bin=node_bin,
                        devtools_port=browser.port,
                        page_url=harness.base_url + "/?token=abc123",
                    )
                self.assertGreaterEqual(harness.payload_count, 1)
            finally:
                harness.stop()

    def test_live_browser_task_editor_queues_modify_command(self) -> None:
        chromium_bin = shutil.which("chromium")
        node_bin = shutil.which("node")
        if not chromium_bin or not node_bin:
            raise unittest.SkipTest("chromium/node not available")

        with tempfile.TemporaryDirectory() as td:
            harness = _TaskEditorServeHarness(Path(td)).start()
            try:
                with _HeadlessChromium(chromium_bin) as browser:
                    _run_cdp_task_editor_contract(
                        node_bin=node_bin,
                        devtools_port=browser.port,
                        page_url=harness.base_url + "/?token=abc123",
                    )
            finally:
                harness.stop()

    def test_live_browser_apply_executes_and_clears_queue(self) -> None:
        chromium_bin = shutil.which("chromium")
        node_bin = shutil.which("node")
        if not chromium_bin or not node_bin:
            raise unittest.SkipTest("chromium/node not available")

        seen: list[list[object]] = []

        def fake_apply(commands: list[object], *, selected: list[object] | None = None) -> dict[str, Any]:
            seen.append(list(commands))
            self.assertEqual(selected, [0])
            return {
                "ok": True,
                "applied": 1,
                "selected": 1,
                "stopped_after_index": None,
                "commands": [
                    {
                        "index": 0,
                        "kind": "modify",
                        "line": str(commands[0]),
                        "argv": ["task", "12345678", "modify", "project:ops"],
                        "ok": True,
                        "returncode": 0,
                        "stdout": "",
                        "stderr": "",
                        "error": None,
                    }
                ],
            }

        with tempfile.TemporaryDirectory() as td:
            harness = _TaskEditorServeHarness(Path(td)).start()
            try:
                with patch("scalpel.serve.execute_apply_commands", side_effect=fake_apply):
                    with _HeadlessChromium(chromium_bin) as browser:
                        _run_cdp_apply_contract(
                            node_bin=node_bin,
                            devtools_port=browser.port,
                            page_url=harness.base_url + "/?token=abc123",
                        )
                self.assertEqual(len(seen), 1)
                self.assertIn("task 12345678 modify project:ops", str(seen[0][0]))
                self.assertGreaterEqual(harness.payload_count, 1)
            finally:
                harness.stop()

    def test_live_browser_apply_failure_shows_error_badge(self) -> None:
        chromium_bin = shutil.which("chromium")
        node_bin = shutil.which("node")
        if not chromium_bin or not node_bin:
            raise unittest.SkipTest("chromium/node not available")

        def fake_apply(commands: list[object], *, selected: list[object] | None = None) -> dict[str, Any]:
            self.assertEqual(selected, [0])
            return {
                "ok": False,
                "applied": 0,
                "selected": 1,
                "stopped_after_index": 0,
                "commands": [
                    {
                        "index": 0,
                        "kind": "modify",
                        "line": str(commands[0]),
                        "argv": ["task", "12345678", "modify", "project:ops"],
                        "ok": False,
                        "returncode": 1,
                        "stdout": "",
                        "stderr": "boom",
                        "error": "Taskwarrior command failed with exit 1.",
                    }
                ],
            }

        with tempfile.TemporaryDirectory() as td:
            harness = _TaskEditorServeHarness(Path(td)).start()
            try:
                with patch("scalpel.serve.execute_apply_commands", side_effect=fake_apply):
                    with _HeadlessChromium(chromium_bin) as browser:
                        _run_cdp_apply_failure_badge_contract(
                            node_bin=node_bin,
                            devtools_port=browser.port,
                            page_url=harness.base_url + "/?token=abc123",
                        )
            finally:
                harness.stop()

    def test_live_browser_timew_day_actions_persist_notes(self) -> None:
        chromium_bin = shutil.which("chromium")
        node_bin = shutil.which("node")
        if not chromium_bin or not node_bin:
            raise unittest.SkipTest("chromium/node not available")

        with tempfile.TemporaryDirectory() as td:
            harness = _BrowserServeHarness(Path(td)).start()
            try:
                with _HeadlessChromium(chromium_bin) as browser:
                    _run_cdp_timew_day_actions_contract(
                        node_bin=node_bin,
                        devtools_port=browser.port,
                        page_url=harness.base_url + "/?token=abc123",
                    )
            finally:
                harness.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
