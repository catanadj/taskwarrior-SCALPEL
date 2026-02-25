# scalpel/render/js/part04_rendering.py
from __future__ import annotations

JS_PART = r'''// Rendering (lists)
  // -----------------------------
  function renderLists(backlog, problems) {
    elBacklog.innerHTML = "";
    elProblems.innerHTML = "";
    elBacklogCount.textContent = `${backlog.length}`;
    elProblemCount.textContent = `${problems.length}`;

    for (const x of backlog) {
      const t = x.t;

      const row = document.createElement("div");
      row.className = "item" + (selected.has(t.uuid) ? " selected" : "") + (isDimmedTask(t) ? " dimmed" : "");
      row.draggable = true;
      row.dataset.uuid = t.uuid;

      // Colorize backlog row if user-colored
      const acc = resolveTaskAccent(t);
      if (acc && acc.color && acc.explicit) {
        const rgb = hexToRgb(acc.color);
        if (rgb) {
          row.classList.add("user-colored");
          if (acc.source === "goal") row.classList.add("goal-colored");
          row.style.setProperty("--row-accent-rgb", `${rgb.r},${rgb.g},${rgb.b}`);
        }
      }

      row.addEventListener("dragstart", (ev) => {
        const uuids = (selected.has(t.uuid) ? Array.from(selected) : [t.uuid]);
        ev.dataTransfer.setData("text/uuidlist", JSON.stringify(uuids));
        ev.dataTransfer.setData("text/uuid", t.uuid);
        ev.dataTransfer.effectAllowed = "move";
      });

      const sel = document.createElement("div");
      sel.className = "selbox2";
      sel.innerHTML = `<span class="tick">✓</span>`;
      sel.addEventListener("pointerdown", (ev) => {
        setActiveDayFromUuid(t.uuid);
        toggleSelection(t.uuid);
        rerenderAll();
        ev.preventDefault();
        ev.stopPropagation();
      });

      const main = document.createElement("div");

      const tags = (t.tags || []).slice(0, 3).map(x => `<span class="pill">${escapeHtml(x)}</span>`).join(" ");
      const proj = t.project ? `<span class="pill">${escapeHtml(t.project)}</span>` : "";
      const hintPill = `<span class="pill warn">${escapeHtml(x.hint)}</span>`;

      main.innerHTML = `
        <div class="line1">${escapeHtml(t.description || "(no description)")}</div>
        <div class="line2">
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">${hintPill} ${proj} ${tags}</div>
          <div class="pill">${escapeHtml((t.uuid || "").slice(0,8))}</div>
        </div>`;

      row.appendChild(sel);
      row.appendChild(main);
      elBacklog.appendChild(row);
    }

    for (const x of problems) {
      const t = x.t;
      const div = document.createElement("div");
      div.className = "item";
      div.style.gridTemplateColumns = "1fr";
      div.innerHTML = `
        <div>
          <div class="line1">${escapeHtml(t.description || "(no description)")}</div>
          <div class="line2">
            <div class="pill bad">${escapeHtml(x.reason)}</div>
            <div class="pill">${escapeHtml((t.uuid || "").slice(0,8))}</div>
          </div>
        </div>`;
      elProblems.appendChild(div);
    }
  }

  // -----------------------------
  // Conflicts panel
  // -----------------------------
  function renderConflicts(allConflictByDay) {
    let total = 0;
    for (const segs of allConflictByDay) total += segs.length;

    const summary = total ? `${total} segment${total===1?"":"s"}` : "None";

    let body = "";
    if (!total) {
      body = `<div class="hint">No overlapping segments detected.</div>`;
    } else {
      for (let di = 0; di < DAYS; di++) {
        const segs = allConflictByDay[di];
        if (!segs || !segs.length) continue;

        const lab = fmtDayLabel(dayStarts[di]);
        body += `<div class="conf-day">
          <div class="dh"><div class="d">${escapeHtml(lab.top)} <span style="color:var(--muted);font-weight:500">${escapeHtml(lab.bot)}</span></div>
          <div class="n">${segs.length} segment${segs.length===1?"":"s"}</div></div>`;

        for (const seg of segs) {
          const s = new Date(seg.startMs);
          const e = new Date(seg.endMs);
          const range = `${pad2(s.getHours())}:${pad2(s.getMinutes())}–${pad2(e.getHours())}:${pad2(e.getMinutes())}`;
          const count = seg.uuids.length;

          const names = seg.uuids.slice(0, 4).map(u => {
            const t = tasksByUuid.get(u);
            return t ? t.description : u.slice(0,8);
          }).filter(Boolean);

          const extra = count > 4 ? ` +${count-4} more` : "";
          const bots = `${names.map(escapeHtml).join(" • ")}${escapeHtml(extra)}`;

          const uu = JSON.stringify(seg.uuids);
          const jumpMin = minuteOfDayFromMs(seg.startMs);

          body += `
            <div class="conf-item">
              <div class="top">
                <div class="range">${escapeHtml(range)}</div>
                <div class="count">${count} tasks</div>
              </div>
              <div class="bots">${bots}</div>
              <div class="acts">
                <button class="small" onclick='window.__scalpel_select_conflict(${uu}, ${di}, ${jumpMin})'>Select</button>
                <button class="small" onclick='window.__scalpel_jump(${di}, ${jumpMin})'>Jump</button>
              </div>
            </div>`;
        }
        body += `</div>`;
      }
    }

    elConflictsBox.innerHTML = `
      <div class="ctitle" id="confToggle">
        <div class="t">Conflicts</div>
        <div class="s">${escapeHtml(summary)}</div>
        <div class="chev" id="confChev">${confCollapsed ? "▸" : "▾"}</div>
      </div>
      <div class="conf-body" id="confBody">${body}</div>
    `;

    const toggle = document.getElementById("confToggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        confCollapsed = !confCollapsed;
        saveConfCollapsed();
        applyConfCollapsed(confCollapsed, false);
      });
    }

    applyConfCollapsed(confCollapsed, false);
  }

  function renderDayLoadsAndConflicts(byDay) {
    const headers = document.querySelectorAll(".day-h");
    const allConflictByDay = [];

    for (let i = 0; i < DAYS; i++) {
      const dayEvents = byDay[i] || [];
      const loadMin = dayEvents.reduce((acc, ev) => acc + Math.max(0, (ev.dueMs - ev.startMs) / 60000), 0);
      const util = CAL_MINUTES > 0 ? (loadMin / CAL_MINUTES) : 0;

      const segs = computeConflictSegments(dayEvents);
      allConflictByDay.push(segs);

      const h = headers[i];
      if (h) {
        const fill = h.querySelector(".loadfill");
        const txt = h.querySelector(".loadtxt");
        const pct = Math.min(200, Math.round(util * 100));
        if (fill) {
          fill.style.width = `${Math.min(100, pct)}%`;
          if (util > 1.0) fill.classList.add("over");
          else fill.classList.remove("over");
        }
        if (txt) {
          const confN = segs.length;
          const loadLabel = `${fmtDuration(loadMin)} / ${fmtDuration(CAL_MINUTES)}`;
          txt.textContent = confN ? `${loadLabel} • ${confN} conflict${confN===1?"":"s"}` : loadLabel;
        }
      }
    }

    renderConflicts(allConflictByDay);
  }

  // -----------------------------
  // Calendar rendering
  // -----------------------------
  function renderCalendar(events, allByDay) {
    const byDay = Array.from({length: DAYS}, () => []);
    for (const ev of events) {
      const di = dayIndexFromMs(ev.dueMs);
      if (di === null) continue;
      byDay[di].push(ev);
    }

    renderDayLoadsAndConflicts(byDay);

    const dayCols = document.querySelectorAll(".day-col");
    for (let i = 0; i < dayCols.length; i++) {
      const col = dayCols[i];

      col.querySelectorAll(".gap").forEach(n => n.remove());
      col.querySelectorAll(".evt").forEach(n => n.remove());
      col.querySelectorAll(".now-line").forEach(n => n.remove());

      renderGapsForDay(i, col, allByDay ? allByDay[i] : []);

      const laidOut = layoutOverlapGroups(byDay[i]);

      for (const ev of laidOut) {
        const t = tasksByUuid.get(ev.uuid);
        if (!t) continue;

        const startMin = minuteOfDayFromMs(ev.startMs);
        const dueMin = minuteOfDayFromMs(ev.dueMs);

        const topMin = clamp(startMin, WORK_START, WORK_END);
        const botMin = clamp(dueMin, WORK_START, WORK_END);
        const durMin = Math.max(1, botMin - topMin);

        const topPx = (topMin - WORK_START) * pxPerMin;
        const hPx = durMin * pxPerMin;

        const w = 100 / ev.laneCount;
        const leftPct = ev.laneIndex * w;

        const el = document.createElement("div");
        el.className = "evt" + (selected.has(ev.uuid) ? " selected" : "") + (isDimmedTask(t) ? " dimmed" : "");
        el.dataset.uuid = ev.uuid;

        // Determine accent
        const acc = resolveTaskAccent(t);
        if (acc && acc.color) {
          el.style.setProperty("--evt-accent", acc.color);
          const rgb = hexToRgb(acc.color);
          if (rgb) el.style.setProperty("--evt-accent-rgb", `${rgb.r},${rgb.g},${rgb.b}`);
          if (acc.explicit) el.classList.add("user-colored");
          if (acc.source === "goal") el.classList.add("goal-colored");
        } else {
          el.style.setProperty("--evt-accent", `hsl(${hashHue(ev.uuid)} 70% 60%)`);
        }

        el.style.top = `${topPx}px`;
        el.style.height = `${hPx}px`;
        el.style.left = `calc(6px + ${leftPct}%)`;
        el.style.width = `calc(${w}% - 12px)`;

        const s = new Date(ev.startMs);
        const d = new Date(ev.dueMs);
        const timeStr = `${pad2(s.getHours())}:${pad2(s.getMinutes())}–${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
        const durLabel = fmtDuration((ev.dueMs - ev.startMs) / 60000);

        const subtitle = (t.project ? t.project : "") + ((t.tags && t.tags.length) ? ` • ${t.tags.slice(0,3).join(",")}` : "");

        el.innerHTML = `
          <div class="evt-top">
            <div class="evt-title">${escapeHtml(t.description || "(no description)")}</div>
            <div class="evt-time">
              <span class="time-pill time-range">${escapeHtml(timeStr)}</span>
              <span class="time-pill dur-pill">${escapeHtml(durLabel)}</span>
            </div>
          </div>
          <div class="evt-bot">
            <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(subtitle)}</div>
            <code>${escapeHtml((t.uuid||"").slice(0,8))}</code>
          </div>
          <div class="resize" title="Resize (changes due)"></div>
        `;

        el.addEventListener("click", (ev2) => {
          if (drag) return;
          const u = ev.uuid;
          setActiveDayFromUuid(u);
          if (ev2.ctrlKey || ev2.metaKey) toggleSelection(u);
          else if (ev2.shiftKey) { selected.add(u); selectionLead = u; updateSelectionMeta(); }
          else setSelectionOnly(u);
          rerenderAll();
          ev2.preventDefault();
          ev2.stopPropagation();
        });

        el.addEventListener("pointerdown", onPointerDownEvent);
        col.appendChild(el);
      }
    }

    renderNowLine();
  }

  // -----------------------------
'''
