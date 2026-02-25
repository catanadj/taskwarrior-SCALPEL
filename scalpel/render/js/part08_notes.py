# scalpel/render/js/part08_notes.py
from __future__ import annotations

JS_PART = r'''// Sticky notes (local planning overlays)
  // ---------------------------------------------
  // Persistence policy:
  // - Global store (survives regenerated HTML / view_key changes)
  // - JSON schema is stable so we can later load from a disk file

  const NOTES_SCHEMA = "scalpel-notes/v1";
  const NOTES_KEY = "scalpel:notes:v1";
  const NOTES_UI_KEY = "scalpel:notes:ui:v1";

  const DOW_LABELS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

  // Note color keys: c1..c8 (palette)
  function _sanitizeColorKey(k){
    const s = String(k || "").trim();
    if (!s) return "";
    return (/^c[1-8]$/.test(s)) ? s : "";
  }

  function _noteColorKey(note){
    try{
      return _sanitizeColorKey(note && note.style && note.style.color);
    }catch(_){
      return "";
    }
  }
// ---------------------------------------------
// Micro-interactions: stable tilt + snap pulse
// ---------------------------------------------
function _hash32FNV1a(s){
  // FNV-1a 32-bit
  let h = 2166136261 >>> 0;
  const str = String(s || "");
  for (let i = 0; i < str.length; i++){
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0);
}

function _tiltVarsForId(id){
  const h = _hash32FNV1a(String(id || ""));
  // Base tilt in [-0.8, +0.8] degrees (stable per id)
  const tilt = ((h % 161) - 80) / 100;
  // Hover tilt sign stable per id (keeps "lift" direction consistent)
  const sign = (h & 1) ? 1 : -1;
  const hover = sign * 1.5; // degrees
  return { tilt, hover };
}

function _applyTiltVars(el, id, isPill){
  if (!el) return;
  const v = _tiltVarsForId(id);
  try{
    if (isPill) {
      el.style.setProperty("--pill-tilt", `${v.tilt}deg`);
      el.style.setProperty("--pill-hover", `${v.hover}deg`);
    } else {
      el.style.setProperty("--note-tilt", `${v.tilt}deg`);
      el.style.setProperty("--note-hover", `${v.hover}deg`);
    }
  }catch(_){ }
}

let pendingPulse = null; // { id, dayIndex }

function _setPendingPulse(noteId, dayIndex){
  pendingPulse = { id: String(noteId), dayIndex: Number(dayIndex) };
}

function _pulseEl(el){
  if (!el) return;
  try{
    el.classList.remove("snap-pulse");
    // force restart
    void el.offsetWidth;
    el.classList.add("snap-pulse");
  }catch(_){
    try{ el.classList.add("snap-pulse"); }catch(__){ }
  }
  setTimeout(() => { try{ el.classList.remove("snap-pulse"); }catch(_){} }, 160);
}




  function _notesNow(){ return Date.now(); }

  function _notesUuid(){
    try{
      if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") return globalThis.crypto.randomUUID();
    }catch(_){ }
    // Fallback: 32 hex chars
    const rnd = (n) => Math.floor(Math.random() * n);
    const hex = () => rnd(16).toString(16);
    let s = "";
    for (let i = 0; i < 32; i++) s += hex();
    return s;
  }

  function _notesEmptyDoc(){
    const now = _notesNow();
    return {
      schema: NOTES_SCHEMA,
      v: 1,
      created_ms: now,
      modified_ms: now,
      default_tz: BUCKET_TZ,
      display_tz: DISPLAY_TZ,
      notes: []
    };
  }

  function _isObj(x){ return x && typeof x === "object"; }

  function _uniqSortedDows(arr){
    if (!Array.isArray(arr)) return [];
    const s = new Set();
    for (const x of arr) {
      const n = Number(x);
      if (!Number.isFinite(n)) continue;
      const nn = ((Math.round(n) % 7) + 7) % 7;
      s.add(nn);
    }
    return Array.from(s).sort((a,b) => a-b);
  }

  function fmtRepeatDows(dows){
    const arr = _uniqSortedDows(dows);
    return arr.map(i => DOW_LABELS[i]).join(",");
  }

  function dowForDayIndex(di){
    try{ return new Date(dayStarts[di]).getUTCDay(); } catch (_) { return null; }
  }

  function dowFromYmd(ymd){
    try{
      const ms = msFromYmd(String(ymd));
      return new Date(ms).getUTCDay();
    }catch(_){
      return null;
    }
  }

  function _normNote(n){
    const now = _notesNow();
    const o = _isObj(n) ? n : {};
    const id = (typeof o.id === "string" && o.id.trim()) ? o.id.trim() : _notesUuid();
    const text = (o.text == null) ? "" : String(o.text);

    let repeat_dows = [];
    try{
      const raw = o.repeat_dows;
      if (Array.isArray(raw)) repeat_dows = _uniqSortedDows(raw);
      else if (typeof raw === "string" && raw.trim()) {
        repeat_dows = _uniqSortedDows(raw.split(/\s*,\s*/).map(x => parseInt(x, 10)));
      }
    }catch(_){ repeat_dows = []; }

    // One-off day
    let day = (typeof o.bucket_day_key === "string" && o.bucket_day_key.trim()) ? o.bucket_day_key.trim() : null;
    if (repeat_dows.length) day = null;  // contract: repeating notes are not bound to a specific date

    const sm = (o.start_min == null) ? null : Number(o.start_min);
    const em = (o.end_min == null) ? null : Number(o.end_min);
    const start_min = Number.isFinite(sm) ? Math.round(sm) : null;
    const end_min = Number.isFinite(em) ? Math.round(em) : null;

    const pinned = !!o.pinned;
    const archived = !!o.archived;
    const scenario = (typeof o.scenario === "string" && o.scenario.trim()) ? o.scenario.trim() : "main";
    let style = _isObj(o.style) ? o.style : {};
    if (!_isObj(style)) style = {};
    const ckey = _sanitizeColorKey(style.color);
    style = { ...style, color: ckey };

    const created_ms = Number.isFinite(Number(o.created_ms)) ? Number(o.created_ms) : now;
    const modified_ms = Number.isFinite(Number(o.modified_ms)) ? Number(o.modified_ms) : now;

    return {
      id,
      text,
      bucket_day_key: day,
      start_min,
      end_min,
      repeat_dows,
      pinned,
      archived,
      scenario,
      style,
      created_ms,
      modified_ms,
    };
  }

  let notesDoc = null;
  let notesById = new Map();

  function loadNotes(){
    let doc = null;
    try { doc = (typeof globalThis.__scalpel_kvGetJSON === "function") ? globalThis.__scalpel_kvGetJSON(NOTES_KEY, null) : null; } catch (_) { doc = null; }

    if (!_isObj(doc) || doc.schema !== NOTES_SCHEMA || !Array.isArray(doc.notes)) {
      doc = _notesEmptyDoc();
    }

    // Keep doc-level tz info for diagnostics only
    if (typeof doc.default_tz !== "string") doc.default_tz = BUCKET_TZ;
    if (typeof doc.display_tz !== "string") doc.display_tz = DISPLAY_TZ;

    notesDoc = doc;
    notesById = new Map();

    for (const raw of (doc.notes || [])) {
      const nn = _normNote(raw);
      notesById.set(nn.id, nn);
    }

    // Normalize stored doc to current structure (no-op if already ok)
    syncNotesDocFromIndex(false);
  }

  function syncNotesDocFromIndex(persist){
    if (!notesDoc) notesDoc = _notesEmptyDoc();
    const arr = Array.from(notesById.values());
    notesDoc.notes = arr;
    notesDoc.modified_ms = _notesNow();
    if (typeof notesDoc.created_ms !== "number") notesDoc.created_ms = notesDoc.modified_ms;

    // Refresh tz hints (doc-level)
    notesDoc.default_tz = BUCKET_TZ;
    notesDoc.display_tz = DISPLAY_TZ;

    if (persist) {
      try {
        if (typeof globalThis.__scalpel_kvSetJSON === "function") globalThis.__scalpel_kvSetJSON(NOTES_KEY, notesDoc);
        else localStorage.setItem(NOTES_KEY, JSON.stringify(notesDoc));
      } catch (_) {}
    }
  }

  function saveNotes(){ syncNotesDocFromIndex(true); }

  function getNote(id){ return notesById.get(String(id)) || null; }

  function upsertNote(note, persist){
    const nn = _normNote(note);
    nn.modified_ms = _notesNow();
    notesById.set(nn.id, nn);
    if (persist) saveNotes();
    else syncNotesDocFromIndex(false);
    return nn;
  }

  function removeNote(id, persist){
    const key = String(id);
    notesById.delete(key);
    if (persist) saveNotes();
    else syncNotesDocFromIndex(false);
  }

  function clearArchivedNotes(){
    const before = notesById.size;
    for (const [id, n] of notesById.entries()) {
      if (n && n.archived) notesById.delete(id);
    }
    const after = notesById.size;
    saveNotes();
    return before - after;
  }

  function listNotesSorted(){
    const arr = Array.from(notesById.values());
    arr.sort((a, b) => {
      // pinned first, then most recently modified
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      const am = Number(a.modified_ms || 0);
      const bm = Number(b.modified_ms || 0);
      if (am !== bm) return bm - am;
      return String(a.id).localeCompare(String(b.id));
    });
    return arr;
  }

  function dayIndexFromYmd(ymd){
    try {
      const ms = msFromYmd(String(ymd));
      return dayIndexFromMs(ms);
    } catch (_) {
      return null;
    }
  }

  function noteLabelForDay(note, di){
    if (!note) return "";
    if (note.start_min == null || note.end_min == null) return "All-day";
    if (di == null) return `${_hmFromMin(note.start_min)}–${_hmFromMin(note.end_min)}`;
    const ds = dayStarts[di];
    const sMs = ds + note.start_min * 60000;
    const eMs = ds + note.end_min * 60000;
    return `${fmtHm(sMs)}–${fmtHm(eMs)}`;
  }

  function noteAppliesToDay(note, di, dayKey){
    if (!note || note.archived) return false;
    if (note.bucket_day_key) return note.bucket_day_key === dayKey;
    const rd = Array.isArray(note.repeat_dows) ? note.repeat_dows : [];
    if (!rd.length) return false;
    const dow = dowForDayIndex(di);
    return (dow != null) && rd.includes(dow);
  }

  function _hmFromMin(min){
    const m = clamp(Math.round(min), 0, 24*60);
    const hh = Math.floor(m / 60);
    const mm = m % 60;
    return `${pad2(hh)}:${pad2(mm)}`;
  }

  function _minFromHm(s){
    const m = /^([0-1]?\d|2[0-3]):([0-5]\d)$/.exec(String(s||""));
    if (!m) return null;
    return (parseInt(m[1], 10) * 60) + parseInt(m[2], 10);
  }

  function createNote(text){
    const now = _notesNow();
    const n = {
      id: _notesUuid(),
      text: (text == null) ? "" : String(text),
      bucket_day_key: null,
      start_min: null,
      end_min: null,
      repeat_dows: [],
      pinned: false,
      archived: false,
      scenario: "main",
      style: { color: "" },
      created_ms: now,
      modified_ms: now,
    };
    return upsertNote(n, true);
  }

  function placeNoteAllDay(noteId, dayIndex){
    const n = getNote(noteId);
    if (!n) return;

    const ymd = ymdFromMs(dayStarts[dayIndex]);

    if (n.repeat_dows && n.repeat_dows.length) {
      // repeating: affect the template (all matching days)
      n.bucket_day_key = null;
      n.start_min = null;
      n.end_min = null;
    } else {
      // one-off
      n.bucket_day_key = ymd;
      n.start_min = null;
      n.end_min = null;
    }

    upsertNote(n, true);
    _setPendingPulse(noteId, dayIndex);
  }

  function placeNoteAt(noteId, dayIndex, minute){
    const n = getNote(noteId);
    if (!n) return;

    const ymd = ymdFromMs(dayStarts[dayIndex]);
    const m = clamp(Math.round(minute), 0, 24*60);

    // Preserve prior duration if it exists; otherwise default to 30m.
    let dur = 30;
    if (n.start_min != null && n.end_min != null && Number.isFinite(n.start_min) && Number.isFinite(n.end_min)) {
      dur = Math.max(5, Math.min(8*60, Math.round(n.end_min - n.start_min)));
    }

    let s = m;
    let e = s + dur;

    // Keep within day
    if (e > 24*60) { e = 24*60; s = Math.max(0, e - dur); }

    if (n.repeat_dows && n.repeat_dows.length) {
      // repeating: affect the template (all matching days)
      n.bucket_day_key = null;
    } else {
      n.bucket_day_key = ymd;
    }

    n.start_min = s;
    n.end_min = e;

    upsertNote(n, true);
    _setPendingPulse(noteId, dayIndex);
  }

  // ---------------------------------------------
  // Calendar rendering helpers
  // ---------------------------------------------
  function renderHeaderNotes(){
    const headers = document.querySelectorAll(".day-h");
    for (const h of headers) {
      const c = h.querySelector(".day-notes");
      if (c) c.innerHTML = "";
    }
    if (!notesAllOn) return;

    const byDay = Array.from({length: DAYS}, () => []);

    for (const n of notesById.values()) {
      if (!n || n.archived) continue;
      // all-day only
      if (n.start_min != null || n.end_min != null) continue;

      if (n.bucket_day_key) {
        const di = dayIndexFromYmd(n.bucket_day_key);
        if (di == null) continue;
        byDay[di].push(n);
      } else if (n.repeat_dows && n.repeat_dows.length) {
        for (let di = 0; di < DAYS; di++) {
          const dayKey = ymdFromMs(dayStarts[di]);
          if (noteAppliesToDay(n, di, dayKey)) byDay[di].push(n);
        }
      }
    }

    for (let di = 0; di < DAYS; di++) {
      const h = headers[di];
      if (!h) continue;
      const c = h.querySelector(".day-notes");
      if (!c) continue;

      const arr = byDay[di];
      if (!arr || !arr.length) continue;

      arr.sort((a,b) => {
        if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
        return Number(b.modified_ms||0) - Number(a.modified_ms||0);
      });

      const maxShown = 2;
      const shown = arr.slice(0, maxShown);
      for (const n of shown) {
        const pill = document.createElement("div");
        const ck = _noteColorKey(n);
        pill.className = "npill" + (n.pinned ? " pinned" : "") + (ck ? " " + ck : "");
        const rep = (n.repeat_dows && n.repeat_dows.length) ? `↻ ${fmtRepeatDows(n.repeat_dows)} ` : "";
        pill.textContent = (n.pinned ? "📌 " : "") + rep + (n.text || "(empty)");
        pill.title = (n.repeat_dows && n.repeat_dows.length)
          ? `${rep}${n.text || ""}`.trim()
          : (n.text || "");
        pill.draggable = true;
        _applyTiltVars(pill, n.id, true);
        pill.addEventListener("dragstart", (ev) => {
          pill.classList.add("is-dragging");
          globalThis.__scalpel_note_drag_offy = 0;
          ev.dataTransfer.setData("text/scalpel_note_id", n.id);
          ev.dataTransfer.effectAllowed = "move";
        });
        pill.addEventListener("dragend", () => { pill.classList.remove("is-dragging"); });
        pill.addEventListener("click", (ev) => {
          openNoteEditor(n.id);
          ev.preventDefault();
          ev.stopPropagation();
        });
        c.appendChild(pill);
        if (pendingPulse && pendingPulse.id === n.id && pendingPulse.dayIndex === di) { _pulseEl(pill); pendingPulse = null; }
      }

      if (arr.length > maxShown) {
        const more = document.createElement("div");
        more.className = "npill more";
        more.textContent = `+${arr.length - maxShown}`;
        more.title = arr.slice(maxShown).map(x => x.text).filter(Boolean).join("\n");
        more.addEventListener("click", (ev) => {
          try{
            setNotesVisible(true, true);
            if (elNotesBox) elNotesBox.classList.remove("collapsed");
            if (elNoteQ) { elNoteQ.value = String(ymdFromMs(dayStarts[di])); elNoteQ.dispatchEvent(new Event("input")); elNoteQ.focus(); }
          }catch(_){ }
          ev.preventDefault();
          ev.stopPropagation();
        });
        c.appendChild(more);
      }
    }
  }

  function renderNotesInColumn(di, col){
    if (!col) return;
    col.querySelectorAll(".note").forEach(n => n.remove());
    if (!notesAllOn) return;

    const dayKey = ymdFromMs(dayStarts[di]);
    const timed = [];
    for (const n of notesById.values()) {
      if (!n || n.archived) continue;
      if (n.start_min == null || n.end_min == null) continue;
      if (!Number.isFinite(n.start_min) || !Number.isFinite(n.end_min)) continue;
      if (!noteAppliesToDay(n, di, dayKey)) continue;
      timed.push(n);
    }

    if (!timed.length) return;

    timed.sort((a,b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      if (a.start_min !== b.start_min) return a.start_min - b.start_min;
      return Number(b.modified_ms||0) - Number(a.modified_ms||0);
    });

    for (const n of timed) {
      const sMin = clamp(n.start_min, 0, 24*60);
      const eMin = clamp(n.end_min, 0, 24*60);
      if (eMin <= sMin) continue;

      // Clamp rendering to visible work window
      const topMin = clamp(sMin, WORK_START, WORK_END);
      const botMin = clamp(eMin, WORK_START, WORK_END);
      const durMin = Math.max(1, botMin - topMin);

      const topPx = (topMin - WORK_START) * pxPerMin;
      const hPx = Math.max(16, durMin * pxPerMin);


      const el = document.createElement("div");
      const ck = _noteColorKey(n);
      el.className = "note" + (n.pinned ? " pinned" : "") + (ck ? " " + ck : "");
      _applyTiltVars(el, n.id, false);
      el.style.top = `${topPx}px`;
      el.style.height = `${hPx}px`;
      el.dataset.noteId = n.id;
      el.draggable = true;

      const label = noteLabelForDay(n, di);
      const rep = (n.repeat_dows && n.repeat_dows.length) ? `↻ ${fmtRepeatDows(n.repeat_dows)}` : "";
      const hdrL = `${label}${rep ? " • " + rep : ""}`;
      const hdrR = n.pinned ? "📌" : "";

      el.innerHTML = `
        <div class="nhdr">
          <div class="lhs">${escapeHtml(hdrL)}</div>
          <div class="rhs">${escapeHtml(hdrR)}</div>
        </div>
        <div class="nbody"><div class="ntxt">${escapeHtml(n.text || "(empty)")}</div></div>
        <div class="nrsz" title="Resize"></div>
      `;

      const h = el.querySelector('.nrsz');
      if (h) {
        h.addEventListener('pointerdown', (ev) => startNoteResize(ev, n, di, col, el));
        h.addEventListener('click', (ev) => { ev.preventDefault(); ev.stopPropagation(); });
      }

      el.addEventListener("dragstart", (ev) => {
        el.classList.add("is-dragging");
        try{
          const r = el.getBoundingClientRect();
          globalThis.__scalpel_note_drag_offy = ev.clientY - r.top;
        }catch(_){ globalThis.__scalpel_note_drag_offy = 0; }
        ev.dataTransfer.setData("text/scalpel_note_id", n.id);
        ev.dataTransfer.effectAllowed = "move";
      });

      el.addEventListener("dragend", () => { el.classList.remove("is-dragging"); });

      el.addEventListener("click", (ev) => {
        openNoteEditor(n.id);
        ev.preventDefault();
        ev.stopPropagation();
      });

      col.appendChild(el);
      if (pendingPulse && pendingPulse.id === n.id && pendingPulse.dayIndex === di) { _pulseEl(el); pendingPulse = null; }
    }
  }



  // ---------------------------------------------
  // Note resize (timed notes)
  // ---------------------------------------------
  let noteResize = null;

  function startNoteResize(ev, note, dayIndex, col, el){
    if (!note || !el) return;
    // prevent starting HTML5 drag
    try{ ev.preventDefault(); }catch(_){ }
    try{ ev.stopPropagation(); }catch(_){ }

    if (note.start_min == null || note.end_min == null) return;

    const sMin = clamp(Number(note.start_min), 0, 24*60);
    const eMin = clamp(Number(note.end_min), 0, 24*60);
    const startMin = clamp(sMin, WORK_START, WORK_END);
    const endMin = clamp(eMin, WORK_START, WORK_END);

    noteResize = {
      pointerId: ev.pointerId,
      noteId: note.id,
      dayIndex,
      startMin,
      baseEndMin: endMin,
      liveEndMin: endMin,
      el,
    };

    try{ el.classList.add("is-resizing"); }catch(_){ }

    window.addEventListener("pointermove", onNoteResizeMove, { passive: false });
    window.addEventListener("pointerup", onNoteResizeEnd, { once: true });
    window.addEventListener("pointercancel", onNoteResizeEnd, { once: true });
  }

  function onNoteResizeMove(ev){
    if (!noteResize) return;
    if (ev.pointerId !== noteResize.pointerId) return;

    autoScrollDaysPane(ev.clientX, ev.clientY);

    const dayCols = document.querySelectorAll(".day-col");
    const dayCol = dayCols[noteResize.dayIndex];
    if (!dayCol) return;

    const rect = dayCol.getBoundingClientRect();
    const yPx = (ev.clientY - rect.top);
    const rawMin = WORK_START + (yPx / pxPerMin);

    let snappedMin = clamp(
      WORK_START + Math.round((rawMin - WORK_START) / SNAP) * SNAP,
      WORK_START,
      WORK_END
    );

    const minDurMin = Math.max(10, SNAP);
    const minEnd = noteResize.startMin + minDurMin;
    if (snappedMin < minEnd) snappedMin = minEnd;
    if (snappedMin > WORK_END) snappedMin = WORK_END;

    noteResize.liveEndMin = snappedMin;
    previewNoteResize(noteResize.el, noteResize.noteId, noteResize.dayIndex, noteResize.startMin, snappedMin);

    ev.preventDefault();
  }

  function onNoteResizeEnd(ev){
    if (!noteResize) return;
    if (ev.pointerId !== noteResize.pointerId) { noteResize = null; return; }

    window.removeEventListener("pointermove", onNoteResizeMove);

    const n = getNote(noteResize.noteId);
    const newEnd = Number(noteResize.liveEndMin);

    if (n && Number.isFinite(newEnd)) {
      const startMin = clamp(Number(n.start_min), 0, 24*60);
      const minDurMin = Math.max(10, SNAP);
      const endMin = clamp(Math.round(newEnd), startMin + minDurMin, WORK_END);
      n.end_min = endMin;
      upsertNote(n, true);
      _setPendingPulse(n.id, noteResize.dayIndex);
      renderNotesPanel();
      rerenderAll();
      elStatus.textContent = "Note resized.";
    }
    try{ if (noteResize && noteResize.el) noteResize.el.classList.remove("is-resizing"); }catch(_){ }

    noteResize = null;
  }

  function previewNoteResize(el, noteId, dayIndex, startMin, endMin){
    try{
      const topMin = clamp(startMin, WORK_START, WORK_END);
      const botMin = clamp(endMin, WORK_START, WORK_END);
      const durMin = Math.max(1, botMin - topMin);
      const hPx = Math.max(16, durMin * pxPerMin);
      el.style.height = `${hPx}px`;

      const n = getNote(noteId);
      if (n) {
        const lab = `${fmtMin(topMin)}–${fmtMin(botMin)}`;
        const rep = (n.repeat_dows && n.repeat_dows.length) ? `↻ ${fmtRepeatDows(n.repeat_dows)}` : "";
        const hdrL = `${lab}${rep ? " • " + rep : ""}`;
        const lhs = el.querySelector('.nhdr .lhs');
        if (lhs) lhs.textContent = hdrL;
      }
    }catch(_){ }
  }

  // ---------------------------------------------
  // Notes panel visibility
  // ---------------------------------------------
  let notesAllOn = true;

  function loadNotesUIState(){
    try{
      const st = (typeof globalThis.__scalpel_kvGetJSON === "function") ? globalThis.__scalpel_kvGetJSON(NOTES_UI_KEY, null) : null;
      if (_isObj(st)) {
        return {
          collapsed: (typeof st.collapsed === "boolean") ? st.collapsed : false,
          visible: (typeof st.visible === "boolean") ? st.visible : false,
          show_all: (typeof st.show_all === "boolean") ? st.show_all : true,
        };
      }
    }catch(_){ }
    return { collapsed: false, visible: false, show_all: true };
  }

  function saveNotesUIState(st){
    try{
      if (typeof globalThis.__scalpel_kvSetJSON === "function") globalThis.__scalpel_kvSetJSON(NOTES_UI_KEY, st);
      else localStorage.setItem(NOTES_UI_KEY, JSON.stringify(st));
    }catch(_){ }
  }

  function applyNotesCollapsed(collapsed, persist){
    if (!elNotesBox) return;
    elNotesBox.classList.toggle("collapsed", !!collapsed);
    const chev = document.getElementById("notesChev");
    if (chev) chev.textContent = collapsed ? "▸" : "▾";
    if (persist) {
      const prev = loadNotesUIState();
      saveNotesUIState({ collapsed: !!collapsed, visible: !!prev.visible, show_all: !!prev.show_all });
    }
  }

  function setNotesVisible(on, persist){
    const vis = !!on;
    if (elNotesWrap) elNotesWrap.style.display = vis ? "block" : "none";
    if (elBtnNotes) elBtnNotes.classList.toggle("on", vis);
    if (persist) {
      const prev = loadNotesUIState();
      saveNotesUIState({ collapsed: !!prev.collapsed, visible: vis, show_all: !!prev.show_all });
    }
  }

  function toggleNotesVisible(){
    const cur = !!(elNotesWrap && elNotesWrap.style.display !== "none");
    setNotesVisible(!cur, true);
    if (!cur) {
      try { elNoteQ && elNoteQ.focus(); } catch (_) {}
    }
  }

  function applyNotesAllToggle(){
    const btn = document.getElementById("noteToggleAll");
    if (!btn) return;
    btn.classList.toggle("on", !!notesAllOn);
    btn.textContent = notesAllOn ? "Hide notes" : "Show notes";
  }

  function setNotesAllVisible(on, persist){
    notesAllOn = !!on;
    applyNotesAllToggle();
    if (persist) {
      const prev = loadNotesUIState();
      saveNotesUIState({ collapsed: !!prev.collapsed, visible: !!prev.visible, show_all: notesAllOn });
    }
    renderNotesPanel();
    try { rerenderAll(); } catch (_) {}
  }

  // ---------------------------------------------
  // Notes panel
  // ---------------------------------------------
  function renderNotesPanel(){
    if (!elNoteList || !elNotesMeta) return;
    if (!notesAllOn) {
      elNotesMeta.textContent = "Notes hidden";
      elNoteList.innerHTML = `<div class="hint">Notes are hidden. Toggle "Show notes" to display them.</div>`;
      return;
    }

    const q = (elNoteQ && elNoteQ.value) ? String(elNoteQ.value).trim().toLowerCase() : "";

    const all = listNotesSorted();
    const recurring = all.filter(n => !n.archived && Array.isArray(n.repeat_dows) && n.repeat_dows.length);
    const unplaced = all.filter(n => !n.archived && !n.bucket_day_key && !(Array.isArray(n.repeat_dows) && n.repeat_dows.length));
    const archived = all.filter(n => !!n.archived);

    let inView = [];
    let otherPlaced = [];

    for (const n of all) {
      if (!n || n.archived) continue;
      if (!n.bucket_day_key) continue;
      const di = dayIndexFromYmd(n.bucket_day_key);
      if (di == null) otherPlaced.push(n);
      else inView.push(n);
    }

    const pinnedN = all.filter(n => !n.archived && n.pinned).length;

    elNotesMeta.textContent = `${unplaced.length} unplaced • ${recurring.length} recurring • ${inView.length} in view • ${pinnedN} pinned` + (archived.length ? ` • ${archived.length} archived` : "");

    // Build list
    elNoteList.innerHTML = "";

    function addHdr(title, badge){
      const h = document.createElement("div");
      h.className = "nghdr";
      h.innerHTML = `<div>${escapeHtml(title)}</div><small>${escapeHtml(badge)}</small>`;
      elNoteList.appendChild(h);
    }

    function addNoteItem(n){
      const di = (n.bucket_day_key ? dayIndexFromYmd(n.bucket_day_key) : null);
      const line1 = n.text || "(empty)";
      const line2Parts = [];

      if (n.repeat_dows && n.repeat_dows.length) {
        line2Parts.push(`↻ ${fmtRepeatDows(n.repeat_dows)}`);
        if (n.start_min == null || n.end_min == null) line2Parts.push("all-day");
        else line2Parts.push(`${_hmFromMin(n.start_min)}–${_hmFromMin(n.end_min)}`);
      } else if (n.bucket_day_key) {
        line2Parts.push(n.bucket_day_key);
        if (di != null) line2Parts.push(noteLabelForDay(n, di));
        else line2Parts.push(n.start_min == null ? "all-day" : `${_hmFromMin(n.start_min)}–${_hmFromMin(n.end_min || (n.start_min + 30))}`);
      } else {
        line2Parts.push("unplaced");
      }

      if (n.pinned) line2Parts.push("pinned");
      if (n.archived) line2Parts.push("archived");
      const line2 = line2Parts.join(" • ");

      if (q) {
        const hay = (line1 + " " + line2).toLowerCase();
        if (!hay.includes(q)) return;
      }

      const row = document.createElement("div");
      row.className = "nitem" + (n.pinned ? " pinned" : "");
      row.dataset.noteId = n.id;
      row.draggable = true;
      row.title = n.text || "";

      row.addEventListener("dragstart", (ev) => {
        globalThis.__scalpel_note_drag_offy = 10;
        ev.dataTransfer.setData("text/scalpel_note_id", n.id);
        ev.dataTransfer.effectAllowed = "move";
      });

      row.addEventListener("click", (ev) => {
        openNoteEditor(n.id);
        ev.preventDefault();
        ev.stopPropagation();
      });

      const sw = document.createElement("div");
      const ck = _noteColorKey(n);
      sw.className = "sw " + (ck ? ck : "none");

      const txt = document.createElement("div");
      txt.className = "txt";
      txt.innerHTML = `<div class="line1">${escapeHtml(line1)}</div><div class="line2">${escapeHtml(line2)}</div>`;

      const acts = document.createElement("div");
      acts.className = "acts";

      const bEdit = document.createElement("button");
      bEdit.className = "small iconbtn";
      bEdit.textContent = "✎";
      bEdit.title = "Edit";
      bEdit.addEventListener("click", (ev) => {
        openNoteEditor(n.id);
        ev.preventDefault();
        ev.stopPropagation();
      });

      const bArch = document.createElement("button");
      bArch.className = "small iconbtn";
      bArch.textContent = n.archived ? "↩" : "✓";
      bArch.title = n.archived ? "Unarchive" : "Archive";
      bArch.addEventListener("click", (ev) => {
        const cur = getNote(n.id);
        if (!cur) return;
        cur.archived = !cur.archived;
        upsertNote(cur, true);
        rerenderAll();
        ev.preventDefault();
        ev.stopPropagation();
      });

      const bDel = document.createElement("button");
      bDel.className = "small iconbtn danger";
      bDel.textContent = "🗑";
      bDel.title = "Delete";
      bDel.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const ok = confirm("Delete this note? This cannot be undone.");
        if (!ok) return;
        removeNote(n.id, true);
        renderNotesPanel();
        rerenderAll();
        elStatus.textContent = "Note deleted.";
      });

      acts.appendChild(bEdit);
      acts.appendChild(bArch);
      acts.appendChild(bDel);

      row.appendChild(sw);
      row.appendChild(txt);
      row.appendChild(acts);
      elNoteList.appendChild(row);
    }

    if (unplaced.length) {
      addHdr("Unplaced", String(unplaced.length));
      for (const n of unplaced) addNoteItem(n);
    }

    if (recurring.length) {
      addHdr("Recurring", String(recurring.length));
      for (const n of recurring) addNoteItem(n);
    }

    addHdr("This view", String(inView.length));
    for (const n of inView) addNoteItem(n);

    // Show other placed notes only when searching.
    if (q && otherPlaced.length) {
      addHdr("Other days", String(otherPlaced.length));
      for (const n of otherPlaced) addNoteItem(n);
    }

    if (archived.length) {
      addHdr("Archived", String(archived.length));
      for (const n of archived) addNoteItem(n);
    }
  }

  // ---------------------------------------------
  // Modal editor
  // ---------------------------------------------
  let noteModalOpenId = null;

  function _modalGetRepeatDows(){
    const out = [];
    try{
      if (!elNoteRepeatDays) return out;
      elNoteRepeatDays.querySelectorAll('input[data-dow]').forEach(cb => {
        if (!cb) return;
        if (cb.checked) {
          const d = Number(cb.getAttribute('data-dow'));
          if (Number.isFinite(d)) out.push(d);
        }
      });
    }catch(_){ }
    return _uniqSortedDows(out);
  }

  function _modalSetRepeatDows(dows){
    const set = new Set(_uniqSortedDows(dows));
    try{
      if (!elNoteRepeatDays) return;
      elNoteRepeatDays.querySelectorAll('input[data-dow]').forEach(cb => {
        const d = Number(cb.getAttribute('data-dow'));
        cb.checked = set.has(d);
      });
    }catch(_){ }
  }

  function _modalSelectAllDows(){
    _modalSetRepeatDows([0,1,2,3,4,5,6]);
  }

  function _modalSelectWeekdays(){
    _modalSetRepeatDows([1,2,3,4,5]);
  }

  function _applyRepeatUI(repeatOn){
    const on = !!repeatOn;
    if (elNoteRepeatBox) elNoteRepeatBox.style.display = on ? "block" : "none";
    try{
      if (elNoteDay) {
        elNoteDay.disabled = on;
        if (on) elNoteDay.value = "";  // requested: clear day when repeat enabled
      }
    }catch(_){ }
  }


  // --- Modal color selector ---
  function _modalSetColor(colorKey){
    const ck = _sanitizeColorKey(colorKey);
    if (!elNoteColors) return;
    try{
      elNoteColors.querySelectorAll('button[data-color]').forEach(b => {
        const bcRaw = b.getAttribute('data-color');
        const bc = _sanitizeColorKey(bcRaw);
        const isOn = (bc === ck) || (!ck && !String(bcRaw||""));
        b.classList.toggle('on', isOn);
      });
    }catch(_){ }
  }

  function _modalGetColor(){
    if (!elNoteColors) return "";
    try{
      const b = elNoteColors.querySelector('button[data-color].on');
      if (b) return _sanitizeColorKey(b.getAttribute('data-color'));
    }catch(_){ }
    return "";
  }

  function openNoteModalWith(note){
    if (!elNoteModal) return;
    if (!note) return;

    noteModalOpenId = note.id;

    if (elNoteModalTitle) elNoteModalTitle.textContent = "Note";
    if (elNoteTzHint) elNoteTzHint.textContent = `Bucket TZ: ${BUCKET_TZ}  |  Display TZ: ${DISPLAY_TZ}`;

    if (elNoteText) elNoteText.value = note.text || "";
    if (elNotePinned) elNotePinned.checked = !!note.pinned;
    if (elNoteArchived) elNoteArchived.checked = !!note.archived;
    _modalSetColor(_noteColorKey(note));

    const repeatOn = !!(note.repeat_dows && note.repeat_dows.length);
    if (elNoteRepeat) elNoteRepeat.checked = repeatOn;
    _modalSetRepeatDows(note.repeat_dows || []);
    _applyRepeatUI(repeatOn);

    const isAllDay = (repeatOn
      ? (note.start_min == null && note.end_min == null)
      : (note.bucket_day_key && note.start_min == null && note.end_min == null)
    );
    if (elNoteAllDay) elNoteAllDay.checked = !!isAllDay;

    if (elNoteDay) elNoteDay.value = (!repeatOn && note.bucket_day_key) ? String(note.bucket_day_key) : "";

    if (elNoteStart) elNoteStart.value = (note.start_min != null) ? _hmFromMin(note.start_min) : "";
    if (elNoteEnd) elNoteEnd.value = (note.end_min != null) ? _hmFromMin(note.end_min) : "";

    // Disable start/end if all-day
    try{
      const dis = !!isAllDay;
      if (elNoteStart) elNoteStart.disabled = dis;
      if (elNoteEnd) elNoteEnd.disabled = dis;
    }catch(_){ }

    elNoteModal.style.display = "flex";
    setTimeout(() => { try { elNoteText && elNoteText.focus(); } catch (_) {} }, 0);
  }

  function closeNoteModal(){
    if (!elNoteModal) return;
    elNoteModal.style.display = "none";
    noteModalOpenId = null;
  }

  function openNoteEditor(noteId){
    const n = getNote(noteId);
    if (!n) return;
    openNoteModalWith(n);
  }

  function openNewNoteEditor(){
    // Create immediately so the user can drag it even before saving.
    const n = createNote("");
    openNoteModalWith(n);
  }

  function onModalAllDayToggle(){
    try{
      const allDay = !!(elNoteAllDay && elNoteAllDay.checked);
      if (elNoteStart) elNoteStart.disabled = allDay;
      if (elNoteEnd) elNoteEnd.disabled = allDay;
      if (allDay) {
        if (elNoteStart) elNoteStart.value = "";
        if (elNoteEnd) elNoteEnd.value = "";
      }
    }catch(_){ }
  }

  function onModalRepeatToggle(){
    const on = !!(elNoteRepeat && elNoteRepeat.checked);
    _applyRepeatUI(on);
    if (on) {
      // If no days selected, default to all (requested)
      const cur = _modalGetRepeatDows();
      if (!cur.length) _modalSelectAllDows();
    }
  }

  function saveNoteFromModal(){
    if (!noteModalOpenId) return;
    const n = getNote(noteModalOpenId);
    if (!n) return;

    n.text = (elNoteText && elNoteText.value != null) ? String(elNoteText.value) : "";
    n.pinned = !!(elNotePinned && elNotePinned.checked);
    n.archived = !!(elNoteArchived && elNoteArchived.checked);

    const repeatOn = !!(elNoteRepeat && elNoteRepeat.checked);
    const allDay = !!(elNoteAllDay && elNoteAllDay.checked);

    if (repeatOn) {
      let dows = _modalGetRepeatDows();
      if (!dows.length) dows = [0,1,2,3,4,5,6];
      n.repeat_dows = dows;
      n.bucket_day_key = null;

      if (allDay) {
        n.start_min = null;
        n.end_min = null;
      } else {
        let s = _minFromHm(elNoteStart ? elNoteStart.value : "");
        let e = _minFromHm(elNoteEnd ? elNoteEnd.value : "");

        if (s == null && e == null) s = WORK_START;
        if (s != null && e == null) e = s + 30;
        if (s == null && e != null) s = Math.max(0, e - 30);

        s = clamp(s, 0, 24*60);
        e = clamp(e, 0, 24*60);
        if (e <= s) e = Math.min(24*60, s + 5);

        n.start_min = s;
        n.end_min = e;
      }
    } else {
      n.repeat_dows = [];
      const day = (elNoteDay && elNoteDay.value) ? String(elNoteDay.value) : "";
      if (!day) {
        n.bucket_day_key = null;
        n.start_min = null;
        n.end_min = null;
      } else {
        n.bucket_day_key = day;
        if (allDay) {
          n.start_min = null;
          n.end_min = null;
        } else {
          let s = _minFromHm(elNoteStart ? elNoteStart.value : "");
          let e = _minFromHm(elNoteEnd ? elNoteEnd.value : "");

          if (s == null && e == null) s = WORK_START;
          if (s != null && e == null) e = s + 30;
          if (s == null && e != null) s = Math.max(0, e - 30);

          s = clamp(s, 0, 24*60);
          e = clamp(e, 0, 24*60);
          if (e <= s) e = Math.min(24*60, s + 5);

          n.start_min = s;
          n.end_min = e;
        }
      }
    }

    // Color
    try{
      if (!_isObj(n.style)) n.style = {};
      n.style.color = _sanitizeColorKey(_modalGetColor());
    }catch(_){ }

    upsertNote(n, true);
    closeNoteModal();
    rerenderAll();
  }



  function deleteModalNote(){
    if (!noteModalOpenId) return;
    const ok = confirm("Delete this note? This cannot be undone.");
    if (!ok) return;
    removeNote(noteModalOpenId, true);
    closeNoteModal();
    renderNotesPanel();
    rerenderAll();
    elStatus.textContent = "Note deleted.";
  }

  function unplaceModalNote(){
    if (!noteModalOpenId) return;
    const n = getNote(noteModalOpenId);
    if (!n) return;
    n.bucket_day_key = null;
    n.start_min = null;
    n.end_min = null;
    n.repeat_dows = [];
    // Color
    try{
      if (!_isObj(n.style)) n.style = {};
      n.style.color = _sanitizeColorKey(_modalGetColor());
    }catch(_){ }

    upsertNote(n, true);
    openNoteModalWith(n);
    rerenderAll();
  }

  // ---------------------------------------------
  // Export / Import
  // ---------------------------------------------
  function exportNotes(){
    try{
      const doc = _isObj(notesDoc) ? notesDoc : _notesEmptyDoc();
      syncNotesDocFromIndex(false);
      const payload = JSON.stringify(doc, null, 2);
      const blob = new Blob([payload], { type: "application/json" });
      const a = document.createElement("a");
      const stamp = ymdFromMs(Date.now()).replaceAll("-", "");
      a.download = `scalpel_notes_${stamp}.json`;
      a.href = URL.createObjectURL(blob);
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        try { URL.revokeObjectURL(a.href); } catch (_) {}
        try { a.remove(); } catch (_) {}
      }, 0);
      elStatus.textContent = "Exported notes JSON.";
    } catch (e) {
      console.error("Notes export failed", e);
      elStatus.textContent = "Notes export failed.";
    }
  }

  function importNotesFile(file){
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try{
        const txt = String(reader.result || "");
        const incoming = JSON.parse(txt);
        if (!_isObj(incoming) || incoming.schema !== NOTES_SCHEMA || !Array.isArray(incoming.notes)) {
          elStatus.textContent = "Import failed: invalid notes schema.";
          return;
        }

        let added = 0;
        let updated = 0;

        for (const raw of incoming.notes) {
          const nn = _normNote(raw);
          const cur = getNote(nn.id);
          if (!cur) {
            notesById.set(nn.id, nn);
            added++;
            continue;
          }
          const curM = Number(cur.modified_ms || 0);
          const inM = Number(nn.modified_ms || 0);
          if (inM > curM) {
            notesById.set(nn.id, nn);
            updated++;
          }
        }

        saveNotes();
        renderNotesPanel();
        rerenderAll();
        elStatus.textContent = `Imported notes: +${added}, updated ${updated}.`;
      } catch (e) {
        console.error("Notes import failed", e);
        elStatus.textContent = "Import failed: JSON parse error.";
      }
    };
    reader.readAsText(file);
  }

  // ---------------------------------------------
  // Notes panel UI wiring
  // ---------------------------------------------
  function initNotesUI(){
    loadNotes();

    // Visibility + collapse state
    const st = loadNotesUIState();
    setNotesVisible(!!st.visible, false);
    applyNotesCollapsed(!!st.collapsed, false);
    notesAllOn = (typeof st.show_all === "boolean") ? st.show_all : true;
    applyNotesAllToggle();

    if (elBtnNotes) {
      elBtnNotes.addEventListener("click", () => {
        toggleNotesVisible();
      });
    }

    if (elNotesHead) {
      elNotesHead.addEventListener("click", () => {
        const next = !elNotesBox.classList.contains("collapsed");
        applyNotesCollapsed(next, true);
      });
    }

    const elNoteToggleAll = document.getElementById("noteToggleAll");
    if (elNoteToggleAll) {
      elNoteToggleAll.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        setNotesAllVisible(!notesAllOn, true);
      });
    }

    if (elNoteAdd) {
      elNoteAdd.addEventListener("click", () => {
        const txt = elNoteNewText ? String(elNoteNewText.value || "").trim() : "";
        if (!txt) { elStatus.textContent = "Note text is empty."; return; }
        createNote(txt);
        if (elNoteNewText) elNoteNewText.value = "";
        renderNotesPanel();
        elStatus.textContent = "Note added (unplaced).";
      });
    }

    if (elNoteNewText) {
      elNoteNewText.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
          ev.preventDefault();
          elNoteAdd && elNoteAdd.click();
        }
      });
    }

    if (elNoteNew) elNoteNew.addEventListener("click", openNewNoteEditor);

    if (elNoteExport) elNoteExport.addEventListener("click", exportNotes);

    if (elNoteImport) elNoteImport.addEventListener("click", () => {
      if (elNoteImportFile) elNoteImportFile.click();
    });

    if (elNoteImportFile) {
      elNoteImportFile.addEventListener("change", () => {
        const f = elNoteImportFile.files && elNoteImportFile.files.length ? elNoteImportFile.files[0] : null;
        if (!f) return;
        importNotesFile(f);
        try { elNoteImportFile.value = ""; } catch (_) {}
      });
    }

    if (elNoteClearArchived) {
      elNoteClearArchived.addEventListener("click", () => {
        const n = clearArchivedNotes();
        renderNotesPanel();
        rerenderAll();
        elStatus.textContent = n ? `Cleared ${n} archived note(s).` : "No archived notes to clear.";
      });
    }

    if (elNoteQ) {
      elNoteQ.addEventListener("input", () => {
        renderNotesPanel();
      });
    }

    // Modal wiring
    if (elNoteClose) elNoteClose.addEventListener("click", closeNoteModal);
    if (elNoteModal) {
      elNoteModal.addEventListener("click", (ev) => {
        if (ev.target === elNoteModal) closeNoteModal();
      });
    }
    if (elNoteSave) elNoteSave.addEventListener("click", saveNoteFromModal);
    if (elNoteDelete) elNoteDelete.addEventListener("click", deleteModalNote);

    if (elNoteColors) {
      try{
        elNoteColors.querySelectorAll('button[data-color]').forEach(b => {
          b.addEventListener("click", (ev) => {
            ev.preventDefault();
            _modalSetColor(b.getAttribute("data-color"));
          });
        });
      }catch(_){ }
    }
    if (elNoteUnplace) elNoteUnplace.addEventListener("click", unplaceModalNote);
    if (elNoteAllDay) elNoteAllDay.addEventListener("change", onModalAllDayToggle);
    if (elNoteRepeat) elNoteRepeat.addEventListener("change", onModalRepeatToggle);

    if (elNoteDowAll) elNoteDowAll.addEventListener("click", (ev) => { ev.preventDefault(); _modalSelectAllDows(); });
    if (elNoteDowWeekdays) elNoteDowWeekdays.addEventListener("click", (ev) => { ev.preventDefault(); _modalSelectWeekdays(); });
    if (elNoteDowClear) elNoteDowClear.addEventListener("click", (ev) => { ev.preventDefault(); _modalSetRepeatDows([]); });

    // Keyboard:
    // - N = new note (unless typing)
    // - Ctrl+Shift+N = toggle notes panel
    document.addEventListener("keydown", (ev) => {
      const t = ev.target;
      const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
      if (typing) return;

      if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && (ev.key === "n" || ev.key === "N")) {
        toggleNotesVisible();
        ev.preventDefault();
        return;
      }

      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;

      if (ev.key === "n" || ev.key === "N") {
        openNewNoteEditor();
        ev.preventDefault();
      }
    });

    // Initial render
    renderNotesPanel();
  }

  // Expose placement fns used by calendar drop handlers
  // (in-scope functions, referenced directly)
  initNotesUI();

  // ---------------------------------------------
'''
