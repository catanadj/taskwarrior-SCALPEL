# scalpel/render/js/part06_drag_resize.py
from __future__ import annotations

JS_PART = r'''// Drag / Resize engine
  // -----------------------------
  function autoScrollDaysPane(x, y) {
    const pane = getDaysPane();
    if (!pane) return;
    const r = pane.getBoundingClientRect();
    const edge = 48;
    const step = 24;

    if (x < r.left + edge) pane.scrollLeft -= step;
    else if (x > r.right - edge) pane.scrollLeft += step;

    if (y < r.top + edge) pane.scrollTop -= step;
    else if (y > r.bottom - edge) pane.scrollTop += step;
  }

  let drag = null;

  function onPointerDownEvent(ev) {
    const el = ev.currentTarget;
    const uuid = el.dataset.uuid;
    if (!uuid) return;
    setActiveDayFromUuid(uuid);

    const isResize = ev.target && ev.target.classList && ev.target.classList.contains("resize");
    const eff = effectiveInterval(uuid);
    if (!eff) return;

    if (isResize) {
      setSelectionOnly(uuid);
      rerenderAll();
    } else {
      if (!selected.has(uuid)) {
        setSelectionOnly(uuid);
        rerenderAll();
      }
    }

    const selection = isResize ? [uuid] : getSelectedCalendarUuids();
    if (!selection.length) return;

    const base = {};
    for (const u of selection) {
      const e = effectiveInterval(u);
      if (!e) continue;
      const node = document.querySelector(`.evt[data-uuid="${u}"]`);
      if (!node) continue;
      base[u] = { startMs: e.startMs, dueMs: e.dueMs, durMs: e.durMs, el: node };
    }
    if (!base[uuid]) return;

    try { base[uuid].el.setPointerCapture(ev.pointerId); } catch (_) {}

    for (const u of selection) {
      const n = base[u] && base[u].el;
      if (n) {
        n.classList.add("dragging");
        n.style.pointerEvents = "none";
        n.style.zIndex = "999";
      }
    }

    const br = base[uuid].el.getBoundingClientRect();

    drag = {
      pointerId: ev.pointerId,
      mode: isResize ? "resize" : "move",
      leadUuid: uuid,
      leadGrabOffsetY: ev.clientY - br.top,
      selection,
      base,
      preview: null
    };

    window.addEventListener("pointermove", onPointerMoveEvent, { passive: false });
    window.addEventListener("pointerup", onPointerUpEvent, { once: true });
    window.addEventListener("pointercancel", onPointerUpEvent, { once: true });

    ev.preventDefault();
    ev.stopPropagation();
  }

  function onPointerMoveEvent(ev) {
    if (!drag) return;
    if (ev.pointerId !== drag.pointerId) return;

    autoScrollDaysPane(ev.clientX, ev.clientY);

    const dayIndex = dayIndexFromClientX(ev.clientX);
    const dayCols = document.querySelectorAll(".day-col");
    const dayCol = dayCols[dayIndex];
    if (!dayCol) return;

    const rect = dayCol.getBoundingClientRect();
    const yTopPx = (ev.clientY - rect.top) - drag.leadGrabOffsetY;

    const rawMin = WORK_START + (yTopPx / pxPerMin);
    const snappedMin = clamp(
      WORK_START + Math.round((rawMin - WORK_START) / SNAP) * SNAP,
      WORK_START,
      WORK_END
    );

    const dayStartMs = dayStarts[dayIndex];
    const lead = drag.base[drag.leadUuid];
    if (!lead) return;

    if (drag.mode === "resize") {
      const newDue = dayStartMs + minuteToMs(snappedMin);
      const minDurMin = Math.max(10, SNAP);
      const minDue = lead.startMs + minDurMin * 60000;
      const dueClamped = Math.max(newDue, minDue);

      if (startOfLocalDayMs(lead.startMs) !== startOfLocalDayMs(dueClamped)) return;

      const sMin = minuteOfDayFromMs(lead.startMs);
      const dMin = minuteOfDayFromMs(dueClamped);
      if (sMin < WORK_START || dMin > WORK_END) return;

      const newDur = (dueClamped - lead.startMs);

      drag.preview = { [drag.leadUuid]: { scheduledMs: lead.startMs, dueMs: dueClamped, durMs: newDur } };
      previewBlock(lead.el, lead.startMs, dueClamped, dayIndex);

      ev.preventDefault();
      return;
    }

    const newLeadStart = dayStartMs + minuteToMs(snappedMin);
    const deltaMs = newLeadStart - lead.startMs;

    const preview = {};
    for (const u of drag.selection) {
      const b = drag.base[u];
      if (!b) continue;

      const ns = b.startMs + deltaMs;
      const nd = b.dueMs + deltaMs;

      if (startOfLocalDayMs(ns) !== startOfLocalDayMs(nd)) return;
      const di = dayIndexFromMs(nd);
      if (di === null) return;

      const sMin = minuteOfDayFromMs(ns);
      const dMin = minuteOfDayFromMs(nd);
      if (sMin < WORK_START || dMin > WORK_END) return;

      preview[u] = { scheduledMs: ns, dueMs: nd, durMs: b.durMs };
    }

    drag.preview = preview;

    for (const u of drag.selection) {
      const b = drag.base[u];
      const p = preview[u];
      if (!b || !p) continue;
      const di = dayIndexFromMs(p.dueMs);
      if (di === null) continue;
      previewBlock(b.el, p.scheduledMs, p.dueMs, di);
    }

    ev.preventDefault();
  }

  function previewBlock(el, startMs, dueMs, dayIndex) {
    const startMin = minuteOfDayFromMs(startMs);
    const dueMin = minuteOfDayFromMs(dueMs);

    const topMin = clamp(startMin, WORK_START, WORK_END);
    const botMin = clamp(dueMin, WORK_START, WORK_END);
    const durMin = Math.max(1, botMin - topMin);

    const topPx = (topMin - WORK_START) * pxPerMin;
    const hPx = durMin * pxPerMin;

    el.style.top = `${topPx}px`;
    el.style.height = `${hPx}px`;

    const cols = document.querySelectorAll(".day-col");
    const col = cols[dayIndex];
    if (col && el.parentElement !== col) col.appendChild(el);

    el.style.left = "6px";
    el.style.width = `calc(100% - 12px)`;

    const s = new Date(startMs);
    const d = new Date(dueMs);
    const timeStr = `${pad2(s.getHours())}:${pad2(s.getMinutes())}–${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
    const durLabel = fmtDuration((dueMs - startMs) / 60000);

    const timeNode = el.querySelector(".evt-time .time-range");
    if (timeNode) timeNode.textContent = timeStr;

    const durNode = el.querySelector(".evt-time .dur-pill");
    if (durNode) durNode.textContent = durLabel;
  }

  function onPointerUpEvent(ev) {
    if (!drag) return;
    window.removeEventListener("pointermove", onPointerMoveEvent);

    for (const u of drag.selection) {
      const b = drag.base[u];
      if (b && b.el) {
        b.el.classList.remove("dragging");
        b.el.style.pointerEvents = "";
        b.el.style.zIndex = "";
      }
    }

    if (drag.preview) commitPlanMany(drag.preview);
    else rerenderAll();

    drag = null;
    ev.preventDefault();
  }

  // -----------------------------
  // Jump helpers / conflict select
  // -----------------------------
  function jumpTo(dayIndex, minute) {
    const pane = getDaysPane();
    if (!pane) return;

    const body = document.getElementById("daysBody");
    if (body) {
      const colW = body.scrollWidth / DAYS;
      pane.scrollLeft = Math.max(0, Math.round(dayIndex * colW - (pane.clientWidth * 0.25)));
    }

    const y = Math.max(0, (minute - WORK_START) * pxPerMin - 80);
    pane.scrollTop = y;
  }

  window.__scalpel_jump = (dayIndex, minute) => jumpTo(dayIndex, minute);

  window.__scalpel_select_conflict = (uuids, dayIndex, minute) => {
    selected.clear();
    for (const u of uuids) selected.add(u);
    selectionLead = uuids.length ? uuids[0] : null;
    updateSelectionMeta();
    rerenderAll();
    jumpTo(dayIndex, minute);
  };

  // -----------------------------
  // Keyboard + operations
  // -----------------------------
  function groupSelectedByDay(uuids) {
    const groups = new Map();
    for (const u of uuids) {
      const eff = effectiveInterval(u);
      if (!eff) continue;
      const di = dayIndexFromMs(eff.dueMs);
      if (di === null) continue;
      if (!groups.has(di)) groups.set(di, []);
      groups.get(di).push(u);
    }
    return groups;
  }

  function moveSelected(deltaMin, deltaDays) {
    const uuids = getSelectedCalendarUuids();
    if (!uuids.length) return;

    const dMs = (deltaMin || 0) * 60000 + (deltaDays || 0) * 86400000;
    if (!dMs) return;

    const changes = {};
    for (const u of uuids) {
      const eff = effectiveInterval(u);
      if (!eff) continue;

      const ns = eff.startMs + dMs;
      const nd = eff.dueMs + dMs;

      const di = dayIndexFromMs(nd);
      if (di === null) continue;

      changes[u] = { scheduledMs: ns, dueMs: nd, durMs: eff.durMs };
    }

    commitPlanMany(changes);
  }

  function resizeSelected(deltaMin) {
    const uuids = getSelectedCalendarUuids();
    if (!uuids.length) return;

    const dMs = (deltaMin || 0) * 60000;
    if (!dMs) return;

    const minDurMin = Math.max(10, SNAP);
    const changes = {};

    for (const u of uuids) {
      const eff = effectiveInterval(u);
      if (!eff) continue;

      const startMs = eff.startMs;
      let newDur = eff.durMs + dMs;
      const minDur = minDurMin * 60000;
      if (newDur < minDur) newDur = minDur;

      const maxDur = (WORK_END - minuteOfDayFromMs(startMs)) * 60000;
      if (maxDur > 0 && newDur > maxDur) newDur = maxDur;

      const nd = startMs + newDur;
      changes[u] = { scheduledMs: startMs, dueMs: nd, durMs: newDur };
    }

    commitPlanMany(changes);
  }

  function alignStarts() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return;

    const groups = groupSelectedByDay(uuids);
    const changes = {};

    for (const [di, arr] of groups.entries()) {
      let ref = null;
      if (selectionLead && arr.includes(selectionLead)) ref = selectionLead;

      if (!ref) {
        let best = null;
        for (const u of arr) {
          const e = effectiveInterval(u);
          if (!e) continue;
          if (!best || e.startMs < best.startMs) best = { u, startMs: e.startMs };
        }
        ref = best ? best.u : null;
      }
      if (!ref) continue;

      const refEff = effectiveInterval(ref);
      if (!refEff) continue;
      const targetStart = refEff.startMs;

      for (const u of arr) {
        const e = effectiveInterval(u);
        if (!e) continue;
        const ns = targetStart;
        const nd = ns + e.durMs;
        changes[u] = { scheduledMs: ns, dueMs: nd, durMs: e.durMs };
      }
    }

    commitPlanMany(changes);
  }

  function alignEnds() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return;

    const groups = groupSelectedByDay(uuids);
    const changes = {};

    for (const [di, arr] of groups.entries()) {
      let ref = null;
      if (selectionLead && arr.includes(selectionLead)) ref = selectionLead;

      if (!ref) {
        let best = null;
        for (const u of arr) {
          const e = effectiveInterval(u);
          if (!e) continue;
          if (!best || e.dueMs > best.dueMs) best = { u, dueMs: e.dueMs };
        }
        ref = best ? best.u : null;
      }
      if (!ref) continue;

      const refEff = effectiveInterval(ref);
      if (!refEff) continue;
      const targetDue = refEff.dueMs;

      for (const u of arr) {
        const e = effectiveInterval(u);
        if (!e) continue;
        const nd = targetDue;
        const ns = nd - e.durMs;
        changes[u] = { scheduledMs: ns, dueMs: nd, durMs: e.durMs };
      }
    }

    commitPlanMany(changes);
  }

  function stackSequentially() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return;

    const groups = groupSelectedByDay(uuids);
    const changes = {};

    for (const [di, arr] of groups.entries()) {
      const items = arr.map(u => ({ u, e: effectiveInterval(u) })).filter(x => x.e);
      items.sort((a,b) => a.e.startMs - b.e.startMs);

      if (!items.length) continue;

      let cursor = items[0].e.startMs;
      for (const it of items) {
        const ns = cursor;
        const nd = ns + it.e.durMs;
        changes[it.u] = { scheduledMs: ns, dueMs: nd, durMs: it.e.durMs };
        cursor = nd;
      }
    }

    commitPlanMany(changes);
  }

  function distributeEvenly() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 3) return;

    const groups = groupSelectedByDay(uuids);
    const changes = {};

    for (const [di, arr] of groups.entries()) {
      const items = arr.map(u => ({ u, e: effectiveInterval(u) })).filter(x => x.e);
      items.sort((a,b) => a.e.startMs - b.e.startMs);

      if (items.length < 3) continue;

      const minStart = items[0].e.startMs;
      const maxEnd = items.reduce((m, it) => Math.max(m, it.e.dueMs), -Infinity);
      const totalDur = items.reduce((s, it) => s + it.e.durMs, 0);

      let window = maxEnd - minStart;
      let gap = 0;
      if (items.length > 1) {
        gap = Math.floor((window - totalDur) / (items.length - 1));
        if (!Number.isFinite(gap) || gap < 0) gap = 0;
      }

      let cursor = minStart;
      for (const it of items) {
        const ns = cursor;
        const nd = ns + it.e.durMs;
        changes[it.u] = { scheduledMs: ns, dueMs: nd, durMs: it.e.durMs };
        cursor = nd + gap;
      }
    }

    commitPlanMany(changes);
  }

  document.getElementById("opAlignStart").addEventListener("click", alignStarts);
  document.getElementById("opAlignEnd").addEventListener("click", alignEnds);
  document.getElementById("opStack").addEventListener("click", stackSequentially);
  document.getElementById("opDistribute").addEventListener("click", distributeEvenly);

  function shouldIgnoreKey(ev) {
    const a = document.activeElement;
    if (!a) return false;
    const tag = (a.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    if (a.isContentEditable) return true;
    return false;
  }

  document.addEventListener("keydown", (ev) => {
    if (shouldIgnoreKey(ev)) return;

    if (ev.key === "Escape") {
      if (elAddModal.style.display === "flex") {
        closeAddModal();
        ev.preventDefault();
        return;
      }
      clearSelection();
      rerenderAll();
      ev.preventDefault();
      return;
    }

    if (ev.altKey && !ev.ctrlKey && !ev.metaKey) {
      if (ev.key === "ArrowUp") {
        if (ev.shiftKey) resizeSelected(-SNAP);
        else moveSelected(-SNAP, 0);
        ev.preventDefault();
      } else if (ev.key === "ArrowDown") {
        if (ev.shiftKey) resizeSelected(+SNAP);
        else moveSelected(+SNAP, 0);
        ev.preventDefault();
      } else if (ev.key === "ArrowLeft" && !ev.shiftKey) {
        moveSelected(0, -1);
        ev.preventDefault();
      } else if (ev.key === "ArrowRight" && !ev.shiftKey) {
        moveSelected(0, +1);
        ev.preventDefault();
      }
      return;
    }

    if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey) {
      const k = ev.key.toLowerCase();
      if (k === "a") { alignStarts(); ev.preventDefault(); }
      else if (k === "e") { alignEnds(); ev.preventDefault(); }
      else if (k === "s") { stackSequentially(); ev.preventDefault(); }
      else if (k === "d") { distributeEvenly(); ev.preventDefault(); }
    }
  });

  // -----------------------------
  // Actions queue
  // -----------------------------
  function queueAction(line) {
    if (!line || typeof line !== "string") return;
    actionQueue.push(line);
    saveActions();
    renderCommands();
  }

  function queueDoneSelected() {
    const uuids = getSelectedAnyUuids();
    if (!uuids.length) { elStatus.textContent = "No tasks selected."; return; }

    let queued = 0;
    let skippedLocal = 0;

    for (const u of uuids) {
      const t = tasksByUuid.get(u);
      if (!t) continue;
      if (t.local) { skippedLocal++; continue; }
      queueAction(`task ${getIdentifier(t)} done`);
      queued++;
    }

    if (!queued && skippedLocal) {
      elStatus.textContent = "Selected tasks are local placeholders. Run the queued `task add` commands first, then refresh.";
      return;
    }

    elStatus.textContent = skippedLocal
      ? `Queued done for ${queued} task(s) (skipped ${skippedLocal} local placeholder(s)).`
      : `Queued done for ${queued} task(s).`;
  }


  function queueDeleteSelected() {
    const uuids = getSelectedAnyUuids();
    if (!uuids.length) { elStatus.textContent = "No tasks selected."; return; }

    const localU = [];
    const realU = [];
    for (const u of uuids) {
      const t = tasksByUuid.get(u);
      if (!t) continue;
      if (t.local) localU.push(u);
      else realU.push(u);
    }

    // Remove local placeholders immediately (non-destructive).
    let removedLocal = 0;
    if (localU.length) {
      for (const u of localU) {
        if (removeLocalTask(u)) removedLocal++;
      }
    }

    // Queue deletes for real tasks (destructive when executed) with confirmation.
    let queued = 0;
    if (realU.length) {
      if (!confirm(`Queue delete for ${realU.length} task(s)? This is destructive when executed.`)) {
        // If user cancels, still keep any local removals already applied.
        if (removedLocal) {
          renderCommands();
          rerenderAll();
          elStatus.textContent = `Removed ${removedLocal} local placeholder(s).`;
        }
        return;
      }

      for (const u of realU) {
        const t = tasksByUuid.get(u);
        if (!t || t.local) continue;
        queueAction(`task ${getIdentifier(t)} delete`);
        queued++;
      }
    }

    // Update UI
    if (removedLocal) {
      // also drop them from selection set
      for (const u of localU) selected.delete(u);
      updateSelectionMeta();
    }

    renderCommands();
    rerenderAll();

    if (queued && removedLocal) elStatus.textContent = `Queued delete for ${queued} task(s) and removed ${removedLocal} local placeholder(s).`;
    else if (queued) elStatus.textContent = `Queued delete for ${queued} task(s).`;
    else if (removedLocal) elStatus.textContent = `Removed ${removedLocal} local placeholder(s).`;
    else elStatus.textContent = "No deletable tasks found in selection.";
  }


  function clearActions() {
    if (!actionQueue.length && !localAdds.length) return;
    if (!confirm("Clear all queued actions (and local add placeholders) for this view?")) return;

    actionQueue = [];
    localAdds = [];
    saveActions();
    purgeLocalTasks();

    renderCommands();
    rerenderAll();
    elStatus.textContent = "Cleared queued actions.";
  }


  function openAddModal() {
    elAddModal.style.display = "flex";
    setTimeout(() => elAddLines.focus(), 0);
  }
  function closeAddModal() {
    elAddModal.style.display = "none";
  }

  function queueAddTasksFromModal() {
    const raw = elAddLines.value || "";
    const lines = raw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    if (!lines.length) { elStatus.textContent = "No lines to add."; closeAddModal(); return; }

    const durMs = DEFAULT_DUR * 60000;

    function snapUpMinute(min) {
      if (min <= WORK_START) return WORK_START;
      const rel = min - WORK_START;
      const snapped = WORK_START + Math.ceil(rel / SNAP) * SNAP;
      return snapped;
    }

    function computeInitialCursor() {
      const calSel = getSelectedCalendarUuids();
      let baseDueMs = null;

      for (const u of calSel) {
        const eff = effectiveInterval(u);
        if (!eff) continue;
        if (baseDueMs === null || eff.dueMs > baseDueMs) baseDueMs = eff.dueMs;
      }

      if (baseDueMs === null) {
        // No calendar selection -> start at the top of the first day.
        return { di: 0, cursorMs: dayStarts[0] + WORK_START * 60000 };
      }

      let di = dayIndexFromMs(baseDueMs);
      if (di === null) di = 0;

      const dayStart = dayStarts[di];
      let min = minuteOfDayFromMs(baseDueMs);
      if (min < WORK_START) min = WORK_START;
      min = snapUpMinute(min);

      // If we're at/after work end, spill to next day.
      if (min >= WORK_END) {
        di = di + 1;
        if (di >= DAYS) return { di: DAYS, cursorMs: dayStarts[DAYS - 1] + WORK_END * 60000 };
        return { di, cursorMs: dayStarts[di] + WORK_START * 60000 };
      }

      return { di, cursorMs: dayStart + min * 60000 };
    }

    function nextSlot(di, cursorMs) {
      while (true) {
        if (di >= DAYS) return null;

        const dayStart = dayStarts[di];

        // Normalize cursor to this day if needed.
        if (startOfLocalDayMs(cursorMs) !== dayStart) {
          cursorMs = dayStart + WORK_START * 60000;
        }

        let min = minuteOfDayFromMs(cursorMs);
        if (min < WORK_START) min = WORK_START;
        min = snapUpMinute(min);

        // If we snapped beyond work end, spill to next day.
        if (min >= WORK_END) {
          di = di + 1;
          cursorMs = (di < DAYS) ? (dayStarts[di] + WORK_START * 60000) : cursorMs;
          continue;
        }

        const startMs = dayStart + min * 60000;
        const dueMs = startMs + durMs;
        const dueMin = min + (durMs / 60000);

        if (dueMin <= WORK_END) return { di, startMs, dueMs };

        // Not enough room in this day; spill to next.
        di = di + 1;
        cursorMs = (di < DAYS) ? (dayStarts[di] + WORK_START * 60000) : cursorMs;
      }
    }

    function createLocalTask(desc, startMs, dueMs) {
      const uuid = `local-${Date.now()}-${++localTaskCounter}`;
      const durMin = Math.max(1, Math.round(durMs / 60000));
      const t = {
        uuid,
        id: null,
        description: desc,
        project: "",
        tags: [],
        scheduled_ms: startMs,
        due_ms: dueMs,
        duration: `${durMin}min`,
        local: true,
      };

      DATA.tasks.push(t);
      tasksByUuid.set(uuid, t);
      baseline.set(uuid, { scheduled_ms: startMs, due_ms: dueMs });
      baselineDur.set(uuid, durMs);
      plan.set(uuid, { scheduled_ms: startMs, due_ms: dueMs, dur_ms: durMs });

      return uuid;
    }

    const init = computeInitialCursor();
    let di = init.di;
    let cursorMs = init.cursorMs;

    const newUuids = [];
    let placed = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const slot = nextSlot(di, cursorMs);
      if (!slot) break;

      di = slot.di;
      cursorMs = slot.dueMs;

      const uuid = createLocalTask(line, slot.startMs, slot.dueMs);
      localAdds.push({ uuid, desc: line });
      newUuids.push(uuid);
      placed++;
    }

    const skipped = lines.length - placed;

    // Select the newly created local tasks for easy nudging/stacking.
    selected.clear();
    for (const u of newUuids) selected.add(u);
    selectionLead = newUuids.length ? newUuids[0] : null;

    elAddLines.value = "";
    closeAddModal();
    setRangeMeta();
    rerenderAll();

    elStatus.textContent = skipped
      ? `Added ${placed} local task(s) below selection (default ${DEFAULT_DUR}m). ${skipped} could not be placed (out of view).`
      : `Added ${placed} local task(s) below selection (default ${DEFAULT_DUR}m).`;
  }


  document.getElementById("actDone").addEventListener("click", queueDoneSelected);
  document.getElementById("actDelete").addEventListener("click", queueDeleteSelected);
  document.getElementById("actClearActions").addEventListener("click", clearActions);
  document.getElementById("actAdd").addEventListener("click", openAddModal);

  elAddClose.addEventListener("click", closeAddModal);
  elAddModal.addEventListener("click", (ev) => {
    if (ev.target === elAddModal) closeAddModal();
  });
  elAddQueue.addEventListener("click", queueAddTasksFromModal);

  // -----------------------------
  // Zoom
  // -----------------------------
  function applyZoom(v, persist) {
    const num = Number(v);
    if (!Number.isFinite(num) || num <= 0) return;
    pxPerMin = num;
    document.documentElement.style.setProperty("--px-per-min", pxPerMin);
    elZoomVal.textContent = `${pxPerMin.toFixed(1)} px/min`;
    if (persist) localStorage.setItem(zoomKey, String(pxPerMin));

    buildCalendarSkeleton();
    rerenderAll();
  }

  (function initZoom() {
    const saved = localStorage.getItem(zoomKey);
    const initial = saved ? Number(saved) : PX_PER_MIN_DEFAULT;
    elZoom.value = String(Number.isFinite(initial) ? initial : PX_PER_MIN_DEFAULT);
    applyZoom(elZoom.value, false);
    elZoom.addEventListener("input", () => applyZoom(elZoom.value, true));
  })();

  // -----------------------------
  // Focus control wiring
  // -----------------------------
  (function initFocusControls(){
    const bar = document.getElementById("focusBar");
    if (!bar) return;
    bar.querySelectorAll("[data-fmode]").forEach(btn => btn.addEventListener("click", () => setFocusMode(btn.getAttribute("data-fmode"))));
    bar.querySelectorAll("[data-fbeh]").forEach(btn => btn.addEventListener("click", () => setFocusBehavior(btn.getAttribute("data-fbeh"))));
    const clr = document.getElementById("btnClearFocus");
    if (clr) clr.addEventListener("click", () => clearFocus());
    updateFocusUI();
  })();

  // -----------------------------
'''
