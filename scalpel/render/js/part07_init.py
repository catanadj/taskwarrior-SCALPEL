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
    try { updatePendingMeta(); } catch (_) {}
    try { if (typeof renderNotesPanel === "function") renderNotesPanel(); } catch (e) { /* ignore */ }
    // keep now line fresh
    try { renderNowLine(); } catch (e) { console.error("NowLine render failed", e); }
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
  }

  function rerenderSelectionOnly() {
    try { if (typeof syncSelectionVisuals === "function") syncSelectionVisuals(); } catch (_) {}
    updateSelectionMeta();
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
      const raw = (typeof globalThis.__scalpel_kvGet === "function")
        ? globalThis.__scalpel_kvGet(DENSITY_KEY, null)
        : localStorage.getItem(DENSITY_KEY);
      if (raw == null) return false;
      const s = String(raw).toLowerCase();
      return (s === "1" || s === "true" || s === "on" || s === "compact");
    }catch(_){ return false; }
  }
  function writeDensityPref(on){
    try{
      if (typeof globalThis.__scalpel_kvSet === "function") globalThis.__scalpel_kvSet(DENSITY_KEY, on ? "1" : "0");
      else localStorage.setItem(DENSITY_KEY, on ? "1" : "0");
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
  const CMD_SECTION_DEFAULTS = { actions: false, arrange: false, ai: false, output: false };
  const CMD_SECTION_ANIM_MS = 170;
  let cmdSectionState = loadJson(CMD_SECTIONS_KEY, CMD_SECTION_DEFAULTS);
  if (!cmdSectionState || typeof cmdSectionState !== "object") cmdSectionState = { ...CMD_SECTION_DEFAULTS };

  function saveCommandSectionState(){
    try {
      if (typeof globalThis.__scalpel_kvSetJSON === "function") {
        globalThis.__scalpel_kvSetJSON(CMD_SECTIONS_KEY, cmdSectionState);
      } else {
        localStorage.setItem(CMD_SECTIONS_KEY, JSON.stringify(cmdSectionState));
      }
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
      if (typeof globalThis.__scalpel_kvSetJSON === "function") {
        globalThis.__scalpel_kvSetJSON(LEFT_SECTIONS_KEY, leftSectionState);
      } else {
        localStorage.setItem(LEFT_SECTIONS_KEY, JSON.stringify(leftSectionState));
      }
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

  // Help + quick commands (lightweight command palette)
  const elBtnHelp = document.getElementById("btnHelp");
  const elBtnCommand = document.getElementById("btnCommand");
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
      label: "Focus filter",
      hint: "Jump cursor to backlog filter input",
      keys: "/",
      codes: ["FF"],
      run: () => { try { elQ.focus(); elQ.select(); } catch (_) {} },
    },
    {
      label: "Add tasks",
      hint: "Open add-tasks modal",
      keys: "A",
      codes: ["AD"],
      run: () => { try { if (typeof openAddModal === "function") openAddModal(); } catch (_) {} },
    },
    {
      label: "Jump to today",
      hint: "Set view window start to today",
      keys: "Today",
      codes: ["TD"],
      run: () => { try { if (elVwToday) elVwToday.click(); } catch (_) {} },
    },
    {
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
      label: "Copy commands",
      hint: "Copy command output to clipboard",
      keys: "Ctrl/Cmd+C",
      codes: ["CP"],
      run: () => { try { const b = document.getElementById("btnCopy"); if (b) b.click(); } catch (_) {} },
    },
    {
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
      label: "Toggle panels",
      hint: "Collapse or expand side panels",
      keys: "Layout",
      codes: ["PN"],
      run: () => { try { const b = document.getElementById("btnTogglePanels"); if (b) b.click(); } catch (_) {} },
    },
    {
      label: "Reset local view",
      hint: "Clear local plan edits and queued actions",
      keys: "Reset",
      codes: ["RS"],
      run: () => { try { const b = document.getElementById("btnReset"); if (b) b.click(); } catch (_) {} },
    },
    {
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
      label: "Theme manager",
      hint: "Open theme manager modal",
      keys: "Ctrl+Shift+T",
      codes: ["TH"],
      run: () => { try { if (typeof openThemeModal === "function") openThemeModal(); } catch (_) {} },
    },
    {
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

  function _quickFilter(){
    const qRaw = String((elCommandQ && elCommandQ.value) || "").trim().toLowerCase();
    const q = qRaw.replace(/\s+/g, " ");
    const terms = q ? q.split(" ").filter(Boolean) : [];
    quickVisible = [];
    for (let i = 0; i < quickCommands.length; i++) {
      const c = quickCommands[i];
      const codes = Array.isArray(c.codes) ? c.codes : [];
      const blob = `${c.label} ${c.hint} ${c.keys} ${codes.join(" ")}`.toLowerCase();
      if (!terms.length || terms.every((term) => blob.includes(term))) quickVisible.push(i);
    }
    if (!quickVisible.length) quickActive = -1;
    else quickActive = clamp(quickActive, 0, quickVisible.length - 1);
  }

  function _quickRender(){
    if (!elCommandList) return;
    elCommandList.innerHTML = "";

    if (!quickVisible.length) {
      const empty = document.createElement("div");
      empty.className = "cmdk-empty";
      empty.textContent = "No matching commands.";
      elCommandList.appendChild(empty);
      return;
    }

    for (let i = 0; i < quickVisible.length; i++) {
      const cmd = quickCommands[quickVisible[i]];
      const row = document.createElement("button");
      row.type = "button";
      row.className = "cmdk-item";
      if (i === quickActive) row.classList.add("active");
      row.dataset.visIndex = String(i);
      const codes = Array.isArray(cmd.codes) ? cmd.codes.filter(Boolean) : [];
      const keyText = `${cmd.keys}${codes.length ? ` · ${codes.map(v => String(v).toUpperCase()).join("/")}` : ""}`;
      row.innerHTML = `<div class="l">${escapeHtml(cmd.label)}<div class="s">${escapeHtml(cmd.hint)}</div></div><div class="k">${escapeHtml(keyText)}</div>`;
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
    for (let i = 0; i < quickCommands.length; i++) {
      const cmd = quickCommands[i];
      const codes = Array.isArray(cmd.codes) ? cmd.codes : [];
      if (codes.some((c) => String(c || "").toUpperCase().startsWith(p))) out.push(i);
    }
    return out;
  }
  function _quickCodeExacts(code){
    const p = String(code || "").trim().toUpperCase();
    if (!p) return [];
    const out = [];
    for (let i = 0; i < quickCommands.length; i++) {
      const cmd = quickCommands[i];
      const codes = Array.isArray(cmd.codes) ? cmd.codes : [];
      if (codes.some((c) => String(c || "").toUpperCase() === p)) out.push(i);
    }
    return out;
  }
  function _quickFocusByCommandIndex(cmdIndex){
    if (!Number.isInteger(cmdIndex) || cmdIndex < 0) return;
    const visIndex = quickVisible.indexOf(cmdIndex);
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
    const cmd = quickCommands[quickVisible[visIndex]];
    if (!cmd || typeof cmd.run !== "function") return;
    closeCommandModal();
    try { cmd.run(); } catch (_) {}
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
              _quickFocusByCommandIndex(matches[0]);
              const exact = _quickCodeExacts(quickCodeBuffer);
              if (exact.length === 1) {
                const visIndex = quickVisible.indexOf(exact[0]);
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
            _quickFocusByCommandIndex(matches[0]);
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
      const raw = (typeof globalThis.__scalpel_kvGet === "function")
        ? globalThis.__scalpel_kvGet(NAUTICAL_PREVIEW_KEY, null)
        : localStorage.getItem(NAUTICAL_PREVIEW_KEY);
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
          if (typeof globalThis.__scalpel_kvSet === "function") {
            globalThis.__scalpel_kvSet(NAUTICAL_PREVIEW_KEY, showNauticalPreview ? "1" : "0");
          } else {
            localStorage.setItem(NAUTICAL_PREVIEW_KEY, showNauticalPreview ? "1" : "0");
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
      const g = (typeof globalThis.__scalpel_kvGet === "function")
        ? globalThis.__scalpel_kvGet(VIEWWIN_GLOBAL_KEY, null)
        : (localStorage.getItem(VIEWWIN_GLOBAL_KEY));
      const stG = __scalpel_safeParseJSON(g);
      if (stG && stG.startYmd) return stG;
    }catch(_){}
    try{
      const p = (typeof globalThis.__scalpel_kvGet === "function")
        ? globalThis.__scalpel_kvGet(viewWinKey, null)
        : (localStorage.getItem(viewWinKey));
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
      if (typeof globalThis.__scalpel_kvSet === "function") {
        // Always keep a global copy (survives regenerated HTML / view_key changes).
        globalThis.__scalpel_kvSet(VIEWWIN_GLOBAL_KEY, s);
        // Also keep per-view copy.
        globalThis.__scalpel_kvSet(viewWinKey, s);
      } else {
        localStorage.setItem(VIEWWIN_GLOBAL_KEY, s);
        localStorage.setItem(viewWinKey, s);
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
      try { localStorage.setItem(activeDayKey, String(activeDayIndex)); } catch (_) {}
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
  function hasPendingActions(){
    return (countPendingActions() + countLocalAdds()) > 0;
  }
  function hasLocalPaletteEdits(){
    try { return !!(colorMap && Object.keys(colorMap).length); } catch (_) { return false; }
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

    if (total > 0) {
      el.classList.add("ready");
      el.textContent = `Ready: ${total} command${total === 1 ? "" : "s"} pending. Copy commands or export plan.`;
      return;
    }
    if (nAny > 0) {
      el.classList.add("focus");
      if (nCal >= 2) {
        el.textContent = "Selection active. Use Align/Stack/Distribute or drag tasks to build command output.";
      } else {
        el.textContent = "Selection active. Use Complete/Delete or move a calendar task to create command output.";
      }
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

    _setDisabledState(_actionBtn("actDone"), nAny < 1, "Select at least one task.", "Queue complete for selected tasks.");
    _setDisabledState(_actionBtn("actDelete"), nAny < 1, "Select at least one task.", "Queue delete for selected tasks.");
    _setDisabledState(_actionBtn("opAlignStart"), nCal < 2, "Select at least two calendar tasks.", "Align start times.");
    _setDisabledState(_actionBtn("opAlignEnd"), nCal < 2, "Select at least two calendar tasks.", "Align end times.");
    _setDisabledState(_actionBtn("opStack"), nCal < 2, "Select at least two calendar tasks.", "Stack selected tasks.");
    _setDisabledState(_actionBtn("opDistribute"), nCal < 3, "Select at least three calendar tasks.", "Distribute selected tasks.");
    _setDisabledState(_actionBtn("actClearActions"), nQueued < 1, "No queued actions to clear.", "Clear queued actions and local placeholders.");
    _setDisabledState(_actionBtn("btnCopy"), (nEdits + nQueued) < 1, "No commands to copy.", "Copy command output.");
    updateCommandGuide();
  }
  globalThis.__scalpel_updateActionButtonStates = updateActionButtonStates;
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
    try { if (typeof globalThis.__scalpel_kvDel === "function") globalThis.__scalpel_kvDel(key); } catch (_) {}
    try { localStorage.removeItem(String(key)); } catch (_) {}
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
      if (typeof globalThis.__scalpel_kvDel === "function") globalThis.__scalpel_kvDel(DENSITY_KEY);
      else localStorage.removeItem(DENSITY_KEY);
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

  // Now line refresh
  setInterval(() => {
    try { renderNowLine(); } catch (_) {}
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
  }, 60000);

  // Initial render
  rerenderAll({ mode: "full", immediate: true });

})();
'''
