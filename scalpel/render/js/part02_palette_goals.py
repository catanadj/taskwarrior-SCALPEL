# scalpel/render/js/part02_palette_goals.py
from __future__ import annotations

JS_PART = r'''// Palette colors (projects/tags)
  // Persistence helpers (KV) + global focus key
  const FOCUS_GLOBAL_KEY = 'scalpel.focus.global';

  function _kvGetRaw(key) {
    try {
      if (typeof globalThis !== 'undefined' && typeof globalThis.__scalpel_kvGet === 'function')
        return globalThis.__scalpel_kvGet(String(key), null);
    } catch (_) {}
    return null;
  }
  function _kvSetRaw(key, val) {
    try {
      if (typeof globalThis !== 'undefined' && typeof globalThis.__scalpel_kvSet === 'function')
        globalThis.__scalpel_kvSet(String(key), String(val));
    } catch (_) {}
  }
  function _parseJSON(v) {
    try {
      if (v == null) return null;
      if (typeof v === 'object') return v;
      const s = String(v);
      if (!s) return null;
      return JSON.parse(s);
    } catch (_) { return null; }
  }
  function _loadJsonAny(key, fallback) {
    try { if (typeof loadJson === 'function') { const o = loadJson(String(key), null); if (o != null) return o; } } catch (_) {}
    const kv = _parseJSON(_kvGetRaw(key));
    if (kv != null) return kv;
    try {
      const s = localStorage.getItem(String(key));
      const o = _parseJSON(s);
      return (o != null) ? o : fallback;
    } catch (_) {}
    return fallback;
  }
  function _saveJsonAny(key, obj) {
    try { if (typeof saveJson === 'function') { saveJson(String(key), obj); return; } } catch (_) {}
    try { _kvSetRaw(key, JSON.stringify(obj)); } catch (_) {}
    try { localStorage.setItem(String(key), JSON.stringify(obj)); } catch (_) {}
  }
  // stored as { "project:work.dev": "#aabbcc", "tag:deep": "#112233" }
  // Prefer a global palette color map so colors persist across different view_key builds.
  const colorsGlobalKey = "scalpel:paletteColors:global";

  let colorMap = loadJson(colorsGlobalKey, null);
  if (!colorMap || typeof colorMap !== "object" || Array.isArray(colorMap)) colorMap = {};

  // Back-compat: merge any legacy per-view colors (view overrides global) and migrate.
  const _viewColorMap = loadJson(colorsKey, null);
  if (_viewColorMap && typeof _viewColorMap === "object" && !Array.isArray(_viewColorMap)) {
    colorMap = Object.assign({}, colorMap, _viewColorMap);
    try { if (typeof globalThis.__scalpel_kvSet === "function") globalThis.__scalpel_kvSet(colorsGlobalKey, JSON.stringify(colorMap)); } catch (_) {}
  }

  function saveColors() {
    try { globalThis.__scalpel_kvSet(colorsGlobalKey, JSON.stringify(colorMap)); } catch (_) {}
    try { globalThis.__scalpel_kvSet(colorsKey, JSON.stringify(colorMap)); } catch (_) {}
  }

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
    const v = globalThis.__scalpel_kvGet(goalsCollapsedKey);
    if (v === "0" || v === "1") goalsCollapsed = (v === "1");
  } catch (_) {}
  function saveGoalsState(){ try { globalThis.__scalpel_kvSet(goalsKey, JSON.stringify(goalsState)); } catch (_) {} }
  function saveGoalsCollapsed(){ try { globalThis.__scalpel_kvSet(goalsCollapsedKey, goalsCollapsed ? "1":"0"); } catch (_) {} }

  // -----------------------------
  // Focus state (dim/hide by goals/projects/tags)
  // -----------------------------
    function loadFocusState() {
    const def = { mode: 'all', behavior: 'dim', keys: [] };

    // Global first (survives viewKey changes), then per-view
    let st = _loadJsonAny(FOCUS_GLOBAL_KEY, null);
    if (!st) st = _loadJsonAny(focusKey, def);

    const mode = (st && typeof st.mode === 'string') ? st.mode : 'all';
    const behavior = (st && typeof st.behavior === 'string') ? st.behavior : 'dim';
    const keys = Array.isArray(st && st.keys) ? st.keys : [];
    return { mode, behavior, keys };
  }

    function saveFocusState() {
    const obj = { mode: focusMode, behavior: focusBehavior, keys: Array.from(focusKeys) };
    _saveJsonAny(focusKey, obj);          // per-view
    _saveJsonAny(FOCUS_GLOBAL_KEY, obj);  // global
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
    const clr = document.getElementById("btnClearFocus");
    const modeLab = (focusMode === "all") ? "All" : (focusMode[0].toUpperCase() + focusMode.slice(1));
    const n = focusKeys.size;
    const active = (focusMode !== "all" && n > 0);
    if (meta) meta.textContent = active ? `${modeLab}: ${n} • ${focusBehavior}` : `${modeLab} • ${focusBehavior}`;
    if (clr) {
      clr.disabled = !active;
      clr.title = active ? "Clear active focus filters" : "No focus filters active";
    }

    bar.querySelectorAll("[data-fmode]").forEach(btn => {
      const m = btn.getAttribute("data-fmode");
      const on = (m === focusMode);
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    bar.querySelectorAll("[data-fbeh]").forEach(btn => {
      const b = btn.getAttribute("data-fbeh");
      const on = (b === focusBehavior);
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
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
  function savePaletteExpanded() { try { globalThis.__scalpel_kvSet(paletteExpandKey, JSON.stringify(paletteExpanded)); } catch (_) {} }

  // Conflicts panel collapse state (default: collapsed)
  let confCollapsed = true;
  try {
    const v = globalThis.__scalpel_kvGet(confCollapsedKey);
    if (v === "0" || v === "1") confCollapsed = (v === "1");
  } catch (_) {}
  function saveConfCollapsed() { try { globalThis.__scalpel_kvSet(confCollapsedKey, confCollapsed ? "1" : "0"); } catch (_) {} }

  let actionQueue = loadJson(actionsKey, []);
  if (!Array.isArray(actionQueue)) actionQueue = [];

  // Action meta (UI-only): { uuid: "done" | "delete" }
  // Persisted per view, so queued actions are visually reflected after refresh.
  const actionsMetaKey = actionsKey + "::meta";
  let actionMeta = loadJson(actionsMetaKey, {});
  if (!actionMeta || typeof actionMeta !== "object" || Array.isArray(actionMeta)) actionMeta = {};

  // If the user had queued actions before this feature existed, try to infer
  // per-task queued state from the persisted actionQueue.
  function _primeActionMetaFromQueue() {
    try {
      if (!Array.isArray(actionQueue) || !actionQueue.length) return;

      const identToUuid = new Map();
      try {
        for (const t of tasksByUuid.values()) {
          if (!t || !t.uuid) continue;
          const u = String(t.uuid);
          identToUuid.set(u.slice(0, 8), u);
          if (t.id != null && t.id !== 0) identToUuid.set(String(t.id), u);
        }
      } catch (_) {}

      let changed = false;
      for (const line of actionQueue) {
        if (!line) continue;
        const m = String(line).trim().match(/^task\s+(\S+)\s+(done|delete)\s*$/);
        if (!m) continue;
        const ident = m[1];
        const kind = m[2];
        const uuid = identToUuid.get(String(ident));
        if (!uuid) continue;
        const cur = actionMeta[uuid];
        if (cur === "delete") continue;
        if (cur === "done" && kind === "done") continue;
        actionMeta[uuid] = kind;
        changed = true;
      }

      if (changed) saveActionMeta();
    } catch (_) {}
  }
  _primeActionMetaFromQueue();

  function saveActions() {
    try { globalThis.__scalpel_kvSet(actionsKey, JSON.stringify(actionQueue)); } catch (_) {}
  }
  function saveActionMeta() {
    try { globalThis.__scalpel_kvSet(actionsMetaKey, JSON.stringify(actionMeta)); } catch (_) {}
  }

  function queuedActionKind(uuid) {
    if (!uuid) return null;
    const k = actionMeta[uuid];
    return (k === "done" || k === "delete") ? k : null;
  }

  function setQueuedAction(uuid, kind) {
    if (!uuid) return;
    if (kind !== "done" && kind !== "delete") return;
    // delete overrides done (more destructive)
    const cur = queuedActionKind(uuid);
    if (cur === "delete") return;
    actionMeta[uuid] = kind;
    saveActionMeta();
  }

  function clearQueuedAction(uuid) {
    if (!uuid) return;
    if (Object.prototype.hasOwnProperty.call(actionMeta, uuid)) {
      delete actionMeta[uuid];
      saveActionMeta();
    }
  }

  function clearAllQueuedActions() {
    actionMeta = {};
    saveActionMeta();
  }
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
    __scalpelDropEffectiveIntervalCache(u);
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
  __scalpelDropEffectiveIntervalCache(uuid);
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
    const caches = __scalpelGetTimeCaches();
    const cur = plan.get(uuid);
    if (!cur) {
      caches.effByUuid.delete(uuid);
      return null;
    }

    const cached = caches.effByUuid.get(uuid);
    if (cached && cached.curRef === cur) return cached.iv;

    const dueMs = cur.due_ms;
    if (!Number.isFinite(dueMs)) {
      caches.effByUuid.delete(uuid);
      return null;
    }
    const durMs = Number.isFinite(cur.dur_ms) ? cur.dur_ms : (DEFAULT_DUR * 60000);
    const startMs = dueMs - durMs;
    const iv = { startMs, dueMs, durMs };
    caches.effByUuid.set(uuid, { curRef: cur, iv });
    return iv;
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
  const elCtxMeta = document.getElementById("ctxMeta");
  const elPendingMeta = document.getElementById("pendingMeta");
  const elBtnNotes = document.getElementById("btnNotes");
  const elRange = document.getElementById("range");
  const elSelBox = document.getElementById("selBox");
  const elSelList = document.getElementById("selList");
  const elSelSummary = document.getElementById("selSummary");
  const elSelExtra = document.getElementById("selExtra");
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
  // Notes (sticky) UI
  const elNotesWrap = document.getElementById("notesWrap");
  const elNotesBox = document.getElementById("notesBox");
  const elNotesHead = document.getElementById("notesHead");
  const elNotesBody = document.getElementById("notesBody");
  const elNotesMeta = document.getElementById("notesMeta");
  const elNoteNewText = document.getElementById("noteNewText");
  const elNoteAdd = document.getElementById("noteAdd");
  const elNoteNew = document.getElementById("noteNew");
  const elNoteExport = document.getElementById("noteExport");
  const elNoteImport = document.getElementById("noteImport");
  const elNoteClearArchived = document.getElementById("noteClearArchived");
  const elNoteQ = document.getElementById("noteQ");
  const elNoteList = document.getElementById("noteList");
  const elNoteImportFile = document.getElementById("noteImportFile");

  const elNoteModal = document.getElementById("noteModal");
  const elNoteModalTitle = document.getElementById("noteModalTitle");
  const elNoteClose = document.getElementById("noteClose");
  const elNoteSave = document.getElementById("noteSave");
  const elNoteText = document.getElementById("noteText");
  const elNoteColors = document.getElementById("noteColors");
  const elNoteDelete = document.getElementById("noteDelete");
  const elNotePinned = document.getElementById("notePinned");
  const elNoteAllDay = document.getElementById("noteAllDay");
  const elNoteRepeat = document.getElementById("noteRepeat");
  const elNoteRepeatBox = document.getElementById("noteRepeatBox");
  const elNoteRepeatDays = document.getElementById("noteRepeatDays");
  const elNoteDowAll = document.getElementById("noteDowAll");
  const elNoteDowWeekdays = document.getElementById("noteDowWeekdays");
  const elNoteDowClear = document.getElementById("noteDowClear");
  const elNoteArchived = document.getElementById("noteArchived");
  const elNoteDay = document.getElementById("noteDay");
  const elNoteStart = document.getElementById("noteStart");
  const elNoteEnd = document.getElementById("noteEnd");
  const elNoteUnplace = document.getElementById("noteUnplace");
  const elNoteTzHint = document.getElementById("noteTzHint");



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
  // Theme (built-ins + custom overrides)
  // -----------------------------
  const THEME_KEY = "scalpel_theme";
  const BUILTIN_THEMES = ["dark", "light", "paper", "muted", "vivid", "contrast"];
  const THEME_LABEL = { dark: "Dark", light: "Light", paper: "Paper planner", muted: "Muted", vivid: "Vivid", contrast: "High contrast" };
  const THEME_STORE_KEY = "scalpel:themes:v1";

  const THEME_EXPORT_KEYS = [
    "--bg","--panel","--panel2","--surface3","--surface4","--cal-surface",
    "--text","--muted","--line","--shadow",
    "--accent","--accent-rgb","--warn","--warn-rgb","--bad","--bad-rgb",
    "--block","--block2",
    "--task-border","--task-selected",
    "--task-title-text","--task-body-text","--task-code-text","--task-resize-glow",
    "--task-hover-ring-ms","--task-hover-outline-alpha","--task-hover-outline-offset","--task-hover-inset-alpha","--task-hover-outer-alpha",
    "--task-hover-sheen-opacity","--task-hover-sheen-ms","--task-snap-pulse-opacity","--task-snap-pulse-ms",
    "--task-z","--task-hover-z","--task-drag-z",
    "--loadfill","--loadfill-over",
    "--npill-bg","--npill-bd","--npill-text",
    "--note-bg","--note-bd","--note-text","--note-meta","--note-pinned-bd",
    "--note-c1-bg","--note-c1-bd","--note-c2-bg","--note-c2-bd","--note-c3-bg","--note-c3-bd","--note-c4-bg","--note-c4-bd",
    "--note-c5-bg","--note-c5-bd","--note-c6-bg","--note-c6-bd","--note-c7-bg","--note-c7-bd","--note-c8-bg","--note-c8-bd"
  ];

  function _loadThemeStore(){
    try{
      const raw = (typeof globalThis.__scalpel_kvGet === "function") ? globalThis.__scalpel_kvGet(THEME_STORE_KEY, null) : (localStorage.getItem(THEME_STORE_KEY));
      if (!raw) return { schema: "scalpel-themes/v1", themes: [] };
      const obj = JSON.parse(raw);
      if (!obj || typeof obj !== "object") return { schema: "scalpel-themes/v1", themes: [] };
      const themes = Array.isArray(obj.themes) ? obj.themes : [];
      return { schema: "scalpel-themes/v1", themes };
    }catch(_){
      return { schema: "scalpel-themes/v1", themes: [] };
    }
  }

  function _saveThemeStore(store){
    try{
      const s = JSON.stringify(store);
      if (typeof globalThis.__scalpel_kvSet === "function") globalThis.__scalpel_kvSet(THEME_STORE_KEY, s);
      else localStorage.setItem(THEME_STORE_KEY, s);
    }catch(_){ }
  }

  function listCustomThemes(){
    const st = _loadThemeStore();
    const out = [];
    for (const t of (st.themes || [])){
      if (!t || typeof t !== "object") continue;
      if (!t.id || typeof t.id !== "string") continue;
      if (!t.name || typeof t.name !== "string") continue;
      out.push(t);
    }
    return out;
  }

  function getCustomTheme(id){
    if (!id || typeof id !== "string") return null;
    for (const t of listCustomThemes()){
      if (t.id === id) return t;
    }
    return null;
  }

  function themeExists(id){
    if (BUILTIN_THEMES.includes(id)) return true;
    return !!getCustomTheme(id);
  }

  function getPreferredTheme(){
    const saved = (typeof globalThis.__scalpel_kvGet === "function") ? globalThis.__scalpel_kvGet(THEME_KEY, null) : (localStorage.getItem(THEME_KEY));
    if (saved && themeExists(saved)) return saved;
    try{
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
    }catch(e){}
    return "dark";
  }

  function getCurrentBaseTheme(){
    for (const t of BUILTIN_THEMES){
      if (document.body.classList.contains("theme-" + t)) return t;
    }
    return null;
  }

  function getCurrentTheme(){
    // If a custom theme id is selected, return that id; else return base class
    const saved = (typeof globalThis.__scalpel_kvGet === "function") ? globalThis.__scalpel_kvGet(THEME_KEY, null) : (localStorage.getItem(THEME_KEY));
    if (saved && !BUILTIN_THEMES.includes(saved) && getCustomTheme(saved)) return saved;
    return getCurrentBaseTheme();
  }

  function _clearThemeOverrides(){
    try{
      const keys = globalThis.__scalpel_theme_override_keys || [];
      for (const k of keys) document.body.style.removeProperty(k);
    }catch(_){ }
    globalThis.__scalpel_theme_override_keys = [];
  }

  function _applyThemeOverrides(tokens){
    const keys = [];
    if (!tokens || typeof tokens !== "object") return;
    for (const k of Object.keys(tokens)){
      if (!/^--[a-zA-Z0-9_-]+$/.test(k)) continue;
      const v = tokens[k];
      if (v === null || v === undefined) continue;
      const sv = String(v).trim();
      if (!sv) continue;
      document.body.style.setProperty(k, sv);
      keys.push(k);
    }
    globalThis.__scalpel_theme_override_keys = keys;
  }

  function _themeLabel(id){
    if (THEME_LABEL[id]) return THEME_LABEL[id];
    const t = getCustomTheme(id);
    if (t && t.name) return t.name;
    return id;
  }

  function applyTheme(themeId){
    let base = "dark";
    let overrides = null;
    if (BUILTIN_THEMES.includes(themeId)){
      base = themeId;
    }else{
      const t = getCustomTheme(themeId);
      if (t){
        base = (t.base && BUILTIN_THEMES.includes(t.base)) ? t.base : "dark";
        overrides = (t.tokens && typeof t.tokens === "object") ? t.tokens : null;
      }else{
        themeId = "dark";
        base = "dark";
      }
    }

    // Base classes
    for (const t of BUILTIN_THEMES) document.body.classList.remove("theme-" + t);
    document.body.classList.add("theme-" + base);

    // Custom overrides
    _clearThemeOverrides();
    if (overrides) _applyThemeOverrides(overrides);

    try{
      if (typeof globalThis.__scalpel_kvSet === "function") globalThis.__scalpel_kvSet(THEME_KEY, themeId);
      else localStorage.setItem(THEME_KEY, themeId);
    }catch(_){ }

    const b = document.getElementById("btnTheme");
    if (b) b.textContent = `Theme: ${_themeLabel(themeId)}`;
  }

  function cycleTheme(){
    // Cycle built-ins only. If on custom, cycle relative to its base.
    const cur = getCurrentTheme() || getPreferredTheme();
    let base = cur;
    if (!BUILTIN_THEMES.includes(cur)){
      const t = getCustomTheme(cur);
      base = (t && t.base && BUILTIN_THEMES.includes(t.base)) ? t.base : (getCurrentBaseTheme() || "dark");
    }
    const idx = Math.max(0, BUILTIN_THEMES.indexOf(base));
    const nxt = BUILTIN_THEMES[(idx + 1) % BUILTIN_THEMES.length];
    applyTheme(nxt);
  }

  function _readCSSVar(k){
    try{
      const v = getComputedStyle(document.body).getPropertyValue(k);
      return (v || "").trim();
    }catch(_){ return ""; }
  }

  function _exportThemeObject(themeId){
    const base = BUILTIN_THEMES.includes(themeId)
      ? themeId
      : ((getCustomTheme(themeId) && getCustomTheme(themeId).base) || getCurrentBaseTheme() || "dark");
    const name = _themeLabel(themeId);
    const tokens = {};
    for (const k of THEME_EXPORT_KEYS){
      const v = _readCSSVar(k);
      if (v) tokens[k] = v;
    }
    return { schema: "scalpel-theme/v1", name, base, tokens };
  }

  function _downloadJSON(obj, filename){
    try{
      const s = JSON.stringify(obj, null, 2);
      const blob = new Blob([s], {type: "application/json"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(()=>URL.revokeObjectURL(url), 2000);
    }catch(e){ console.error("Theme export failed", e); }
  }

  function _randId(){
    return "theme_" + Math.random().toString(16).slice(2) + "_" + Date.now().toString(16);
  }

  function _upsertCustomTheme(theme){
    const st = _loadThemeStore();
    const arr = Array.isArray(st.themes) ? st.themes : [];
    const out = [];
    let found = false;
    for (const t of arr){
      if (!t || typeof t !== "object" || !t.id) continue;
      if (t.id === theme.id){ out.push(theme); found = true; }
      else out.push(t);
    }
    if (!found) out.push(theme);
    st.themes = out;
    _saveThemeStore(st);
  }

  function _deleteCustomTheme(id){
    const st = _loadThemeStore();
    const arr = Array.isArray(st.themes) ? st.themes : [];
    st.themes = arr.filter(t => !(t && t.id === id));
    _saveThemeStore(st);
  }

  // Theme manager modal
  function _el(id){ return document.getElementById(id); }
  function openThemeModal(){
    const m = _el("themeModal");
    if (!m) return;
    m.style.display = "flex";
    const pick = _el("themePick");
    if (pick){
      pick.innerHTML = "";
      for (const t of BUILTIN_THEMES){
        const o = document.createElement("option");
        o.value = t;
        o.textContent = THEME_LABEL[t] || t;
        pick.appendChild(o);
      }
      const customs = listCustomThemes();
      if (customs.length){
        const og = document.createElement("optgroup");
        og.label = "Custom";
        for (const t of customs){
          const o = document.createElement("option");
          o.value = t.id;
          o.textContent = t.name;
          og.appendChild(o);
        }
        pick.appendChild(og);
      }
      const cur = getCurrentTheme() || getPreferredTheme();
      if (themeExists(cur)) pick.value = cur;
    }
    _renderThemePreview();
    _updateThemeBaseLabel();
  }

  function closeThemeModal(){
    const m = _el("themeModal");
    if (m) m.style.display = "none";
  }

  function _selectedThemeId(){
    const pick = _el("themePick");
    return pick ? pick.value : (getCurrentTheme() || getPreferredTheme());
  }

  function _updateThemeBaseLabel(){
    const baseEl = _el("themeBase");
    if (!baseEl) return;
    const id = _selectedThemeId();
    let base = id;
    if (!BUILTIN_THEMES.includes(id)){
      const t = getCustomTheme(id);
      base = (t && t.base) ? t.base : (getCurrentBaseTheme() || "dark");
    }
    baseEl.textContent = (THEME_LABEL[base] || base);
  }

  function _renderThemePreview(){
    const box = _el("themeSwatches");
    if (!box) return;
    box.innerHTML = "";
    for (let i = 1; i <= 8; i++){
      const d = document.createElement("div");
      d.className = "sw c" + i;
      box.appendChild(d);
    }
  }

  function _cloneCurrentTheme(){
    const cur = getCurrentTheme() || getPreferredTheme();
    const base = BUILTIN_THEMES.includes(cur) ? cur : ((getCustomTheme(cur) && getCustomTheme(cur).base) || getCurrentBaseTheme() || "dark");
    const nm = prompt("Name for the cloned theme:", `My ${THEME_LABEL[base] || base}`);
    if (!nm) return;
    const tokens = {};
    for (const k of THEME_EXPORT_KEYS){
      const v = _readCSSVar(k);
      if (v) tokens[k] = v;
    }
    const id = _randId();
    _upsertCustomTheme({ schema: "scalpel-theme/v1", id, name: nm, base, tokens });
    applyTheme(id);
    openThemeModal();
  }

  function _exportSelectedTheme(){
    const id = _selectedThemeId();
    const obj = _exportThemeObject(id);
    const slug = (obj.name || "theme").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g, "");
    _downloadJSON(obj, `scalpel-theme-${slug || "export"}.json`);
  }

  function _importThemeFile(file){
    const r = new FileReader();
    r.onload = () => {
      try{
        const txt = String(r.result || "");
        const obj = JSON.parse(txt);
        let themeObj = null;
        if (obj && typeof obj === "object" && obj.tokens && typeof obj.tokens === "object"){
          themeObj = obj;
        }else{
          // tokens-only file
          const toks = {};
          for (const k of Object.keys(obj || {})){
            if (/^--[a-zA-Z0-9_-]+$/.test(k)) toks[k] = String(obj[k]);
          }
          themeObj = { schema: "scalpel-theme/v1", tokens: toks };
        }
        const name = (themeObj.name && typeof themeObj.name === "string") ? themeObj.name : "Imported theme";
        const base = (themeObj.base && BUILTIN_THEMES.includes(themeObj.base)) ? themeObj.base : (getCurrentBaseTheme() || "dark");
        const tokens = (themeObj.tokens && typeof themeObj.tokens === "object") ? themeObj.tokens : {};
        const id = (themeObj.id && typeof themeObj.id === "string") ? themeObj.id : _randId();
        const finalId = themeExists(id) ? _randId() : id;
        _upsertCustomTheme({ schema: "scalpel-theme/v1", id: finalId, name, base, tokens });
        applyTheme(finalId);
        openThemeModal();
      }catch(e){
        alert("Invalid theme JSON");
        console.error("Theme import failed", e);
      }
    };
    r.readAsText(file);
  }

  function _deleteSelectedTheme(){
    const id = _selectedThemeId();
    if (BUILTIN_THEMES.includes(id)) return;
    const t = getCustomTheme(id);
    if (!t) return;
    if (!confirm(`Delete custom theme '${t.name}'?`)) return;
    _deleteCustomTheme(id);
    applyTheme("dark");
    openThemeModal();
  }

  function _bindThemeModal(){
    const m = _el("themeModal");
    if (!m) return;
    const close = () => closeThemeModal();
    const c1 = _el("themeClose");
    const c2 = _el("themeClose2");
    if (c1) c1.addEventListener("click", close);
    if (c2) c2.addEventListener("click", close);
    m.addEventListener("click", (e)=>{ if (e.target === m) close(); });

    const pick = _el("themePick");
    if (pick) pick.addEventListener("change", ()=>{ _updateThemeBaseLabel(); _renderThemePreview(); });

    const applyBtn = _el("themeApply");
    if (applyBtn) applyBtn.addEventListener("click", ()=>{ applyTheme(_selectedThemeId()); closeThemeModal(); });

    const cloneBtn = _el("themeClone");
    if (cloneBtn) cloneBtn.addEventListener("click", ()=>{ _cloneCurrentTheme(); });

    const editBtn = _el("themeEdit");
    if (editBtn) editBtn.addEventListener("click", ()=>{ try { openThemeEditModal(); } catch (_) {} });

    const expBtn = _el("themeExport");
    if (expBtn) expBtn.addEventListener("click", ()=>{ _exportSelectedTheme(); });

    const impBtn = _el("themeImport");
    const impFile = _el("themeImportFile");
    if (impBtn && impFile){
      impBtn.addEventListener("click", ()=> impFile.click());
      impFile.addEventListener("change", ()=>{
        const f = impFile.files && impFile.files[0];
        if (f) _importThemeFile(f);
        impFile.value = "";
      });
    }

    const delBtn = _el("themeDelete");
    if (delBtn) delBtn.addEventListener("click", ()=>{ _deleteSelectedTheme(); });
  }

  
  // Theme editor (palette UI)
  // -----------------------------
  const THEME_EDIT_CORE = [
    { k: "--accent", label: "Accent", rgb: "--accent-rgb" },
    { k: "--warn",   label: "Warn",   rgb: "--warn-rgb"   },
    { k: "--bad",    label: "Danger", rgb: "--bad-rgb"    },
    { k: "--bg",     label: "Background" },
    { k: "--panel",  label: "Panel" },
    { k: "--text",   label: "Text" },

    { k: "--block",        label: "Task block A" },
    { k: "--block2",       label: "Task block B" },
    { k: "--task-title-text", label: "Task title text" },
    { k: "--task-body-text", label: "Task subtitle text" },
    { k: "--task-code-text", label: "Task UUID text" },
    { k: "--note-text",    label: "Note text" },
    { k: "--note-meta",    label: "Note meta" },
  ];

  function _clamp01(x){ x = Number(x); if (!isFinite(x)) return 0; return Math.max(0, Math.min(1, x)); }

  function _hexToRgb(hex){
    if (!hex) return null;
    let s = String(hex).trim();
    if (!s) return null;
    if (s[0] === "#") s = s.slice(1);
    if (s.length === 3) s = s[0]+s[0]+s[1]+s[1]+s[2]+s[2];
    if (!/^[0-9a-fA-F]{6}$/.test(s)) return null;
    const r = parseInt(s.slice(0,2), 16);
    const g = parseInt(s.slice(2,4), 16);
    const b = parseInt(s.slice(4,6), 16);
    return {r,g,b};
  }

  function _rgbToHex(r,g,b){
    const h = (n)=>("0"+Math.max(0,Math.min(255,Math.round(Number(n)||0))).toString(16)).slice(-2);
    return "#" + h(r) + h(g) + h(b);
  }

  function _parseCssColorToRgba(s){
    if (s == null) return null;
    const v = String(s).trim();
    if (!v) return null;
    // rgba()
    let m = v.match(/^rgba\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$/i);
    if (m) return {r:Number(m[1]), g:Number(m[2]), b:Number(m[3]), a:_clamp01(m[4])};
    // rgb()
    m = v.match(/^rgb\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$/i);
    if (m) return {r:Number(m[1]), g:Number(m[2]), b:Number(m[3]), a:1};
    // #hex
    if (v[0] === "#"){
      const rgb = _hexToRgb(v);
      if (rgb) return {r:rgb.r, g:rgb.g, b:rgb.b, a:1};
    }
    return null;
  }

  function _rgbaCss(rgba){
    if (!rgba) return "";
    const r = Math.round(Number(rgba.r)||0), g = Math.round(Number(rgba.g)||0), b = Math.round(Number(rgba.b)||0);
    const a = _clamp01(rgba.a == null ? 1 : rgba.a);
    if (a >= 0.999) return "rgb(" + r + "," + g + "," + b + ")";
    return "rgba(" + r + "," + g + "," + b + "," + a.toFixed(3) + ")";
  }

  function _teState(){
    if (!globalThis.__scalpel_theme_edit_state) globalThis.__scalpel_theme_edit_state = {};
    return globalThis.__scalpel_theme_edit_state;
  }

  function _teBuild(){
    const notesBox = _el("themeEditNotes");
    const coreBox = _el("themeEditCore");
    if (!notesBox || !coreBox) return;
    if (notesBox.childElementCount) return; // already built

    // Notes swatches c1..c8
    for (let i = 1; i <= 8; i++){
      const row = document.createElement("div");
      row.className = "r";
      row.dataset.i = String(i);

      const k = document.createElement("div");
      k.className = "k";
      k.textContent = "c" + i;

      const sw = document.createElement("div");
      sw.className = "sw";

      const c = document.createElement("input");
      c.type = "color";
      c.id = "teNc" + i;

      const a = document.createElement("input");
      a.type = "range";
      a.min = "10";
      a.max = "100";
      a.step = "1";
      a.id = "teAc" + i;

      const av = document.createElement("div");
      av.className = "aval mono";
      av.id = "teAvc" + i;
      av.textContent = "100%";

      row.appendChild(k);
      row.appendChild(sw);
      row.appendChild(c);
      row.appendChild(a);
      row.appendChild(av);
      notesBox.appendChild(row);
    }

    // Core tokens
    for (const it of THEME_EDIT_CORE){
      const row = document.createElement("div");
      row.className = "r";
      row.dataset.k = it.k;

      const k = document.createElement("div");
      k.className = "k";
      k.textContent = it.label;

      const sw = document.createElement("div");
      sw.className = "sw";

      const c = document.createElement("input");
      c.type = "color";
      c.id = "teCoreColor_" + it.k.replace(/^--/,"");

      const t = document.createElement("input");
      t.type = "text";
      t.className = "mono";
      t.id = "teCoreText_" + it.k.replace(/^--/,"");
      t.placeholder = it.k;

      row.appendChild(k);
      row.appendChild(sw);
      row.appendChild(c);
      row.appendChild(t);
      coreBox.appendChild(row);
    }
  }

  function _teLoad(){
    _teBuild();
    const st = _teState();
    st.prevTheme = getPreferredTheme();
    st.live = true;

    const title = _el("themeEditTitle");
    if (title) title.textContent = "Editing current theme: " + _themeLabel(st.prevTheme);

    const nameIn = _el("themeEditNameInput");
    if (nameIn){
      if (BUILTIN_THEMES.includes(st.prevTheme)) nameIn.value = (_themeLabel(st.prevTheme) + " Custom");
      else nameIn.value = _themeLabel(st.prevTheme);
    }

    // Notes
    const alphas = [];
    for (let i = 1; i <= 8; i++){
      const bg = _readCSSVar("--note-c" + i + "-bg");
      const rgba = _parseCssColorToRgba(bg);
      const colIn = _el("teNc" + i);
      const aIn = _el("teAc" + i);
      const av = _el("teAvc" + i);
      const row = colIn && colIn.closest(".r");
      const sw = row ? row.querySelector(".sw") : null;

      if (rgba && colIn && aIn){
        colIn.disabled = false; aIn.disabled = false;
        colIn.value = _rgbToHex(rgba.r, rgba.g, rgba.b);
        const ap = Math.round(_clamp01(rgba.a) * 100);
        aIn.value = String(ap);
        if (av) av.textContent = ap + "%";
        if (sw) sw.style.background = _rgbaCss(rgba);
        alphas.push(ap);
      }else{
        if (colIn) colIn.disabled = true;
        if (aIn) aIn.disabled = true;
        if (av) av.textContent = "—";
        if (sw) sw.style.background = "";
      }
    }
    // Global alpha slider
    const ga = _el("themeEditNoteAlpha");
    const gav = _el("themeEditNoteAlphaVal");
    if (ga){
      const v = alphas.length ? Math.round(alphas.reduce((a,b)=>a+b,0)/alphas.length) : 90;
      ga.value = String(v);
      if (gav) gav.textContent = v + "%";
    }

    // Core
    for (const it of THEME_EDIT_CORE){
      const v = _readCSSVar(it.k);
      const rgba = _parseCssColorToRgba(v);
      const cIn = _el("teCoreColor_" + it.k.replace(/^--/,""));
      const tIn = _el("teCoreText_" + it.k.replace(/^--/,""));
      const row = tIn && tIn.closest(".r");
      const sw = row ? row.querySelector(".sw") : null;
      if (tIn) tIn.value = v || "";
      if (rgba && cIn){
        cIn.disabled = false;
        cIn.value = _rgbToHex(rgba.r, rgba.g, rgba.b);
        if (sw) sw.style.background = _rgbaCss(rgba);
      }else if (cIn){
        cIn.disabled = true;
        if (sw) sw.style.background = "";
      }
    }
  }

  function _teApplyNote(i){
    const colIn = _el("teNc" + i);
    const aIn = _el("teAc" + i);
    const av = _el("teAvc" + i);
    if (!colIn || !aIn || colIn.disabled || aIn.disabled) return;
    const rgb = _hexToRgb(colIn.value);
    if (!rgb) return;
    const a = _clamp01(Number(aIn.value)/100);
    const bg = _rgbaCss({r:rgb.r,g:rgb.g,b:rgb.b,a});
    const bd = _rgbaCss({r:rgb.r,g:rgb.g,b:rgb.b,a: _clamp01(a + 0.22)});
    document.body.style.setProperty("--note-c" + i + "-bg", bg);
    document.body.style.setProperty("--note-c" + i + "-bd", bd);
    if (av) av.textContent = Math.round(a*100) + "%";
    const row = colIn.closest(".r");
    const sw = row ? row.querySelector(".sw") : null;
    if (sw) sw.style.background = bg;
  }

  function _teApplyCore(k){
    const id = k.replace(/^--/,"");
    const tIn = _el("teCoreText_" + id);
    const cIn = _el("teCoreColor_" + id);
    if (!tIn) return;
    const v = String(tIn.value||"").trim();
    if (v) document.body.style.setProperty(k, v);
    const rgba = _parseCssColorToRgba(v);
    const row = tIn.closest(".r");
    const sw = row ? row.querySelector(".sw") : null;
    if (rgba && sw) sw.style.background = _rgbaCss(rgba);

    // keep rgb companion in sync when applicable
    const it = THEME_EDIT_CORE.find(x => x.k === k);
    if (it && it.rgb && rgba){
      document.body.style.setProperty(it.rgb, Math.round(rgba.r) + "," + Math.round(rgba.g) + "," + Math.round(rgba.b));
    }
  }

  function _teCollectTokens(){
    const tokens = {};
    // notes palette
    for (let i = 1; i <= 8; i++){
      const colIn = _el("teNc" + i);
      const aIn = _el("teAc" + i);
      if (!colIn || !aIn || colIn.disabled || aIn.disabled) continue;
      const rgb = _hexToRgb(colIn.value);
      if (!rgb) continue;
      const a = _clamp01(Number(aIn.value)/100);
      const bg = _rgbaCss({r:rgb.r,g:rgb.g,b:rgb.b,a});
      const bd = _rgbaCss({r:rgb.r,g:rgb.g,b:rgb.b,a:_clamp01(a+0.22)});
      tokens["--note-c" + i + "-bg"] = bg;
      tokens["--note-c" + i + "-bd"] = bd;
    }
    // core
    for (const it of THEME_EDIT_CORE){
      const id = it.k.replace(/^--/,"");
      const tIn = _el("teCoreText_" + id);
      if (!tIn) continue;
      const v = String(tIn.value||"").trim();
      if (!v) continue;
      tokens[it.k] = v;
      const rgba = _parseCssColorToRgba(v);
      if (it.rgb && rgba) tokens[it.rgb] = Math.round(rgba.r) + "," + Math.round(rgba.g) + "," + Math.round(rgba.b);
    }
    return tokens;
  }

  function openThemeEditModal(){
    const m = _el("themeEditModal");
    if (!m) return;
    m.style.display = "flex";
    _teLoad();
    _bindThemeEditModal();
  }

  function closeThemeEditModal(cancel){
    const m = _el("themeEditModal");
    if (!m) return;
    m.style.display = "none";
    const st = _teState();
    // restore saved theme when cancelling
    try{
      if (cancel && st && st.prevTheme) applyTheme(st.prevTheme);
    }catch(_){ }
  }

  function _bindThemeEditModal(){
    const m = _el("themeEditModal");
    if (!m || m.__bound) return;
    m.__bound = true;

    const close = () => closeThemeEditModal(true);
    const c1 = _el("themeEditClose");
    const c2 = _el("themeEditCancel");
    if (c1) c1.addEventListener("click", close);
    if (c2) c2.addEventListener("click", close);
    m.addEventListener("click", (e)=>{ if (e.target === m) close(); });

    const reset = _el("themeEditReset");
    if (reset) reset.addEventListener("click", ()=>{ try { applyTheme(getPreferredTheme()); } catch(_){} _teLoad(); });

    // notes handlers
    for (let i = 1; i <= 8; i++){
      const colIn = _el("teNc" + i);
      const aIn = _el("teAc" + i);
      if (colIn) colIn.addEventListener("input", ()=>_teApplyNote(i));
      if (aIn) aIn.addEventListener("input", ()=>_teApplyNote(i));
    }
    const ga = _el("themeEditNoteAlpha");
    const gav = _el("themeEditNoteAlphaVal");
    if (ga) ga.addEventListener("input", ()=>{
      const v = Math.max(10, Math.min(100, Number(ga.value)||100));
      if (gav) gav.textContent = v + "%";
      for (let i = 1; i <= 8; i++){
        const aIn = _el("teAc" + i);
        if (aIn && !aIn.disabled){ aIn.value = String(v); _teApplyNote(i); }
      }
    });

    // core handlers
    for (const it of THEME_EDIT_CORE){
      const id = it.k.replace(/^--/,"");
      const cIn = _el("teCoreColor_" + id);
      const tIn = _el("teCoreText_" + id);
      if (cIn && tIn){
        cIn.addEventListener("input", ()=>{
          const rgb = _hexToRgb(cIn.value);
          if (!rgb) return;
          tIn.value = _rgbToHex(rgb.r,rgb.g,rgb.b);
          _teApplyCore(it.k);
        });
      }
      if (tIn) tIn.addEventListener("input", ()=>_teApplyCore(it.k));
    }

    const save = _el("themeEditSave");
    if (save) save.addEventListener("click", ()=>{
      const cur = getPreferredTheme();
      const tokens = _teCollectTokens();
      const nameIn = _el("themeEditNameInput");
      const desiredName = nameIn ? String(nameIn.value||"").trim() : "";
      if (BUILTIN_THEMES.includes(cur)){
        const id = "custom_" + _newId();
        const theme = { id, name: desiredName || (_themeLabel(cur) + " Custom"), base: cur, tokens };
        _upsertCustomTheme(theme);
        setPreferredTheme(id);
        applyTheme(id);
      }else{
        const ex = getCustomTheme(cur) || { id: cur, name: desiredName || _themeLabel(cur), base: getCurrentBaseTheme() || "dark", tokens: {} };
        ex.name = desiredName || ex.name || cur;
        ex.tokens = Object.assign({}, ex.tokens || {}, tokens);
        _upsertCustomTheme(ex);
        setPreferredTheme(ex.id);
        applyTheme(ex.id);
      }
      closeThemeEditModal(false);
      try{ if (typeof openThemeModal === "function") { /* keep theme manager open state unchanged */ } }catch(_){}
    });
  }


// Expose open/close for init
  globalThis.openThemeModal = openThemeModal;
  globalThis.closeThemeModal = closeThemeModal;
  globalThis.__scalpel_bindThemeModal = _bindThemeModal;


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
    __scalpelInvalidateTimeCaches("dayIndex");
  }
  recomputeDayStarts();
  function setRangeMeta() {
    const a = new Date(dayStarts[0]);
    const b = new Date(dayStarts[dayStarts.length - 1]);
    const fmt = (d) => `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
    elRange.textContent = `${fmt(a)} → ${fmt(b)}`;
    elMeta.textContent = `Due-based view • Snap ${SNAP}m • Workhours ${pad2(Math.floor(WORK_START/60))}:${pad2(WORK_START%60)}-${pad2(Math.floor(WORK_END/60))}:${pad2(WORK_END%60)} • ${(DATA.tasks||[]).length} tasks`;
    try { updateContextMeta(); } catch (_) {}
  }
  setRangeMeta();


  // -----------------------------
  // Day balance (active day)
  // -----------------------------
  const activeDayKey = "scalpel.activeDayIndex";
  let activeDayIndex = (() => {
    let di = null;
    try {
      const v = globalThis.__scalpel_kvGet(activeDayKey);
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
    try { globalThis.__scalpel_kvSet(activeDayKey, String(activeDayIndex)); } catch (_) {}
  }

  function applyActiveDayHighlight() {
    const headers = document.querySelectorAll(".day-h");
    for (let i = 0; i < headers.length; i++) {
      const on = (i === activeDayIndex);
      headers[i].classList.toggle("active-day", on);
      if (on) headers[i].setAttribute("aria-current", "date");
      else headers[i].removeAttribute("aria-current");
    }
    const cols = document.querySelectorAll(".day-col");
    for (let i = 0; i < cols.length; i++) {
      cols[i].classList.toggle("active-day", i === activeDayIndex);
    }
  }

  function updateContextMeta() {
    if (!elCtxMeta) return;
    const dayCount = (Number.isInteger(DAYS) && DAYS > 0) ? DAYS : dayStarts.length;
    let dayText = "Day —";
    try {
      if (Number.isInteger(activeDayIndex) && activeDayIndex >= 0 && activeDayIndex < dayStarts.length) {
        const d = new Date(dayStarts[activeDayIndex]);
        const wd = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()];
        dayText = `Day ${wd} ${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
      }
    } catch (_) {}
    elCtxMeta.textContent = `${dayText} • ${dayCount}d`;
  }
  updateContextMeta();

  function setActiveDay(di, persist) {
    if (!Number.isInteger(di)) return false;
    if (!Number.isFinite(DAYS) || DAYS <= 0) return false;
    const next = clamp(di, 0, DAYS - 1);
    const changed = (next !== activeDayIndex);
    activeDayIndex = next;
    if (persist !== false) saveActiveDay();
    applyActiveDayHighlight();
    updateContextMeta();
    try { if (lastDayVis) renderDayBalance(activeDayIndex, lastDayVis); } catch (_) {}
    return changed;
  }

  function setActiveDayFromUuid(uuid) {
    const cur = plan.get(uuid);
    const dueMs = cur && Number.isFinite(cur.due_ms) ? cur.due_ms : (tasksByUuid.get(uuid) ? tasksByUuid.get(uuid).due_ms : null);
    if (!Number.isFinite(dueMs)) return;
    const di = dayIndexFromMs(dueMs);
    if (di === null) return;
    setActiveDay(di, true);
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
