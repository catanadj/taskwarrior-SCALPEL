# scalpel/render/js/part01_core.py
from __future__ import annotations

JS_PART = r'''
(() => {
  "use strict";


try { if (typeof globalThis !== "undefined" && !globalThis.__scalpel_phase) globalThis.__scalpel_phase = "boot"; } catch (_) {}


  // Storage wrappers (fallback)
  // Ensures the UI never crashes if persistence injection order changes.
  try {
    const g = (typeof globalThis !== "undefined") ? globalThis : null;
    if (g) {
      g.__scalpel_lsGet = g.__scalpel_lsGet || function(k){ try { return localStorage.getItem(k); } catch(_){ return null; } };
      g.__scalpel_lsSet = g.__scalpel_lsSet || function(k,v){ try { localStorage.setItem(k, String(v)); } catch(_){ } };
      g.__scalpel_lsDel = g.__scalpel_lsDel || function(k){ try { localStorage.removeItem(k); } catch(_){ } };
    }
  } catch (_) {}


  

  // Prefs wrappers (fallback)
  // Prevents blank UI if persist injection order changes.
  try {
    const g = (typeof globalThis !== "undefined") ? globalThis : null;
    if (g) {
      const _prefsKey = function(scope){ const s=(scope==null)?"":String(scope); return s?("scalpel:prefs:"+s):"scalpel:prefs:global"; };
      g.__scalpel_prefsGet = g.__scalpel_prefsGet || function(scope,k,fb){
        try{
          const raw = g.__scalpel_lsGet ? g.__scalpel_lsGet(_prefsKey(scope)) : null;
          if (!raw) return fb;
          const obj = JSON.parse(raw);
          const p = (obj && obj.p && typeof obj.p==="object") ? obj.p : obj;
          return (p && Object.prototype.hasOwnProperty.call(p,k)) ? p[k] : fb;
        }catch(_){ return fb; }
      };
      g.__scalpel_prefsSet = g.__scalpel_prefsSet || function(scope,k,v){
        try{
          const key=_prefsKey(scope);
          let p={};
          const raw = g.__scalpel_lsGet ? g.__scalpel_lsGet(key) : null;
          if (raw){
            try{
              const obj=JSON.parse(raw);
              p = (obj && obj.p && typeof obj.p==="object") ? obj.p : (obj||{});
            }catch(_){}
          }
          p[k]=v;
          const out = JSON.stringify({v:1,p:p});
          if (g.__scalpel_lsSet) g.__scalpel_lsSet(key, out);
          else localStorage.setItem(key, out);
        }catch(_){}
      };
    }
  } catch (_) {}


  // KV wrappers (fallback)
  // Ensures the UI doesn't crash if persist injection order changes.
  try {
    const g = (typeof globalThis !== "undefined") ? globalThis : null;
    if (g) {
      const _ns = (k) => "kv:" + String(k);
      g.__scalpel_kvGet = g.__scalpel_kvGet || function(k, fb){
        try{
          if (typeof g.__scalpel_prefsGet === "function") return g.__scalpel_prefsGet(null, _ns(k), fb);
          if (typeof g.__scalpel_lsGet === "function") return (g.__scalpel_lsGet(String(k)) ?? fb);
          return fb;
        }catch(_){ return fb; }
      };
      g.__scalpel_kvSet = g.__scalpel_kvSet || function(k, v){
        try{
          if (typeof g.__scalpel_prefsSet === "function") { g.__scalpel_prefsSet(null, _ns(k), String(v)); return; }
          if (typeof g.__scalpel_lsSet === "function") { g.__scalpel_lsSet(String(k), String(v)); return; }
          localStorage.setItem(String(k), String(v));
        }catch(_){}
      };
      g.__scalpel_kvDel = g.__scalpel_kvDel || function(k){
        try{
          if (typeof g.__scalpel_prefsSet === "function") { g.__scalpel_prefsSet(null, _ns(k), undefined); return; }
          if (typeof g.__scalpel_lsDel === "function") { g.__scalpel_lsDel(String(k)); return; }
          localStorage.removeItem(String(k));
        }catch(_){}
      };
      g.__scalpel_kvGetJSON = g.__scalpel_kvGetJSON || function(k, fb){
        try{
          const v = g.__scalpel_kvGet(k, null);
          if (v == null) return fb;
          if (typeof v === "object") return v;
          return JSON.parse(String(v));
        }catch(_){ return fb; }
      };
      g.__scalpel_kvSetJSON = g.__scalpel_kvSetJSON || function(k, obj){
        try{
          if (typeof g.__scalpel_prefsSet === "function") { g.__scalpel_prefsSet(null, _ns(k), obj); return; }
          const s = JSON.stringify(obj);
          g.__scalpel_kvSet(k, s);
        }catch(_){}
      };
    }
  } catch (_) {}
function showFatal(msg, err) {
    try {
      const s = document.getElementById("status");
      if (s) s.textContent = msg + (err ? " " + String(err) : "");
      console.error(msg, err);
    } catch (_) {}
  }

  let DATA;
  try {
    DATA = JSON.parse(document.getElementById("tw-data").textContent);
  } catch (e) {
    showFatal("Failed to parse embedded data. Your HTML may be truncated or invalid.", e);
    return;
  }

  // Config (safe default)
  const cfg = (DATA && typeof DATA === "object" && DATA.cfg && typeof DATA.cfg === "object") ? DATA.cfg : {};
  let showNauticalPreview = false;
  const hasNauticalPreview = (DATA && Array.isArray(DATA.tasks)) ? DATA.tasks.some(t => t && t.nautical_preview) : false;

  // -----------------------------
  // Utilities
  // -----------------------------
  const pad2 = (n) => (n < 10 ? "0" + n : "" + n);
  const clamp = (n, lo, hi) => (n < lo ? lo : (n > hi ? hi : n));
  const isNauticalPreviewTask = (t) => !!(t && t.nautical_preview);
  function getNauticalPreviewSourceUuid(t) {
    const raw = t && (
      t.nautical_source_uuid ??
      t.nauticalSourceUuid ??
      t.nautical_source ??
      t.nauticalSource
    );
    const uuid = String(raw || "").trim();
    return uuid || null;
  }
  function isNauticalPreviewForwardFromSource(t) {
    if (!isNauticalPreviewTask(t)) return true;
    const sourceUuid = getNauticalPreviewSourceUuid(t);
    if (!sourceUuid || sourceUuid === t.uuid) return true;

    const sourceTask = (tasksByUuid && typeof tasksByUuid.get === "function") ? tasksByUuid.get(sourceUuid) : null;
    if (!sourceTask || sourceTask.nautical_preview) return true;

    const sourceIv = (typeof effectiveInterval === "function") ? effectiveInterval(sourceUuid) : null;
    if (!sourceIv || !Number.isFinite(sourceIv.dueMs)) return true;

    let previewDueMs = NaN;
    const previewIv = (typeof effectiveInterval === "function") ? effectiveInterval(t.uuid) : null;
    if (previewIv && Number.isFinite(previewIv.dueMs)) previewDueMs = previewIv.dueMs;
    else previewDueMs = Number(t.due_ms);
    if (!Number.isFinite(previewDueMs)) return true;

    // Only show previews strictly after the current source task placement.
    return previewDueMs > sourceIv.dueMs;
  }
  function isTaskVisibleForRender(t) {
    if (!t) return false;
    if (!isNauticalPreviewTask(t)) return true;
    if (!showNauticalPreview) return false;
    return isNauticalPreviewForwardFromSource(t);
  }


  // Timezones
  // - BUCKET_TZ defines day boundaries (day_key, view_start_ms midnight)
  // - DISPLAY_TZ defines how timestamps are presented to the user
  const BUCKET_TZ = (cfg && typeof cfg.tz === "string" && cfg.tz.trim()) ? cfg.tz.trim() : "local";
  const DISPLAY_TZ = (cfg && typeof cfg.display_tz === "string" && cfg.display_tz.trim()) ? cfg.display_tz.trim() : "local";

  const __scalpel_dtf_cache = new Map();
  function _tzNorm(tz){
    const s = String(tz || "").trim();
    if (!s) return "local";
    const u = s.toUpperCase();
    if (u === "Z" || u === "UTC") return "UTC";
    if (u === "LOCAL" || u === "SYSTEM") return "local";
    return s;
  }
  function _isLocalTz(tz){ return _tzNorm(tz) === "local"; }
  function _isUtcTz(tz){ return _tzNorm(tz) === "UTC"; }

  function _dtf(tz, opts){
    const tzn = _tzNorm(tz);
    const key = tzn + "|" + JSON.stringify(opts || {});
    if (__scalpel_dtf_cache.has(key)) return __scalpel_dtf_cache.get(key);
    const o = Object.assign({}, opts || {});
    if (!_isLocalTz(tzn)) o.timeZone = tzn;
    const f = new Intl.DateTimeFormat(undefined, o);
    __scalpel_dtf_cache.set(key, f);
    return f;
  }

  function _parts(ms, tz){
    const tzn = _tzNorm(tz);
    if (_isLocalTz(tzn)){
      const d = new Date(ms);
      return { y:d.getFullYear(), mo:(d.getMonth()+1), d:d.getDate(), hh:d.getHours(), mm:d.getMinutes(), wd:d.getDay(), mon:d.getMonth() };
    }
    if (_isUtcTz(tzn)){
      const d = new Date(ms);
      return { y:d.getUTCFullYear(), mo:(d.getUTCMonth()+1), d:d.getUTCDate(), hh:d.getUTCHours(), mm:d.getUTCMinutes(), wd:d.getUTCDay(), mon:d.getUTCMonth() };
    }

    const fmt = _dtf(tzn, { year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", hour12:false, hourCycle:"h23" });
    const parts = fmt.formatToParts(new Date(ms));
    const out = { y:0, mo:0, d:0, hh:0, mm:0 };
    for (const p of parts){
      if (p.type === "year") out.y = parseInt(p.value, 10);
      else if (p.type === "month") out.mo = parseInt(p.value, 10);
      else if (p.type === "day") out.d = parseInt(p.value, 10);
      else if (p.type === "hour") out.hh = parseInt(p.value, 10);
      else if (p.type === "minute") out.mm = parseInt(p.value, 10);
    }
    try{
      out.wd_str = _dtf(tzn, { weekday:"short" }).format(new Date(ms));
      out.mon_str = _dtf(tzn, { month:"short" }).format(new Date(ms));
    }catch(_){ }
    return out;
  }

  function _dtKey(p){
    return (p.y * 100000000) + (p.mo * 1000000) + (p.d * 10000) + (p.hh * 100) + p.mm;
  }

  function _newTimeCacheState() {
    return {
      sodByMs: new Map(),
      minuteByMs: new Map(),
      dayIndexByMs: new Map(),
      effByUuid: new Map(),
      stamp: 0
    };
  }

  var __scalpel_timeCaches = null;
  function __scalpelGetTimeCaches() {
    if (!__scalpel_timeCaches || typeof __scalpel_timeCaches !== "object") {
      __scalpel_timeCaches = _newTimeCacheState();
    }
    return __scalpel_timeCaches;
  }

  function __scalpelCacheSetWithCap(map, key, value, cap) {
    if (!(map instanceof Map)) return value;
    if (map.size >= cap) map.clear();
    map.set(key, value);
    return value;
  }

  function __scalpelInvalidateTimeCaches(scope) {
    const caches = __scalpelGetTimeCaches();
    const mode = String(scope || "all");
    if (mode === "all" || mode === "sod") caches.sodByMs.clear();
    if (mode === "all" || mode === "minute") caches.minuteByMs.clear();
    if (mode === "all" || mode === "dayIndex") caches.dayIndexByMs.clear();
    if (mode === "all" || mode === "effective") caches.effByUuid.clear();
    caches.stamp++;
  }

  function __scalpelDropEffectiveIntervalCache(uuid) {
    if (uuid == null) return;
    const caches = __scalpelGetTimeCaches();
    caches.effByUuid.delete(uuid);
    caches.stamp++;
  }

  function _msFromYmdInTz(y, mo, d, tz){
    // Find epoch-ms such that local datetime in tz is y-mo-d 00:00.
    const target = (y * 100000000) + (mo * 1000000) + (d * 10000);
    let lo = Date.UTC(y, mo-1, d, 0,0,0,0) - 36*3600000;
    let hi = Date.UTC(y, mo-1, d, 0,0,0,0) + 36*3600000;
    for (let i = 0; i < 48; i++){
      const mid = Math.floor((lo + hi) / 2);
      const p = _parts(mid, tz);
      const k = _dtKey(p);
      if (k < target) lo = mid + 1;
      else hi = mid;
    }
    const res = hi;
    const p = _parts(res, tz);
    if (p.y === y && p.mo === mo && p.d === d && p.hh === 0 && p.mm === 0) return res;
    return Date.UTC(y, mo-1, d, 0,0,0,0);
  }

  function startOfLocalDayMs(ms) {
    // Start-of-day for BUCKET_TZ (day boundary semantics)
    const n = Number(ms);
    if (!Number.isFinite(n)) return NaN;

    const caches = __scalpelGetTimeCaches();
    if (caches.sodByMs.has(n)) return caches.sodByMs.get(n);

    const p = _parts(n, BUCKET_TZ);
    const sod = msFromYmd(`${p.y}-${pad2(p.mo)}-${pad2(p.d)}`);
    return __scalpelCacheSetWithCap(caches.sodByMs, n, sod, 24000);
  }

  function ymdFromMs(ms) {
    // Day key in BUCKET_TZ
    const p = _parts(ms, BUCKET_TZ);
    return `${p.y}-${pad2(p.mo)}-${pad2(p.d)}`;
  }

  function msFromYmd(ymd) {
    // Midnight in BUCKET_TZ for a yyyy-mm-dd date
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(ymd || ""));
    if (!m) return NaN;
    const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
    const tzn = _tzNorm(BUCKET_TZ);
    if (_isLocalTz(tzn)) return new Date(y, mo - 1, d, 0,0,0,0).getTime();
    if (_isUtcTz(tzn)) return Date.UTC(y, mo - 1, d, 0,0,0,0);
    return _msFromYmdInTz(y, mo, d, tzn);
  }

  // Optional seed from payload (bypasses persisted view window)
  const _seedCfg = (cfg && typeof cfg.viewwin_seed === "object") ? cfg.viewwin_seed : null;
  if (_seedCfg && typeof _seedCfg.startYmd === "string") {
    const sMs = msFromYmd(_seedCfg.startYmd);
    if (Number.isFinite(sMs)) {
      const overdueDays = Number.isFinite(+_seedCfg.overdueDays) ? (+_seedCfg.overdueDays) : 0;
      const futureDays = Number.isFinite(+_seedCfg.futureDays) ? (+_seedCfg.futureDays) : (cfg && cfg.days ? +cfg.days : 7);
      globalThis.__scalpel_seed_viewwin = { startYmd: _seedCfg.startYmd, overdueDays, futureDays, __seedMs0: sMs };
      globalThis.__scalpel_viewwin_seed_locked = true;
    }
  }

  function formatLocalNoOffset(ms) {
    // Timestamp in DISPLAY_TZ (YYYY-MM-DDTHH:MM)
    const p = _parts(ms, DISPLAY_TZ);
    const y = p.y;
    const m = pad2(p.mo);
    const dd = pad2(p.d);
    const hh = pad2(p.hh);
    const mm = pad2(p.mm);
    return `${y}-${m}-${dd}T${hh}:${mm}`;
  }

  function parseLocalNoOffset(s) {
    // Parse DISPLAY_TZ "YYYY-MM-DDTHH:MM" -> epoch ms
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(String(s || ""));
    if (!m) return NaN;
    const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
    const hh = Number(m[4]), mm = Number(m[5]);
    const tzn = _tzNorm(DISPLAY_TZ);
    if (_isLocalTz(tzn)) return new Date(y, mo - 1, d, hh, mm, 0, 0).getTime();
    if (_isUtcTz(tzn)) return Date.UTC(y, mo - 1, d, hh, mm, 0, 0);
    return _msFromYmdInTz(y, mo, d, tzn) + ((hh * 60 + mm) * 60000);
  }

  function fmtHm(ms){
    const s = formatLocalNoOffset(ms);
    return s.length >= 16 ? s.slice(11, 16) : s;
  }

  function fmtDayLabel(dayStartMs) {
    // Day label aligned to BUCKET_TZ boundaries
    const tzn = _tzNorm(BUCKET_TZ);
    if (_isLocalTz(tzn)){
      const d = new Date(dayStartMs);
      const wd = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()];
      const mo = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.getMonth()];
      return { top: wd, bot: `${mo} ${d.getDate()}` };
    }
    if (_isUtcTz(tzn)){
      const d = new Date(dayStartMs);
      const wd = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getUTCDay()];
      const mo = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.getUTCMonth()];
      return { top: wd, bot: `${mo} ${d.getUTCDate()}` };
    }
    const p = _parts(dayStartMs, tzn);
    const top = p.wd_str ? String(p.wd_str) : ymdFromMs(dayStartMs);
    const bot = p.mon_str ? `${String(p.mon_str)} ${p.d}` : `${pad2(p.mo)} ${p.d}`;
    return { top, bot };
  }

  function isWeekendDayMs(dayStartMs) {
    // Weekend detection aligned to BUCKET_TZ boundaries.
    const tzn = _tzNorm(BUCKET_TZ);
    if (_isLocalTz(tzn)) {
      const d = new Date(dayStartMs);
      const wd = d.getDay();
      return wd === 0 || wd === 6;
    }
    if (_isUtcTz(tzn)) {
      const d = new Date(dayStartMs);
      const wd = d.getUTCDay();
      return wd === 0 || wd === 6;
    }
    const p = _parts(dayStartMs, tzn);
    const wdNum = Number(p && p.wd);
    if (Number.isFinite(wdNum)) return wdNum === 0 || wdNum === 6;
    const wdStr = String((p && p.wd_str) || "");
    return wdStr === "Sun" || wdStr === "Sat";
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;")
      .replaceAll("'","&#39;");
  }

  function fmtDuration(mins) {
    const m = Math.max(0, Math.round(mins));
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    const r = m % 60;
    return r ? `${h}h${pad2(r)}m` : `${h}h`;
  }

  // Alias used by UI helpers
  function fmtDur(mins){ return fmtDuration(mins); }


  function escapeAttr(s){ return escapeHtml(s); }

  function parseDurationToMs(val) {
    if (val == null) return null;
    if (typeof val === "number" && isFinite(val) && val > 0) return Math.round(val * 1000);
    if (typeof val !== "string") return null;
    const s = val.trim();
    if (!s) return null;

    let m = s.match(/^(\d+):(\d{2})(?::(\d{2}))?$/);
    if (m) {
      const hh = parseInt(m[1], 10);
      const mm = parseInt(m[2], 10);
      const ss = m[3] ? parseInt(m[3], 10) : 0;
      const total = hh * 3600 + mm * 60 + ss;
      return total > 0 ? total * 1000 : null;
    }

    m = s.match(/^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/i);
    if (m) {
      const days = m[1] ? parseInt(m[1], 10) : 0;
      const hours = m[2] ? parseInt(m[2], 10) : 0;
      const mins = m[3] ? parseInt(m[3], 10) : 0;
      const secs = m[4] ? parseInt(m[4], 10) : 0;
      const total = days * 86400 + hours * 3600 + mins * 60 + secs;
      return total > 0 ? total * 1000 : null;
    }

    const s2 = s.toLowerCase().replace(/\s+/g, "");
    const re = /(\d+)(d|day|days|h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds)/g;
    let totalSec = 0;
    let found = false;
    while ((m = re.exec(s2)) !== null) {
      found = true;
      const n = parseInt(m[1], 10);
      const u = m[2];
      if (u === "d" || u === "day" || u === "days") totalSec += n * 86400;
      else if (u === "h" || u === "hr" || u === "hrs" || u === "hour" || u === "hours") totalSec += n * 3600;
      else if (u === "m" || u === "min" || u === "mins" || u === "minute" || u === "minutes") totalSec += n * 60;
      else totalSec += n;
    }
    if (found && totalSec > 0) return totalSec * 1000;
    return null;
  }

  function hashHue(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return Math.abs(h) % 360;
  }

  function rectFromPoints(x1,y1,x2,y2) {
    const l = Math.min(x1,x2), r = Math.max(x1,x2);
    const t = Math.min(y1,y2), b = Math.max(y1,y2);
    return { left:l, right:r, top:t, bottom:b, width:(r-l), height:(b-t) };
  }
  function rectsIntersect(a, b) {
    return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
  }

  function hexToRgb(hex) {
    const h = String(hex || "").trim();
    const m = h.match(/^#?([0-9a-f]{6})$/i);
    if (!m) return null;
    const v = m[1];
    const r = parseInt(v.slice(0,2), 16);
    const g = parseInt(v.slice(2,4), 16);
    const b = parseInt(v.slice(4,6), 16);
    return { r, g, b };
  }

  function posixShellQuote(s) {
    // Safe single-quote POSIX strategy: 'abc'"'"'def'
    const str = String(s);
    if (str.length === 0) return "''";
    return "'" + str.replaceAll("'", "'\"'\"'") + "'";
  }

  // -----------------------------
  // Config
  // -----------------------------

  const PX_PER_MIN_DEFAULT = cfg.px_per_min;
  let pxPerMin = PX_PER_MIN_DEFAULT;

  const WORK_START = cfg.work_start_min;
  const WORK_END = cfg.work_end_min;
  const CAL_MINUTES = WORK_END - WORK_START;
  const SNAP = cfg.snap_min;

  const DEFAULT_DUR = cfg.default_duration_min;
  const MAX_INFER_DUR = cfg.max_infer_duration_min;

  // View window:
  // - Start: the first *planning* day (local date).
  // - Overdue: additional days shown before Start.
  // - Days: number of planning days shown after Start.
  let FUTURE_DAYS = cfg.days;
  let OVERDUE_DAYS = 0;
    // === Seed viewwin (no flicker) ===
  function __scalpel_localMidnightMsFromYmd(ymd){
    return msFromYmd(ymd);
  }
  function __scalpel_readViewWinFromStorage(){
    // Read persisted view window early so the initial skeleton is built with the
    // correct column count.
    // Note: persistence may be backed by scalpel prefs/KV, not direct localStorage.
    try{
      const vk = (cfg && (cfg.view_key || cfg.viewKey)) ? String(cfg.view_key || cfg.viewKey) : "";
      const perKeyLegacy = vk ? ("scalpel.viewwin." + vk) : "";
      const perKeyV1 = vk ? ("scalpel:v1:" + vk + ":viewwin") : "";

      const getRaw = (k) => {
        if (!k) return null;
        try{
          if (typeof globalThis.__scalpel_kvGet === "function") {
            const v = globalThis.__scalpel_kvGet(k, null);
            if (v != null) return (typeof v === "string") ? v : JSON.stringify(v);
          }
        }catch(_){ }
        try{ return localStorage.getItem(k); }catch(_){ }
        return null;
      };

      const sGlobal = getRaw("scalpel.viewwin.global");
      const sPer = getRaw(perKeyV1) || getRaw(perKeyLegacy);
      const raw = sGlobal || sPer;
      if(!raw) return null;
      const st = JSON.parse(raw);
      if(!st || typeof st !== "object") return null;
      if(!st.startYmd || typeof st.startYmd !== "string") return null;
      return st;
    }catch(_){ }
    return null;
  }
  (function(){
    if (globalThis.__scalpel_viewwin_seed_locked) return;
    const st = __scalpel_readViewWinFromStorage();
    if(!st) return;
    const ms0 = __scalpel_localMidnightMsFromYmd(st.startYmd);
    if(!Number.isFinite(ms0)) return;
    const overdueDays = Number.isFinite(+st.overdueDays) ? (+st.overdueDays) : 0;
    const futureDays  = Number.isFinite(+st.futureDays) ? (+st.futureDays) : (cfg && cfg.days ? +cfg.days : 7);
    globalThis.__scalpel_seed_viewwin = { startYmd: st.startYmd, overdueDays, futureDays, __seedMs0: ms0 };
  })();
  // === /Seed viewwin (no flicker) ===

let START_YMD = (globalThis.__scalpel_seed_viewwin && globalThis.__scalpel_seed_viewwin.startYmd) ? globalThis.__scalpel_seed_viewwin.startYmd : ymdFromMs(cfg.view_start_ms);   // planning start (yyyy-mm-dd)
  let VIEW_START_MS = (globalThis.__scalpel_seed_viewwin && Number.isFinite(globalThis.__scalpel_seed_viewwin.__seedMs0)) ? (globalThis.__scalpel_seed_viewwin.__seedMs0 - (globalThis.__scalpel_seed_viewwin.overdueDays * 86400000)) : cfg.view_start_ms;
  // === Boot seed view window (persist) ===
  (function(){
    if (globalThis.__scalpel_seeded_viewwin_v2) return;
    globalThis.__scalpel_seeded_viewwin_v2 = true;

    function safeParse(s){ try { return JSON.parse(s); } catch(_) { return null; } }
    function localMidnightMs(ymd){
      return msFromYmd(ymd);
    }

    const getRaw = (k) => {
      if (!k) return null;
      try{
        if (typeof globalThis.__scalpel_kvGet === "function") {
          const v = globalThis.__scalpel_kvGet(k, null);
          if (v != null) return (typeof v === "string") ? v : JSON.stringify(v);
        }
      }catch(_){ }
      try{ return localStorage.getItem(k); }catch(_){ }
      return null;
    };

    // Prefer global key.
    let st = safeParse((getRaw("scalpel.viewwin.global") || "null"));

    // Best-effort per-view key (new + legacy).
    try{
      const vk = (cfg && (cfg.view_key || cfg.viewKey)) ? String(cfg.view_key || cfg.viewKey) : "";
      const k1 = vk ? ("scalpel:v1:" + vk + ":viewwin") : "";
      const k2 = vk ? ("scalpel.viewwin." + vk) : "";
      if (!st && (k1 || k2)) {
        const raw = getRaw(k1) || getRaw(k2);
        if (raw) st = safeParse(raw);
      }
    }catch(_){ }

    if (!st || !st.startYmd) return;

    const ymd = String(st.startYmd);
    const fut = Number.isFinite(+st.futureDays) ? +st.futureDays : null;
    const ovd = Number.isFinite(+st.overdueDays) ? +st.overdueDays : null;

    try{ START_YMD = ymd; }catch(_){}
    try{
      const base = localMidnightMs(ymd);
      if (Number.isFinite(base)){
        const od = (ovd != null) ? ovd : 0;
        VIEW_START_MS = base - (od * 86400000);
      }
    }catch(_){}

    try{ if (typeof FUTURE_DAYS !== "undefined" && fut != null) FUTURE_DAYS = fut; }catch(_){}
    try{ if (typeof OVERDUE_DAYS !== "undefined" && ovd != null) OVERDUE_DAYS = ovd; }catch(_){}
  })();
  // === /Boot seed view window (persist) ===
          // actual visible start = Start - Overdue
  let DAYS = FUTURE_DAYS + OVERDUE_DAYS;          // total visible columns
  document.documentElement.style.setProperty("--work-start-mod60", String(WORK_START % 60));
  document.documentElement.style.setProperty("--work-start-mod15", String(WORK_START % 15));

  document.documentElement.style.setProperty("--cal-minutes", CAL_MINUTES);
  document.documentElement.style.setProperty("--days", DAYS);
  document.documentElement.style.setProperty("--px-per-min", pxPerMin);

  const viewKey = `scalpel:v1:${cfg.view_key}`;
  const zoomKey = `${viewKey}:zoom`;
  const panelsKey = `${viewKey}:panelsCollapsed`;
  const colorsKey = `${viewKey}:colors`;
  const actionsKey = `${viewKey}:actions`;
  const viewWinKey = `${viewKey}:viewwin`;


  const paletteExpandKey = `${viewKey}:paletteExpanded`;
  const confCollapsedKey = `${viewKey}:confCollapsed`;
  const goalsKey = `${viewKey}:goals`;

  // Load persisted view window (if any)
  const _loadViewWin = (typeof globalThis !== "undefined" && typeof globalThis.__scalpel_loadViewWin === "function")
    ? globalThis.__scalpel_loadViewWin
    : ((key, defObj) => defObj);
  let viewWin = _loadViewWin(viewWinKey, {
startYmd: ymdFromMs(cfg.view_start_ms),
      futureDays: cfg.days,
      overdueDays: 0,
  });

  // Apply initial window state early (before skeleton build)
  START_YMD = viewWin.startYmd;
  FUTURE_DAYS = viewWin.futureDays;
  OVERDUE_DAYS = viewWin.overdueDays;

  {
    const sMs = msFromYmd(START_YMD);
    if (Number.isFinite(sMs)) {
      VIEW_START_MS = sMs - OVERDUE_DAYS * 86400000;
      DAYS = FUTURE_DAYS + OVERDUE_DAYS;
    } else {
      START_YMD = ymdFromMs(cfg.view_start_ms);
      FUTURE_DAYS = cfg.days;
      OVERDUE_DAYS = 0;
      VIEW_START_MS = cfg.view_start_ms;
      DAYS = cfg.days;
      viewWin = { startYmd: START_YMD, futureDays: FUTURE_DAYS, overdueDays: OVERDUE_DAYS };
    }
  }

  // Ensure CSS knows current columns count (overrides the initial default if needed)
  document.documentElement.style.setProperty("--days", String(DAYS));

  const goalsCollapsedKey = `${viewKey}:goalsCollapsed`;
  const focusKey = `${viewKey}:focusState`;

  // -----------------------------
  // Data indexes & baseline
  // -----------------------------
  const baseline = new Map();     // uuid -> {scheduled_ms, due_ms}
  const baselineDur = new Map();  // uuid -> dur_ms
  const tasksByUuid = new Map();
  let __scalpelVisibleEventUuids = new Set();

  function __scalpelBuildTaskSearch(t) {
    if (!t || typeof t !== "object") return "";
    const desc = String(t.description || "");
    const proj = String(t.project || "");
    const tags = Array.isArray(t.tags) ? t.tags.join(" ") : "";
    return `${desc} ${proj} ${tags}`.toLowerCase();
  }

  function __scalpelIndexTaskForSearch(t) {
    if (!t || typeof t !== "object") return;
    t.__search = __scalpelBuildTaskSearch(t);
  }

  for (const t of (DATA.tasks || [])) {
    __scalpelIndexTaskForSearch(t);
    tasksByUuid.set(t.uuid, t);
    baseline.set(t.uuid, { scheduled_ms: t.scheduled_ms ?? null, due_ms: t.due_ms ?? null });

    let durMs = DEFAULT_DUR * 60000;

    const d1 = parseDurationToMs(t.duration);
    if (Number.isFinite(d1) && d1 > 0) {
      durMs = d1;
    } else {
      const sm = t.scheduled_ms;
      const dm = t.due_ms;
      if (Number.isFinite(sm) && Number.isFinite(dm) && dm > sm) {
        const deltaMin = (dm - sm) / 60000;
        if (deltaMin > 0 && deltaMin <= MAX_INFER_DUR) durMs = (dm - sm);
      }
    }

    baselineDur.set(t.uuid, durMs);
  }

  // Plan state: uuid -> {scheduled_ms, due_ms, dur_ms}
  let plan = new Map();

  function resetPlanToBaseline() {
    plan = new Map();
    for (const t of (DATA.tasks || [])) {
      if (t && t.local) continue;
      const b = baseline.get(t.uuid) || { scheduled_ms: null, due_ms: null };
      const d = baselineDur.get(t.uuid) ?? (DEFAULT_DUR * 60000);
      plan.set(t.uuid, { scheduled_ms: b.scheduled_ms, due_ms: b.due_ms, dur_ms: d });
    }
    __scalpelInvalidateTimeCaches("effective");
  }
  resetPlanToBaseline();

  function loadJson(key, fallback) {
    // Prefer KV (prefs-backed) storage, then fall back to raw localStorage.
    try {
      if (typeof globalThis.__scalpel_kvGetJSON === "function") {
        const v = globalThis.__scalpel_kvGetJSON(key, null);
        if (v != null) return v;
      }
    } catch (_) {}

    try {
      const raw = globalThis.__scalpel_lsGet(key);
      if (!raw) return fallback;
      const obj = JSON.parse(raw);
      return (obj && typeof obj === "object") ? obj : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function saveEdits() {
    const diffs = {};
    for (const [u, cur] of plan.entries()) {
      const tt = tasksByUuid.get(u);
      if (tt && (tt.local || tt.nautical_preview)) continue;
      const b = baseline.get(u) || { scheduled_ms: null, due_ms: null };
      const bd = baselineDur.get(u) ?? (DEFAULT_DUR * 60000);

      const changedSD = (cur.scheduled_ms !== b.scheduled_ms) || (cur.due_ms !== b.due_ms);
      const changedDur = (cur.dur_ms !== bd);

      if (changedSD || changedDur) {
        diffs[u] = { scheduled_ms: cur.scheduled_ms, due_ms: cur.due_ms, dur_ms: cur.dur_ms };
      }
    }
    try { globalThis.__scalpel_lsSet(viewKey, JSON.stringify(diffs)); } catch (_) {}
  }

  function loadEdits() {
    const obj = loadJson(viewKey, null);
    if (!obj) return;
    let changed = false;

    for (const [u, v] of Object.entries(obj)) {
      const tt = tasksByUuid.get(u);
      if (tt && tt.nautical_preview) continue;
      if (!plan.has(u) || !v || typeof v !== "object") continue;
      const sm = v.scheduled_ms == null ? null : Number(v.scheduled_ms);
      const dm = v.due_ms == null ? null : Number(v.due_ms);
      const dur = v.dur_ms == null ? null : Number(v.dur_ms);

      const cur = plan.get(u);
      plan.set(u, {
        scheduled_ms: Number.isFinite(sm) ? sm : cur.scheduled_ms,
        due_ms: Number.isFinite(dm) ? dm : cur.due_ms,
        dur_ms: Number.isFinite(dur) ? dur : cur.dur_ms,
      });
      changed = true;
    }
    if (changed) __scalpelInvalidateTimeCaches("effective");
  }
  loadEdits();
'''
