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
    const tt = tasksByUuid.get(uuid);
    if (tt && tt.nautical_preview) return;
    setActiveDayFromUuid(uuid);

    // Resize affordance
    // Historically, users resize by grabbing the bottom edge of a task block.
    // Keep the explicit handle (.resize) but also treat "near bottom" grabs as resize.
    const br0 = el.getBoundingClientRect();
    const nearBottom = (ev.clientY >= (br0.bottom - 12));
    const isResize = !!(
      (ev.target && ev.target.closest && ev.target.closest(".resize")) ||
      (ev.target && ev.target.classList && ev.target.classList.contains("resize")) ||
      nearBottom
    );
    const eff = effectiveInterval(uuid);
    if (!eff) return;

    if (isResize) {
      setSelectionOnly(uuid);
      rerenderAll({ mode: "selection", immediate: true });
    } else {
      if (!selected.has(uuid)) {
        setSelectionOnly(uuid);
        rerenderAll({ mode: "selection", immediate: true });
      }
    }

    const selection = isResize ? [uuid] : getSelectedCalendarUuids();
    if (!selection.length) return;

    // Do not drag/resize tasks with queued final actions (done/delete).
    // (User can still select them; this only blocks interactive rescheduling.)
    for (const u of selection) {
      if (queuedActionKind(u)) return;
    }

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
    // For move we want to preserve the grab offset so the block tracks the pointer.
    // For resize we want the pointer Y itself to dictate the new due (bottom edge).
    const yPx = (drag.mode === "resize")
      ? (ev.clientY - rect.top)
      : ((ev.clientY - rect.top) - drag.leadGrabOffsetY);

    const rawMin = WORK_START + (yPx / pxPerMin);
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
    const timeStr = `${fmtHm(startMs)}–${fmtHm(dueMs)}`;
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
    rerenderAll({ mode: "selection" });
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

  function computeMoveSelectedChanges(deltaMin, deltaDays) {
    const uuids = getSelectedCalendarUuids();
    if (!uuids.length) return {};

    const dMs = (deltaMin || 0) * 60000 + (deltaDays || 0) * 86400000;
    if (!dMs) return {};

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

    return changes;
  }

  function moveSelected(deltaMin, deltaDays) {
    const changes = computeMoveSelectedChanges(deltaMin, deltaDays);
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

  function computeAlignStartsChanges() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return {};

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

    return changes;
  }

  function alignStarts() {
    const changes = computeAlignStartsChanges();
    commitPlanMany(changes);
  }

  function computeAlignEndsChanges() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return {};

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

    return changes;
  }

  function alignEnds() {
    const changes = computeAlignEndsChanges();
    commitPlanMany(changes);
  }

  function computeStackSequentiallyChanges() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 2) return {};

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

    return changes;
  }

  function stackSequentially() {
    const changes = computeStackSequentiallyChanges();
    commitPlanMany(changes);
  }

  function computeDistributeEvenlyChanges() {
    const uuids = getSelectedCalendarUuids();
    if (uuids.length < 3) return {};

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

    return changes;
  }

  function distributeEvenly() {
    const changes = computeDistributeEvenlyChanges();
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

  // -----------------------------
  // Keyboard navigation (arrow keys)
  // -----------------------------
  function __scalpel_navCenter() {
    // Center point of the visible timeline viewport (best effort).
    const body = document.getElementById("daysBody") || document.getElementById("daysCol") || getDaysPane();
    if (!body) return { di: activeDayIndex || 0, minute: WORK_START };
    const br = body.getBoundingClientRect();
    const cx = br.left + (br.width / 2);
    const cy = br.top + (br.height / 2);
    let di = null;
    try { di = dayIndexFromClientX(cx); } catch (_) { di = activeDayIndex || 0; }
    di = clamp(di, 0, DAYS - 1);
    const cols = document.querySelectorAll(".day-col");
    const col = (cols && cols.length) ? cols[di] : null;
    if (!col) return { di, minute: WORK_START };
    const cr = col.getBoundingClientRect();
    const y = cy - cr.top;
    let minute = WORK_START;
    try { minute = yToMinute(y); } catch (_) { minute = WORK_START; }
    return { di, minute };
  }

  function __scalpel_indexCalendarEvents() {
    // Build an index of rendered calendar events by day, sorted by start time.
    const byDay = new Map(); // di -> [{uuid, startMs, startMin}]
    const idx = new Map();   // uuid -> {di, i, startMin}
    const all = [];

    const nodes = document.querySelectorAll('.evt[data-uuid]');
    for (const node of nodes) {
      const uuid = node.getAttribute('data-uuid');
      if (!uuid) continue;

      const eff = effectiveInterval(uuid);
      if (!eff || !Number.isFinite(eff.startMs) || !Number.isFinite(eff.dueMs)) continue;

      let di = null;
      try { di = dayIndexFromMs(eff.dueMs); } catch (_) { di = null; }
      if (di == null) {
        try { di = dayIndexFromMs(eff.startMs); } catch (_) { di = null; }
      }
      if (di == null) {
        try {
          const col = node.closest('.day-col');
          const n = col && col.dataset ? parseInt(col.dataset.dayIndex, 10) : NaN;
          if (Number.isFinite(n)) di = n;
        } catch (_) {}
      }
      if (di == null) continue;
      di = clamp(di, 0, DAYS - 1);

      const startMin = minuteOfDayFromMs(eff.startMs);
      const it = { uuid, startMs: eff.startMs, startMin };
      all.push(it);
      if (!byDay.has(di)) byDay.set(di, []);
      byDay.get(di).push(it);
    }

    for (const [di, arr] of byDay.entries()) {
      arr.sort((a, b) => (a.startMs - b.startMs) || (a.uuid.localeCompare(b.uuid)));
      for (let i = 0; i < arr.length; i++) idx.set(arr[i].uuid, { di, i, startMin: arr[i].startMin });
    }

    return { byDay, idx, all };
  }

  function __scalpel_pickNearestEvent(index, di, minute) {
    const all = index && index.all ? index.all : [];
    if (!all.length) return null;
    let best = null;
    let bestScore = Infinity;
    for (const it of all) {
      const meta = index.idx.get(it.uuid);
      if (!meta) continue;
      const score = Math.abs(meta.di - di) * 1440 + Math.abs(meta.startMin - minute);
      if (score < bestScore) { bestScore = score; best = it.uuid; }
    }
    return best;
  }

  function __scalpel_selectUuid(uuid) {
    if (!uuid) return false;
    setSelectionOnly(uuid);
    try { setActiveDayFromUuid(uuid); } catch (_) {}
    rerenderAll({ mode: "selection", immediate: true });
    try { focusTask(uuid); } catch (_) {}
    return true;
  }

  function __scalpel_navigateSelection(key) {
    const index = __scalpel_indexCalendarEvents();
    if (!index.all.length) return false;

    // If nothing selected (or lead is not visible), select the task nearest to viewport center.
    const lead = (selectionLead && index.idx.has(selectionLead)) ? selectionLead : null;
    if (!lead) {
      const c = __scalpel_navCenter();
      const u = __scalpel_pickNearestEvent(index, c.di, c.minute);
      return __scalpel_selectUuid(u);
    }

    const cur = index.idx.get(lead);
    if (!cur) return false;

    if (key === 'ArrowUp' || key === 'ArrowDown') {
      const arr = index.byDay.get(cur.di) || [];
      if (!arr.length) return false;
      const nextI = clamp(cur.i + (key === 'ArrowUp' ? -1 : +1), 0, arr.length - 1);
      const u = arr[nextI] ? arr[nextI].uuid : null;
      if (u && u !== lead) return __scalpel_selectUuid(u);
      return false;
    }

    if (key === 'ArrowLeft' || key === 'ArrowRight') {
      const dir = (key === 'ArrowLeft') ? -1 : +1;
      let di = cur.di + dir;
      while (di >= 0 && di < DAYS) {
        const arr = index.byDay.get(di) || [];
        if (arr.length) {
          // Choose the item in that day whose start minute is closest to current start minute.
          let bestU = arr[0].uuid;
          let bestD = Math.abs(arr[0].startMin - cur.startMin);
          for (const it of arr) {
            const d = Math.abs(it.startMin - cur.startMin);
            if (d < bestD) { bestD = d; bestU = it.uuid; }
          }
          return __scalpel_selectUuid(bestU);
        }
        di += dir;
      }
      return false;
    }

    return false;
  }

  function __scalpel_ensureSelectionForMove() {
    // If nothing selected, select the nearest event to center (single-lead) so Ctrl+arrows can act.
    if (getSelectedCalendarUuids().length) return true;
    const index = __scalpel_indexCalendarEvents();
    if (!index.all.length) return false;
    const c = __scalpel_navCenter();
    const u = __scalpel_pickNearestEvent(index, c.di, c.minute);
    return __scalpel_selectUuid(u);
  }

  document.addEventListener("keydown", (ev) => {
    if (shouldIgnoreKey(ev)) return;

    if (ev.key === "Escape") {
      try {
        if (typeof globalThis.__scalpel_closeTopModal === "function" && globalThis.__scalpel_closeTopModal()) {
          ev.preventDefault();
          return;
        }
      } catch (_) {}
      if (elAddModal.style.display === "flex") {
        closeAddModal();
        ev.preventDefault();
        return;
      }
      clearSelection();
      rerenderAll({ mode: "selection" });
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

    // Ctrl/Cmd + arrows: move selection
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && !ev.shiftKey) {
      if (ev.key === "ArrowUp") {
        if (__scalpel_ensureSelectionForMove()) {
          moveSelected(-SNAP, 0);
          ev.preventDefault();
        }
        return;
      } else if (ev.key === "ArrowDown") {
        if (__scalpel_ensureSelectionForMove()) {
          moveSelected(+SNAP, 0);
          ev.preventDefault();
        }
        return;
      } else if (ev.key === "ArrowLeft") {
        if (__scalpel_ensureSelectionForMove()) {
          moveSelected(0, -1);
          ev.preventDefault();
        }
        return;
      } else if (ev.key === "ArrowRight") {
        if (__scalpel_ensureSelectionForMove()) {
          moveSelected(0, +1);
          ev.preventDefault();
        }
        return;
      }
    }

    // Plain arrows: move selection focus from task to task
    if (!ev.altKey && !ev.ctrlKey && !ev.metaKey && !ev.shiftKey) {
      if (ev.key === "ArrowUp" || ev.key === "ArrowDown" || ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
        if (__scalpel_navigateSelection(ev.key)) {
          ev.preventDefault();
          return;
        }
      }
    }

    // Single-key actions on selected tasks.
    // - c : complete (queue done)
    // - d : delete (queue delete)
    // Only fires when there is an active selection and no modifiers.
    if (!ev.altKey && !ev.ctrlKey && !ev.metaKey && !ev.shiftKey) {
      const k = (ev.key || "").toLowerCase();
      if (k === "c") {
        if (getSelectedAnyUuids().length) {
          queueDoneSelected();
          ev.preventDefault();
          return;
        }
      } else if (k === "d") {
        if (getSelectedAnyUuids().length) {
          queueDeleteSelected();
          ev.preventDefault();
          return;
        }
      }
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
      setQueuedAction(u, "done");
      queued++;
    }

    if (!queued && skippedLocal) {
      elStatus.textContent = "Selected tasks are local placeholders. Run the queued `task add` commands first, then refresh.";
      return;
    }

    elStatus.textContent = skippedLocal
      ? `Queued done for ${queued} task(s) (skipped ${skippedLocal} local placeholder(s)).`
      : `Queued done for ${queued} task(s).`;
  
    rerenderAll();
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
        setQueuedAction(u, "delete");
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
    clearAllQueuedActions();

    renderCommands();
    rerenderAll();
    elStatus.textContent = "Cleared queued actions.";
  }


  let addModalSeed = null; // { di, cursorMs } or null

  function openAddModal(seed) {
    // Optional seed:
    // - { dayIndex, minute } where minute is minutes since midnight
    // - { cursorMs } epoch-ms within view
    try{
      addModalSeed = null;
      if (seed && typeof seed === "object") {
        if (Number.isFinite(seed.cursorMs)) {
          const ms = Number(seed.cursorMs);
          const di0 = dayIndexFromMs(ms);
          if (di0 != null) {
            addModalSeed = { di: di0, cursorMs: ms };
          }
        } else {
          let di = null;
          if (Number.isFinite(seed.dayIndex)) di = Math.floor(Number(seed.dayIndex));
          else if (Number.isFinite(seed.di)) di = Math.floor(Number(seed.di));

          if (di != null && Number.isFinite(seed.minute)) {
            di = clamp(di, 0, DAYS - 1);
            const m = clamp(Math.round(Number(seed.minute)), WORK_START, WORK_END);
            addModalSeed = { di: di, cursorMs: (dayStarts[di] + minuteToMs(m)) };
          }
        }
      }
    }catch(_){ addModalSeed = null; }

    elAddModal.style.display = "flex";
    setTimeout(() => { try { elAddLines && elAddLines.focus(); } catch (_) {} }, 0);
  }
  function closeAddModal() {
    elAddModal.style.display = "none";
    addModalSeed = null;
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
      // If opened via timeline dblclick, seed cursor at the click point.
      try{
        if (addModalSeed && Number.isFinite(addModalSeed.cursorMs)) {
          let di = addModalSeed.di;
          const ms = Number(addModalSeed.cursorMs);
          if (!Number.isInteger(di)) di = dayIndexFromMs(ms);
          if (di == null) di = 0;
          di = clamp(di, 0, DAYS - 1);
          const dayStart = dayStarts[di];
          let min = minuteOfDayFromMs(ms);
          if (!Number.isFinite(min)) min = WORK_START;
          min = clamp(min, WORK_START, WORK_END);
          return { di: di, cursorMs: (dayStart + min * 60000) };
        }
      }catch(_){ }

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

      if (typeof __scalpelIndexTaskForSearch === "function") __scalpelIndexTaskForSearch(t);
      DATA.tasks.push(t);
      tasksByUuid.set(uuid, t);
      baseline.set(uuid, { scheduled_ms: startMs, due_ms: dueMs });
      baselineDur.set(uuid, durMs);
      plan.set(uuid, { scheduled_ms: startMs, due_ms: dueMs, dur_ms: durMs });
      __scalpelDropEffectiveIntervalCache(uuid);

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

  // Add modal keyboard shortcuts:
  // - Ctrl/Cmd+Enter = queue add
  // - Esc = close
  if (elAddLines) {
    elAddLines.addEventListener("keydown", (ev) => {
      try{
        if (ev.key === "Escape") {
          closeAddModal();
          ev.preventDefault();
          ev.stopPropagation();
          return;
        }
        if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
          queueAddTasksFromModal();
          ev.preventDefault();
          ev.stopPropagation();
          return;
        }
      }catch(_){ }
    });
  }
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
