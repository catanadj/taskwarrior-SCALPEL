# scalpel/render/js/part02_palette_goals.py
from __future__ import annotations

JS_PART = r'''// Palette colors (projects/tags)
  // stored as { "project:work.dev": "#aabbcc", "tag:deep": "#112233" }
  let colorMap = loadJson(colorsKey, {});

  function saveColors() { try { localStorage.setItem(colorsKey, JSON.stringify(colorMap)); } catch (_) {} }

  // -----------------------------
  // Goals (config-driven highlighting)
  // -----------------------------
  const rawGoalsCfg = (DATA.goals && DATA.goals.goals) ? DATA.goals.goals : [];
  const goals = Array.isArray(rawGoalsCfg) ? rawGoalsCfg : [];

  let goalsState = loadJson(goalsKey, null);
  if (!goalsState || typeof goalsState !== "object") goalsState = {};
  if (!goalsState.enabled || typeof goalsState.enabled !== "object") goalsState.enabled = {};

  let goalsCollapsed = true;
  try {
    const v = localStorage.getItem(goalsCollapsedKey);
    if (v === "0" || v === "1") goalsCollapsed = (v === "1");
  } catch (_) {}
  function saveGoalsState(){ try { localStorage.setItem(goalsKey, JSON.stringify(goalsState)); } catch (_) {} }
  function saveGoalsCollapsed(){ try { localStorage.setItem(goalsCollapsedKey, goalsCollapsed ? "1":"0"); } catch (_) {} }

  // -----------------------------
  // Focus state (dim/hide by goals/projects/tags)
  // -----------------------------
  function loadFocusState() {
    const st = loadJson(focusKey, { mode: "all", behavior: "dim", keys: [] });
    const mode = (st && typeof st.mode === "string") ? st.mode : "all";
    const behavior = (st && typeof st.behavior === "string") ? st.behavior : "dim";
    const keys = Array.isArray(st && st.keys) ? st.keys : [];
    return { mode, behavior, keys };
  }
  function saveFocusState() {
    try { localStorage.setItem(focusKey, JSON.stringify({ mode: focusMode, behavior: focusBehavior, keys: Array.from(focusKeys) })); } catch (_) {}
  }

  let _fst = loadFocusState();
  let focusMode = ["all","goals","projects","tags"].includes(_fst.mode) ? _fst.mode : "all";
  let focusBehavior = ["dim","hide"].includes(_fst.behavior) ? _fst.behavior : "dim";
  let focusKeys = new Set((Array.isArray(_fst.keys) ? _fst.keys : []).map(String));

  function focusActive() { return focusMode !== "all" && focusKeys.size > 0; }

  function taskMatchesFocus(t) {
    if (!t) return true;
    if (focusMode === "all" || focusKeys.size === 0) return true;

    if (focusMode === "projects") {
      const p = t.project || "";
      if (!p) return focusKeys.has("No Project");
      for (const key of focusKeys) {
        if (p === key || p.startsWith(key + ".")) return true;
      }
      return false;
    }

    if (focusMode === "tags") {
      const tags = Array.isArray(t.tags) ? t.tags : [];
      if (!tags.length) return false;
      const setTags = new Set(tags.map(String));
      for (const key of focusKeys) if (setTags.has(key)) return true;
      return false;
    }

    if (focusMode === "goals") {
      for (const g of goals) {
        if (!g || !g.id) continue;
        if (!focusKeys.has(String(g.id))) continue;
        if (taskMatchesGoal(t, g)) return true;
      }
      return false;
    }

    return true;
  }

  function isDimmedTask(t) {
    return (focusBehavior === "dim" && focusActive() && !taskMatchesFocus(t));
  }

  function setFocusMode(mode) {
    const m = String(mode || "all");
    if (!["all","goals","projects","tags"].includes(m)) return;
    if (focusMode !== m) {
      focusMode = m;
      focusKeys.clear();
      saveFocusState();
      updateFocusUI();
      rerenderAll();
    } else {
      updateFocusUI();
    }
  }

  function setFocusBehavior(beh) {
    const b = String(beh || "dim");
    if (!["dim","hide"].includes(b)) return;
    focusBehavior = b;
    saveFocusState();
    updateFocusUI();
    rerenderAll();
  }

  function clearFocus() {
    focusKeys.clear();
    saveFocusState();
    updateFocusUI();
    rerenderAll();
  }

  function toggleFocusKey(key) {
    if (focusMode === "all") return;
    const k = String(key || "").trim();
    if (!k) return;
    if (focusKeys.has(k)) focusKeys.delete(k);
    else focusKeys.add(k);
    saveFocusState();
    updateFocusUI();
    rerenderAll();
  }

  function updateFocusUI() {
    const bar = document.getElementById("focusBar");
    if (!bar) return;
    const meta = document.getElementById("focusMeta");
    const modeLab = (focusMode === "all") ? "All" : (focusMode[0].toUpperCase() + focusMode.slice(1));
    const n = focusKeys.size;
    const active = (focusMode !== "all" && n > 0);
    if (meta) meta.textContent = active ? `${modeLab}: ${n} • ${focusBehavior}` : `${modeLab} • ${focusBehavior}`;

    bar.querySelectorAll("[data-fmode]").forEach(btn => {
      const m = btn.getAttribute("data-fmode");
      btn.classList.toggle("on", m === focusMode);
    });
    bar.querySelectorAll("[data-fbeh]").forEach(btn => {
      const b = btn.getAttribute("data-fbeh");
      btn.classList.toggle("on", b === focusBehavior);
    });
  }


  function goalEnabled(gid){
    const v = goalsState.enabled[gid];
    return (v === undefined) ? true : !!v;
  }
  function setGoalEnabled(gid, on){
    goalsState.enabled[gid] = !!on;
    saveGoalsState();
  }

  function taskMatchesGoal(task, g){
    const p = (task.project || "").trim();
    const tags = (task.tags || []);
    let projHit = false;
    let tagAnyHit = false;
    let tagAllHit = false;

    const projects = (g.projects || []);
    if (p && projects && projects.length){
      for (const pr of projects){
        if (!pr) continue;
        if (p === pr || p.startsWith(pr + ".")) { projHit = true; break; }
      }
    }

    const tagsAny = (g.tags || []);
    if (tagsAny && tagsAny.length){
      for (const tg of tagsAny){
        if (tg && tags.includes(tg)) { tagAnyHit = true; break; }
      }
    }

    const tagsAll = (g.tags_all || []);
    if (tagsAll && tagsAll.length){
      tagAllHit = tagsAll.every(tg => tg && tags.includes(tg));
    }

    const mode = (g.mode || "any");
    if (mode === "all"){
      const dims = [];
      if (projects && projects.length) dims.push(projHit);
      if (tagsAny && tagsAny.length) dims.push(tagAnyHit);
      if (tagsAll && tagsAll.length) dims.push(tagAllHit);
      if (!dims.length) return false;
      return dims.every(Boolean);
    }

    // any (default)
    return projHit || tagAnyHit || tagAllHit;
  }

  function resolveGoalAccent(task){
    for (const g of goals){
      if (!g || !g.id || !g.color) continue;
      if (!goalEnabled(g.id)) continue;
      if (taskMatchesGoal(task, g)) return g;
    }
    return null;
  }


  // Action commands queue: array of strings
  // Palette expand/collapse state (projects). Stored as { "work":1, "work.dev":1, ... } per view.
  let paletteExpanded = loadJson(paletteExpandKey, {});
  if (!paletteExpanded || typeof paletteExpanded !== "object") paletteExpanded = {};
  function savePaletteExpanded() { try { localStorage.setItem(paletteExpandKey, JSON.stringify(paletteExpanded)); } catch (_) {} }

  // Conflicts panel collapse state (default: collapsed)
  let confCollapsed = true;
  try {
    const v = localStorage.getItem(confCollapsedKey);
    if (v === "0" || v === "1") confCollapsed = (v === "1");
  } catch (_) {}
  function saveConfCollapsed() { try { localStorage.setItem(confCollapsedKey, confCollapsed ? "1" : "0"); } catch (_) {} }

  let actionQueue = loadJson(actionsKey, []);
  if (!Array.isArray(actionQueue)) actionQueue = [];

  function saveActions() { try { localStorage.setItem(actionsKey, JSON.stringify(actionQueue)); } catch (_) {} }
// Local "new task" placeholders created via the Add Tasks modal.
// These are rendered on the calendar immediately for planning, but are NOT persisted.
// Commands output will include corresponding `task add ... scheduled:... due:... duration:...` lines derived from the current plan.
let localAdds = []; // [{ uuid, desc }]
let localTaskCounter = 0;

function isLocalTask(uuid) {
  const t = tasksByUuid.get(uuid);
  return !!(t && t.local);
}

function purgeLocalTasks() {
  const locals = [];
  for (const t of (DATA.tasks || [])) {
    if (t && t.local) locals.push(t.uuid);
  }
  if (!locals.length) return;

  DATA.tasks = (DATA.tasks || []).filter(t => !(t && t.local));

  for (const u of locals) {
    tasksByUuid.delete(u);
    baseline.delete(u);
    baselineDur.delete(u);
    plan.delete(u);
    selected.delete(u);
    if (selectionLead === u) selectionLead = null;
  }

  localAdds = localAdds.filter(x => !locals.includes(x.uuid));
  setRangeMeta();
  updateSelectionMeta();
}

function removeLocalTask(uuid) {
  const t = tasksByUuid.get(uuid);
  if (!t || !t.local) return false;

  DATA.tasks = (DATA.tasks || []).filter(x => !(x && x.uuid === uuid));

  tasksByUuid.delete(uuid);
  baseline.delete(uuid);
  baselineDur.delete(uuid);
  plan.delete(uuid);
  selected.delete(uuid);
  if (selectionLead === uuid) selectionLead = null;

  localAdds = localAdds.filter(x => x.uuid !== uuid);

  setRangeMeta();
  updateSelectionMeta();
  return true;
}

function buildAddCommandForLocal(uuid, desc) {
  const cur = plan.get(uuid);
  if (!cur || !Number.isFinite(cur.due_ms)) return null;
  const durMs = Number.isFinite(cur.dur_ms) ? cur.dur_ms : (DEFAULT_DUR * 60000);
  const dueMs = cur.due_ms;
  const schMs = dueMs - durMs;
  if (!Number.isFinite(schMs) || dueMs <= schMs) return null;

  const sch = formatLocalNoOffset(schMs);
  const due = formatLocalNoOffset(dueMs);
  const durMin = Math.max(1, Math.round(durMs / 60000));
  const descRaw = String(desc || "").replace(/\s+/g, " ").trim();
  return `task add ${descRaw} scheduled:${sch} due:${due} duration:${durMin}min`;
}

  // Effective interval: [due - dur, due]
  function effectiveInterval(uuid) {
    const cur = plan.get(uuid);
    if (!cur) return null;
    const dueMs = cur.due_ms;
    if (!Number.isFinite(dueMs)) return null;
    const durMs = Number.isFinite(cur.dur_ms) ? cur.dur_ms : (DEFAULT_DUR * 60000);
    const startMs = dueMs - durMs;
    return { startMs, dueMs, durMs };
  }

  // -----------------------------
  // Color resolution
  // -----------------------------
  function resolveTaskAccent(task) {
    // returns { color, explicit, source, goal } where explicit indicates a user-assigned mapping was used
    const g = resolveGoalAccent(task);
    if (g) return { color: g.color, explicit: true, source: "goal", goal: g };

    const tags = (task.tags || []);
    for (const tag of tags) {
      const k = `tag:${tag}`;
      if (colorMap[k]) return { color: colorMap[k], explicit: true, source: "palette" };
    }

    const p = (task.project || "").trim();
    if (p) {
      let cur = p;
      while (true) {
        const k = `project:${cur}`;
        if (colorMap[k]) return { color: colorMap[k], explicit: true, source: "palette" };
        const idx = cur.lastIndexOf(".");
        if (idx < 0) break;
        cur = cur.slice(0, idx);
      }
    }
    return { color: null, explicit: false, source: "auto" };
  }

  // -----------------------------
  // DOM
  // -----------------------------
  const elMeta = document.getElementById("meta");
  const elSelMeta = document.getElementById("selMeta");
  const elRange = document.getElementById("range");
  const elSelBox = document.getElementById("selBox");
  const elSelList = document.getElementById("selList");
  const elSelSummary = document.getElementById("selSummary");
  const elCal = document.getElementById("calendar");
  const elBacklog = document.getElementById("backlog");
  const elProblems = document.getElementById("problems");
  const elBacklogCount = document.getElementById("backlogCount");
  const elProblemCount = document.getElementById("problemCount");
  const elGoalsBox = document.getElementById("goalsBox");
  const elPaletteTree = document.getElementById("paletteTree");
  const elQ = document.getElementById("q");
  const elCommands = document.getElementById("commands");
  const elCmdCount = document.getElementById("cmdCount");
  const elStatus = document.getElementById("status");
  const elConflictsBox = document.getElementById("conflictsBox");
  const elNextUp = document.getElementById("nextUp");
  const elNextUpMeta = document.getElementById("nextUpMeta");
  const elNextUpBody = document.getElementById("nextUpBody");


  const elDayBal = document.getElementById("dayBal");
  const elDayBalDay = document.getElementById("dayBalDay");
  const elDayBalBar = document.getElementById("dayBalBar");
  const elDayBalLegend = document.getElementById("dayBalLegend");


  const elZoom = document.getElementById("zoom");
  const elZoomVal = document.getElementById("zoomVal");

  const elVwPrevPage = document.getElementById("vwPrevPage");
  const elVwPrevDay = document.getElementById("vwPrevDay");
  const elVwToday = document.getElementById("vwToday");
  const elVwNextDay = document.getElementById("vwNextDay");
  const elVwNextPage = document.getElementById("vwNextPage");
  const elVwStart = document.getElementById("vwStart");
  const elVwDays = document.getElementById("vwDays");
  const elVwOverdue = document.getElementById("vwOverdue");

  // -----------------------------
  // Theme (dark/light)
  // -----------------------------
  const THEME_KEY = "scalpel_theme";
  function getPreferredTheme(){
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") return saved;
    try{
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
    }catch(e){}
    return "dark";
  }
  function applyTheme(theme){
    const isLight = theme === "light";
    document.body.classList.toggle("theme-light", isLight);
    document.body.classList.toggle("theme-dark", !isLight);
    localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    const b = document.getElementById("btnTheme");
    if (b) b.textContent = isLight ? "Dark theme" : "Light theme";
  }


  const elLayout = document.getElementById("layout");
  const elBtnTogglePanels = document.getElementById("btnTogglePanels");

  const elMarquee = document.getElementById("marquee");

  const elAddModal = document.getElementById("addModal");
  const elAddLines = document.getElementById("addLines");
  const elAddClose = document.getElementById("addClose");
  const elAddQueue = document.getElementById("addQueue");

  // -----------------------------
  // Calendar constants
  // -----------------------------
  const dayStarts = [];
  function recomputeDayStarts() {
    dayStarts.length = 0;
    for (let i = 0; i < DAYS; i++) dayStarts.push(VIEW_START_MS + i * 86400000);
  }
  recomputeDayStarts();
  function setRangeMeta() {
    const a = new Date(dayStarts[0]);
    const b = new Date(dayStarts[dayStarts.length - 1]);
    const fmt = (d) => `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
    elRange.textContent = `${fmt(a)} → ${fmt(b)}`;
    elMeta.textContent = `Due-based view • Snap ${SNAP}m • Workhours ${pad2(Math.floor(WORK_START/60))}:${pad2(WORK_START%60)}-${pad2(Math.floor(WORK_END/60))}:${pad2(WORK_END%60)} • ${(DATA.tasks||[]).length} tasks`;
  }
  setRangeMeta();


  // -----------------------------
  // Day balance (active day)
  // -----------------------------
  const activeDayKey = "scalpel.activeDayIndex";
  let activeDayIndex = (() => {
    let di = null;
    try {
      const v = localStorage.getItem(activeDayKey);
      if (v !== null) di = parseInt(v, 10);
    } catch (_) {}
    if (!Number.isInteger(di) || di < 0 || di >= DAYS) {
      di = dayIndexFromMs(Date.now());
    }
    if (di === null) di = 0;
    return di;
  })();

  let lastDayVis = null;

  function saveActiveDay() {
    try { localStorage.setItem(activeDayKey, String(activeDayIndex)); } catch (_) {}
  }

  function setActiveDayFromUuid(uuid) {
    const cur = plan.get(uuid);
    const dueMs = cur && Number.isFinite(cur.due_ms) ? cur.due_ms : (tasksByUuid.get(uuid) ? tasksByUuid.get(uuid).due_ms : null);
    if (!Number.isFinite(dueMs)) return;
    const di = dayIndexFromMs(dueMs);
    if (di === null) return;
    if (di !== activeDayIndex) {
      activeDayIndex = di;
      saveActiveDay();
    }
  }

  function renderDayBalance(di, dayVis) {
    if (!elDayBal || !elDayBalBar || !elDayBalLegend || !elDayBalDay) return;
    if (!Number.isInteger(di) || di < 0 || di >= DAYS) { elDayBal.style.display = "none"; return; }
    elDayBal.style.display = "";

    const dayStart = dayStarts[di];
    const d = new Date(dayStart);
    const wd = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()];
    const dayStr = `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
    elDayBalDay.textContent = `${wd} ${dayStr}`;

    const workMin = Math.max(0, (WORK_END - WORK_START));
    if (workMin <= 0) {
      elDayBalBar.innerHTML = "";
      elDayBalLegend.innerHTML = `<div class="hint">Workhours are disabled.</div>`;
      return;
    }

    const wStartMs = dayStart + WORK_START * 60000;
    const wEndMs   = dayStart + WORK_END * 60000;

    const items = (dayVis && dayVis[di]) ? dayVis[di] : [];
    const intervals = [];
    const catByUuid = new Map();

    for (const it of items) {
      if (!it || !it.uuid) continue;
      const s0 = it.startMs;
      const e0 = it.dueMs;
      if (!Number.isFinite(s0) || !Number.isFinite(e0) || e0 <= s0) continue;

      const s = Math.max(s0, wStartMs);
      const e = Math.min(e0, wEndMs);
      if (e <= s) continue;

      intervals.push({ uuid: it.uuid, s, e });

      if (!catByUuid.has(it.uuid)) {
        const t = tasksByUuid.get(it.uuid);
        const g = t ? resolveGoalAccent(t) : null;
        if (g && g.id && g.color) {
          catByUuid.set(it.uuid, { key: `goal:${g.id}`, label: (g.name || g.id), color: g.color });
        } else {
          catByUuid.set(it.uuid, { key: "other", label: "Other", color: "rgba(154,166,178,0.80)" });
        }
      }
    }

    // Allocate each minute of the workday to overlapping tasks (evenly), so totals never exceed 100%.
    const minsByKey = new Map();
    let freeMin = 0;

    for (let i = 0; i < workMin; i++) {
      const ms0 = wStartMs + i * 60000;
      const ms1 = ms0 + 60000;

      let overlapUuids = null;
      for (const iv of intervals) {
        if (iv.s < ms1 && iv.e > ms0) {
          if (!overlapUuids) overlapUuids = [];
          overlapUuids.push(iv.uuid);
        }
      }

      if (!overlapUuids || overlapUuids.length === 0) {
        freeMin += 1;
        continue;
      }

      const share = 1 / overlapUuids.length;
      for (const u of overlapUuids) {
        const cat = catByUuid.get(u);
        const key = cat ? cat.key : "other";
        minsByKey.set(key, (minsByKey.get(key) || 0) + share);
      }
    }

    const cats = [];
    for (const [key, mins] of minsByKey.entries()) {
      let label = "Other";
      let color = "rgba(154,166,178,0.80)";
      if (key === "other") {
        label = "Other";
      } else if (key.startsWith("goal:")) {
        const gid = key.slice(5);
        const g = (goals || []).find(x => x && x.id === gid);
        label = (g && (g.name || g.id)) || gid;
        color = (g && g.color) ? g.color : color;
      }
      cats.push({ key, label, color, mins });
    }
    if (freeMin > 0) cats.push({ key: "free", label: "Free", color: "rgba(210,255,210,0.70)", mins: freeMin });

    // Sort: goals by minutes desc, then Other, then Free
    cats.sort((a,b) => {
      const aIsFree = a.key === "free";
      const bIsFree = b.key === "free";
      const aIsOther = a.key === "other";
      const bIsOther = b.key === "other";
      if (aIsFree !== bIsFree) return aIsFree ? 1 : -1;
      if (aIsOther !== bIsOther) return aIsOther ? 1 : -1;
      return (b.mins - a.mins);
    });

    const pct = (mins) => (mins / workMin) * 100;

    // Bar
    elDayBalBar.innerHTML = cats
      .filter(c => c.mins > 0.0001)
      .map(c => {
        const p = pct(c.mins);
        const title = `${c.label}: ${fmtDuration(c.mins)} (${Math.round(p)}%)`;
        return `<div class="dbseg" title="${escapeHtml(title)}" style="flex:0 0 ${p}%;background:${escapeHtml(c.color)};"></div>`;
      })
      .join("");

    // Legend
    elDayBalLegend.innerHTML = cats
      .filter(c => c.mins > 0.0001)
      .map(c => {
        const p = Math.round(pct(c.mins));
        return `
          <div class="dbrow">
            <div class="left">
              <span class="sw" style="background:${escapeHtml(c.color)};"></span>
              <span class="lbl">${escapeHtml(c.label)}</span>
            </div>
            <div class="val">${escapeHtml(fmtDuration(c.mins))} • ${p}%</div>
          </div>
        `;
      })
      .join("");
  }

  // -----------------------------
'''
