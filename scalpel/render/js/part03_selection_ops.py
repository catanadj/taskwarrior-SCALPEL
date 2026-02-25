# scalpel/render/js/part03_selection_ops.py
from __future__ import annotations

JS_PART = r'''// Selection model
  // -----------------------------
  const selected = new Set(); // uuid
  let selectionLead = null;   // uuid

  function updateSelectionMeta() {
    const n = selected.size;
    elSelMeta.textContent = n ? `Selected: ${n}` : "";
    try {
      if (typeof globalThis.__scalpel_updateActionButtonStates === "function") {
        globalThis.__scalpel_updateActionButtonStates();
      }
    } catch (_) {}
    try { renderSelectedList(); } catch (_) {}
  }
  function clearSelection() {
    selected.clear();
    selectionLead = null;
    updateSelectionMeta();
  }
  function toggleSelection(uuid) {
    if (!uuid) return;
    const tt = tasksByUuid.get(uuid);
    if (tt && tt.nautical_preview) return;
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
      const tt = tasksByUuid.get(uuid);
      if (tt && tt.nautical_preview) return;
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

  function fmtSignedDurationMin(mins) {
    const m = Math.round(Number(mins) || 0);
    if (!m) return "0m";
    return (m > 0) ? (`+${fmtDuration(m)}`) : (`-${fmtDuration(-m)}`);
  }

  function taskInterval(u) {
    const t = tasksByUuid.get(u) || null;
    const cur = plan.get(u) || null;
    if (!t && !cur) return null;

    // Effective duration: plan override -> baseline-derived -> default
    let durMs = (cur && Number.isFinite(cur.dur_ms)) ? cur.dur_ms :
      (baselineDur.get(u) ?? (DEFAULT_DUR * 60000));

    // In TW-Cal, placement/commands are due-dominant:
    //   start = due - duration
    // This keeps selection UX consistent with the blocks you see on the timeline.
    const dueMs = (cur && Number.isFinite(cur.due_ms)) ? cur.due_ms :
      (t && Number.isFinite(t.due_ms)) ? t.due_ms : null;

    const schMs = (cur && Number.isFinite(cur.scheduled_ms)) ? cur.scheduled_ms :
      (t && Number.isFinite(t.scheduled_ms)) ? t.scheduled_ms : null;

    let startMs = null;
    let endMs = null;

    if (Number.isFinite(dueMs) && Number.isFinite(durMs) && durMs > 0) {
      endMs = dueMs;
      startMs = dueMs - durMs;
    } else if (Number.isFinite(schMs) && Number.isFinite(durMs) && durMs > 0) {
      startMs = schMs;
      endMs = schMs + durMs;
    } else if (Number.isFinite(schMs) && Number.isFinite(dueMs) && dueMs > schMs) {
      // Last-resort fallback: treat scheduled->due as the interval.
      startMs = schMs;
      endMs = dueMs;
      durMs = endMs - startMs;
    }

    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) return null;
    return { u, t, startMs, endMs, durMs };
  }

  function mergeIntervals(ivs) {
    const arr = (ivs || []).filter(x => x && Number.isFinite(x.s) && Number.isFinite(x.e) && x.e > x.s)
      .sort((a, b) => (a.s - b.s) || (a.e - b.e));
    if (!arr.length) return [];
    const out = [];
    let cs = arr[0].s, ce = arr[0].e;
    for (let i = 1; i < arr.length; i++) {
      const s = arr[i].s, e = arr[i].e;
      if (s <= ce) ce = Math.max(ce, e);
      else { out.push({ s: cs, e: ce }); cs = s; ce = e; }
    }
    out.push({ s: cs, e: ce });
    return out;
  }

  const __scalpelBusyIntervalsCache = { stamp: -1, merged: [] };

  function allBusyMergedIntervals() {
    const caches = __scalpelGetTimeCaches();
    const stamp = Number.isFinite(caches && caches.stamp) ? Number(caches.stamp) : 0;
    if (__scalpelBusyIntervalsCache.stamp === stamp) return __scalpelBusyIntervalsCache.merged;

    const ivs = [];
    for (const [u] of tasksByUuid.entries()) {
      const it = taskInterval(u);
      if (!it) continue;
      if (!Number.isFinite(it.startMs) || !Number.isFinite(it.endMs)) continue;
      if (it.endMs <= it.startMs) continue;
      ivs.push({ s: it.startMs, e: it.endMs });
    }

    const merged = mergeIntervals(ivs);
    __scalpelBusyIntervalsCache.stamp = stamp;
    __scalpelBusyIntervalsCache.merged = merged;
    return merged;
  }

  function clippedUnionMinutes(merged, w0, w1) {
    if (!Array.isArray(merged) || !Number.isFinite(w0) || !Number.isFinite(w1) || w1 <= w0) return 0;
    let ms = 0;
    for (const iv of merged) {
      if (!iv) continue;
      if (iv.s >= w1) break;
      const s = Math.max(w0, iv.s);
      const e = Math.min(w1, iv.e);
      if (e > s) ms += (e - s);
    }
    return Math.max(0, Math.round(ms / 60000));
  }

  function sumIntervalsMs(ivs) {
    let ms = 0;
    for (const x of (ivs || [])) ms += (x.e - x.s);
    return ms;
  }

  function intersectIntervalsMs(a, b) {
    // a, b must be merged/sorted non-overlapping intervals
    let i = 0, j = 0, ms = 0;
    while (i < a.length && j < b.length) {
      const s = Math.max(a[i].s, b[j].s);
      const e = Math.min(a[i].e, b[j].e);
      if (e > s) ms += (e - s);
      if (a[i].e <= b[j].e) i++;
      else j++;
    }
    return ms;
  }

  function buildWorkIntervals(windowStartMs, windowEndMs) {
    const out = [];
    let ds = startOfLocalDayMs(windowStartMs);
    let guard = 0;
    while (ds < windowEndMs && guard++ < 4000) {
      const ws = ds + minuteToMs(WORK_START);
      const we = ds + minuteToMs(WORK_END);
      const s = Math.max(ws, windowStartMs);
      const e = Math.min(we, windowEndMs);
      if (e > s) out.push({ s, e });
      // Advance to next day (robust-ish across DST): jump by 25h, then normalize to BUCKET_TZ midnight.
      const nextYmd = ymdFromMs(ds + 90000000);
      const nd = msFromYmd(nextYmd);
      ds = (nd > ds) ? nd : (ds + 86400000);
    }
    return mergeIntervals(out);
  }

  function renderSelectedList() {
    if (!elSelBox || !elSelList) return;
    const uuids = Array.from(selected);
    if (!uuids.length) {
      elSelBox.style.display = "none";
      elSelList.innerHTML = "";
      if(elSelSummary) elSelSummary.textContent = "";
      if(elSelExtra){ elSelExtra.innerHTML = ""; elSelExtra.style.display = "none"; }
      return;
    }
    elSelBox.style.display = "";
    const items = uuids.map(u => taskInterval(u) || { u, t: (tasksByUuid.get(u) || null), startMs: null, endMs: null, durMs: (DEFAULT_DUR * 60000) });

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
        const spanRange = `${fmtHm(minStart)}–${fmtHm(maxEnd)}`;

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

    // Extra: "time until scheduled" + free/busy/work time between now and the lead task's scheduled start.
    try {
      if (elSelExtra) {
        const nowMs = Date.now();
        let lead = null;
        if (selectionLead) lead = items.find(x => x && x.u === selectionLead) || null;
        if (!lead) {
          // choose earliest-start item as lead
          let best = null;
          for (const it of items) {
            if (!it || !Number.isFinite(it.startMs)) continue;
            if (!best || it.startMs < best.startMs) best = it;
          }
          lead = best;
        }

        if (lead && Number.isFinite(lead.startMs)) {
          const startMs = lead.startMs;
          const deltaMin = (startMs - nowMs) / 60000;
          const w0 = Math.min(nowMs, startMs);
          const w1 = Math.max(nowMs, startMs);
          const windowMin = Math.max(0, Math.round((w1 - w0) / 60000));

          // Busy time (union) from all tasks loaded in this view that overlap the window.
          const busyMerged = allBusyMergedIntervals();
          const busyMin = clippedUnionMinutes(busyMerged, w0, w1);

          // Work time is the intersection of the window with the configured work band.
          const workIvs = buildWorkIntervals(w0, w1);
          const workMin = Math.max(0, Math.round(sumIntervalsMs(workIvs) / 60000));
          const busyWorkMin = Math.max(0, Math.round(intersectIntervalsMs(busyMerged, workIvs) / 60000));
          const freeMin = Math.max(0, windowMin - busyMin);
          const freeWorkMin = Math.max(0, workMin - busyWorkMin);

          const label = (deltaMin >= 0) ? "Until scheduled" : "Overdue by";
          const when = escapeHtml(formatLocalNoOffset(startMs));

          // Note: `.selextra` is `display:none` in CSS by default.
          // We must explicitly override it when we have content to show.
          elSelExtra.style.display = "block";
          elSelExtra.innerHTML = `
            <div class="selex-top">
              <span class="k">${label}</span>
              <span class="v">${escapeHtml(fmtSignedDurationMin(deltaMin))}</span>
              <span class="k">Scheduled</span>
              <span class="v">${when}</span>
            </div>
            <div class="selex-bot">
              <span class="pill">Wall ${escapeHtml(fmtDuration(windowMin))}</span>
              <span class="pill">Work ${escapeHtml(fmtDuration(workMin))}</span>
              <span class="pill">Busy ${escapeHtml(fmtDuration(busyMin))}</span>
              <span class="pill">Free ${escapeHtml(fmtDuration(freeMin))}</span>
              <span class="pill">Work free ${escapeHtml(fmtDuration(freeWorkMin))}</span>
            </div>`;
        } else {
          elSelExtra.innerHTML = "";
          elSelExtra.style.display = "none";
        }
      }
    } catch (_) {
      try { if (elSelExtra) { elSelExtra.innerHTML = ""; elSelExtra.style.display = "none"; } } catch (_2) {}
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

    const nowMsForRows = Date.now();
    const html = items.map(({u, t, startMs, endMs}) => {
      const desc = (t && t.description) ? escapeHtml(t.description) : "(missing)";
      const short = (t && t.short) ? t.short : (u ? u.slice(0,8) : "????");
      const isLocal = !!(t && t.local);
      const hasCal = !!(__scalpelVisibleEventUuids && __scalpelVisibleEventUuids.has(u));
      const where = isLocal ? "NEW" : (hasCal ? "CAL" : "BACK");

      const proj = (t && t.project) ? `<span class="pill">${escapeHtml(t.project)}</span>` : "";
      const tags = (t && t.tags && t.tags.length) ? t.tags.slice(0, 5).map(x => `<span class="pill">${escapeHtml(x)}</span>`).join(" ") : "";

      const range = (Number.isFinite(startMs) && Number.isFinite(endMs)) ? `${fmtHm(startMs)}–${fmtHm(endMs)}` : "";
      const delta = Number.isFinite(startMs) ? fmtSignedDurationMin((startMs - nowMsForRows) / 60000) : "";

      const line2 = (proj || tags)
        ? `<div class="sline2">${proj} ${tags}</div>`
        : "";

      const line3Bits = [];
      if (range) line3Bits.push(`<span class="pill">${escapeHtml(range)}</span>`);
      if (delta) line3Bits.push(`<span class="pill">Δ ${escapeHtml(delta)}</span>`);
      line3Bits.push(`<span class="pill">${escapeHtml(where)}</span>`);
      const line3 = `<div class="sline3">${line3Bits.join(" ")}</div>`;

      return `<div class="selitem" data-uuid="${escapeAttr(u)}">
        <div class="sid">${escapeHtml(short)}</div>
        <div class="sbody">
          <div class="sdesc" title="${escapeAttr(desc)}">${escapeHtml(desc)}</div>
          ${line2}
          ${line3}
        </div>
      </div>`;
    }).join("");

    elSelList.innerHTML = html;
  }

  if (elSelList) {
    elSelList.addEventListener("click", (ev) => {
      const sid = ev.target.closest(".sid");
      if (sid) {
        const row = sid.closest(".selitem");
        const uuid = row ? row.getAttribute("data-uuid") : null;
        if (uuid) {
          const txt = String(uuid).trim();
          try {
            if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
              navigator.clipboard.writeText(txt);
            } else {
              const ta = document.createElement("textarea");
              ta.value = txt;
              ta.style.position = "fixed";
              ta.style.opacity = "0";
              document.body.appendChild(ta);
              ta.select();
              document.execCommand("copy");
              ta.remove();
            }
            if (elStatus) elStatus.textContent = `Copied UUID ${txt.slice(0, 8)}.`;
          } catch (_) {
            if (elStatus) elStatus.textContent = "Copy failed.";
          }
        }
        ev.preventDefault();
        ev.stopPropagation();
        return;
      }
      const row = ev.target.closest(".selitem");
      if (!row) return;
      focusTask(row.getAttribute("data-uuid"));
    });
  }

  // -----------------------------
  // Panels toggle
  // -----------------------------
  const MOBILE_TAB_KEY = `${viewKey}:mobileTab`;
  const MOBILE_PANELS = ["left", "calendar", "commands"];
  const mqlMobileTabs = (typeof window !== "undefined" && typeof window.matchMedia === "function")
    ? window.matchMedia("(max-width: 820px)")
    : { matches: false };
  let mobilePanel = (() => {
    const raw = String(globalThis.__scalpel_kvGet(MOBILE_TAB_KEY) || "").trim();
    return MOBILE_PANELS.includes(raw) ? raw : "calendar";
  })();

  function _isMobileTabsMode() {
    return !!(mqlMobileTabs && mqlMobileTabs.matches);
  }
  function applyMobilePanel(panel, persist) {
    const next = MOBILE_PANELS.includes(String(panel || "")) ? String(panel) : "calendar";
    mobilePanel = next;

    elLayout.classList.remove("mobile-panel-left", "mobile-panel-calendar", "mobile-panel-commands");
    elLayout.classList.add(`mobile-panel-${next}`);

    const tabs = document.querySelectorAll("#mobileTabs [data-mobile-panel]");
    for (const tab of tabs) {
      const p = String(tab.getAttribute("data-mobile-panel") || "");
      const on = (p === next);
      tab.classList.toggle("on", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    }

    if (persist) globalThis.__scalpel_kvSet(MOBILE_TAB_KEY, next);
  }
  function applyMobileTabsMode() {
    const on = _isMobileTabsMode();
    elLayout.classList.toggle("mobile-view", on);
    if (on) {
      applyPanelsCollapsed(false, false);
      applyMobilePanel(mobilePanel, false);
    } else {
      elLayout.classList.remove("mobile-panel-left", "mobile-panel-calendar", "mobile-panel-commands");
    }
  }

  function applyPanelsCollapsed(collapsed, persist) {
    const effective = _isMobileTabsMode() ? false : !!collapsed;
    if (effective) elLayout.classList.add("panels-collapsed");
    else elLayout.classList.remove("panels-collapsed");
    elBtnTogglePanels.textContent = _isMobileTabsMode()
      ? "Panels via tabs"
      : (effective ? "Show panels" : "Hide panels");
    if (persist) globalThis.__scalpel_kvSet(panelsKey, effective ? "1" : "0");
  }
  (function initPanelsCollapsed() {
    const saved = globalThis.__scalpel_kvGet(panelsKey);
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
    if (_isMobileTabsMode()) {
      applyMobilePanel("calendar", true);
      return;
    }
    const nowCollapsed = !elLayout.classList.contains("panels-collapsed");
    applyPanelsCollapsed(nowCollapsed, true);
  });
  (function bindMobileTabs(){
    const tabs = document.querySelectorAll("#mobileTabs [data-mobile-panel]");
    for (const tab of tabs) {
      tab.addEventListener("click", () => {
        const p = String(tab.getAttribute("data-mobile-panel") || "");
        applyMobilePanel(p, true);
      });
    }
    const onChange = () => {
      applyMobileTabsMode();
      const saved = globalThis.__scalpel_kvGet(panelsKey);
      if (saved === "1" || saved === "0") applyPanelsCollapsed(saved === "1", false);
      else applyPanelsCollapsed(window.innerWidth < 1100, false);
    };
    if (mqlMobileTabs && typeof mqlMobileTabs.addEventListener === "function") {
      mqlMobileTabs.addEventListener("change", onChange);
    } else if (mqlMobileTabs && typeof mqlMobileTabs.addListener === "function") {
      mqlMobileTabs.addListener(onChange);
    }
    applyMobileTabsMode();
  })();

  // -----------------------------
  // Calendar skeleton
  // -----------------------------
  function minuteToMs(min) { return min * 60000; }
  function minuteOfDayFromMs(ms) {
    const n = Number(ms);
    if (!Number.isFinite(n)) return NaN;

    const caches = __scalpelGetTimeCaches();
    if (caches.minuteByMs.has(n)) return caches.minuteByMs.get(n);

    const sod = startOfLocalDayMs(n);
    const out = Math.floor((n - sod) / 60000);
    return __scalpelCacheSetWithCap(caches.minuteByMs, n, out, 24000);
  }
  function dayIndexFromMs(ms) {
    const n = Number(ms);
    if (!Number.isFinite(n)) return null;

    const d0 = dayStarts[0];
    if (!Number.isFinite(d0)) return null;

    const caches = __scalpelGetTimeCaches();
    const cached = caches.dayIndexByMs.get(n);
    if (cached && cached.d0 === d0 && cached.days === DAYS) return cached.di;

    const raw = Math.floor((startOfLocalDayMs(n) - d0) / 86400000);
    const di = (raw < 0 || raw >= DAYS) ? null : raw;
    __scalpelCacheSetWithCap(caches.dayIndexByMs, n, { d0, days: DAYS, di }, 24000);
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
      if (isWeekendDayMs(dayStarts[i])) h.classList.add("weekend");

      const lab = fmtDayLabel(dayStarts[i]);
      const dayKey = ymdFromMs(dayStarts[i]);
      if (dayKey === ymdFromMs(Date.now())) h.classList.add("today");
      h.innerHTML = `
        <div class="dtop">
          <div>${escapeHtml(lab.top)}</div>
          <span>${escapeHtml(lab.bot)}</span>
        </div>
        <div class="loadrow">
          <div class="loadbar"><div class="loadfill"></div></div>
          <div class="loadtxt">0m</div>
        </div>
        <div class="day-notes"></div>
      `;
      h.addEventListener("pointerdown", (ev) => {
        if (ev && ev.button != null && ev.button !== 0) return;
        try {
          if (typeof setActiveDay === "function") setActiveDay(i, true);
          else {
            activeDayIndex = i;
            saveActiveDay();
            renderDayBalance(activeDayIndex, lastDayVis);
          }
        } catch (_) {}
      });
      header.appendChild(h);
      // Allow dropping notes onto the day header (creates an all-day note)
      h.addEventListener("dragover", (ev) => {
        const nid = ev.dataTransfer.getData("text/scalpel_note_id");
        if (!nid) return;
        ev.preventDefault();
        h.classList.add("dragover");
      });
      h.addEventListener("dragleave", () => h.classList.remove("dragover"));
      h.addEventListener("drop", (ev) => {
        ev.preventDefault();
        h.classList.remove("dragover");
        const nid = ev.dataTransfer.getData("text/scalpel_note_id");
        if (!nid) return;
        try { placeNoteAllDay(nid, i); } catch (e) { console.error("Note drop failed", e); }
        try { if (typeof setActiveDay === "function") setActiveDay(i, true); } catch (_) {}
        rerenderAll();
      });

    }

    const body = document.createElement("div");
    body.className = "days-body";
    body.id = "daysBody";

    for (let i = 0; i < DAYS; i++) {
      const col = document.createElement("div");
      col.className = "day-col";
      col.dataset.dayIndex = String(i);
      if (isWeekendDayMs(dayStarts[i])) col.classList.add("weekend");
      col.innerHTML = `<div class="drop-hint"></div>`;

      col.addEventListener("dragover", (ev) => {
        ev.preventDefault();
        col.classList.add("dragover");
      });
      col.addEventListener("dragleave", () => col.classList.remove("dragover"));

      col.addEventListener("drop", (ev) => {
        ev.preventDefault();
        col.classList.remove("dragover");
        try { if (typeof setActiveDay === "function") setActiveDay(i, true); } catch (_) {}

        // Notes (sticky): drop a note to place it
        const noteId = ev.dataTransfer.getData("text/scalpel_note_id");
        if (noteId) {
          const rect = col.getBoundingClientRect();
          let y = ev.clientY - rect.top;
          try{
            const off = Number(globalThis.__scalpel_note_drag_offy || 0);
            if (Number.isFinite(off)) y -= off;
          }catch(_){ }
          const minute = yToMinute(y);
          try { placeNoteAt(noteId, i, minute); } catch (e) { console.error("Note drop failed", e); }
          rerenderAll();
          return;
        }

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
    body.addEventListener("dblclick", onCalendarBackgroundDoubleClick, { capture: true });

    daysCol.addEventListener("scroll", () => {
      const tb = document.getElementById("timeBody");
      if (tb) tb.style.transform = `translateY(-${daysCol.scrollTop}px)`;
    }, { passive: true });

    const tb = document.getElementById("timeBody");
    if (tb) tb.style.transform = `translateY(-0px)`;
  }

  buildCalendarSkeleton();
  try { if (typeof applyActiveDayHighlight === "function") applyActiveDayHighlight(); } catch (_) {}

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
    if (ev.target && ev.target.closest && (ev.target.closest(".evt") || ev.target.closest(".note") || ev.target.closest(".npill"))) return;

    try {
      const di = clamp(dayIndexFromClientX(ev.clientX), 0, DAYS - 1);
      if (typeof setActiveDay === "function") setActiveDay(di, true);
      else {
        activeDayIndex = di;
        saveActiveDay();
        renderDayBalance(activeDayIndex, lastDayVis);
      }
    } catch (_) {}

    const daysCol = document.getElementById("daysCol");
    if (daysCol) daysCol.classList.add("selecting");

    marquee = { startX: ev.clientX, startY: ev.clientY, lastRect: null, pointerId: ev.pointerId };

    window.addEventListener("pointermove", onMarqueeMove, { passive: false });
    window.addEventListener("pointerup", onMarqueeUp, { once: true });
    window.addEventListener("pointercancel", onMarqueeUp, { once: true });

    ev.preventDefault();
    ev.stopPropagation();
  }



  function onCalendarBackgroundDoubleClick(ev) {
    // Double-click on empty calendar timeline:
    // - plain dblclick: open task add modal seeded at the click time
    // - Ctrl/Meta + dblclick: create and place a note at the click time, then open editor
    try{
      if (ev && ev.button != null && ev.button !== 0) return;
      if (!ev || !ev.target) return;

      // Ignore dblclick on interactive elements
      if (ev.target.closest && (
        ev.target.closest(".evt") ||
        ev.target.closest(".resize") ||
        ev.target.closest(".note") ||
        ev.target.closest(".npill") ||
        ev.target.closest(".modal")
      )) return;

      const colEl = ev.target.closest ? ev.target.closest(".day-col") : null;
      let di = null;
      if (colEl && colEl.dataset && colEl.dataset.dayIndex != null) {
        const n = parseInt(colEl.dataset.dayIndex, 10);
        if (Number.isFinite(n)) di = n;
      }
      if (di == null) di = dayIndexFromClientX(ev.clientX);
      di = clamp(di, 0, DAYS - 1);

      const cols = document.querySelectorAll(".day-col");
      const col = (cols && cols.length) ? cols[di] : null;
      if (!col) return;

      const rect = col.getBoundingClientRect();
      const y = ev.clientY - rect.top;
      const minute = yToMinute(y);

      // Update active day context
      try {
        if (Number.isInteger(di) && di >= 0 && di < DAYS) {
          if (typeof setActiveDay === "function") setActiveDay(di, true);
          else {
            activeDayIndex = di;
            saveActiveDay();
            renderDayBalance(activeDayIndex, lastDayVis);
          }
        }
      } catch (_) {}

      if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && !ev.altKey) {
        // Ctrl/Meta + dblclick: create a note placed at click point
        try {
          const n = createNote("");
          if (n && n.id) {
            placeNoteAt(n.id, di, minute);
            rerenderAll();
            openNoteEditor(n.id);
          }
        } catch (e) {
          console.error("Ctrl+dblclick note create failed", e);
        }
      } else if (!ev.ctrlKey && !ev.metaKey && !ev.shiftKey && !ev.altKey) {
        // plain dblclick: open Add Tasks modal seeded at click point
        try {
          openAddModal({ dayIndex: di, minute: minute });
        } catch (e) {
          try { openAddModal(); } catch (_) {}
        }
      } else {
        return;
      }

      ev.preventDefault();
      ev.stopPropagation();
    }catch(_){ }
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
      rerenderAll({ mode: "selection" });
      marquee = null;
      return;
    }

    const hits = [];
    for (const node of __eventNodeByUuid.values()) {
      if (node && node.dataset && node.dataset.preview === "1") continue;
      const r = node.getBoundingClientRect();
      const nr = { left:r.left, right:r.right, top:r.top, bottom:r.bottom };
      if (rectsIntersect(rect, nr)) {
        const u = node.dataset.uuid;
        if (u) hits.push(u);
      }
    }

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
    rerenderAll({ mode: "selection" });
    marquee = null;
  }

  // -----------------------------
  // Classification (due-based population)
  // -----------------------------
  function taskSearchHaystack(t) {
    if (!t) return "";
    if (typeof t.__search === "string") return t.__search;
    if (typeof __scalpelBuildTaskSearch === "function") {
      const s = __scalpelBuildTaskSearch(t);
      t.__search = s;
      return s;
    }
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
      if (!isTaskVisibleForRender(t)) continue;
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
  // scalpel:layoutOverlapGroups:v1 (defensive)
  // Guard against transient boot/order mismatches where byDay[i] can be undefined.
  if (!Array.isArray(dayEvents)) dayEvents = [];

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
  const __scalpelGapNodesByDay = new Map();

  function renderGapsForDay(dayIndex, col, allIntervals) {
    const oldNodes = __scalpelGapNodesByDay.get(dayIndex);
    if (oldNodes && oldNodes.length) {
      for (const n of oldNodes) {
        try { if (n && n.parentNode) n.parentNode.removeChild(n); } catch (_) {}
      }
    }

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
    const newNodes = [];

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
      newNodes.push(div);
    }

    __scalpelGapNodesByDay.set(dayIndex, newNodes);
  }

  // -----------------------------
  // Now line
  // -----------------------------
  let __scalpelNowLineNode = null;

  function renderNowLine() {
    if (__scalpelNowLineNode) {
      try { if (__scalpelNowLineNode.parentNode) __scalpelNowLineNode.parentNode.removeChild(__scalpelNowLineNode); } catch (_) {}
      __scalpelNowLineNode = null;
    }

    const nowMs = Date.now();
    const dayStart = startOfLocalDayMs(nowMs);
    const di = Math.floor((dayStart - dayStarts[0]) / 86400000);
    if (di < 0 || di >= DAYS) return;

    const min = Math.floor((nowMs - dayStart) / 60000);
    if (min < WORK_START || min > WORK_END) return;

    const cols = document.querySelectorAll(".day-col");
    const col = cols[di];
    if (!col) return;

    const topPx = (min - WORK_START) * pxPerMin;
    const line = document.createElement("div");
    line.className = "now-line";
    line.style.top = `${topPx}px`;
    line.innerHTML = `<div class="now-label">Now ${escapeHtml(fmtHm(nowMs))}</div>`;
    col.appendChild(line);
    __scalpelNowLineNode = line;
  }

  // -----------------------------
  // Next up banner
  // -----------------------------
  function fmtHMFromMs(ms){
    return fmtHm(ms);
  }
  function fmtDayLabelFromMs(ms){
    return ymdFromMs(ms);
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
      if (!isTaskVisibleForRender(t)) continue;

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
        if (!isTaskVisibleForRender(t)) continue;

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

  const elBtnClearColors = document.getElementById("btnClearColors");
  const elBtnExportColors = document.getElementById("btnExportColors");
  const elBtnImportColors = document.getElementById("btnImportColors");
  const elColorsImportFile = document.getElementById("colorsImportFile");

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
    }catch(e){ console.error("Palette export failed", e); }
  }

  function _sanitizeColorMap(obj){
    const out = Object.create(null);
    try{
      if (!obj || typeof obj !== "object") return out;
      for (const [k, v] of Object.entries(obj)){
        if (typeof k !== "string" || typeof v !== "string") continue;
        if (!(k.startsWith("project:") || k.startsWith("tag:"))) continue;
        const vv = v.trim();
        if (!vv || vv.length > 128) continue;
        out[k] = vv;
      }
    }catch(_){ }
    return out;
  }

  function _mergeColorMaps(base, add){
    const out = Object.create(null);
    try{
      for (const [k,v] of Object.entries(base || {})){
        if (typeof v === "string") out[k] = v;
      }
      for (const [k,v] of Object.entries(add || {})){
        if (typeof v === "string") out[k] = v;
      }
    }catch(_){ }
    return out;
  }

  if (elBtnClearColors) elBtnClearColors.addEventListener("click", () => {
    if (!Object.keys(colorMap || {}).length) return;
    if (!confirm("Clear all custom palette colors (global)?")) return;
    colorMap = Object.create(null);
    saveColors();
    rerenderAll();
  });

  if (elBtnExportColors) elBtnExportColors.addEventListener("click", () => {
    const obj = { schema: "scalpel-palette-colors/v1", exported_at_utc: new Date().toISOString(), colors: colorMap || {} };
    _downloadJSON(obj, "scalpel-palette-colors.json");
  });

  if (elBtnImportColors && elColorsImportFile) elBtnImportColors.addEventListener("click", () => {
    try{ elColorsImportFile.value = ""; }catch(_){ }
    elColorsImportFile.click();
  });

  if (elColorsImportFile) elColorsImportFile.addEventListener("change", async () => {
    try{
      const f = (elColorsImportFile.files && elColorsImportFile.files[0]) ? elColorsImportFile.files[0] : null;
      if (!f) return;
      const txt = await f.text();
      const parsed = JSON.parse(txt);
      let incoming = null;
      if (parsed && typeof parsed === "object") {
        if (parsed.colors && typeof parsed.colors === "object") incoming = parsed.colors;
        else incoming = parsed;
      }
      const imp = _sanitizeColorMap(incoming);
      if (!Object.keys(imp).length) {
        alert("No valid palette colors found in the imported file.");
        return;
      }

      const replace = confirm("Replace existing palette colors?\n\nOK = replace\nCancel = merge");
      if (replace) colorMap = Object.create(null);

      colorMap = _mergeColorMaps(colorMap, imp);
      saveColors();
      rerenderAll();
    }catch(e){
      console.error("Palette import failed", e);
      alert("Palette import failed. Please ensure the file is valid JSON.");
    }
  });

  // -----------------------------
'''
