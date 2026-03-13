# scalpel/render/js/part07_init.py
from __future__ import annotations

JS_PART = r'''// Controls / rerender
  // -----------------------------
  function rerenderFull() {
    const { events, backlog, problems, allByDay } = classifyTasks(elQ.value);
    renderGoalsFromEvents(events, backlog);
    renderPaletteFromEvents(events);

    let evVis = events;
    let backVis = backlog;
    let dayVis = allByDay;
    if (focusBehavior === "hide" && focusActive()) {
      evVis = events.filter(ev => taskMatchesFocus(tasksByUuid.get(ev.uuid)));
      backVis = backlog.filter(x => taskMatchesFocus(x && x.t));
      dayVis = Array.from({length: DAYS}, (_, i) => (allByDay && allByDay[i] ? allByDay[i].filter(it => taskMatchesFocus(tasksByUuid.get(it.uuid))) : []));
    }

    renderLists(backVis, problems);
    renderCalendar(evVis, dayVis);
    lastDayVis = dayVis;
    renderDayBalance(activeDayIndex, dayVis);
    renderCommands();
    updateSelectionMeta();
    try { renderExecutionSession(); } catch (_) {}
    try { updatePendingMeta(); } catch (_) {}
    try { if (typeof renderNotesPanel === "function") renderNotesPanel(); } catch (e) { /* ignore */ }
    // keep now line fresh
    try { renderNowLine(); } catch (e) { console.error("NowLine render failed", e); }
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
  }

  function rerenderSelectionOnly() {
    try { if (typeof syncSelectionVisuals === "function") syncSelectionVisuals(); } catch (_) {}
    try { if (typeof syncExecutionVisuals === "function") syncExecutionVisuals(); } catch (_) {}
    updateSelectionMeta();
    try { renderExecutionSession(); } catch (_) {}
    try { updatePendingMeta(); } catch (_) {}
    try { if (lastDayVis) renderDayBalance(activeDayIndex, lastDayVis); } catch (_) {}
  }

  var RERENDER_INPUT_DEBOUNCE_MS = 110;
  var __scalpelRerenderQueued = false;
  var __scalpelRerenderTimer = null;
  var __scalpelRerenderMode = "full"; // "selection" | "full"

  function __scalpelModeRank(mode) {
    return (mode === "selection") ? 1 : 2;
  }
  function __scalpelQueueMode(mode) {
    if (__scalpelRerenderMode !== "selection" && __scalpelRerenderMode !== "full") {
      __scalpelRerenderMode = "full";
    }
    const next = (mode === "selection") ? "selection" : "full";
    if (__scalpelModeRank(next) > __scalpelModeRank(__scalpelRerenderMode)) {
      __scalpelRerenderMode = next;
    }
  }
  function __scalpelFlushRerender() {
    __scalpelRerenderQueued = false;
    const mode = __scalpelRerenderMode;
    __scalpelRerenderMode = "selection";
    if (mode === "selection") rerenderSelectionOnly();
    else rerenderFull();
  }
  function rerenderAll(opts) {
    const o = opts || {};
    const mode = (o.mode === "selection") ? "selection" : "full";
    const immediate = !!o.immediate;
    const debounceMs = Number.isFinite(Number(o.debounceMs)) ? Math.max(0, Number(o.debounceMs)) : null;

    __scalpelQueueMode(mode);

    if (immediate) {
      if (__scalpelRerenderTimer) {
        clearTimeout(__scalpelRerenderTimer);
        __scalpelRerenderTimer = null;
      }
      __scalpelFlushRerender();
      return;
    }

    if (debounceMs != null) {
      if (__scalpelRerenderTimer) clearTimeout(__scalpelRerenderTimer);
      __scalpelRerenderTimer = setTimeout(() => {
        __scalpelRerenderTimer = null;
        if (__scalpelRerenderQueued) return;
        __scalpelRerenderQueued = true;
        requestAnimationFrame(__scalpelFlushRerender);
      }, debounceMs);
      return;
    }

    if (__scalpelRerenderQueued) return;
    __scalpelRerenderQueued = true;
    requestAnimationFrame(__scalpelFlushRerender);
  }

  elQ.addEventListener("input", () => rerenderAll({ mode: "full", debounceMs: RERENDER_INPUT_DEBOUNCE_MS }));


  // Theme init
  applyTheme(getPreferredTheme());
  const btnTheme = document.getElementById("btnTheme");
  if (btnTheme){
    btnTheme.addEventListener("click", (ev) => {
      if (ev && ev.shiftKey && typeof openThemeModal === "function"){
        ev.preventDefault();
        try { openThemeModal(); } catch (_) {}
        return;
      }
      try { cycleTheme(); } catch (e) {
        const cur = document.body.classList.contains("theme-light") ? "light" : "dark";
        applyTheme(cur === "light" ? "dark" : "light");
      }
    });
    btnTheme.addEventListener("contextmenu", (ev)=>{
      if (typeof openThemeModal !== "function") return;
      ev.preventDefault();
      try { openThemeModal(); } catch (_) {}
    });
  }
  try { if (typeof globalThis.__scalpel_bindThemeModal === "function") globalThis.__scalpel_bindThemeModal(); } catch (_) {}
  document.addEventListener("keydown", (ev)=>{
    try{
      if (ev && ev.ctrlKey && ev.shiftKey && String(ev.key||"").toLowerCase() === "t"){
        if (typeof openThemeModal === "function"){
          ev.preventDefault();
          openThemeModal();
        }
      }
    }catch(_){ }
  });

  // Density (compact "pro mode")
  const DENSITY_KEY = "scalpel.density.compact";
  const btnDensity = document.getElementById("btnDensity");
  let compactDensity = false;

  function readDensityPref(){
    try{
      const raw = (typeof globalThis.__scalpel_storeGet === "function")
        ? globalThis.__scalpel_storeGet(DENSITY_KEY, null)
        : null;
      if (raw == null) return false;
      const s = String(raw).toLowerCase();
      return (s === "1" || s === "true" || s === "on" || s === "compact");
    }catch(_){ return false; }
  }
  function writeDensityPref(on){
    try{
      if (typeof globalThis.__scalpel_storeSet === "function") globalThis.__scalpel_storeSet(DENSITY_KEY, on ? "1" : "0");
    }catch(_){}
  }
  function applyDensity(on){
    compactDensity = !!on;
    document.body.classList.toggle("compact", compactDensity);
    if (btnDensity){
      btnDensity.classList.toggle("on", compactDensity);
      btnDensity.textContent = compactDensity ? "Density: Compact" : "Density: Comfort";
    }
  }
  applyDensity(readDensityPref());
  if (btnDensity){
    btnDensity.addEventListener("click", () => {
      applyDensity(!compactDensity);
      writeDensityPref(compactDensity);
      try { renderNowLine(); } catch (_) {}
    });
  }
  document.addEventListener("keydown", (ev)=>{
    try{
      if (ev && ev.ctrlKey && ev.shiftKey && String(ev.key||"").toLowerCase() === "m"){
        ev.preventDefault();
        applyDensity(!compactDensity);
        writeDensityPref(compactDensity);
        try { renderNowLine(); } catch (_) {}
      }
    }catch(_){}
  });

  // Commands panel sections (accordion)
  const CMD_SECTIONS_KEY = `${viewKey}:cmdSections`;
  const CMD_SECTION_DEFAULTS = { actions: false, arrange: false, execution: false, ai: false, output: false };
  const CMD_SECTION_ANIM_MS = 170;
  let cmdSectionState = loadJson(CMD_SECTIONS_KEY, CMD_SECTION_DEFAULTS);
  if (!cmdSectionState || typeof cmdSectionState !== "object") cmdSectionState = { ...CMD_SECTION_DEFAULTS };

  function saveCommandSectionState(){
    try {
      if (typeof globalThis.__scalpel_storeSetJSON === "function") globalThis.__scalpel_storeSetJSON(CMD_SECTIONS_KEY, cmdSectionState);
    } catch (_) {}
  }
  function commandSectionIsOpen(name){
    const v = cmdSectionState[name];
    return !!(v === true || v === 1 || v === "1" || v === "true");
  }
  function commandSectionsReduceMotion(){
    try {
      return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (_) {
      return false;
    }
  }
  function clearCommandSectionTimer(body){
    if (!body) return;
    const raw = Number(body.dataset.scalpelAnimTimer || 0);
    if (raw) {
      try { clearTimeout(raw); } catch (_) {}
    }
    body.dataset.scalpelAnimTimer = "";
  }
  function setCommandSectionBodyState(body, on){
    if (!body) return;
    const ready = (body.dataset.scalpelReady === "1");
    body.dataset.scalpelReady = "1";
    clearCommandSectionTimer(body);
    body.classList.remove("anim-open", "anim-close");
    body.setAttribute("aria-hidden", on ? "false" : "true");
    try { body.inert = !on; } catch (_) {}
    const animate = ready && !commandSectionsReduceMotion();
    if (!on) {
      if (!animate) {
        body.hidden = true;
        body.style.maxHeight = "";
        return;
      }
      body.hidden = false;
      const h = Math.max(0, body.scrollHeight);
      body.style.maxHeight = `${h}px`;
      void body.offsetHeight;
      body.classList.add("anim-close");
      body.style.maxHeight = "0px";
      const tid = setTimeout(() => {
        body.hidden = true;
        body.classList.remove("anim-close");
        body.style.maxHeight = "";
        body.dataset.scalpelAnimTimer = "";
      }, CMD_SECTION_ANIM_MS + 40);
      body.dataset.scalpelAnimTimer = String(tid);
      return;
    }

    body.hidden = false;
    if (!animate) {
      body.style.maxHeight = "";
      return;
    }
    body.style.maxHeight = "0px";
    void body.offsetHeight;
    body.classList.add("anim-open");
    const h = Math.max(120, body.scrollHeight + 4);
    body.style.maxHeight = `${h}px`;
    const tid = setTimeout(() => {
      body.classList.remove("anim-open");
      body.style.maxHeight = "";
      body.dataset.scalpelAnimTimer = "";
    }, CMD_SECTION_ANIM_MS + 40);
    body.dataset.scalpelAnimTimer = String(tid);
  }
  function setCommandSectionOpen(name, open, persist){
    const root = document.querySelector(`.rsec[data-rsec="${name}"]`);
    if (!root) return;
    const btn = root.querySelector("[data-rsec-toggle]");
    const body = root.querySelector(".rsec-b");
    const on = !!open;
    root.classList.toggle("open", on);
    if (body) setCommandSectionBodyState(body, on);
    if (btn) btn.setAttribute("aria-expanded", on ? "true" : "false");
    cmdSectionState[name] = on;
    if (persist !== false) saveCommandSectionState();
  }
  function resetCommandSections(persist){
    cmdSectionState = { ...CMD_SECTION_DEFAULTS };
    for (const name of Object.keys(CMD_SECTION_DEFAULTS)) {
      setCommandSectionOpen(name, cmdSectionState[name], false);
    }
    if (persist !== false) saveCommandSectionState();
  }
  (function bindCommandSections(){
    const roots = document.querySelectorAll(".rsec[data-rsec]");
    for (const root of roots) {
      const name = String(root.getAttribute("data-rsec") || "");
      if (!name) continue;
      if (!(name in cmdSectionState)) cmdSectionState[name] = false;
      const btn = root.querySelector("[data-rsec-toggle]");
      if (btn) {
        btn.addEventListener("click", () => {
          setCommandSectionOpen(name, !commandSectionIsOpen(name), true);
        });
      }
      setCommandSectionOpen(name, commandSectionIsOpen(name), false);
    }
    saveCommandSectionState();
  })();
  globalThis.__scalpel_openCommandSection = (name) => setCommandSectionOpen(String(name || ""), true, true);
  globalThis.__scalpel_resetCommandSections = () => resetCommandSections(true);

  // Left panel sections (accordion)
  const LEFT_SECTIONS_KEY = `${viewKey}:leftSections`;
  const LEFT_SECTION_DEFAULTS = { focus: true, palette: true, problems: true };
  const LEFT_SECTION_ANIM_MS = 160;
  let leftSectionState = loadJson(LEFT_SECTIONS_KEY, LEFT_SECTION_DEFAULTS);
  if (!leftSectionState || typeof leftSectionState !== "object") leftSectionState = { ...LEFT_SECTION_DEFAULTS };

  function saveLeftSectionState(){
    try {
      if (typeof globalThis.__scalpel_storeSetJSON === "function") globalThis.__scalpel_storeSetJSON(LEFT_SECTIONS_KEY, leftSectionState);
    } catch (_) {}
  }
  function leftSectionIsOpen(name){
    const v = leftSectionState[name];
    return !!(v === true || v === 1 || v === "1" || v === "true");
  }
  function leftSectionsReduceMotion(){
    try {
      return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (_) {
      return false;
    }
  }
  function clearLeftSectionTimer(body){
    if (!body) return;
    const raw = Number(body.dataset.scalpelAnimTimer || 0);
    if (raw) {
      try { clearTimeout(raw); } catch (_) {}
    }
    body.dataset.scalpelAnimTimer = "";
  }
  function setLeftSectionBodyState(body, on){
    if (!body) return;
    const ready = (body.dataset.scalpelReady === "1");
    body.dataset.scalpelReady = "1";
    clearLeftSectionTimer(body);
    body.classList.remove("anim-open", "anim-close");
    body.setAttribute("aria-hidden", on ? "false" : "true");
    try { body.inert = !on; } catch (_) {}
    const animate = ready && !leftSectionsReduceMotion();

    if (!on) {
      if (!animate) {
        body.hidden = true;
        body.style.maxHeight = "";
        return;
      }
      body.hidden = false;
      const h = Math.max(0, body.scrollHeight);
      body.style.maxHeight = `${h}px`;
      void body.offsetHeight;
      body.classList.add("anim-close");
      body.style.maxHeight = "0px";
      const tid = setTimeout(() => {
        body.hidden = true;
        body.classList.remove("anim-close");
        body.style.maxHeight = "";
        body.dataset.scalpelAnimTimer = "";
      }, LEFT_SECTION_ANIM_MS + 40);
      body.dataset.scalpelAnimTimer = String(tid);
      return;
    }

    body.hidden = false;
    if (!animate) {
      body.style.maxHeight = "";
      return;
    }
    body.style.maxHeight = "0px";
    void body.offsetHeight;
    body.classList.add("anim-open");
    const h = Math.max(120, body.scrollHeight + 4);
    body.style.maxHeight = `${h}px`;
    const tid = setTimeout(() => {
      body.classList.remove("anim-open");
      body.style.maxHeight = "";
      body.dataset.scalpelAnimTimer = "";
    }, LEFT_SECTION_ANIM_MS + 40);
    body.dataset.scalpelAnimTimer = String(tid);
  }
  function setLeftSectionOpen(name, open, persist){
    const root = document.querySelector(`.lsec[data-lsec="${name}"]`);
    if (!root) return;
    const btn = root.querySelector("[data-lsec-toggle]");
    const body = root.querySelector(".lsec-b");
    const chev = root.querySelector(".lsec-chev");
    const on = !!open;
    root.classList.toggle("open", on);
    if (body) setLeftSectionBodyState(body, on);
    if (btn) btn.setAttribute("aria-expanded", on ? "true" : "false");
    if (chev) chev.textContent = on ? "▾" : "▸";
    leftSectionState[name] = on;
    if (persist !== false) saveLeftSectionState();
  }
  (function bindLeftSections(){
    const roots = document.querySelectorAll(".lsec[data-lsec]");
    for (const root of roots) {
      const name = String(root.getAttribute("data-lsec") || "");
      if (!name) continue;
      if (!(name in leftSectionState)) leftSectionState[name] = true;
      const btn = root.querySelector("[data-lsec-toggle]");
      if (btn) {
        btn.addEventListener("click", () => {
          setLeftSectionOpen(name, !leftSectionIsOpen(name), true);
        });
      }
      setLeftSectionOpen(name, leftSectionIsOpen(name), false);
    }
    saveLeftSectionState();
  })();
  globalThis.__scalpel_setLeftSectionOpen = (name, open) => setLeftSectionOpen(String(name || ""), !!open, true);

  // Help + unified search / command center
  const elBtnHelp = document.getElementById("btnHelp");
  const elBtnCommand = document.getElementById("btnCommand");
  const elBtnRefresh = document.getElementById("btnRefresh");
  const elActionOverflow = document.getElementById("actionOverflow");
  const elBtnMoreActions = document.getElementById("btnMoreActions");
  const elOverflowMenu = document.getElementById("overflowMenu");
  const elHelpModal = document.getElementById("helpModal");
  const elHelpClose = document.getElementById("helpClose");
  const elHelpOpenCommands = document.getElementById("helpOpenCommands");
  const elCommandModal = document.getElementById("commandModal");
  const elCommandClose = document.getElementById("commandClose");
  const elCommandQ = document.getElementById("commandQ");
  const elCommandList = document.getElementById("commandList");
  const elToast = document.getElementById("toast");

  let toastHideTimer = null;
  let toastLastText = "";
  let toastLastTs = 0;

  function showToast(message, opts){
    if (!elToast) return;
    const msg = String(message || "").trim();
    if (!msg) return;
    const o = opts || {};
    const now = Date.now();
    const dur = Number.isFinite(Number(o.durationMs)) ? clamp(Number(o.durationMs), 700, 5000) : 2200;
    if (msg === toastLastText && (now - toastLastTs) < 350) return;

    toastLastText = msg;
    toastLastTs = now;
    elToast.textContent = msg;
    elToast.classList.add("show");
    if (toastHideTimer) clearTimeout(toastHideTimer);
    toastHideTimer = setTimeout(() => {
      elToast.classList.remove("show");
    }, dur);
  }
  globalThis.__scalpel_notify = showToast;

  (function initStatusToastBridge(){
    if (!elStatus || !elToast || typeof MutationObserver !== "function") return;
    let lastSeen = "";
    const flush = () => {
      const cur = String(elStatus.textContent || "").trim();
      if (!cur || cur === lastSeen) return;
      lastSeen = cur;
      showToast(cur);
    };
    try{
      const obs = new MutationObserver(flush);
      obs.observe(elStatus, { childList: true, characterData: true, subtree: true });
    }catch(_){ }
  })();

  function _isTypingTarget(ev){
    const t = ev && ev.target;
    if (!t) return false;
    const tag = String(t.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    return !!t.isContentEditable;
  }
  function _isOpen(el){ return !!(el && el.style.display === "flex"); }
  function _isOverflowOpen(){
    return !!(elOverflowMenu && !elOverflowMenu.hidden);
  }
  function closeOverflowMenu(){
    if (!elOverflowMenu) return;
    elOverflowMenu.hidden = true;
    if (elActionOverflow) elActionOverflow.classList.remove("open");
    if (elBtnMoreActions) elBtnMoreActions.setAttribute("aria-expanded", "false");
  }
  function openOverflowMenu(){
    if (!elOverflowMenu) return;
    elOverflowMenu.hidden = false;
    if (elActionOverflow) elActionOverflow.classList.add("open");
    if (elBtnMoreActions) elBtnMoreActions.setAttribute("aria-expanded", "true");
  }

  if (elBtnRefresh){
    const canRefreshViaHttp = /^https?:$/i.test(String(location.protocol || ""));
    if (!canRefreshViaHttp) {
      elBtnRefresh.disabled = true;
      elBtnRefresh.title = "Refresh is unavailable in one-shot mode.";
    } else {
      elBtnRefresh.addEventListener("click", async () => {
        closeOverflowMenu();

        try{
          const dirty = (typeof hasPendingActions === "function" && hasPendingActions())
            || (typeof hasPlanOverrides === "function" && hasPlanOverrides());
          if (dirty){
            const ok = confirm(
              "You have local pending changes.\n\n"
              + "Refreshing will reload the page from fresh Taskwarrior data. Continue?"
            );
            if (!ok) {
              elStatus.textContent = "Refresh cancelled.";
              return;
            }
          }
        }catch(_){ }

        elBtnRefresh.disabled = true;
        elStatus.textContent = "Refreshing data...";
        try{
          const res = await fetch("/refresh", {
            method: "POST",
            headers: { "Accept": "application/json" },
            cache: "no-store",
          });
          let body = null;
          try { body = await res.json(); } catch (_) {}
          if (!res.ok || !body || body.ok !== true) {
            const reason = (body && body.error) ? String(body.error) : `HTTP ${res.status}`;
            elStatus.textContent = `Refresh failed: ${reason}`;
            return;
          }
          elStatus.textContent = "Data refreshed. Reloading...";
          setTimeout(() => location.reload(), 40);
        } catch (e) {
          elStatus.textContent = `Refresh failed: ${String((e && e.message) || e || "network error")}`;
        } finally {
          elBtnRefresh.disabled = false;
        }
      });
    }
  }

  function openHelpModal(){
    if (!elHelpModal) return;
    closeOverflowMenu();
    closeCommandModal();
    elHelpModal.style.display = "flex";
  }
  function closeHelpModal(){
    if (!elHelpModal) return;
    elHelpModal.style.display = "none";
  }

  const quickCommands = [
    {
      id: "focus-filter",
      label: "Focus filter",
      hint: "Jump cursor to backlog filter input",
      keys: "/",
      codes: ["FF"],
      run: () => { try { elQ.focus(); elQ.select(); } catch (_) {} },
    },
    {
      id: "add-tasks",
      label: "Add tasks",
      hint: "Open add-tasks modal",
      keys: "A",
      codes: ["AD"],
      run: () => { try { if (typeof openAddModal === "function") openAddModal(); } catch (_) {} },
    },
    {
      id: "jump-today",
      label: "Jump to today",
      hint: "Set view window start to today",
      keys: "Today",
      codes: ["TD"],
      run: () => { try { if (elVwToday) elVwToday.click(); } catch (_) {} },
    },
    {
      id: "clear-selection",
      label: "Clear selection",
      hint: "Drop selected tasks",
      keys: "Esc",
      codes: ["CL"],
      run: () => {
        try { clearSelection(); } catch (_) {}
        try { rerenderAll({ mode: "selection", immediate: true }); } catch (_) {}
      },
    },
    {
      id: "copy-commands",
      label: "Copy commands",
      hint: "Copy command output to clipboard",
      keys: "Ctrl/Cmd+C",
      codes: ["CP"],
      run: () => { try { const b = document.getElementById("btnCopy"); if (b) b.click(); } catch (_) {} },
    },
    {
      id: "start-focus-selected",
      label: "Start selected focus session",
      hint: "Start execution mode for the lead selected task",
      keys: "Focus",
      codes: ["FS"],
      run: () => { try { if (typeof startExecutionSessionFromSelection === "function") startExecutionSessionFromSelection(); } catch (_) {} },
    },
    {
      id: "start-focus-next",
      label: "Start next-up focus session",
      hint: "Start execution mode from the Next up task",
      keys: "Next up",
      codes: ["FN"],
      run: () => { try { if (typeof startExecutionSessionFromNextUp === "function") startExecutionSessionFromNextUp(); } catch (_) {} },
    },
    {
      id: "stop-focus-session",
      label: "Stop focus session",
      hint: "Clear the active execution session",
      keys: "Stop",
      codes: ["SX"],
      run: () => { try { if (typeof stopExecutionSession === "function") stopExecutionSession(); } catch (_) {} },
    },
    {
      id: "toggle-notes",
      label: "Toggle notes",
      hint: "Show or hide notes panel",
      keys: "Ctrl+Shift+N",
      codes: ["NT"],
      run: () => {
        try {
          if (typeof toggleNotesVisible === "function") toggleNotesVisible();
          else if (document.getElementById("btnNotes")) document.getElementById("btnNotes").click();
        } catch (_) {}
      },
    },
    {
      id: "toggle-panels",
      label: "Toggle panels",
      hint: "Collapse or expand side panels",
      keys: "Layout",
      codes: ["PN"],
      run: () => { try { const b = document.getElementById("btnTogglePanels"); if (b) b.click(); } catch (_) {} },
    },
    {
      id: "reset-local-view",
      label: "Reset local view",
      hint: "Clear local plan edits and queued actions",
      keys: "Reset",
      codes: ["RS"],
      run: () => { try { const b = document.getElementById("btnReset"); if (b) b.click(); } catch (_) {} },
    },
    {
      id: "toggle-density",
      label: "Toggle density",
      hint: "Switch comfort/compact spacing",
      keys: "Ctrl+Shift+M",
      codes: ["DN"],
      run: () => {
        try {
          applyDensity(!compactDensity);
          writeDensityPref(compactDensity);
          renderNowLine();
        } catch (_) {}
      },
    },
    {
      id: "theme-manager",
      label: "Theme manager",
      hint: "Open theme manager modal",
      keys: "Ctrl+Shift+T",
      codes: ["TH"],
      run: () => { try { if (typeof openThemeModal === "function") openThemeModal(); } catch (_) {} },
    },
    {
      id: "open-help",
      label: "Open help",
      hint: "Show shortcut reference",
      keys: "?",
      codes: ["HP"],
      run: () => { try { openHelpModal(); } catch (_) {} },
    },
  ];

  let quickVisible = [];
  let quickActive = 0;
  const QUICK_CODE_TIMEOUT_MS = 950;
  let quickCodeBuffer = "";
  let quickCodeTimer = null;

  function _commandSearchNorm(value) {
    return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function _commandItemCodeText(cmd) {
    const codes = Array.isArray(cmd && cmd.codes) ? cmd.codes.filter(Boolean) : [];
    return `${String((cmd && cmd.keys) || "").trim()}${codes.length ? ` · ${codes.map(v => String(v).toUpperCase()).join("/")}` : ""}`.trim();
  }

  function _commandSearchResultChip(kind) {
    const k = String(kind || "").trim().toLowerCase();
    if (k === "task") return "Task";
    if (k === "note") return "Note";
    if (k === "timew") return "Timew";
    if (k === "day") return "Day";
    if (k === "queued") return "Queued";
    return "Cmd";
  }

  function _commandSearchResultClass(kind) {
    return `kind-${String(kind || "command").trim().toLowerCase()}`;
  }

  function _commandSearchTerms() {
    const qRaw = String((elCommandQ && elCommandQ.value) || "").trim();
    const q = _commandSearchNorm(qRaw);
    const terms = q ? q.split(" ").filter(Boolean) : [];
    return { qRaw, q, terms };
  }

  function _commandTodayYmd() {
    try { return ymdFromMs(Date.now()); } catch (_) { return ""; }
  }

  function _commandDayLabel(dayMs) {
    const dt = new Date(Number(dayMs) || 0);
    const wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.getDay()] || "Day";
    return `${wd} ${ymdFromMs(dayMs)}`;
  }

  function _commandDaySummary(di, ymd, noteCount) {
    const taskCount = Array.isArray(lastDayVis) && Array.isArray(lastDayVis[di]) ? lastDayVis[di].length : 0;
    const bits = [];
    bits.push(`${taskCount} planned`);
    if (noteCount) bits.push(`${noteCount} note${noteCount === 1 ? "" : "s"}`);
    if (di === activeDayIndex) bits.push("active");
    if (ymd === _commandTodayYmd()) bits.push("today");
    return bits.join(" • ");
  }

  function _commandTaskTimeLabel(uuid) {
    try {
      const eff = effectiveInterval(uuid);
      if (eff && Number.isFinite(eff.startMs) && Number.isFinite(eff.dueMs)) {
        return `${ymdFromMs(eff.startMs)} ${_hmFromMin(minuteOfDayFromMs(eff.startMs))}-${_hmFromMin(minuteOfDayFromMs(eff.dueMs))}`;
      }
    } catch (_) {}
    return "backlog";
  }

  function _commandTaskProjectLabel(task) {
    const proj = String((task && task.project) || "").trim();
    return proj ? `project:${proj}` : "no project";
  }

  function _commandTaskTagsLabel(task) {
    const tags = Array.isArray(task && task.tags) ? task.tags.map(v => String(v || "").trim()).filter(Boolean) : [];
    return tags.length ? tags.map(tag => `#${tag}`).join(" ") : "no tags";
  }

  function _commandNoteSummary(note) {
    if (!note) return "";
    const bits = [];
    if (Array.isArray(note.repeat_dows) && note.repeat_dows.length) {
      bits.push(`recurring ${fmtRepeatDows(note.repeat_dows)}`);
      if (note.start_min == null || note.end_min == null) bits.push("all-day");
      else bits.push(`${_hmFromMin(note.start_min)}-${_hmFromMin(note.end_min)}`);
    } else if (note.bucket_day_key) {
      bits.push(String(note.bucket_day_key));
      if (note.start_min == null || note.end_min == null) bits.push("all-day");
      else bits.push(`${_hmFromMin(note.start_min)}-${_hmFromMin(note.end_min || note.start_min)}`);
    } else {
      bits.push("unplaced");
    }
    if (note.pinned) bits.push("pinned");
    if (note.archived) bits.push("archived");
    return bits.join(" • ");
  }

  function _commandQueuedTargetUuid(line) {
    const raw = String(line || "").trim();
    if (!raw) return null;
    const m = raw.match(/^task\s+([0-9a-f]{8})\b/i);
    if (!m) return null;
    const ident = String(m[1] || "").toLowerCase();
    for (const task of (DATA.tasks || [])) {
      const uuid = String((task && task.uuid) || "").trim();
      if (uuid && uuid.toLowerCase().startsWith(ident)) return uuid;
    }
    return null;
  }

  function _jumpToTaskFromSearch(uuid) {
    const u = String(uuid || "").trim();
    if (!u) return;
    try { setActiveDayFromUuid(u); } catch (_) {}
    try { setSelectionOnly(u); } catch (_) {}
    try {
      const eff = effectiveInterval(u);
      if (eff && Number.isFinite(eff.startMs)) {
        const di = dayIndexFromMs(eff.startMs);
        const minute = minuteOfDayFromMs(eff.startMs);
        if (di != null && Number.isFinite(minute) && typeof window.__scalpel_jump === "function") {
          window.__scalpel_jump(di, minute);
        }
      }
    } catch (_) {}
    try { rerenderAll({ mode: "selection", immediate: true }); } catch (_) {}
  }

  function _openQueuedSearchResult(entry) {
    const e = entry || {};
    const line = String(e.line || "");
    const targetUuid = _commandQueuedTargetUuid(line);
    try {
      if (typeof globalThis.__scalpel_openCommandSection === "function") {
        globalThis.__scalpel_openCommandSection("output");
      }
    } catch (_) {}
    if (targetUuid) _jumpToTaskFromSearch(targetUuid);
    try {
      const card = document.querySelector(".card.commands");
      if (card && typeof card.scrollIntoView === "function") {
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    } catch (_) {}
    if (elStatus) {
      elStatus.textContent = targetUuid
        ? `Queued change ready for ${String(targetUuid).slice(0, 8)}.`
        : "Queued change ready in Commands.";
    }
  }

  function _buildCommandSearchItems() {
    return quickCommands.map((cmd, idx) => ({
      kind: "command",
      itemId: String(cmd.id || `cmd-${idx}`),
      commandId: String(cmd.id || `cmd-${idx}`),
      label: cmd.label,
      hint: cmd.hint,
      aux: _commandItemCodeText(cmd),
      search: _commandSearchNorm(`command ${cmd.label} ${cmd.hint} ${cmd.keys} ${(Array.isArray(cmd.codes) ? cmd.codes.join(" ") : "")}`),
      codes: Array.isArray(cmd.codes) ? cmd.codes.slice() : [],
      defaultVisible: true,
      defaultRank: 2000 - idx,
      run: cmd.run,
    }));
  }

  function _buildDaySearchItems() {
    const todayYmd = _commandTodayYmd();
    const notes = (typeof listNotesSorted === "function") ? listNotesSorted() : [];
    const noteCounts = new Map();
    for (const note of notes) {
      const ymd = String((note && note.bucket_day_key) || "").trim();
      if (!ymd) continue;
      noteCounts.set(ymd, (noteCounts.get(ymd) || 0) + 1);
    }
    const out = [];
    for (let i = 0; i < DAYS; i++) {
      const dayMs = Array.isArray(dayStarts) && Number.isFinite(dayStarts[i]) ? dayStarts[i] : (VIEW_START_MS + i * 86400000);
      const ymd = ymdFromMs(dayMs);
      const label = _commandDayLabel(dayMs);
      const aliases = [];
      if (ymd === todayYmd) aliases.push("today");
      if (i === activeDayIndex) aliases.push("active");
      const noteCount = Number(noteCounts.get(ymd) || 0);
      out.push({
        kind: "day",
        itemId: `day:${i}:${ymd}`,
        label,
        hint: _commandDaySummary(i, ymd, noteCount),
        aux: `#${i + 1}`,
        search: _commandSearchNorm(`day ${label} ${ymd} ${aliases.join(" ")} ${_commandDaySummary(i, ymd, noteCount)}`),
        defaultVisible: (i === activeDayIndex) || i < Math.min(3, DAYS),
        defaultRank: 1200 - i,
        boost: (i === activeDayIndex) ? 12 : 0,
        run: () => {
          try { setActiveDay(i, true); } catch (_) {}
          try { if (typeof window.__scalpel_jump === "function") window.__scalpel_jump(i, WORK_START); } catch (_) {}
          try { rerenderAll({ mode: "selection", immediate: true }); } catch (_) {}
        },
      });
    }
    return out;
  }

  function _buildTaskSearchItems() {
    const out = [];
    for (const task of (DATA.tasks || [])) {
      if (!task || !task.uuid || task.nautical_preview) continue;
      const ident = String(task.uuid || "").slice(0, 8);
      const proj = _commandTaskProjectLabel(task);
      const tags = _commandTaskTagsLabel(task);
      const status = String(task.status || "pending");
      const timeLabel = _commandTaskTimeLabel(task.uuid);
      const localLabel = task.local ? "local draft" : "task";
      out.push({
        kind: "task",
        itemId: `task:${task.uuid}`,
        label: String(task.description || ident || "Task"),
        hint: `${localLabel} ${ident} • ${proj} • ${timeLabel}`,
        aux: tags,
        search: _commandSearchNorm(`task ${localLabel} ${ident} ${task.uuid} ${task.description || ""} ${proj} ${tags} ${status} ${timeLabel}`),
        boost: task.local ? 2 : 0,
        run: async () => {
          _jumpToTaskFromSearch(task.uuid);
          try { await __openTaskEditModal(task.uuid); } catch (_) {}
        },
      });
    }
    return out;
  }

  function _buildNoteSearchItems() {
    const out = [];
    const notes = (typeof listNotesSorted === "function") ? listNotesSorted() : [];
    for (const note of notes) {
      if (!note) continue;
      const isTimew = !!(typeof _isTimewNote === "function" && _isTimewNote(note));
      const summary = _commandNoteSummary(note);
      out.push({
        kind: isTimew ? "timew" : "note",
        itemId: `${isTimew ? "timew" : "note"}:${String(note.id || "")}`,
        label: String(note.text || "(empty note)"),
        hint: summary || (isTimew ? "imported interval" : "note"),
        aux: isTimew ? "imported interval" : "notes",
        search: _commandSearchNorm(`${isTimew ? "timew imported interval" : "note"} ${note.text || ""} ${summary} ${note.bucket_day_key || ""}`),
        run: () => {
          try { setNotesVisible(true, true); } catch (_) {}
          try {
            if (note.bucket_day_key) {
              const di = dayIndexFromYmd(note.bucket_day_key);
              if (di != null) {
                setActiveDay(di, true);
                if (typeof window.__scalpel_jump === "function") {
                  const minute = Number.isFinite(note.start_min) ? note.start_min : WORK_START;
                  window.__scalpel_jump(di, minute);
                }
              }
            }
          } catch (_) {}
          try { openNoteEditor(note.id); } catch (_) {}
        },
      });
    }
    return out;
  }

  function _buildQueuedSearchItems() {
    const out = [];
    const entries = (typeof buildApplyCommandEntries === "function") ? buildApplyCommandEntries() : [];
    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i] || {};
      const kind = String(entry.kind || "queued");
      const line = String(entry.line || "").trim();
      if (!line) continue;
      const targetUuid = _commandQueuedTargetUuid(line);
      out.push({
        kind: "queued",
        itemId: `queued:${i}`,
        label: line,
        hint: `queued ${kind} #${i + 1}${targetUuid ? ` • ${String(targetUuid).slice(0, 8)}` : ""}`,
        aux: kind,
        search: _commandSearchNorm(`queued change ${kind} command ${line} ${targetUuid || ""}`),
        run: () => _openQueuedSearchResult(entry),
      });
    }
    return out;
  }

  function _scoreCommandSearchItem(item, q, terms) {
    if (!item) return -1;
    const label = _commandSearchNorm(item.label);
    const hint = _commandSearchNorm(item.hint);
    const aux = _commandSearchNorm(item.aux);
    const search = _commandSearchNorm(item.search || `${item.label} ${item.hint} ${item.aux}`);
    if (!terms.length) return item.defaultVisible ? (Number(item.defaultRank) || 0) : -1;
    if (!terms.every((term) => search.includes(term))) return -1;
    let score = 0;
    if (label === q) score += 180;
    else if (label.startsWith(q)) score += 130;
    else if (search.startsWith(q)) score += 95;
    else if (search.includes(q)) score += 72;
    for (const term of terms) {
      if (label.includes(term)) score += 12;
      else if (hint.includes(term)) score += 7;
      else if (aux.includes(term)) score += 5;
    }
    return score + (Number(item.boost) || 0);
  }

  function _buildUnifiedSearchItems() {
    return []
      .concat(_buildCommandSearchItems())
      .concat(_buildTaskSearchItems())
      .concat(_buildNoteSearchItems())
      .concat(_buildDaySearchItems())
      .concat(_buildQueuedSearchItems());
  }

  function _quickFilter(){
    const { q, terms } = _commandSearchTerms();
    const scored = [];
    for (const item of _buildUnifiedSearchItems()) {
      const score = _scoreCommandSearchItem(item, q, terms);
      if (score < 0) continue;
      scored.push({ item, score });
    }
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return String(a.item.label || "").localeCompare(String(b.item.label || ""));
    });
    quickVisible = scored.slice(0, 60).map(x => x.item);
    if (!quickVisible.length) quickActive = -1;
    else quickActive = clamp(quickActive, 0, quickVisible.length - 1);
  }

  function _quickRender(){
    if (!elCommandList) return;
    elCommandList.innerHTML = "";

    if (!quickVisible.length) {
      const empty = document.createElement("div");
      empty.className = "cmdk-empty";
      empty.textContent = "No matching search results.";
      elCommandList.appendChild(empty);
      return;
    }

    for (let i = 0; i < quickVisible.length; i++) {
      const item = quickVisible[i];
      const row = document.createElement("button");
      row.type = "button";
      row.className = "cmdk-item";
      if (i === quickActive) row.classList.add("active");
      row.dataset.visIndex = String(i);
      row.dataset.kind = String((item && item.kind) || "command");
      row.dataset.itemId = String((item && item.itemId) || `result-${i}`);
      row.innerHTML =
        `<div class="cmdk-main">`
        + `<div class="cmdk-top"><span class="cmdk-kind ${escapeAttr(_commandSearchResultClass(item.kind))}">${escapeHtml(_commandSearchResultChip(item.kind))}</span>`
        + `<span class="l">${escapeHtml(item.label)}</span></div>`
        + `<div class="s">${escapeHtml(String(item.hint || ""))}</div>`
        + `</div>`
        + `<div class="k">${escapeHtml(String(item.aux || ""))}</div>`;
      row.addEventListener("click", () => runQuickCommand(i));
      elCommandList.appendChild(row);
    }
  }

  function _quickCodeClearTimer(){
    if (!quickCodeTimer) return;
    try { clearTimeout(quickCodeTimer); } catch (_) {}
    quickCodeTimer = null;
  }
  function _quickCodeReset(){
    quickCodeBuffer = "";
    _quickCodeClearTimer();
  }
  function _quickCodeArmTimer(){
    _quickCodeClearTimer();
    quickCodeTimer = setTimeout(() => {
      quickCodeBuffer = "";
      quickCodeTimer = null;
    }, QUICK_CODE_TIMEOUT_MS);
  }
  function _quickCodeMatches(prefix){
    const p = String(prefix || "").trim().toUpperCase();
    if (!p) return [];
    const out = [];
    for (const cmd of quickCommands) {
      const codes = Array.isArray(cmd.codes) ? cmd.codes : [];
      if (codes.some((c) => String(c || "").toUpperCase().startsWith(p))) out.push(String(cmd.id || ""));
    }
    return out;
  }
  function _quickCodeExacts(code){
    const p = String(code || "").trim().toUpperCase();
    if (!p) return [];
    const out = [];
    for (const cmd of quickCommands) {
      const codes = Array.isArray(cmd.codes) ? cmd.codes : [];
      if (codes.some((c) => String(c || "").toUpperCase() === p)) out.push(String(cmd.id || ""));
    }
    return out;
  }
  function _quickFocusByCommandId(commandId){
    const id = String(commandId || "").trim();
    if (!id) return;
    const visIndex = quickVisible.findIndex(item => String((item && item.commandId) || "") === id);
    if (visIndex < 0) return;
    quickActive = visIndex;
    _quickRender();
    try {
      const row = elCommandList && elCommandList.querySelector(`[data-vis-index="${visIndex}"]`);
      if (row && typeof row.scrollIntoView === "function") row.scrollIntoView({ block: "nearest" });
    } catch (_) {}
  }

  function runQuickCommand(visIndex){
    if (!Number.isInteger(visIndex) || visIndex < 0 || visIndex >= quickVisible.length) return;
    const item = quickVisible[visIndex];
    if (!item || typeof item.run !== "function") return;
    closeCommandModal();
    try {
      const out = item.run();
      if (out && typeof out.then === "function") out.catch(() => {});
    } catch (_) {}
  }

  function openCommandModal(seed){
    if (!elCommandModal) return;
    closeOverflowMenu();
    closeHelpModal();
    elCommandModal.style.display = "flex";
    if (elCommandQ) {
      elCommandQ.value = (seed == null) ? "" : String(seed);
      setTimeout(() => { try { elCommandQ.focus(); elCommandQ.select(); } catch (_) {} }, 0);
    }
    _quickCodeReset();
    quickActive = 0;
    _quickFilter();
    _quickRender();
  }
  function closeCommandModal(){
    if (!elCommandModal) return;
    _quickCodeReset();
    elCommandModal.style.display = "none";
  }

  function closeTopModal(){
    if (_isOpen(elCommandModal)) { closeCommandModal(); return true; }
    if (_isOpen(elHelpModal)) { closeHelpModal(); return true; }
    return false;
  }
  globalThis.__scalpel_closeTopModal = closeTopModal;

  if (elBtnHelp) elBtnHelp.addEventListener("click", openHelpModal);
  if (elBtnCommand) elBtnCommand.addEventListener("click", () => openCommandModal(""));
  if (elBtnMoreActions && elOverflowMenu) {
    elBtnMoreActions.addEventListener("click", (ev) => {
      ev.preventDefault();
      if (_isOverflowOpen()) closeOverflowMenu();
      else openOverflowMenu();
    });
  }
  if (elOverflowMenu) {
    elOverflowMenu.addEventListener("click", (ev) => {
      const t = ev && ev.target;
      if (t && typeof t.closest === "function" && t.closest("button")) closeOverflowMenu();
    });
  }
  document.addEventListener("pointerdown", (ev) => {
    if (!_isOverflowOpen()) return;
    const t = ev && ev.target;
    if (!elActionOverflow || !t || (typeof elActionOverflow.contains === "function" && elActionOverflow.contains(t))) return;
    closeOverflowMenu();
  });
  if (elHelpClose) elHelpClose.addEventListener("click", closeHelpModal);
  if (elHelpModal) elHelpModal.addEventListener("click", (ev) => { if (ev.target === elHelpModal) closeHelpModal(); });
  if (elHelpOpenCommands) elHelpOpenCommands.addEventListener("click", () => {
    closeHelpModal();
    openCommandModal("");
  });
  if (elCommandClose) elCommandClose.addEventListener("click", closeCommandModal);
  if (elCommandModal) elCommandModal.addEventListener("click", (ev) => { if (ev.target === elCommandModal) closeCommandModal(); });

  if (elCommandQ) {
    elCommandQ.addEventListener("input", () => {
      if (String(elCommandQ.value || "").trim()) _quickCodeReset();
      quickActive = 0;
      _quickFilter();
      _quickRender();
    });
    elCommandQ.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        closeCommandModal();
        ev.preventDefault();
        ev.stopPropagation();
        return;
      }
      if (ev.key === "ArrowDown") {
        _quickCodeReset();
        if (quickVisible.length) {
          quickActive = (quickActive + 1 + quickVisible.length) % quickVisible.length;
          _quickRender();
        }
        ev.preventDefault();
        return;
      }
      if (ev.key === "ArrowUp") {
        _quickCodeReset();
        if (quickVisible.length) {
          quickActive = (quickActive - 1 + quickVisible.length) % quickVisible.length;
          _quickRender();
        }
        ev.preventDefault();
        return;
      }
      if (!ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        const key = String(ev.key || "");
        const keyIsChar = (key.length === 1 && /[a-z0-9]/i.test(key));
        const queryEmpty = !String(elCommandQ.value || "").trim();
        if (queryEmpty && (keyIsChar || (key === "Backspace" && quickCodeBuffer))) {
          if (keyIsChar) {
            const next = (quickCodeBuffer + key.toUpperCase()).slice(-4);
            const matches = _quickCodeMatches(next);
            if (matches.length) {
              ev.preventDefault();
              quickCodeBuffer = next;
              _quickCodeArmTimer();
              _quickFocusByCommandId(matches[0]);
              const exact = _quickCodeExacts(quickCodeBuffer);
              if (exact.length === 1) {
                const visIndex = quickVisible.findIndex(item => String((item && item.commandId) || "") === exact[0]);
                _quickCodeReset();
                if (visIndex >= 0) runQuickCommand(visIndex);
              } else {
                showToast(`Code: ${quickCodeBuffer}`, { durationMs: 900 });
              }
              return;
            }
            if (quickCodeBuffer) _quickCodeReset();
          } else if (key === "Backspace" && quickCodeBuffer) {
            ev.preventDefault();
            quickCodeBuffer = quickCodeBuffer.slice(0, -1);
            if (!quickCodeBuffer) {
              _quickCodeReset();
              return;
            }
            const matches = _quickCodeMatches(quickCodeBuffer);
            if (!matches.length) {
              _quickCodeReset();
              return;
            }
            _quickCodeArmTimer();
            _quickFocusByCommandId(matches[0]);
            showToast(`Code: ${quickCodeBuffer}`, { durationMs: 800 });
            return;
          }
        } else if (!queryEmpty && quickCodeBuffer) {
          _quickCodeReset();
        }
      }
      if (ev.key === "Enter") {
        _quickCodeReset();
        if (quickVisible.length && quickActive >= 0) {
          runQuickCommand(quickActive);
          ev.preventDefault();
        }
      }
    });
  }

  document.addEventListener("keydown", (ev) => {
    try {
      const key = String(ev.key || "");
      const lower = key.toLowerCase();
      const typing = _isTypingTarget(ev);

      if (key === "Escape" && _isOverflowOpen()) {
        closeOverflowMenu();
        ev.preventDefault();
        return;
      }

      if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && !ev.shiftKey && lower === "k") {
        if (typing) return;
        ev.preventDefault();
        openCommandModal("");
        return;
      }

      if (!ev.ctrlKey && !ev.metaKey && !ev.altKey && !typing) {
        if (key === "?" || (ev.shiftKey && key === "/")) {
          ev.preventDefault();
          openHelpModal();
          return;
        }
        if (key === "F1") {
          ev.preventDefault();
          openHelpModal();
          return;
        }
      }
    } catch (_) {}
  });

  // Nautical preview toggle
  const NAUTICAL_PREVIEW_KEY = "scalpel.nautical.preview";
  const elBtnNauticalPreview = document.getElementById("btnNauticalPreview");
  if (elBtnNauticalPreview && !hasNauticalPreview) {
    elBtnNauticalPreview.style.display = "none";
  }
  (function initNauticalPreview(){
    if (!hasNauticalPreview) return;
    try {
      const raw = (typeof globalThis.__scalpel_storeGet === "function")
        ? globalThis.__scalpel_storeGet(NAUTICAL_PREVIEW_KEY, null)
        : null;
      if (raw != null) {
        const s = String(raw).toLowerCase();
        showNauticalPreview = (s === "1" || s === "true" || s === "on");
      }
    } catch (_) {}

    function applyNauticalPreviewUI(){
      if (!elBtnNauticalPreview) return;
      elBtnNauticalPreview.classList.toggle("on", !!showNauticalPreview);
      elBtnNauticalPreview.textContent = showNauticalPreview ? "Nautical: On" : "Nautical: Off";
    }
    applyNauticalPreviewUI();

    if (elBtnNauticalPreview) {
      elBtnNauticalPreview.addEventListener("click", () => {
        showNauticalPreview = !showNauticalPreview;
        try {
          if (typeof globalThis.__scalpel_storeSet === "function") {
            globalThis.__scalpel_storeSet(NAUTICAL_PREVIEW_KEY, showNauticalPreview ? "1" : "0");
          }
        } catch (_) {}
        applyNauticalPreviewUI();
        rerenderAll({ mode: "full", immediate: true });
      });
    }
  })();
  // -----------------------------
  // View window controls (Start / Days / Overdue)
  // -----------------------------
  // === scalpel view window persistence (boot-safe, v1) ===
  const VIEWWIN_GLOBAL_KEY = "scalpel.viewwin.global";
  if (!globalThis.__scalpel_boot_viewwin_phase) globalThis.__scalpel_boot_viewwin_phase = "init";

  function __scalpel_safeParseJSON(s){
    if (!s || typeof s !== "string") return null;
    try { return JSON.parse(s); } catch (_) { return null; }
  }

  function __scalpel_readViewWin(){
    if (globalThis.__scalpel_viewwin_seed_locked) return null;
    // Priority: global -> per-view
    try{
      const g = (typeof globalThis.__scalpel_storeGet === "function")
        ? globalThis.__scalpel_storeGet(VIEWWIN_GLOBAL_KEY, null)
        : null;
      const stG = __scalpel_safeParseJSON(g);
      if (stG && stG.startYmd) return stG;
    }catch(_){}
    try{
      const p = (typeof globalThis.__scalpel_storeGet === "function")
        ? globalThis.__scalpel_storeGet(viewWinKey, null)
        : null;
      const stP = __scalpel_safeParseJSON(p);
      if (stP && stP.startYmd) return stP;
    }catch(_){}
    return null;
  }

  // Seed the view window BEFORE the first render to prevent "today" clobber.
  (function __scalpel_bootApplyViewWin(){
    if (globalThis.__scalpel_viewwin_seed_locked) {
      globalThis.__scalpel_boot_viewwin_phase = "applied";
      return;
    }
    if (globalThis.__scalpel_boot_viewwin_phase === "applied") return;
    globalThis.__scalpel_boot_viewwin_phase = "applying";
    const st = __scalpel_readViewWin();
    if (st && st.startYmd){
      try{
        const startYmd = String(st.startYmd);
        const futureDays = Number.isFinite(+st.futureDays) ? clamp(+st.futureDays, 1, 60) : FUTURE_DAYS;
        const overdueDays = Number.isFinite(+st.overdueDays) ? clamp(+st.overdueDays, 0, 30) : OVERDUE_DAYS;

        const sMs = msFromYmd(startYmd);
        if (Number.isFinite(sMs)){
          START_YMD = startYmd;
          FUTURE_DAYS = futureDays;
          OVERDUE_DAYS = overdueDays;

          VIEW_START_MS = sMs - (OVERDUE_DAYS * 86400000);
          DAYS = FUTURE_DAYS + OVERDUE_DAYS;

          document.documentElement.style.setProperty("--days", String(DAYS));
          recomputeDayStarts();
          setRangeMeta();

          // If persisted view window changed the column count, rebuild the skeleton now
          // so headers/body match the CSS grid column count on first paint.
          try{
            const cols = document.querySelectorAll(".day-col");
            if (!cols || cols.length !== DAYS) {
              if (typeof buildCalendarSkeleton === "function") buildCalendarSkeleton();
            }
          }catch(_){
            try{ if (typeof buildCalendarSkeleton === "function") buildCalendarSkeleton(); }catch(_2){}
          }
        }
      }catch(_){}
    }
    globalThis.__scalpel_boot_viewwin_phase = "applied";
  })();
  // === /scalpel view window persistence (boot-safe, v1) ===
    function saveViewWin() {
    // Guard: avoid overwriting persisted startYmd during boot (e.g., initZoom->rerenderAll).
    if (globalThis.__scalpel_boot_viewwin_phase && globalThis.__scalpel_boot_viewwin_phase !== "applied") return;

    const obj = { startYmd: START_YMD, futureDays: FUTURE_DAYS, overdueDays: OVERDUE_DAYS };

    try {
      const s = JSON.stringify(obj);
      if (typeof globalThis.__scalpel_storeSet === "function") {
        // Always keep a global copy (survives regenerated HTML / view_key changes).
        globalThis.__scalpel_storeSet(VIEWWIN_GLOBAL_KEY, s);
        // Also keep per-view copy.
        globalThis.__scalpel_storeSet(viewWinKey, s);
      }
    } catch (_) {}
  }

  function syncViewWinControls() {
    if (elVwStart) elVwStart.value = START_YMD;

    if (elVwDays) {
      if (!elVwDays._populated) {
        const opts = [1,3,5,7,10,14,21,28];
        for (const v of opts) {
          const o = document.createElement("option");
          o.value = String(v);
          o.textContent = String(v);
          elVwDays.appendChild(o);
        }
        elVwDays._populated = true;
      }
      elVwDays.value = String(FUTURE_DAYS);
    }

    if (elVwOverdue) {
      if (!elVwOverdue._populated) {
        const opts = [0,1,2,3,5,7,14];
        for (const v of opts) {
          const o = document.createElement("option");
          o.value = String(v);
          o.textContent = String(v);
          elVwOverdue.appendChild(o);
        }
        elVwOverdue._populated = true;
      }
      elVwOverdue.value = String(OVERDUE_DAYS);
    }
  }

  function applyViewWin(next) {
    const startYmd = (next && next.startYmd) ? String(next.startYmd) : START_YMD;
    const futureDays = next && Number.isFinite(Number(next.futureDays)) ? clamp(Number(next.futureDays), 1, 60) : FUTURE_DAYS;
    const overdueDays = next && Number.isFinite(Number(next.overdueDays)) ? clamp(Number(next.overdueDays), 0, 30) : OVERDUE_DAYS;

    const sMs = msFromYmd(startYmd);
    if (!Number.isFinite(sMs)) return;

    START_YMD = startYmd;
    FUTURE_DAYS = futureDays;
    OVERDUE_DAYS = overdueDays;

    VIEW_START_MS = sMs - OVERDUE_DAYS * 86400000;
    DAYS = FUTURE_DAYS + OVERDUE_DAYS;

    document.documentElement.style.setProperty("--days", String(DAYS));
    recomputeDayStarts();
    setRangeMeta();

    // Active day becomes "today if visible", else first day.
    let di = dayIndexFromMs(Date.now());
    if (di < 0) di = 0;
    if (typeof setActiveDay === "function") setActiveDay(clamp(di, 0, DAYS - 1), true);
    else {
      activeDayIndex = clamp(di, 0, DAYS - 1);
      try { if (typeof globalThis.__scalpel_storeSet === "function") globalThis.__scalpel_storeSet(activeDayKey, String(activeDayIndex)); } catch (_) {}
    }

    buildCalendarSkeleton();
    rerenderAll({ mode: "full", immediate: true });
    try { renderNowLine(); } catch (_) {}
    try { renderNextUp(); } catch (_) {}

    saveViewWin();
    syncViewWinControls();
  }

  function shiftStartDays(deltaDays) {
    const sMs = msFromYmd(START_YMD);
    if (!Number.isFinite(sMs)) return;
    const nextMs = sMs + deltaDays * 86400000;
    applyViewWin({ startYmd: ymdFromMs(nextMs) });
  }

  // Wire controls
  syncViewWinControls();

  if (elVwStart) elVwStart.addEventListener("change", () => applyViewWin({ startYmd: elVwStart.value }));
  if (elVwDays) elVwDays.addEventListener("change", () => applyViewWin({ futureDays: Number(elVwDays.value) }));
  if (elVwOverdue) elVwOverdue.addEventListener("change", () => applyViewWin({ overdueDays: Number(elVwOverdue.value) }));

  if (elVwPrevDay) elVwPrevDay.addEventListener("click", () => shiftStartDays(-1));
  if (elVwNextDay) elVwNextDay.addEventListener("click", () => shiftStartDays(1));
  if (elVwPrevPage) elVwPrevPage.addEventListener("click", () => shiftStartDays(-Math.max(1, FUTURE_DAYS)));
  if (elVwNextPage) elVwNextPage.addEventListener("click", () => shiftStartDays(Math.max(1, FUTURE_DAYS)));
  if (elVwToday) elVwToday.addEventListener("click", () => applyViewWin({ startYmd: ymdFromMs(Date.now()) }));

  function countPlanOverrides(){
    let n = 0;
    try{
      for (const [u, cur] of plan.entries()){
        const t = tasksByUuid.get(u);
        if (t && (t.local || t.nautical_preview)) continue;
        const b = baseline.get(u) || { scheduled_ms: null, due_ms: null };
        const bd = baselineDur.get(u) ?? (DEFAULT_DUR * 60000);
        if (!cur) continue;
        if (cur.scheduled_ms !== b.scheduled_ms || cur.due_ms !== b.due_ms || cur.dur_ms !== bd) n += 1;
      }
    }catch(_){ }
    return n;
  }
  function hasPlanOverrides(){
    return countPlanOverrides() > 0;
  }
  function countPendingActions(){
    return (Array.isArray(actionQueue) ? actionQueue.length : 0);
  }
  function countLocalAdds(){
    return (Array.isArray(localAdds) ? localAdds.length : 0);
  }
  function countActiveDayScheduled(){
    try {
      if (!lastDayVis || !Number.isInteger(activeDayIndex) || activeDayIndex < 0 || activeDayIndex >= DAYS) return 0;
      const arr = lastDayVis[activeDayIndex];
      return Array.isArray(arr) ? arr.length : 0;
    } catch (_) {
      return 0;
    }
  }
  function hasPendingActions(){
    return (countPendingActions() + countLocalAdds()) > 0;
  }
  function hasLocalPaletteEdits(){
    try { return !!(colorMap && Object.keys(colorMap).length); } catch (_) { return false; }
  }

  const EXEC_SESSION_KEY = "scalpel.execution.session";
  const elExecBox = document.getElementById("execBox");
  const elExecMeta = document.getElementById("execMeta");
  const elExecBody = document.getElementById("execBody");
  const elExecHint = document.getElementById("execHint");
  const elBtnExecStartSel = document.getElementById("btnExecStartSel");
  const elBtnExecStartNext = document.getElementById("btnExecStartNext");
  const elBtnExecJump = document.getElementById("btnExecJump");
  const elBtnExecTimew = document.getElementById("btnExecTimew");
  const elBtnExecStop = document.getElementById("btnExecStop");

  function loadExecutionSession(){
    const raw = loadJson(EXEC_SESSION_KEY, null);
    if (!raw || typeof raw !== "object") return null;
    const uuid = String(raw.uuid || "").trim();
    const startedMs = Number(raw.started_ms);
    const dayYmd = String(raw.day_ymd || "").trim();
    if (!uuid || !Number.isFinite(startedMs) || startedMs <= 0) return null;
    return {
      uuid,
      started_ms: startedMs,
      day_ymd: /^\d{4}-\d{2}-\d{2}$/.test(dayYmd) ? dayYmd : "",
    };
  }
  let executionSession = loadExecutionSession();

  function saveExecutionSession(){
    try {
      if (!executionSession) {
        if (typeof globalThis.__scalpel_storeDel === "function") globalThis.__scalpel_storeDel(EXEC_SESSION_KEY);
        return;
      }
      if (typeof globalThis.__scalpel_storeSetJSON === "function") globalThis.__scalpel_storeSetJSON(EXEC_SESSION_KEY, executionSession);
    } catch (_) {}
  }

  function getExecutionSession(){
    return executionSession ? { ...executionSession } : null;
  }
  globalThis.__scalpel_getExecutionSession = getExecutionSession;

  function executionSessionTask(){
    const sess = executionSession;
    if (!sess || !sess.uuid) return null;
    return tasksByUuid.get(sess.uuid) || null;
  }

  function executionSessionEffective(){
    const sess = executionSession;
    if (!sess || !sess.uuid) return null;
    try { return effectiveInterval(sess.uuid); } catch (_) { return null; }
  }

  function executionSessionDayYmd(){
    const sess = executionSession;
    if (!sess) return "";
    if (sess.day_ymd) return sess.day_ymd;
    const eff = executionSessionEffective();
    if (eff && Number.isFinite(eff.startMs)) return ymdFromMs(eff.startMs);
    return "";
  }

  function executionSessionTargetUuidFromSelection(){
    if (selectionLead && tasksByUuid.has(selectionLead)) {
      const lead = tasksByUuid.get(selectionLead);
      if (lead && !lead.nautical_preview) return selectionLead;
    }
    for (const uuid of selected) {
      const t = tasksByUuid.get(uuid);
      if (t && !t.nautical_preview) return uuid;
    }
    return "";
  }

  function executionNextUpUuid(){
    try {
      const cand = chooseNextUpCandidate(Date.now());
      return cand && cand.uuid ? String(cand.uuid) : "";
    } catch (_) {
      return "";
    }
  }

  function startExecutionSession(uuid, sourceLabel){
    const u = String(uuid || "").trim();
    if (!u) {
      if (elStatus) elStatus.textContent = "Pick a task first to start execution mode.";
      return false;
    }
    const t = tasksByUuid.get(u);
    if (!t || t.nautical_preview) {
      if (elStatus) elStatus.textContent = "Execution mode requires a real task in the current view.";
      return false;
    }
    const eff = (() => { try { return effectiveInterval(u); } catch (_) { return null; } })();
    const dayYmd = (eff && Number.isFinite(eff.startMs)) ? ymdFromMs(eff.startMs) : (Number.isInteger(activeDayIndex) ? ymdFromMs(dayStarts[activeDayIndex]) : ymdFromMs(Date.now()));
    executionSession = {
      uuid: u,
      started_ms: Date.now(),
      day_ymd: dayYmd,
    };
    saveExecutionSession();
    try { setSelectionOnly(u); } catch (_) {}
    try { setActiveDayFromUuid(u); } catch (_) {}
    try { if (typeof globalThis.__scalpel_openCommandSection === "function") globalThis.__scalpel_openCommandSection("execution"); } catch (_) {}
    rerenderAll({ mode: "selection", immediate: true });
    if (elStatus) {
      const desc = String((t && t.description) || u.slice(0, 8));
      elStatus.textContent = `Started focus session from ${String(sourceLabel || "task")}: ${desc}.`;
    }
    return true;
  }

  function startExecutionSessionFromSelection(){
    return startExecutionSession(executionSessionTargetUuidFromSelection(), "selection");
  }

  function startExecutionSessionFromNextUp(){
    return startExecutionSession(executionNextUpUuid(), "Next up");
  }

  function stopExecutionSession(){
    if (!executionSession) {
      if (elStatus) elStatus.textContent = "No active focus session.";
      return false;
    }
    const prev = executionSessionTask();
    executionSession = null;
    saveExecutionSession();
    rerenderAll({ mode: "selection", immediate: true });
    if (elStatus) {
      elStatus.textContent = prev
        ? `Stopped focus session for ${String(prev.description || "").trim() || String((prev.uuid || "")).slice(0, 8)}.`
        : "Stopped focus session.";
    }
    return true;
  }

  function jumpToExecutionSession(){
    const t = executionSessionTask();
    if (!t || !t.uuid) {
      if (elStatus) elStatus.textContent = "Active focus task is not available in this view.";
      return false;
    }
    try { setSelectionOnly(t.uuid); } catch (_) {}
    try { setActiveDayFromUuid(t.uuid); } catch (_) {}
    try { focusTask(t.uuid); } catch (_) {}
    rerenderAll({ mode: "selection", immediate: true });
    return true;
  }

  function importExecutionSessionTimew(){
    const dayYmd = executionSessionDayYmd() || (Number.isInteger(activeDayIndex) && activeDayIndex >= 0 && activeDayIndex < DAYS ? ymdFromMs(dayStarts[activeDayIndex]) : "");
    if (!dayYmd) {
      if (elStatus) elStatus.textContent = "No execution day available for Timewarrior import.";
      return false;
    }
    const di = (typeof __visibleDayIndexFromYmd === "function") ? __visibleDayIndexFromYmd(dayYmd) : null;
    try { if (typeof __showTimewIntervalsForYmd === "function") __showTimewIntervalsForYmd(dayYmd, di); } catch (_) {}
    return true;
  }

  function renderExecutionSession(){
    if (!elExecBody || !elExecMeta || !elExecHint) return;
    const sess = executionSession;
    const task = executionSessionTask();
    const eff = executionSessionEffective();
    const active = !!(sess && task && task.uuid);
    document.body.classList.toggle("execution-mode-active", active);

    if (!active) {
      elExecMeta.textContent = "Idle";
      elExecBody.innerHTML = `<div class="hint">Start a focus session from the current selection or Next up.</div>`;
      elExecHint.textContent = "Execution mode keeps one active task in focus and lets you pull Timewarrior intervals for its day.";
      return;
    }

    const nowMs = Date.now();
    const elapsedMin = Math.max(0, Math.round((nowMs - Number(sess.started_ms || nowMs)) / 60000));
    const startLabel = elapsedMin <= 0 ? "Started just now" : `Started ${fmtDuration(elapsedMin)} ago`;
    const whenLine = (eff && Number.isFinite(eff.startMs) && Number.isFinite(eff.dueMs))
      ? `${ymdFromMs(eff.startMs)} • ${_hmFromMin(minuteOfDayFromMs(eff.startMs))}-${_hmFromMin(minuteOfDayFromMs(eff.dueMs))}`
      : "No planned interval in view";
    const remainingMin = (eff && Number.isFinite(eff.dueMs)) ? Math.round((eff.dueMs - nowMs) / 60000) : null;
    const remainLabel = (remainingMin == null)
      ? "No remaining estimate"
      : (remainingMin >= 0 ? `${fmtDuration(remainingMin)} left` : `${fmtDuration(Math.abs(remainingMin))} overdue`);
    const dayYmd = executionSessionDayYmd();
    const notes = (typeof listNotesSorted === "function") ? listNotesSorted() : [];
    let timewCount = 0;
    for (const note of notes) {
      if (!note) continue;
      if (String(note.bucket_day_key || "") !== dayYmd) continue;
      if (typeof _isTimewNote === "function" && _isTimewNote(note)) timewCount += 1;
    }

    elExecMeta.textContent = remainingMin != null && remainingMin < 0 ? "Overtime" : "Live";
    elExecBody.innerHTML = `
      <div class="exec-main">
        <div class="nutxt">
          <div class="title">${escapeHtml(String(task.description || "(missing task)"))}</div>
          <div class="sub">${escapeHtml(String((task.uuid || "")).slice(0, 8))} • ${escapeHtml(whenLine)}</div>
        </div>
      </div>
      <div class="exec-badges">
        <span class="exec-badge live">${escapeHtml(startLabel)}</span>
        <span class="exec-badge ${remainingMin != null && remainingMin < 0 ? "warn" : ""}">${escapeHtml(remainLabel)}</span>
        <span class="exec-badge">${escapeHtml(dayYmd || "today")}</span>
        <span class="exec-badge">${timewCount} timew note${timewCount === 1 ? "" : "s"}</span>
      </div>
    `;
    elExecHint.textContent = timewCount
      ? `Timewarrior notes already loaded for ${dayYmd}.`
      : `Import Timewarrior intervals for ${dayYmd || "the session day"} to compare plan vs execution.`;
  }

  globalThis.__scalpel_startExecutionSession = startExecutionSession;
  globalThis.__scalpel_startExecutionSessionFromSelection = startExecutionSessionFromSelection;
  globalThis.__scalpel_startExecutionSessionFromNextUp = startExecutionSessionFromNextUp;
  globalThis.__scalpel_jumpToExecutionSession = jumpToExecutionSession;
  globalThis.__scalpel_importExecutionSessionTimew = importExecutionSessionTimew;
  globalThis.__scalpel_stopExecutionSession = stopExecutionSession;
  const HISTORY_LIMIT = 48;
  let undoStack = [];
  let redoStack = [];
  let historyRestoring = false;

  function cloneJsonValue(value){
    try {
      return JSON.parse(JSON.stringify(value == null ? null : value));
    } catch (_) {
      return null;
    }
  }
  function snapshotPlanState(){
    const out = {};
    try {
      for (const [uuid, cur] of plan.entries()) {
        if (!cur) continue;
        out[uuid] = {
          scheduled_ms: cur.scheduled_ms == null ? null : Number(cur.scheduled_ms),
          due_ms: cur.due_ms == null ? null : Number(cur.due_ms),
          dur_ms: Number.isFinite(Number(cur.dur_ms)) ? Number(cur.dur_ms) : (DEFAULT_DUR * 60000),
        };
      }
    } catch (_) {}
    return out;
  }
  function snapshotLocalTaskState(){
    const out = [];
    try {
      for (const t of (DATA.tasks || [])) {
        if (!(t && t.local && t.uuid)) continue;
        const copy = cloneJsonValue(t);
        if (copy) out.push(copy);
      }
    } catch (_) {}
    out.sort((a, b) => String(a.uuid || "").localeCompare(String(b.uuid || "")));
    return out;
  }
  function exportRuntimeState(){
    const selectedUuids = [];
    try {
      for (const u of selected.values()) {
        if (tasksByUuid.has(u)) selectedUuids.push(u);
      }
    } catch (_) {}
    const notesState = (typeof globalThis.__scalpel_exportNotesState === "function")
      ? globalThis.__scalpel_exportNotesState()
      : null;
    return {
      plan: snapshotPlanState(),
      actionQueue: Array.isArray(actionQueue) ? actionQueue.slice() : [],
      actionMeta: cloneJsonValue(actionMeta || {}) || {},
      localAdds: cloneJsonValue(Array.isArray(localAdds) ? localAdds : []) || [],
      localTasks: snapshotLocalTaskState(),
      selected: selectedUuids,
      selectionLead: selectionLead || null,
      notes: cloneJsonValue(notesState),
    };
  }
  function restoreLocalTaskState(state){
    try { purgeLocalTasks(); } catch (_) {}

    const locals = Array.isArray(state && state.localTasks) ? state.localTasks : [];
    let maxLocalCounter = localTaskCounter;
    for (const raw of locals) {
      const t = cloneJsonValue(raw);
      if (!(t && typeof t === "object" && t.uuid)) continue;
      t.local = true;
      if (typeof __scalpelIndexTaskForSearch === "function") __scalpelIndexTaskForSearch(t);
      DATA.tasks.push(t);
      tasksByUuid.set(t.uuid, t);

      const planCur = state && state.plan && state.plan[t.uuid] ? state.plan[t.uuid] : null;
      const scheduledMs = (planCur && Number.isFinite(Number(planCur.scheduled_ms))) ? Number(planCur.scheduled_ms) : (Number.isFinite(Number(t.scheduled_ms)) ? Number(t.scheduled_ms) : null);
      const dueMs = (planCur && Number.isFinite(Number(planCur.due_ms))) ? Number(planCur.due_ms) : (Number.isFinite(Number(t.due_ms)) ? Number(t.due_ms) : null);
      const durMs = (planCur && Number.isFinite(Number(planCur.dur_ms)) && Number(planCur.dur_ms) > 0)
        ? Number(planCur.dur_ms)
        : (Number.isFinite(Number(t.duration_min)) && Number(t.duration_min) > 0)
          ? (Math.round(Number(t.duration_min)) * 60000)
          : (parseDurationToMs(t.duration) || (DEFAULT_DUR * 60000));

      baseline.set(t.uuid, { scheduled_ms: scheduledMs, due_ms: dueMs });
      baselineDur.set(t.uuid, durMs);
      plan.set(t.uuid, { scheduled_ms: scheduledMs, due_ms: dueMs, dur_ms: durMs });
      __scalpelDropEffectiveIntervalCache(t.uuid);

      const m = String(t.uuid).match(/^local-\d+-(\d+)$/);
      if (m) {
        const n = Number(m[1]);
        if (Number.isFinite(n) && n > maxLocalCounter) maxLocalCounter = n;
      }
    }
    localTaskCounter = maxLocalCounter;
  }
  function restoreRuntimeState(state, label){
    const snap = state && typeof state === "object" ? state : {};
    historyRestoring = true;
    try {
      resetPlanToBaseline();
      restoreLocalTaskState(snap);

      const planState = (snap && snap.plan && typeof snap.plan === "object") ? snap.plan : {};
      for (const [uuid, raw] of Object.entries(planState)) {
        if (!tasksByUuid.has(uuid) || !raw || typeof raw !== "object") continue;
        const cur = plan.get(uuid) || { scheduled_ms: null, due_ms: null, dur_ms: DEFAULT_DUR * 60000 };
        const scheduledMs = raw.scheduled_ms == null ? null : Number(raw.scheduled_ms);
        const dueMs = raw.due_ms == null ? null : Number(raw.due_ms);
        const durMs = Number(raw.dur_ms);
        plan.set(uuid, {
          scheduled_ms: Number.isFinite(scheduledMs) ? scheduledMs : cur.scheduled_ms,
          due_ms: Number.isFinite(dueMs) ? dueMs : cur.due_ms,
          dur_ms: Number.isFinite(durMs) && durMs > 0 ? durMs : cur.dur_ms,
        });
        __scalpelDropEffectiveIntervalCache(uuid);
      }
      saveEdits();

      actionQueue = Array.isArray(snap.actionQueue) ? snap.actionQueue.slice() : [];
      saveActions();
      actionMeta = cloneJsonValue(snap.actionMeta || {}) || {};
      saveActionMeta();
      localAdds = cloneJsonValue(Array.isArray(snap.localAdds) ? snap.localAdds : []) || [];

      if (snap.notes != null && typeof globalThis.__scalpel_importNotesState === "function") {
        globalThis.__scalpel_importNotesState(cloneJsonValue(snap.notes), { persist: true, render: false });
      }

      selected.clear();
      const selectedUuids = Array.isArray(snap.selected) ? snap.selected : [];
      for (const uuid of selectedUuids) {
        if (tasksByUuid.has(uuid)) selected.add(uuid);
      }
      selectionLead = (snap.selectionLead && tasksByUuid.has(snap.selectionLead)) ? snap.selectionLead : null;

      try { if (typeof __closeTaskEditModal === "function") __closeTaskEditModal(); } catch (_) {}
      try { if (typeof closeNoteModal === "function") closeNoteModal(); } catch (_) {}

      setRangeMeta();
      renderCommands();
      rerenderAll({ mode: "full", immediate: true });
      if (elStatus) elStatus.textContent = label || "Local state restored.";
    } finally {
      historyRestoring = false;
      updateHistoryButtonStates();
    }
  }
  function recordUndoSnapshot(label){
    if (historyRestoring) return false;
    undoStack.push({
      label: String(label || "change"),
      state: exportRuntimeState(),
    });
    if (undoStack.length > HISTORY_LIMIT) undoStack.shift();
    redoStack = [];
    updateHistoryButtonStates();
    return true;
  }
  function undoLastChange(){
    if (!undoStack.length) return false;
    const entry = undoStack.pop();
    redoStack.push({
      label: entry && entry.label ? entry.label : "change",
      state: exportRuntimeState(),
    });
    restoreRuntimeState(entry && entry.state ? entry.state : null, `Undid ${entry && entry.label ? entry.label : "change"}.`);
    return true;
  }
  function redoLastChange(){
    if (!redoStack.length) return false;
    const entry = redoStack.pop();
    undoStack.push({
      label: entry && entry.label ? entry.label : "change",
      state: exportRuntimeState(),
    });
    restoreRuntimeState(entry && entry.state ? entry.state : null, `Redid ${entry && entry.label ? entry.label : "change"}.`);
    return true;
  }
  function historyDepth(which){
    return which === "redo" ? redoStack.length : undoStack.length;
  }
  function _actionBtn(id){
    return document.getElementById(id);
  }
  function _cmdGuideEl(){
    return document.getElementById("cmdGuide");
  }
  function updateCommandGuide(){
    const el = _cmdGuideEl();
    if (!el) return;
    const nAny = (typeof getSelectedAnyUuids === "function") ? getSelectedAnyUuids().length : 0;
    const nCal = (typeof getSelectedCalendarUuids === "function") ? getSelectedCalendarUuids().length : 0;
    const nEdits = countPlanOverrides();
    const nQueued = countPendingActions() + countLocalAdds();
    const total = nEdits + nQueued;

    el.classList.remove("ready", "focus");

    if (executionSessionTask()) {
      const task = executionSessionTask();
      const dayYmd = executionSessionDayYmd();
      el.classList.add("focus");
      el.textContent = `Focus session active: ${String((task && task.description) || "").trim() || String((task && task.uuid) || "").slice(0, 8)} • ${dayYmd || "session day"} • import Timewarrior or jump back in.`;
      return;
    }
    if (total > 0) {
      el.classList.add("ready");
      el.textContent = `Ready: ${total} command${total === 1 ? "" : "s"} pending. Apply live, copy commands, or export plan.`;
      return;
    }
    if (nAny > 0) {
      el.classList.add("focus");
      if (nCal >= 2) {
        el.textContent = "Selection active. Use Align/Stack/Distribute, Next free slot, or drag tasks to build command output.";
      } else {
        el.textContent = "Selection active. Use Next free slot, Complete/Delete, or move a calendar task to create command output.";
      }
      return;
    }
    if (countActiveDayScheduled() > 1) {
      el.textContent = "No changes yet. Rebalance the active day, or select tasks and use Arrange tools to start building commands.";
      return;
    }
    el.textContent = "No changes yet. Select tasks or drag on the calendar to start building commands.";
  }
  function _setDisabledState(el, disabled, onTitle, offTitle){
    if (!el) return;
    el.disabled = !!disabled;
    if (disabled && onTitle) el.title = onTitle;
    else if (!disabled && offTitle) el.title = offTitle;
  }
  function updateActionButtonStates(){
    const nAny = (typeof getSelectedAnyUuids === "function") ? getSelectedAnyUuids().length : 0;
    const nCal = (typeof getSelectedCalendarUuids === "function") ? getSelectedCalendarUuids().length : 0;
    const nEdits = countPlanOverrides();
    const nQueued = countPendingActions() + countLocalAdds();
    const nActiveDay = countActiveDayScheduled();
    const execTask = executionSessionTask();
    const execDay = executionSessionDayYmd();
    const canHttp = /^https?:$/i.test(String(location.protocol || ""));
    const canStartSelection = !!executionSessionTargetUuidFromSelection();
    const canStartNext = !!executionNextUpUuid();

    _setDisabledState(_actionBtn("actDone"), nAny < 1, "Select at least one task.", "Queue complete for selected tasks.");
    _setDisabledState(_actionBtn("actDelete"), nAny < 1, "Select at least one task.", "Queue delete for selected tasks.");
    _setDisabledState(_actionBtn("opAlignStart"), nCal < 2, "Select at least two calendar tasks.", "Align start times.");
    _setDisabledState(_actionBtn("opAlignEnd"), nCal < 2, "Select at least two calendar tasks.", "Align end times.");
    _setDisabledState(_actionBtn("opStack"), nCal < 2, "Select at least two calendar tasks.", "Stack selected tasks.");
    _setDisabledState(_actionBtn("opDistribute"), nCal < 3, "Select at least three calendar tasks.", "Distribute selected tasks.");
    _setDisabledState(_actionBtn("opNextFree"), nCal < 1, "Select at least one calendar task.", "Move selected tasks to the next free slot.");
    _setDisabledState(_actionBtn("opRebalanceDay"), nActiveDay < 2, "Active day needs at least two scheduled tasks.", "Rebalance the active day inside workhours.");
    _setDisabledState(_actionBtn("actClearActions"), nQueued < 1, "No queued actions to clear.", "Clear queued actions and local placeholders.");
    _setDisabledState(_actionBtn("btnCopy"), (nEdits + nQueued) < 1, "No commands to copy.", "Copy command output.");
    _setDisabledState(
      _actionBtn("btnApplyChanges"),
      (nEdits + nQueued) < 1 || !/^https?:$/i.test(String(location.protocol || "")),
      !/^https?:$/i.test(String(location.protocol || "")) ? "Direct apply requires live mode." : "No commands to apply.",
      "Apply selected command output in live mode."
    );
    _setDisabledState(_actionBtn("btnExecStartSel"), !canStartSelection, "Select a task first.", "Start execution mode from the lead selected task.");
    _setDisabledState(_actionBtn("btnExecStartNext"), !canStartNext, "No scheduled Next up task in view.", "Start execution mode from Next up.");
    _setDisabledState(_actionBtn("btnExecJump"), !execTask, "No active focus session.", "Jump to the active execution task.");
    _setDisabledState(_actionBtn("btnExecTimew"), !canHttp || !execDay, !canHttp ? "Timewarrior import requires live mode." : "No active session day available.", "Import Timewarrior intervals for the session day.");
    _setDisabledState(_actionBtn("btnExecStop"), !execTask, "No active focus session.", "Stop the active execution session.");
    updateCommandGuide();
    updateHistoryButtonStates();
  }
  globalThis.__scalpel_updateActionButtonStates = updateActionButtonStates;
  function updateHistoryButtonStates(){
    const undoCount = historyDepth("undo");
    const redoCount = historyDepth("redo");
    _setDisabledState(_actionBtn("btnUndo"), undoCount < 1, "Nothing to undo.", "Undo last local change.");
    _setDisabledState(_actionBtn("btnRedo"), redoCount < 1, "Nothing to redo.", "Redo last undone change.");
  }
  globalThis.__scalpel_recordUndoSnapshot = recordUndoSnapshot;
  globalThis.__scalpel_undoLastChange = undoLastChange;
  globalThis.__scalpel_redoLastChange = redoLastChange;
  function updatePendingMeta(){
    if (!elPendingMeta) return;
    const nEdits = countPlanOverrides();
    const nActions = countPendingActions();
    const nAdds = countLocalAdds();
    const total = nEdits + nActions + nAdds;
    if (!total){
      elPendingMeta.textContent = "Local clean";
      elPendingMeta.classList.remove("dirty");
      elPendingMeta.title = "No local pending changes";
      return;
    }

    const bits = [];
    if (nEdits) bits.push(`${nEdits} edit${nEdits === 1 ? "" : "s"}`);
    if (nActions) bits.push(`${nActions} action${nActions === 1 ? "" : "s"}`);
    if (nAdds) bits.push(`${nAdds} add${nAdds === 1 ? "" : "s"}`);
    elPendingMeta.textContent = "Pending: " + bits.join(" • ");
    elPendingMeta.classList.add("dirty");
    elPendingMeta.title = "Local pending changes. Click to jump to Commands panel.";
  }
  function hasResettableState(){
    return hasPlanOverrides() || hasPendingActions() || hasLocalPaletteEdits() || !!compactDensity;
  }
  function dropStorageKey(key){
    if (!key) return;
    try { if (typeof globalThis.__scalpel_storeDel === "function") globalThis.__scalpel_storeDel(key); } catch (_) {}
  }

  window.addEventListener("beforeunload", (ev) => {
    try{
      if (!hasPendingActions()) return;
      ev.preventDefault();
      ev.returnValue = "";
      return "";
    }catch(_){ }
  });
  if (elPendingMeta) {
    const jumpToCommands = () => {
      try {
        if (typeof globalThis.__scalpel_openCommandSection === "function") {
          globalThis.__scalpel_openCommandSection("output");
        }
      } catch (_) {}
      const card = document.querySelector(".card.commands");
      if (card && typeof card.scrollIntoView === "function") {
        try { card.scrollIntoView({ behavior: "smooth", block: "start" }); } catch (_) {}
      }
    };
    elPendingMeta.addEventListener("click", jumpToCommands);
    elPendingMeta.addEventListener("keydown", (ev) => {
      const k = String(ev.key || "");
      if (k === "Enter" || k === " ") {
        ev.preventDefault();
        jumpToCommands();
      }
    });
  }

  document.getElementById("btnCopy").addEventListener("click", async () => {
    const text = elCommands.textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      elStatus.textContent = "Copied to clipboard.";
    } catch (e) {
      elStatus.textContent = "Clipboard copy failed (browser permissions). Select and copy manually.";
    }
  });

  document.getElementById("btnReset").addEventListener("click", () => {
    if (hasResettableState()) {
      const ok = confirm(
        "Reset local view state?\n\n"
        + "This clears local plan edits, queued actions, local placeholders, palette colors, and view preferences.\n"
        + "It does not run Taskwarrior commands."
      );
      if (!ok) {
        elStatus.textContent = "Reset cancelled.";
        return;
      }
    }

    dropStorageKey(viewKey);
    dropStorageKey(zoomKey);
    dropStorageKey(panelsKey);
    dropStorageKey(colorsKey);
    dropStorageKey(actionsKey);
    dropStorageKey(actionsMetaKey);
    dropStorageKey(CMD_SECTIONS_KEY);
    dropStorageKey(VIEWWIN_GLOBAL_KEY);
    try {
      if (typeof globalThis.__scalpel_storeDel === "function") globalThis.__scalpel_storeDel(DENSITY_KEY);
    } catch (_) {}
    applyDensity(false);

    colorMap = {};
    saveColors();
    actionQueue = [];
    saveActions();
    clearAllQueuedActions();
    localAdds = [];
    purgeLocalTasks();
    try { if (typeof resetCommandSections === "function") resetCommandSections(false); } catch (_) {}

    resetPlanToBaseline();
    clearSelection();
    applyPanelsCollapsed(window.innerWidth < 1100, false);
    buildCalendarSkeleton();
    rerenderAll({ mode: "full", immediate: true });
    elStatus.textContent = "View plan reset (localStorage cleared).";
  });

  document.getElementById("btnClearSel").addEventListener("click", () => {
    clearSelection();
    rerenderAll({ mode: "selection", immediate: true });
  });

  if (elBtnExecStartSel) {
    elBtnExecStartSel.addEventListener("click", () => {
      if (!startExecutionSessionFromSelection() && elStatus) elStatus.textContent = "Select a task first to start execution mode.";
    });
  }
  if (elBtnExecStartNext) {
    elBtnExecStartNext.addEventListener("click", () => {
      if (!startExecutionSessionFromNextUp() && elStatus) elStatus.textContent = "No scheduled Next up task is available.";
    });
  }
  if (elBtnExecJump) {
    elBtnExecJump.addEventListener("click", () => {
      if (!jumpToExecutionSession() && elStatus) elStatus.textContent = "Active focus task is not available in this view.";
    });
  }
  if (elBtnExecTimew) {
    elBtnExecTimew.addEventListener("click", () => {
      if (!importExecutionSessionTimew() && elStatus) elStatus.textContent = "No execution day available for Timewarrior import.";
    });
  }
  if (elBtnExecStop) {
    elBtnExecStop.addEventListener("click", () => {
      if (!stopExecutionSession() && elStatus) elStatus.textContent = "No active focus session.";
    });
  }

  const btnUndo = document.getElementById("btnUndo");
  if (btnUndo) {
    btnUndo.addEventListener("click", () => {
      if (!undoLastChange() && elStatus) elStatus.textContent = "Nothing to undo.";
    });
  }
  const btnRedo = document.getElementById("btnRedo");
  if (btnRedo) {
    btnRedo.addEventListener("click", () => {
      if (!redoLastChange() && elStatus) elStatus.textContent = "Nothing to redo.";
    });
  }

  function eventTargetsEditable(ev){
    const el = ev && ev.target && ev.target.closest
      ? ev.target.closest('input, textarea, select, [contenteditable="true"]')
      : null;
    return !!el;
  }
  document.addEventListener("keydown", (ev) => {
    try {
      if (!ev || eventTargetsEditable(ev)) return;
      const key = String(ev.key || "").toLowerCase();
      if (key !== "z") return;
      if (!(ev.ctrlKey || ev.metaKey)) return;
      if (ev.altKey) return;
      ev.preventDefault();
      if (ev.shiftKey) {
        if (!redoLastChange() && elStatus) elStatus.textContent = "Nothing to redo.";
        return;
      }
      if (!undoLastChange() && elStatus) elStatus.textContent = "Nothing to undo.";
    } catch (_) {}
  });

  // Now line refresh
  setInterval(() => {
    try { renderNowLine(); } catch (_) {}
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
    try { renderExecutionSession(); } catch (_) {}
  }, 60000);

  // Initial render
  rerenderAll({ mode: "full", immediate: true });
  if (executionSessionTask()) {
    try { if (typeof globalThis.__scalpel_openCommandSection === "function") globalThis.__scalpel_openCommandSection("execution"); } catch (_) {}
  }

})();
'''
