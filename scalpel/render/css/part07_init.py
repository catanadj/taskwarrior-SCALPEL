# scalpel/render/js/part07_init.py
from __future__ import annotations

JS_PART = r'''// Controls / rerender
  // -----------------------------
  function rerenderAll() {
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
    // keep now line fresh
    try { renderNowLine(); } catch (e) { console.error("NowLine render failed", e); }
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
  }

  elQ.addEventListener("input", () => rerenderAll());


  // Theme init
  applyTheme(getPreferredTheme());
  const btnTheme = document.getElementById("btnTheme");
  if (btnTheme){
    btnTheme.addEventListener("click", () => {
      const cur = document.body.classList.contains("theme-light") ? "light" : "dark";
      applyTheme(cur === "light" ? "dark" : "light");
    });
  }
  // -----------------------------
  // View window controls (Start / Days / Overdue)
  // -----------------------------
  function saveViewWin() {
    try {
      localStorage.setItem(viewWinKey, JSON.stringify({
        startYmd: START_YMD,
        futureDays: FUTURE_DAYS,
        overdueDays: OVERDUE_DAYS,
      }));
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
    activeDayIndex = clamp(di, 0, DAYS - 1);
    try { localStorage.setItem(activeDayKey, String(activeDayIndex)); } catch (_) {}

    buildCalendarSkeleton();
    rerenderAll();
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
    localStorage.removeItem(viewKey);
    localStorage.removeItem(zoomKey);
    localStorage.removeItem(panelsKey);
    localStorage.removeItem(colorsKey);
    localStorage.removeItem(actionsKey);

    colorMap = {};
    actionQueue = [];
    localAdds = [];
    purgeLocalTasks();

    resetPlanToBaseline();
    clearSelection();
    applyPanelsCollapsed(window.innerWidth < 1100, false);
    buildCalendarSkeleton();
    rerenderAll();
    elStatus.textContent = "View plan reset (localStorage cleared).";
  });

  document.getElementById("btnClearSel").addEventListener("click", () => {
    clearSelection();
    rerenderAll();
  });

  // Now line refresh
  setInterval(() => {
    try { renderNowLine(); } catch (_) {}
    try { renderNextUp(); } catch (e) { console.error("NextUp render failed", e); }
  }, 60000);

  // Initial render
  rerenderAll();

})();
'''
