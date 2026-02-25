# scalpel/render/js/part01_core.py
from __future__ import annotations

JS_PART = r'''
(() => {
  "use strict";

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

  // -----------------------------
  // Utilities
  // -----------------------------
  const pad2 = (n) => (n < 10 ? "0" + n : "" + n);
  const clamp = (n, lo, hi) => (n < lo ? lo : (n > hi ? hi : n));

  function startOfLocalDayMs(ms) {
    const d = new Date(ms);
    return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0,0,0,0).getTime();
  }

  function ymdFromMs(ms) {
    const d = new Date(ms);
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  }

  function msFromYmd(ymd) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(ymd || ""));
    if (!m) return NaN;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 0,0,0,0).getTime();
  }


  function formatLocalNoOffset(ms) {
    const d = new Date(ms);
    const y = d.getFullYear();
    const m = pad2(d.getMonth() + 1);
    const dd = pad2(d.getDate());
    const hh = pad2(d.getHours());
    const mm = pad2(d.getMinutes());
    return `${y}-${m}-${dd}T${hh}:${mm}`;
  }

  function fmtDayLabel(dayStartMs) {
    const d = new Date(dayStartMs);
    const wd = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()];
    const mo = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][d.getMonth()];
    return { top: wd, bot: `${mo} ${d.getDate()}` };
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
  const cfg = DATA.cfg;

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
  let START_YMD = ymdFromMs(cfg.view_start_ms);   // planning start (yyyy-mm-dd)
  let VIEW_START_MS = cfg.view_start_ms;          // actual visible start = Start - Overdue
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
  let viewWin = (() => {
    const def = {
      startYmd: ymdFromMs(cfg.view_start_ms),
      futureDays: cfg.days,
      overdueDays: 0,
    };
    try {
      const raw = localStorage.getItem(viewWinKey);
      if (!raw) return def;
      const obj = JSON.parse(raw);
      if (!obj || typeof obj !== "object") return def;

      if (typeof obj.startYmd === "string" && /^(\d{4})-(\d{2})-(\d{2})$/.test(obj.startYmd)) {
        def.startYmd = obj.startYmd;
      }
      if (Number.isFinite(Number(obj.futureDays))) def.futureDays = clamp(Number(obj.futureDays), 1, 60);
      if (Number.isFinite(Number(obj.overdueDays))) def.overdueDays = clamp(Number(obj.overdueDays), 0, 30);
      return def;
    } catch (_) {
      return def;
    }
  })();

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

  for (const t of (DATA.tasks || [])) {
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
  }
  resetPlanToBaseline();

  function loadJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
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
      if (tt && tt.local) continue;
      const b = baseline.get(u) || { scheduled_ms: null, due_ms: null };
      const bd = baselineDur.get(u) ?? (DEFAULT_DUR * 60000);

      const changedSD = (cur.scheduled_ms !== b.scheduled_ms) || (cur.due_ms !== b.due_ms);
      const changedDur = (cur.dur_ms !== bd);

      if (changedSD || changedDur) {
        diffs[u] = { scheduled_ms: cur.scheduled_ms, due_ms: cur.due_ms, dur_ms: cur.dur_ms };
      }
    }
    try { localStorage.setItem(viewKey, JSON.stringify(diffs)); } catch (_) {}
  }

  function loadEdits() {
    const obj = loadJson(viewKey, null);
    if (!obj) return;

    for (const [u, v] of Object.entries(obj)) {
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
    }
  }
  loadEdits();
'''
