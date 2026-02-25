# scalpel/render/js/persist.py
from __future__ import annotations

JS_PART = r'''  // -----------------------------
  // Persistence helpers (localStorage)
  // -----------------------------
  function _clampInt(v, lo, hi) {
    const n = Math.floor(Number(v));
    if (!Number.isFinite(n)) return lo;
    return Math.max(lo, Math.min(hi, n));
  }

  function lsGet(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }
  function lsSet(key, val) {
    try { localStorage.setItem(key, String(val)); } catch (_) {}
  }
  function lsDel(key) {
    try { localStorage.removeItem(key); } catch (_) {}
  }
  function lsGetJSON(key, fallback) {
    try {
      const raw = lsGet(key);
      if (!raw) return fallback;
      const obj = JSON.parse(raw);
      return obj == null ? fallback : obj;
    } catch (_) {
      return fallback;
    }
  }
  function lsSetJSON(key, obj) {
    try { lsSet(key, JSON.stringify(obj)); } catch (_) {}
  }

  // View window schema v1
  // Returns an object: { startYmd, futureDays, overdueDays }
  function loadViewWin(key, defObj) {
    const def = Object.assign({}, defObj || {});
    const obj = lsGetJSON(key, null);
    if (!obj || typeof obj !== "object") return def;

    if (typeof obj.startYmd === "string" && /^(\d{4})-(\d{2})-(\d{2})$/.test(obj.startYmd)) {
      def.startYmd = obj.startYmd;
    }
    if (Number.isFinite(Number(obj.futureDays))) def.futureDays = _clampInt(obj.futureDays, 1, 60);
    if (Number.isFinite(Number(obj.overdueDays))) def.overdueDays = _clampInt(obj.overdueDays, 0, 30);
    return def;
  }

  // Persist handshake: signal KV API is ready (splice-safe)
  globalThis.__scalpel_persist_ready = true;
  window.dispatchEvent(new Event("scalpel:persist-ready"));

'''
