# scalpel/render/js/part03_selection_ops.py
from __future__ import annotations

JS_PART = r'''// Selection model
  // -----------------------------
  const selected = new Set(); // uuid
  let selectionLead = null;   // uuid

  function updateSelectionMeta() {
    const n = selected.size;
    elSelMeta.textContent = n ? `Selected: ${n}` : "";
    try { renderSelectedList(); } catch (_) {}
  }
  function clearSelection() {
    selected.clear();
    selectionLead = null;
    updateSelectionMeta();
  }
  function toggleSelection(uuid) {
    if (!uuid) return;
    if (selected.has(uuid)) {
      selected.delete(uuid);
      if (selectionLead === uuid) selectionLead = null;
    } else {
      selected.add(uuid);
      selectionLead = uuid;
    }
    updateSelectionMeta();
  }
  function setSelectionOnly(uuid) {
    selected.clear();
    if (uuid) {
      selected.add(uuid);
      selectionLead = uuid;
    } else {
      selectionLead = null;
    }
    updateSelectionMeta();
  }
  function getSelectedCalendarUuids() {
    const out = [];
    for (const u of selected) {
      const node = document.querySelector(`.evt[data-uuid="${u}"]`);
      if (node) out.push(u);
    }
    return out;
  }
  function getSelectedAnyUuids() {
    // selected set is global across calendar/backlog; return in stable order
    return Array.from(selected);
  }

  function focusTask(uuid) {
    if (!uuid) return;
    const node =
      document.querySelector(`.evt[data-uuid="${uuid}"]`) ||
      document.querySelector(`.bl-item[data-uuid="${uuid}"]`);
    if (!node) return;
    try { node.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" }); }
    catch (_) { try { node.scrollIntoView(); } catch (_) {} }
    node.classList.add("pulse");
    setTimeout(() => node.classList.remove("pulse"), 700);
  }

  function renderSelectedList() {
    if (!elSelBox || !elSelList) return;
    const uuids = Array.from(selected);
    if (!uuids.length) {
      elSelBox.style.display = "none";
      elSelList.innerHTML = "";
      if(elSelSummary) elSelSummary.textContent = "";
      return;
    }
    elSelBox.style.display = "";
    const items = uuids.map(u => {
      const t = tasksByUuid.get(u) || null;
      const cur = plan.get(u) || null;

      const durMs = (cur && Number.isFinite(cur.dur_ms)) ? cur.dur_ms :
        (baselineDur.get(u) ?? (DEFAULT_DUR * 60000));

      let startMs = (cur && Number.isFinite(cur.scheduled_ms)) ? cur.scheduled_ms :
        (t && Number.isFinite(t.scheduled_ms)) ? t.scheduled_ms : null;

      let endMs = (cur && Number.isFinite(cur.due_ms)) ? cur.due_ms :
        (t && Number.isFinite(t.due_ms)) ? t.due_ms : null;

      // Prefer due as dominant: when scheduled is missing but due exists, infer start = due - duration.
      if (!Number.isFinite(startMs) && Number.isFinite(endMs)) startMs = endMs - durMs;
      if (!Number.isFinite(endMs) && Number.isFinite(startMs)) endMs = startMs + durMs;

      return { u, t, startMs, endMs, durMs };
    });

    // Selected summary: (1) sum of durations, (2) span from earliest start to latest due.
    let totalMin = 0;
    let minStart = null;
    let maxEnd = null;

    for (const it of items) {
      const durMin = Math.max(1, Math.round(it.durMs / 60000));
      totalMin += durMin;

      if (Number.isFinite(it.startMs)) minStart = (minStart === null) ? it.startMs : Math.min(minStart, it.startMs);
      if (Number.isFinite(it.endMs)) maxEnd = (maxEnd === null) ? it.endMs : Math.max(maxEnd, it.endMs);
    }

    if (elSelSummary) {
      if (Number.isFinite(minStart) && Number.isFinite(maxEnd) && maxEnd >= minStart) {
        const spanMin = Math.max(0, Math.round((maxEnd - minStart) / 60000));
        const a = new Date(minStart), b = new Date(maxEnd);
        const spanRange = `${pad2(a.getHours())}:${pad2(a.getMinutes())}–${pad2(b.getHours())}:${pad2(b.getMinutes())}`;

        // Union duration and gaps inside the selection span (robust to overlaps).
        const ivs = items
          .filter(it => Number.isFinite(it.startMs) && Number.isFinite(it.endMs) && it.endMs >= it.startMs)
          .map(it => ({ s: it.startMs, e: it.endMs }))
          .sort((x, y) => (x.s - y.s) || (x.e - y.e));

        let unionMs = 0;
        if (ivs.length) {
          let cs = ivs[0].s, ce = ivs[0].e;
          for (let i = 1; i < ivs.length; i++) {
            const s = ivs[i].s, e = ivs[i].e;
            if (s <= ce) ce = Math.max(ce, e);
            else { unionMs += (ce - cs); cs = s; ce = e; }
          }
          unionMs += (ce - cs);
        }
        const unionMin = Math.max(0, Math.round(unionMs / 60000));
        const gapMin = Math.max(0, spanMin - unionMin);
        const overlapMin = Math.max(0, totalMin - unionMin);

        const parts = [
          `Total ${fmtDuration(totalMin)}`,
          `Span ${spanRange} (${fmtDuration(spanMin)})`,
          `Gap ${fmtDuration(gapMin)}`
        ];
        if (overlapMin > 0) parts.push(`Overlap ${fmtDuration(overlapMin)}`);
        elSelSummary.textContent = parts.join(" • ");
      } else {
        elSelSummary.textContent = `Total ${fmtDuration(totalMin)}`;
      }
    }
    items.sort((a, b) => {
      const ta = a.t, tb = b.t;
      const sa = Number.isFinite(a.startMs) ? a.startMs : (ta ? (ta.scheduled_ms ?? (ta.due_ms ?? 0)) : 0);
      const sb = Number.isFinite(b.startMs) ? b.startMs : (tb ? (tb.scheduled_ms ?? (tb.due_ms ?? 0)) : 0);
      if (sa !== sb) return sa - sb;
      const da = (ta && ta.description) ? ta.description : "";
      const db = (tb && tb.description) ? tb.description : "";
      return da.localeCompare(db);
    });

    const html = items.map(({u, t}) => {
      const desc = (t && t.description) ? escapeHtml(t.description) : "(missing)";
      const short = (t && t.short) ? t.short : (u ? u.slice(0,8) : "????");
      const isLocal = !!(t && t.local);
      const hasCal = !!document.querySelector(`.evt[data-uuid="${u}"]`);
      const where = isLocal ? "NEW" : (hasCal ? "CAL" : "BACK");
      return `<div class="selitem" data-uuid="${escapeAttr(u)}">
        <div class="sid">${escapeHtml(short)}</div>
        <div class="sdesc" title="${escapeAttr(desc)}">${escapeHtml(desc)}</div>
        <div class="smeta">${where}</div>
      </div>`;
    }).join("");

    elSelList.innerHTML = html;
  }

  if (elSelList) {
    elSelList.addEventListener("click", (ev) => {
      const row = ev.target.closest(".selitem");
      if (!row) return;
      focusTask(row.getAttribute("data-uuid"));
    });
  }

  // -----------------------------
  // Panels toggle
  // -----------------------------
  function applyPanelsCollapsed(collapsed, persist) {
    if (collapsed) elLayout.classList.add("panels-collapsed");
    else elLayout.classList.remove("panels-collapsed");
    elBtnTogglePanels.textContent = collapsed ? "Show panels" : "Hide panels";
    if (persist) localStorage.setItem(panelsKey, collapsed ? "1" : "0");
  }
  (function initPanelsCollapsed() {
    const saved = localStorage.getItem(panelsKey);
    if (saved === "1" || saved === "0") {
      applyPanelsCollapsed(saved === "1", false);
    } else {
      applyPanelsCollapsed(window.innerWidth < 1100, false);
    }
  })();

  // -----------------------------
  // Conflicts panel collapse
  // -----------------------------
  function applyConfCollapsed(collapsed, persist) {
    confCollapsed = !!collapsed;
    if (confCollapsed) elConflictsBox.classList.add("collapsed");
    else elConflictsBox.classList.remove("collapsed");

    const chev = document.getElementById("confChev");
    if (chev) chev.textContent = confCollapsed ? "▸" : "▾";

    if (persist) saveConfCollapsed();
  }


  elBtnTogglePanels.addEventListener("click", () => {
    const nowCollapsed = !elLayout.classList.contains("panels-collapsed");
    applyPanelsCollapsed(nowCollapsed, true);
  });

  // -----------------------------
  // Calendar skeleton
  // -----------------------------
  function minuteToMs(min) { return min * 60000; }
  function minuteOfDayFromMs(ms) {
    const d = new Date(ms);
    return d.getHours() * 60 + d.getMinutes();
  }
  function dayIndexFromMs(ms) {
    const d0 = dayStarts[0];
    const di = Math.floor((startOfLocalDayMs(ms) - d0) / 86400000);
    if (di < 0 || di >= DAYS) return null;
    return di;
  }
  function yToMinute(yPx) {
    const raw = WORK_START + (yPx / pxPerMin);
    const snapped = WORK_START + Math.round((raw - WORK_START) / SNAP) * SNAP;
    return clamp(snapped, WORK_START, WORK_END);
  }
  function getDaysPane() { return document.querySelector(".days-col"); }

  function dayIndexFromClientX(clientX) {
    const cols = document.querySelectorAll(".day-col");
    if (!cols.length) return 0;

    for (let i = 0; i < cols.length; i++) {
      const r = cols[i].getBoundingClientRect();
      if (clientX >= r.left && clientX < r.right) return i;
    }
    const r0 = cols[0].getBoundingClientRect();
    const rn = cols[cols.length - 1].getBoundingClientRect();
    if (clientX < r0.left) return 0;
    if (clientX >= rn.right) return cols.length - 1;

    let best = 0, bestDist = Infinity;
    for (let i = 0; i < cols.length; i++) {
      const r = cols[i].getBoundingClientRect();
      const cx = (r.left + r.right) / 2;
      const dist = Math.abs(clientX - cx);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    return best;
  }

  function buildCalendarSkeleton() {
    elCal.innerHTML = "";

    const timeCol = document.createElement("div");
    timeCol.className = "time-col";

    const timeHead = document.createElement("div");
    timeHead.className = "time-head";

    const timeBody = document.createElement("div");
    timeBody.className = "time-body";
    timeBody.id = "timeBody";

    const firstHourMin = Math.ceil(WORK_START / 60) * 60;
    for (let m = firstHourMin; m <= WORK_END; m += 60) {
      const topPx = (m - WORK_START) * pxPerMin;
      const tick = document.createElement("div");
      tick.className = "time-tick";
      tick.style.top = `${topPx}px`;

      const hh = Math.floor(m / 60);
      const lbl = document.createElement("div");
      lbl.className = "lbl";
      lbl.textContent = `${pad2(hh)}:00`;

      tick.appendChild(lbl);
      timeBody.appendChild(tick);
    }

    timeCol.appendChild(timeHead);
    timeCol.appendChild(timeBody);

    const daysCol = document.createElement("div");
    daysCol.className = "days-col";
    daysCol.id = "daysCol";

    const header = document.createElement("div");
    header.className = "days-header";

    for (let i = 0; i < DAYS; i++) {
      const h = document.createElement("div");
      h.className = "day-h";
      h.dataset.dayIndex = String(i);

      const lab = fmtDayLabel(dayStarts[i]);
      h.innerHTML = `
        <div class="dtop">
          <div>${escapeHtml(lab.top)}</div>
          <span>${escapeHtml(lab.bot)}</span>
        </div>
        <div class="loadrow">
          <div class="loadbar"><div class="loadfill"></div></div>
          <div class="loadtxt">0m</div>
        </div>
      `;
      header.appendChild(h);
    }

    const body = document.createElement("div");
    body.className = "days-body";
    body.id = "daysBody";

    for (let i = 0; i < DAYS; i++) {
      const col = document.createElement("div");
      col.className = "day-col";
      col.dataset.dayIndex = String(i);
      col.innerHTML = `<div class="drop-hint"></div>`;

      col.addEventListener("dragover", (ev) => {
        ev.preventDefault();
        col.classList.add("dragover");
      });
      col.addEventListener("dragleave", () => col.classList.remove("dragover"));

      col.addEventListener("drop", (ev) => {
        ev.preventDefault();
        col.classList.remove("dragover");

        let uuids = [];
        const rawList = ev.dataTransfer.getData("text/uuidlist");
        const rawOne = ev.dataTransfer.getData("text/uuid");

        if (rawList) {
          try {
            const arr = JSON.parse(rawList);
            if (Array.isArray(arr)) uuids = arr.filter(x => typeof x === "string");
          } catch (_) {}
        } else if (rawOne) {
          uuids = [rawOne];
        }

        uuids = uuids.filter(u => tasksByUuid.has(u));
        if (!uuids.length) return;

        const rect = col.getBoundingClientRect();
        const y = ev.clientY - rect.top;
        const minute = yToMinute(y);

        let startMs = dayStarts[i] + minuteToMs(minute);
        const changes = {};

        for (const uuid of uuids) {
          const cur = plan.get(uuid) || { scheduled_ms: null, due_ms: null, dur_ms: DEFAULT_DUR * 60000 };
          const durMs = Number.isFinite(cur.dur_ms) ? cur.dur_ms : (DEFAULT_DUR * 60000);

          let sMs = startMs;
          let dMs = sMs + durMs;

          const dayStartMs = dayStarts[i];
          const dayEndMs = dayStartMs + 86400000;

          if (sMs < dayStartMs) { sMs = dayStartMs; dMs = sMs + durMs; }
          if (dMs > dayEndMs) break;

          const sMin = minuteOfDayFromMs(sMs);
          const dMin = minuteOfDayFromMs(dMs);
          if (sMin < WORK_START || dMin > WORK_END) break;

          // due-dominant: store due; scheduled computed at command time as due - duration
          changes[uuid] = { scheduledMs: sMs, dueMs: dMs, durMs };
          startMs = dMs;
        }

        commitPlanMany(changes);
      });

      body.appendChild(col);
    }

    daysCol.appendChild(header);
    daysCol.appendChild(body);

    elCal.appendChild(timeCol);
    elCal.appendChild(daysCol);

    body.addEventListener("pointerdown", onCalendarBackgroundPointerDown, { capture: true });

    daysCol.addEventListener("scroll", () => {
      const tb = document.getElementById("timeBody");
      if (tb) tb.style.transform = `translateY(-${daysCol.scrollTop}px)`;
    }, { passive: true });

    const tb = document.getElementById("timeBody");
    if (tb) tb.style.transform = `translateY(-0px)`;
  }

  buildCalendarSkeleton();

  // -----------------------------
  // Marquee selection
  // -----------------------------
  let marquee = null;

  function showMarquee(rect) {
    elMarquee.style.display = "block";
    elMarquee.style.left = rect.left + "px";
    elMarquee.style.top = rect.top + "px";
    elMarquee.style.width = rect.width + "px";
    elMarquee.style.height = rect.height + "px";
  }
  function hideMarquee() {
    elMarquee.style.display = "none";
    elMarquee.style.width = "0px";
    elMarquee.style.height = "0px";
  }

  function onCalendarBackgroundPointerDown(ev) {
    if (ev.button !== 0) return;
    if (ev.target && ev.target.closest && ev.target.closest(".evt")) return;

    const daysCol = document.getElementById("daysCol");
    if (daysCol) daysCol.classList.add("selecting");

    marquee = { startX: ev.clientX, startY: ev.clientY, lastRect: null, pointerId: ev.pointerId };

    window.addEventListener("pointermove", onMarqueeMove, { passive: false });
    window.addEventListener("pointerup", onMarqueeUp, { once: true });
    window.addEventListener("pointercancel", onMarqueeUp, { once: true });

    ev.preventDefault();
    ev.stopPropagation();
  }

  function onMarqueeMove(ev) {
    if (!marquee || ev.pointerId !== marquee.pointerId) return;

    const pane = getDaysPane();
    if (pane) {
      const r = pane.getBoundingClientRect();
      const edge = 36;
      const step = 20;
      if (ev.clientX < r.left + edge) pane.scrollLeft -= step;
      else if (ev.clientX > r.right - edge) pane.scrollLeft += step;
      if (ev.clientY < r.top + edge) pane.scrollTop -= step;
      else if (ev.clientY > r.bottom - edge) pane.scrollTop += step;
    }

    const rect = rectFromPoints(marquee.startX, marquee.startY, ev.clientX, ev.clientY);
    marquee.lastRect = rect;
    showMarquee(rect);
    ev.preventDefault();
  }

  function onMarqueeUp(ev) {
    window.removeEventListener("pointermove", onMarqueeMove);

    const daysCol = document.getElementById("daysCol");
    if (daysCol) daysCol.classList.remove("selecting");

    if (!marquee) return;

    const rect = marquee.lastRect;
    hideMarquee();

    if (!rect || (rect.width < 6 && rect.height < 6)) {
      clearSelection();
      rerenderAll();
      marquee = null;
      return;
    }

    const hits = [];
    document.querySelectorAll(".evt").forEach((node) => {
      const r = node.getBoundingClientRect();
      const nr = { left:r.left, right:r.right, top:r.top, bottom:r.bottom };
      if (rectsIntersect(rect, nr)) {
        const u = node.dataset.uuid;
        if (u) hits.push(u);
      }
    });

    const shift = !!ev.shiftKey;
    const toggle = !!(ev.ctrlKey || ev.metaKey);

    if (!shift && !toggle) {
      selected.clear();
      for (const u of hits) selected.add(u);
      selectionLead = hits.length ? hits[0] : null;
    } else if (shift) {
      for (const u of hits) selected.add(u);
      if (!selectionLead && hits.length) selectionLead = hits[0];
    } else if (toggle) {
      for (const u of hits) {
        if (selected.has(u)) selected.delete(u);
        else selected.add(u);
      }
      if (hits.length) selectionLead = hits[0];
    }

    updateSelectionMeta();
    rerenderAll();
    marquee = null;
  }

  // -----------------------------
  // Classification (due-based population)
  // -----------------------------
  function taskSearchHaystack(t) {
    const tags = (t.tags || []).join(" ");
    return `${t.description || ""} ${t.project || ""} ${tags}`.toLowerCase();
  }

  function classifyTasks(filterText) {
    const f = (filterText || "").trim().toLowerCase();
    const events = [];
    const backlog = [];
    const problems = [];
    const allByDay = Array.from({length: DAYS}, () => []);

    for (const t of (DATA.tasks || [])) {
      if (f && !taskSearchHaystack(t).includes(f)) continue;

      const cur = plan.get(t.uuid);
      const dueMs = cur ? cur.due_ms : null;

      if (Number.isFinite(dueMs)) {
        const di = dayIndexFromMs(dueMs);
        if (di === null) { backlog.push({ t, hint: "due outside view" }); continue; }

        const eff = effectiveInterval(t.uuid);
        if (!eff) { backlog.push({ t, hint: "missing due" }); continue; }

        if (startOfLocalDayMs(eff.startMs) !== startOfLocalDayMs(eff.dueMs)) {
          problems.push({ t, reason: "computed start crosses day (reduce duration or adjust due)" });
          continue;
        }

        allByDay[di].push({ uuid: t.uuid, startMs: eff.startMs, dueMs: eff.dueMs });

        const sMin = minuteOfDayFromMs(eff.startMs);
        const dMin = minuteOfDayFromMs(eff.dueMs);
        if (sMin < WORK_START || dMin > WORK_END) {
          backlog.push({ t, hint: "outside workhours" });
          continue;
        }

        events.push({ uuid: t.uuid, startMs: eff.startMs, dueMs: eff.dueMs, durMs: eff.durMs });
        continue;
      }

      backlog.push({ t, hint: "no due" });
    }

    return { events, backlog, problems, allByDay };
  }

  // -----------------------------
  // Overlap layout
  // -----------------------------
  function layoutOverlapGroups(dayEvents) {
    const items = dayEvents.slice().sort((a,b) => (a.startMs - b.startMs) || (a.dueMs - b.dueMs));

    const groups = [];
    let cur = [];
    let maxEnd = -Infinity;

    for (const ev of items) {
      if (cur.length === 0) { cur = [ev]; maxEnd = ev.dueMs; continue; }
      if (ev.startMs < maxEnd) { cur.push(ev); maxEnd = Math.max(maxEnd, ev.dueMs); }
      else { groups.push(cur); cur = [ev]; maxEnd = ev.dueMs; }
    }
    if (cur.length) groups.push(cur);

    const out = [];
    for (const g of groups) {
      const lanes = [];
      const assigned = [];
      for (const ev of g) {
        let laneIndex = -1;
        for (let i = 0; i < lanes.length; i++) {
          if (lanes[i] <= ev.startMs) { laneIndex = i; break; }
        }
        if (laneIndex === -1) { laneIndex = lanes.length; lanes.push(ev.dueMs); }
        else { lanes[laneIndex] = ev.dueMs; }
        assigned.push({ ...ev, laneIndex });
      }
      const laneCount = lanes.length || 1;
      for (const ev of assigned) out.push({ ...ev, laneCount });
    }
    return out;
  }

  // -----------------------------
  // Conflicts
  // -----------------------------
  function computeConflictSegments(dayEvents) {
    const pts = [];
    for (const ev of dayEvents) {
      pts.push({ t: ev.startMs, kind: +1, uuid: ev.uuid });
      pts.push({ t: ev.dueMs, kind: -1, uuid: ev.uuid });
    }
    pts.sort((a,b) => (a.t - b.t) || (b.kind - a.kind));

    const active = new Set();
    const segs = [];
    let prevT = null;

    for (const p of pts) {
      if (prevT !== null && p.t > prevT && active.size >= 2) {
        const uuids = Array.from(active).sort();
        const key = uuids.join(",");
        const last = segs.length ? segs[segs.length - 1] : null;
        if (last && last.key === key && last.endMs === prevT) {
          last.endMs = p.t;
        } else {
          segs.push({ startMs: prevT, endMs: p.t, uuids, key });
        }
      }

      if (p.kind === +1) active.add(p.uuid);
      else active.delete(p.uuid);

      prevT = p.t;
    }

    return segs;
  }

  // -----------------------------
  // Gaps
  // -----------------------------
  function renderGapsForDay(dayIndex, col, allIntervals) {
    const dayStart = dayStarts[dayIndex];
    const dayEnd = dayStart + 86400000;

    const workStartMs = dayStart + WORK_START * 60000;
    const workEndMs = dayStart + WORK_END * 60000;

    const ints = (allIntervals || [])
      .map(x => ({
        start: Math.max(dayStart, Math.min(dayEnd, x.startMs)),
        end: Math.max(dayStart, Math.min(dayEnd, x.dueMs)),
      }))
      .filter(x => Number.isFinite(x.start) && Number.isFinite(x.end) && x.end > x.start)
      .sort((a,b) => a.start - b.start);

    const merged = [];
    for (const it of ints) {
      const last = merged.length ? merged[merged.length - 1] : null;
      if (!last) merged.push({ start: it.start, end: it.end });
      else if (it.start <= last.end) last.end = Math.max(last.end, it.end);
      else merged.push({ start: it.start, end: it.end });
    }

    const gaps = [];
    let cursor = dayStart;
    for (const it of merged) {
      if (it.start > cursor) gaps.push({ start: cursor, end: it.start });
      cursor = Math.max(cursor, it.end);
    }
    if (cursor < dayEnd) gaps.push({ start: cursor, end: dayEnd });

    const MIN_RENDER_MIN = 5;
    const MIN_LABEL_PX = 20;

    for (const g of gaps) {
      const fullMin = (g.end - g.start) / 60000;
      if (fullMin < MIN_RENDER_MIN) continue;

      const ds = Math.max(g.start, workStartMs);
      const de = Math.min(g.end, workEndMs);
      if (de <= ds) continue;

      const sMin = minuteOfDayFromMs(ds);
      const eMin = minuteOfDayFromMs(de);

      const topPx = (sMin - WORK_START) * pxPerMin;
      const hPx = Math.max(2, (eMin - sMin) * pxPerMin);

      const div = document.createElement("div");
      div.className = "gap";
      div.style.top = `${topPx}px`;
      div.style.height = `${hPx}px`;

      if (hPx >= MIN_LABEL_PX) {
        div.innerHTML = `<div class="gap-label">Free ${escapeHtml(fmtDuration(fullMin))}</div>`;
      }

      col.appendChild(div);
    }
  }

  // -----------------------------
  // Now line
  // -----------------------------
  function renderNowLine() {
    document.querySelectorAll(".now-line").forEach(n => n.remove());

    const now = new Date();
    const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0,0,0,0).getTime();
    const di = Math.floor((dayStart - dayStarts[0]) / 86400000);
    if (di < 0 || di >= DAYS) return;

    const min = now.getHours() * 60 + now.getMinutes();
    if (min < WORK_START || min > WORK_END) return;

    const cols = document.querySelectorAll(".day-col");
    const col = cols[di];
    if (!col) return;

    const topPx = (min - WORK_START) * pxPerMin;
    const line = document.createElement("div");
    line.className = "now-line";
    line.style.top = `${topPx}px`;
    line.innerHTML = `<div class="now-label">Now ${pad2(now.getHours())}:${pad2(now.getMinutes())}</div>`;
    col.appendChild(line);
  }

  // -----------------------------
  // Next up banner
  // -----------------------------
  function fmtHMFromMs(ms){
    const d = new Date(ms);
    return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  }
  function fmtDayLabelFromMs(ms){
    const d = new Date(ms);
    return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
  }

  function chooseNextUpCandidate(nowMs){
    const viewEndMs = VIEW_START_MS + (DAYS * 86400000);

    // If the current time is outside the visible range, use a view-relative reference point
    // so the banner still provides context while planning past/future days.
    let refMs = nowMs;
    let refTag = "in_view";
    if (nowMs > viewEndMs){
      refMs = VIEW_START_MS;
      refTag = "view_start";
    } else if (nowMs < VIEW_START_MS){
      refTag = "before_view";
    }

    let bestNow = null;
    let bestNext = null;

    for (const [uuid, _cur] of plan.entries()){
      const t = tasksByUuid.get(uuid);
      if (!t) continue;

      if (focusBehavior === "hide" && focusActive() && !taskMatchesFocus(t)) continue;

      const iv = effectiveInterval(uuid);
      if (!iv) continue;

      // ignore tasks fully outside the view
      if (iv.dueMs <= VIEW_START_MS || iv.startMs >= viewEndMs) continue;

      if (iv.startMs <= refMs && refMs < iv.dueMs){
        if (!bestNow || iv.dueMs < bestNow.iv.dueMs){
          bestNow = { uuid, t, iv, refMs, refTag };
        }
        continue;
      }

      if (iv.startMs >= refMs){
        if (!bestNext || iv.startMs < bestNext.iv.startMs){
          bestNext = { uuid, t, iv, refMs, refTag };
        }
      }
    }

    const primary = bestNow || bestNext;
    if (!primary) return null;

    // When a task is currently in progress (only meaningful when refMs is real "now" in view),
    // also compute the next task starting after it ends.
    let nextAfter = null;
    if (bestNow && refTag === "in_view"){
      const afterMs = bestNow.iv.dueMs;
      for (const [uuid, _cur] of plan.entries()){
        const t = tasksByUuid.get(uuid);
        if (!t) continue;

        if (focusBehavior === "hide" && focusActive() && !taskMatchesFocus(t)) continue;

        const iv = effectiveInterval(uuid);
        if (!iv) continue;

        if (iv.dueMs <= VIEW_START_MS || iv.startMs >= viewEndMs) continue;

        if (iv.startMs >= afterMs){
          if (!nextAfter || iv.startMs < nextAfter.iv.startMs){
            nextAfter = { uuid, t, iv };
          }
        }
      }
    }

    primary.nextAfter = nextAfter;
    return primary;
  }

  function renderNextUp(){
    if (!elNextUp || !elNextUpMeta || !elNextUpBody) return;

    elNextUp.style.display = "";

    try {
      const nowMs = Date.now();
      const cand = chooseNextUpCandidate(nowMs);

      if (!cand){
        elNextUpMeta.textContent = "No scheduled tasks in view";
        elNextUpBody.innerHTML = `<div class="nub"><div class="nutxt"><div class="nusub">Add a task to the calendar to populate Next up.</div></div></div>`;
        return;
      }

      const { uuid, t, iv, refMs, refTag, nextAfter } = cand;
      const isNow = (refTag === "in_view" && iv.startMs <= refMs && refMs < iv.dueMs);

      const startHM = fmtHMFromMs(iv.startMs);
      const endHM = fmtHMFromMs(iv.dueMs);
      const dayLbl = fmtDayLabelFromMs(iv.startMs);
      const durMin = Math.max(0, Math.round(iv.durMs / 60000));

      const minsTo = Math.max(0, Math.round((iv.startMs - refMs) / 60000));
      const minsLeft = Math.max(0, Math.round((iv.dueMs - refMs) / 60000));

      let meta = "";
      if (refTag === "view_start"){
        meta = (iv.startMs <= refMs && refMs < iv.dueMs) ? `At view start • ends in ${fmtDur(minsLeft)}` : "First in view";
      } else if (refTag === "before_view"){
        meta = (iv.startMs <= refMs && refMs < iv.dueMs) ? `Now • ends in ${fmtDur(minsLeft)}` : `In ${fmtDur(minsTo)}`;
      } else {
        meta = isNow ? `Now • ends in ${fmtDur(minsLeft)}` : `In ${fmtDur(minsTo)}`;
      }

      if (focusBehavior === "dim" && focusActive() && t && !taskMatchesFocus(t)) meta += " • dimmed";
      elNextUpMeta.textContent = meta;

      const desc = (t && t.description) ? t.description : "(missing)";
      const short = (t && t.short) ? t.short : (uuid ? uuid.slice(0,8) : "????");
      const whenLine = `${dayLbl} • ${startHM}–${endHM} • ${fmtDur(durMin)}`;

      let afterBlock = "";
      if (isNow){
        if (nextAfter && nextAfter.iv){
          const at = nextAfter.t || {};
          const aDesc = at.description || "(missing)";
          const aShort = at.short || (nextAfter.uuid ? nextAfter.uuid.slice(0,8) : "????");
          const aStartHM = fmtHMFromMs(nextAfter.iv.startMs);
          const aEndHM = fmtHMFromMs(nextAfter.iv.dueMs);
          const aDayLbl = fmtDayLabelFromMs(nextAfter.iv.startMs);
          const aDurMin = Math.max(0, Math.round(nextAfter.iv.durMs/60000));
          const aMinsTo = Math.max(0, Math.round((nextAfter.iv.startMs - refMs)/60000));
          const dim2 = (focusBehavior === "dim" && focusActive() && at && !taskMatchesFocus(at)) ? " • dimmed" : "";
          afterBlock = `
            <div class="nusep"></div>
            <div class="nurow">
              <div class="nutxt">
                <div class="nusub" style="font-weight:900; opacity:0.92;">Next after • in ${fmtDur(aMinsTo)}${dim2}</div>
                <div class="nutitle" style="font-size:13px; margin-top:4px;">${escapeHtml(aDesc)}</div>
                <div class="nusub">${escapeHtml(aShort)} • ${escapeHtml(aDayLbl)} • ${escapeHtml(aStartHM)}–${escapeHtml(aEndHM)} • ${escapeHtml(fmtDur(aDurMin))}</div>
              </div>
              <button class="nujump" data-uuid="${escapeAttr(nextAfter.uuid)}">Jump</button>
            </div>
          `;
        } else {
          afterBlock = `
            <div class="nusep"></div>
            <div class="nutxt">
              <div class="nusub" style="font-weight:900; opacity:0.92;">Next after</div>
              <div class="nusub">No later task in view.</div>
            </div>
          `;
        }
      }

      elNextUpBody.innerHTML = `
        <div class="nub">
          <div class="nurow">
            <div class="nutxt">
              <div class="nutitle">${escapeHtml(desc)}</div>
              <div class="nusub">${escapeHtml(short)} • ${escapeHtml(whenLine)}</div>
            </div>
            <button class="nujump" data-uuid="${escapeAttr(uuid)}">Jump</button>
          </div>
          ${afterBlock}
        </div>
      `;

      elNextUpBody.querySelectorAll(".nujump").forEach(btn => {
        btn.addEventListener("click", (e) => {
          const u = e.currentTarget.getAttribute("data-uuid");
          if (u) focusTask(u);
        });
      });
    } catch (e) {
      elNextUpMeta.textContent = "Error";
      const msg = (e && e.message) ? e.message : String(e);
      elNextUpBody.innerHTML = `<div class="nub"><div class="nutxt"><div class="nusub">Next up failed: ${escapeHtml(msg)}</div></div></div>`;
      console.error("NextUp render failed", e);
    }
  }

  if (elNextUp) {
    elNextUp.addEventListener("click", (ev) => {
      const btn = ev.target.closest("button.nujump");
      if (!btn) return;
      const u = btn.getAttribute("data-uuid");
      if (!u) return;
      try { focusTask(u); } catch (_) {}
    });
  }


  // -----------------------------
  // Palette tree build/render
  // -----------------------------
  function buildProjectTagTree(calendarUuids) {
    const root = { name: "Tasks", path: "", count: 0, children: new Map(), tags: new Map() };
    const projectCounts = new Map();

    for (const uuid of calendarUuids) {
      const t = tasksByUuid.get(uuid);
      if (!t) continue;

      const proj = (t.project && String(t.project).trim()) ? String(t.project).trim() : "No Project";
      const tags = (t.tags && t.tags.length) ? t.tags : ["No Tag"];

      const levels = proj.split(".");
      let curPath = "";
      for (let i = 0; i < levels.length; i++) {
        curPath = curPath ? `${curPath}.${levels[i]}` : levels[i];
        projectCounts.set(curPath, (projectCounts.get(curPath) || 0) + 1);
      }

      let node = root;
      node.count++;

      curPath = "";
      for (let i = 0; i < levels.length; i++) {
        const level = levels[i];
        curPath = curPath ? `${curPath}.${level}` : level;

        if (!node.children.has(level)) {
          node.children.set(level, { name: level, path: curPath, count: 0, children: new Map(), tags: new Map() });
        }
        node = node.children.get(level);
        node.count = projectCounts.get(curPath) || node.count;
      }

      for (const tag of tags) {
        node.tags.set(tag, (node.tags.get(tag) || 0) + 1);
      }
    }

    return root;
  }

  function renderPaletteNode(node, container, depth) {
    const hasChildren = node.children && node.children.size > 0;
    const hasTags = node.tags && node.tags.size > 0;
    const projKey = node.path ? `project:${node.path}` : null;

    const row = document.createElement("div");
    row.className = "pnode" + ((focusMode === "projects" && node.path && focusKeys.has(String(node.path))) ? " focused" : "");

    const left = document.createElement("div");
    left.className = "left";

    const twisty = document.createElement("div");
    twisty.className = "twisty";
    twisty.textContent = hasChildren || hasTags ? "▸" : "•";
    left.appendChild(twisty);

    const label = document.createElement("div");
    label.className = "label clickable";
    label.textContent = node.name;
    label.addEventListener("click", (ev) => {
      if (focusMode !== "projects") return;
      ev.stopPropagation();
      if (node.path) toggleFocusKey(String(node.path));
    });
    left.appendChild(label);

    const count = document.createElement("div");
    count.className = "count";
    count.textContent = depth === 0 ? "" : `[${node.count}]`;
    left.appendChild(count);

    const right = document.createElement("div");
    right.className = "right";

    if (projKey) {
      const c = colorMap[projKey] || "#000000";
      const picker = document.createElement("input");
      picker.type = "color";
      picker.value = (colorMap[projKey] || "#63b3ff");
      picker.title = `Color for project ${node.path}`;
      picker.addEventListener("input", () => {
        colorMap[projKey] = picker.value;
        saveColors();
        rerenderAll();
      });

      const clr = document.createElement("div");
      clr.className = "clear";
      clr.textContent = "Clear";
      clr.addEventListener("click", () => {
        delete colorMap[projKey];
        saveColors();
        rerenderAll();
      });

      right.appendChild(picker);
      right.appendChild(clr);
    }

    row.appendChild(left);
    row.appendChild(right);
    container.appendChild(row);

    const childrenWrap = document.createElement("div");
    childrenWrap.className = "pchildren";
    childrenWrap.style.display = "none";
    container.appendChild(childrenWrap);

    function setExpanded(exp) {
      childrenWrap.style.display = exp ? "" : "none";
      twisty.textContent = (hasChildren || hasTags) ? (exp ? "▾" : "▸") : "•";
    }

    let expanded = false;
    if (node.path && paletteExpanded[node.path]) expanded = true;
    setExpanded(expanded);

    twisty.addEventListener("click", () => {
      if (!(hasChildren || hasTags)) return;
      expanded = !expanded;
      setExpanded(expanded);

      if (node.path) {
        if (expanded) paletteExpanded[node.path] = 1;
        else delete paletteExpanded[node.path];
        savePaletteExpanded();
      }
    });

    // child projects
    const sortedChildren = Array.from(node.children.values()).sort((a,b) => a.name.localeCompare(b.name));
    for (const ch of sortedChildren) {
      renderPaletteNode(ch, childrenWrap, depth + 1);
    }

    // tag leaves (only at this project node)
    if (hasTags) {
      const tagsSorted = Array.from(node.tags.entries()).sort((a,b) => String(a[0]).localeCompare(String(b[0])));
      for (const [tag, n] of tagsSorted) {
        const tagRow = document.createElement("div");
        tagRow.className = "pnode" + ((focusMode === "tags" && focusKeys.has(String(tag))) ? " focused" : "");
        tagRow.style.paddingLeft = "22px";

        const l2 = document.createElement("div");
        l2.className = "left";
        const tw2 = document.createElement("div");
        tw2.className = "twisty";
        tw2.textContent = "#";
        l2.appendChild(tw2);

        const lab2 = document.createElement("div");
        lab2.className = "label clickable";
        lab2.textContent = String(tag);
        lab2.addEventListener("click", (ev) => {
          if (focusMode !== "tags") return;
          ev.stopPropagation();
          toggleFocusKey(String(tag));
        });
        l2.appendChild(lab2);

        const c2 = document.createElement("div");
        c2.className = "count";
        c2.textContent = `[${n}]`;
        l2.appendChild(c2);

        const r2 = document.createElement("div");
        r2.className = "right";

        const key = `tag:${tag}`;
        const picker = document.createElement("input");
        picker.type = "color";
        picker.value = (colorMap[key] || "#63b3ff");
        picker.title = `Color for tag ${tag}`;
        picker.addEventListener("input", () => {
          colorMap[key] = picker.value;
          saveColors();
          rerenderAll();
        });

        const clr = document.createElement("div");
        clr.className = "clear";
        clr.textContent = "Clear";
        clr.addEventListener("click", () => {
          delete colorMap[key];
          saveColors();
          rerenderAll();
        });

        r2.appendChild(picker);
        r2.appendChild(clr);

        tagRow.appendChild(l2);
        tagRow.appendChild(r2);
        childrenWrap.appendChild(tagRow);
      }
    }
  }


  // -----------------------------
  // Goals panel
  // -----------------------------
  function renderGoalsFromEvents(events, backlog) {
    if (!elGoalsBox) return;

    if (!goals.length) {
      elGoalsBox.innerHTML = `
        <div class="goals-head" id="goalsToggle">
          <div>
            <div class="t">Goals</div>
            <div class="s">No goals configured (create goals.json)</div>
          </div>
          <div class="chev">▸</div>
        </div>
      `;
      elGoalsBox.classList.add("collapsed");
      return;
    }

    // Count matches in calendar events and backlog list
    const calUuids = new Set(events.map(e => e.uuid));
    const countsCal = {};
    const countsBack = {};
    for (const g of goals) { countsCal[g.id] = 0; countsBack[g.id] = 0; }

    for (const u of calUuids) {
      const t = tasksByUuid.get(u);
      if (!t) continue;
      for (const g of goals) {
        if (taskMatchesGoal(t, g)) { countsCal[g.id] += 1; break; }
      }
    }

    for (const x of backlog) {
      const t = x.t;
      if (!t) continue;
      for (const g of goals) {
        if (taskMatchesGoal(t, g)) { countsBack[g.id] += 1; break; }
      }
    }

    let totalOn = 0;
    for (const g of goals) if (goalEnabled(g.id)) totalOn += 1;

    const summary = `${totalOn}/${goals.length} on`;

    let body = `<div class="hint" style="margin-bottom:10px;">
      Goals are loaded from <code>goals.json</code> and apply color to matching tasks (goal colors override palette colors).
      Matching is based on project prefix and/or tags.
    </div>`;

    body += `<div class="glist">`;
    for (const g of goals) {
      const on = goalEnabled(g.id);
      const metaBits = [];
      if (g.projects && g.projects.length) metaBits.push(`projects: ${g.projects.join(", ")}`);
      if (g.tags && g.tags.length) metaBits.push(`tags: ${g.tags.join(", ")}`);
      if (g.tags_all && g.tags_all.length) metaBits.push(`tags_all: ${g.tags_all.join(", ")}`);
      const meta = metaBits.join(" • ");
      const ccal = countsCal[g.id] || 0;
      const cback = countsBack[g.id] || 0;

      body += `
        <div class="gitem ${ (focusMode === "goals" && focusKeys.has(String(g.id))) ? "focused" : "" }" data-gid="${escapeHtml(g.id)}">
          <input type="checkbox" class="gchk" ${on ? "checked":""} />
          <div class="gswatch" style="background:${escapeHtml(g.color)};"></div>
          <div>
            <div class="gname">${escapeHtml(g.name)}</div>
            <div class="gmeta">${escapeHtml(meta || "—")}</div>
          </div>
          <div class="gcount">${ccal} cal • ${cback} back</div>
        </div>
      `;
    }
    body += `</div>`;

    elGoalsBox.classList.toggle("collapsed", goalsCollapsed);
    elGoalsBox.innerHTML = `
      <div class="goals-head" id="goalsToggle">
        <div>
          <div class="t">Goals</div>
          <div class="s">${escapeHtml(summary)}</div>
        </div>
        <div class="chev">${goalsCollapsed ? "▸" : "▾"}</div>
      </div>
      <div class="goals-body">${body}</div>
    `;

    const toggle = document.getElementById("goalsToggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        goalsCollapsed = !goalsCollapsed;
        elGoalsBox.classList.toggle("collapsed", goalsCollapsed);
        const chev = elGoalsBox.querySelector(".chev");
        if (chev) chev.textContent = goalsCollapsed ? "▸" : "▾";
        saveGoalsCollapsed();
      });
    }

    elGoalsBox.querySelectorAll(".gitem").forEach(row => {
      const gid = row.getAttribute("data-gid");
      const chk = row.querySelector(".gchk");
      if (!gid || !chk) return;
      chk.addEventListener("change", () => {
        setGoalEnabled(gid, chk.checked);
        rerenderAll();
      });
      row.addEventListener("click", (ev) => {
        if (focusMode !== "goals") return;
        if (ev.target && ev.target.tagName === "INPUT") return;
        toggleFocusKey(gid);
      });
    });
  }

function renderPaletteFromEvents(events) {
    elPaletteTree.innerHTML = "";
    const uuids = events.map(e => e.uuid);
    const root = buildProjectTagTree(uuids);

    // Render children of root so we don't show "Tasks" as a node
    const sortedChildren = Array.from(root.children.values()).sort((a,b) => a.name.localeCompare(b.name));
    for (const ch of sortedChildren) {
      renderPaletteNode(ch, elPaletteTree, 1);
    }

    if (!sortedChildren.length) {
      elPaletteTree.innerHTML = `<div class="hint">No calendar tasks in view (or filtered out).</div>`;
    }
  }

  document.getElementById("btnClearColors").addEventListener("click", () => {
    if (!Object.keys(colorMap).length) return;
    if (!confirm("Clear all custom colors for this view?")) return;
    colorMap = {};
    saveColors();
    rerenderAll();
  });

  // -----------------------------
'''
