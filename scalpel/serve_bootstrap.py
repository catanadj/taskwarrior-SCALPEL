from __future__ import annotations

import json
from typing import Any


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
        "    flushTimer = setTimeout(() => { void flushNow(false); }, 60);\n"
        "  }\n"
        "  function takePending(){\n"
        "    const values = pendingValues;\n"
        "    const del = Array.from(pendingDelete);\n"
        "    pendingValues = {};\n"
        "    pendingDelete = new Set();\n"
        "    if (!Object.keys(values).length && !del.length) return null;\n"
        "    return { values, del, body: JSON.stringify({ values, delete: del }) };\n"
        "  }\n"
        "  function restorePending(batch){\n"
        "    if (!batch) return;\n"
        "    for (const [k, v] of Object.entries(batch.values || {})) pendingValues[k] = v;\n"
        "    for (const k of (batch.del || [])) pendingDelete.add(k);\n"
        "  }\n"
        "  async function flushNow(keepalive){\n"
        "    if (flushTimer){ clearTimeout(flushTimer); flushTimer = 0; }\n"
        "    const batch = takePending();\n"
        "    if (!batch) return;\n"
        "    const body = batch.body;\n"
        "    if (keepalive) {\n"
        "      try {\n"
        "        if (typeof navigator !== 'undefined' && navigator && typeof navigator.sendBeacon === 'function') {\n"
        "          const blob = new Blob([body], { type: 'application/json' });\n"
        "          if (navigator.sendBeacon('/client-state', blob)) return;\n"
        "        }\n"
        "      } catch (_) {}\n"
        "    }\n"
        "    try {\n"
        "      await fetch('/client-state', {\n"
        "        method: 'POST',\n"
        "        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },\n"
        "        credentials: 'same-origin',\n"
        "        cache: 'no-store',\n"
        "        keepalive: !!keepalive,\n"
        "        body,\n"
        "      });\n"
        "      return;\n"
        "    } catch (_) {\n"
        "      restorePending(batch);\n"
        "    }\n"
        "  }\n"
        "  function flushForPageExit(){ void flushNow(true); }\n"
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
        "  g.__scalpel_kvFlush = flushNow;\n"
        "  if (typeof window !== 'undefined' && window && typeof window.addEventListener === 'function') {\n"
        "    window.addEventListener('pagehide', flushForPageExit);\n"
        "    window.addEventListener('beforeunload', flushForPageExit);\n"
        "  }\n"
        "  if (typeof document !== 'undefined' && document && typeof document.addEventListener === 'function') {\n"
        "    document.addEventListener('visibilitychange', () => {\n"
        "      if (document.visibilityState === 'hidden') flushForPageExit();\n"
        "    });\n"
        "  }\n"
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


__all__ = ["_escape_script_json", "_inject_serve_bootstrap", "_serve_bootstrap_script"]
