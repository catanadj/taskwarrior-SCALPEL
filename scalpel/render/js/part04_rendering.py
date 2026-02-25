# scalpel/render/js/part04_rendering.py
from __future__ import annotations

JS_PART = r'''// Rendering (lists)
  // -----------------------------
  const __backlogRowByUuid = new Map();
  const __eventNodeByUuid = new Map();
  const __selectedVisualUuids = new Set();
  const __nauticalSelectedPreviewUuids = new Set();
  let __nauticalSelectionMode = false;

  function __replaceChildrenSafe(parent, nodes) {
    if (!parent) return;
    parent.textContent = "";
    const frag = document.createDocumentFragment();
    for (const n of (nodes || [])) {
      if (n) frag.appendChild(n);
    }
    parent.appendChild(frag);
  }

  function __hintKind(hintRaw) {
    const hint = String(hintRaw || "").toLowerCase().trim();
    if (!hint) return "other";
    if (hint === "no due" || hint === "missing due") return "missing";
    if (hint === "outside workhours") return "work";
    if (hint === "due outside view") return "window";
    return "other";
  }

  function __emptyState(message, tone) {
    const el = document.createElement("div");
    el.className = "empty-state" + (tone ? ` ${tone}` : "");
    el.textContent = String(message || "");
    return el;
  }

  function __setSelectedVisual(uuid, isSelected) {
    if (!uuid) return;
    const evNode = __eventNodeByUuid.get(uuid);
    if (evNode) evNode.classList.toggle("selected", !!isSelected);

    const rowNode = __backlogRowByUuid.get(uuid);
    if (rowNode) rowNode.classList.toggle("selected", !!isSelected);
  }

  function syncSelectionVisuals() {
    const changed = new Set();
    for (const u of __selectedVisualUuids) if (!selected.has(u)) changed.add(u);
    for (const u of selected) if (!__selectedVisualUuids.has(u)) changed.add(u);
    for (const u of changed) __setSelectedVisual(u, selected.has(u));

    __selectedVisualUuids.clear();
    for (const u of selected) __selectedVisualUuids.add(u);
  }

  function __isNauticalPreviewSelected(uuid) {
    return __nauticalSelectedPreviewUuids.has(String(uuid || ""));
  }

  function __toggleNauticalPreviewSelection(uuid) {
    const u = String(uuid || "").trim();
    if (!u) return false;
    const t = tasksByUuid.get(u);
    if (!t || !t.nautical_preview) return false;
    if (__nauticalSelectedPreviewUuids.has(u)) {
      __nauticalSelectedPreviewUuids.delete(u);
      return false;
    }
    __nauticalSelectedPreviewUuids.add(u);
    return true;
  }

  function __clearNauticalPreviewSelection() {
    __nauticalSelectedPreviewUuids.clear();
    try {
      document.body.classList.remove("nautical-selection-has-picked");
    } catch (_) {}
  }

  function __syncNauticalSelectionBodyState() {
    try {
      const hasPicked = __nauticalSelectedPreviewUuids.size > 0;
      document.body.classList.toggle("nautical-selection-has-picked", hasPicked);
    } catch (_) {}
  }

  function __setNauticalSelectionMode(on) {
    __nauticalSelectionMode = !!on;
    if (!__nauticalSelectionMode) __clearNauticalPreviewSelection();
    try {
      document.body.classList.toggle("nautical-selection-mode", __nauticalSelectionMode);
    } catch (_) {}
    __syncNauticalSelectionBodyState();
  }

  function __pulseNauticalPreviewSelection(uuid) {
    const u = String(uuid || "").trim();
    if (!u) return;
    const row = __backlogRowByUuid.get(u);
    const ev = __eventNodeByUuid.get(u);
    const nodes = [row, ev].filter(Boolean);
    if (!nodes.length) return;

    requestAnimationFrame(() => {
      for (const n of nodes) {
        try {
          n.classList.remove("nautical-picked-pulse");
          void n.offsetWidth;
          n.classList.add("nautical-picked-pulse");
        } catch (_) {}
      }
      setTimeout(() => {
        for (const n of nodes) {
          try { n.classList.remove("nautical-picked-pulse"); } catch (_) {}
        }
      }, 760);
    });
  }

  function __applyNauticalSelectionVisual(node, isPreview, previewPicked) {
    if (!node) return;
    const hasPicked = (__nauticalSelectedPreviewUuids.size > 0);
    if (isPreview && __nauticalSelectionMode) {
      if (hasPicked) {
        if (previewPicked) {
          node.style.setProperty("opacity", "1", "important");
          node.style.setProperty("filter", "saturate(1.10) brightness(1.08)", "important");
        } else {
          // Keep unselected ghosts visible; selected ghosts should stand out without hiding context.
          node.style.setProperty("opacity", "0.70", "important");
          node.style.setProperty("filter", "grayscale(0.06) saturate(0.86) brightness(0.95)", "important");
        }
        return;
      }
    }
    node.style.removeProperty("opacity");
    node.style.removeProperty("filter");
  }

  function __createBacklogRow() {
    const row = document.createElement("div");
    const sel = document.createElement("div");
    const main = document.createElement("div");
    sel.className = "selbox2";
    sel.innerHTML = `<span class="tick">✓</span>`;

    row.__scalpelSel = sel;
    row.__scalpelMain = main;
    row.appendChild(sel);
    row.appendChild(main);

    row.addEventListener("contextmenu", (ev) => {
      const uuid = row.dataset ? row.dataset.uuid : null;
      if (!uuid || row.dataset.preview !== "1") return;
      ev.preventDefault();
      ev.stopPropagation();
      __openNauticalContextMenu(uuid, ev.clientX, ev.clientY);
    });

    row.addEventListener("dragstart", (ev) => {
      const uuid = row.dataset ? row.dataset.uuid : null;
      if (!uuid) return;
      const uuids = (selected.has(uuid) ? Array.from(selected) : [uuid]);
      ev.dataTransfer.setData("text/uuidlist", JSON.stringify(uuids));
      ev.dataTransfer.setData("text/uuid", uuid);
      ev.dataTransfer.effectAllowed = "move";
    });

    sel.addEventListener("pointerdown", (ev) => {
      const uuid = row.dataset ? row.dataset.uuid : null;
      if (!uuid || row.dataset.preview === "1") return;
      setActiveDayFromUuid(uuid);
      toggleSelection(uuid);
      rerenderAll({ mode: "selection", immediate: true });
      ev.preventDefault();
      ev.stopPropagation();
    });

    row.addEventListener("click", (ev) => {
      const uuid = row.dataset ? row.dataset.uuid : null;
      if (!uuid || row.dataset.preview !== "1") return;
      if (!__nauticalSelectionMode) return;
      __toggleNauticalPreviewSelection(uuid);
      __syncNauticalSelectionBodyState();
      __pulseNauticalPreviewSelection(uuid);
      rerenderAll({ mode: "full", immediate: true });
      ev.preventDefault();
      ev.stopPropagation();
    });
    return row;
  }

  function __nauticalSourceUuid(task) {
    const raw = task && (
      task.nautical_source_uuid ??
      task.nauticalSourceUuid ??
      task.nautical_source ??
      task.nauticalSource
    );
    const uuid = String(raw || "").trim();
    return uuid || null;
  }

  function __computeNauticalMove(previewUuid, opts) {
    const silent = !!(opts && opts.silent);
    const pUuid = String(previewUuid || "").trim();
    if (!pUuid) return null;

    const previewTask = tasksByUuid.get(pUuid);
    if (!previewTask || !previewTask.nautical_preview) return null;

    const sourceUuid = __nauticalSourceUuid(previewTask);
    if (!sourceUuid) {
      if (!silent && elStatus) elStatus.textContent = "Cannot move: this Nautical preview has no source task UUID.";
      return null;
    }

    const sourceTask = tasksByUuid.get(sourceUuid);
    if (!sourceTask || sourceTask.nautical_preview) {
      if (!silent && elStatus) elStatus.textContent = `Cannot move: source task ${sourceUuid.slice(0,8)} is not available in this view.`;
      return null;
    }

    if (queuedActionKind(sourceUuid)) {
      if (!silent && elStatus) elStatus.textContent = "Cannot move: source task already has a queued done/delete action.";
      return null;
    }

    const previewIv = effectiveInterval(pUuid);
    const dueMs = (previewIv && Number.isFinite(previewIv.dueMs))
      ? Math.round(previewIv.dueMs)
      : Math.round(Number(previewTask.due_ms));
    if (!Number.isFinite(dueMs)) {
      if (!silent && elStatus) elStatus.textContent = "Cannot move: preview has no valid due time.";
      return null;
    }

    const sourceIv = effectiveInterval(sourceUuid);
    let durMs = (sourceIv && Number.isFinite(sourceIv.durMs) && sourceIv.durMs > 0)
      ? Math.round(sourceIv.durMs)
      : Math.round(baselineDur.get(sourceUuid) ?? (DEFAULT_DUR * 60000));
    if (!Number.isFinite(durMs) || durMs <= 0) durMs = Math.round(DEFAULT_DUR * 60000);

    const scheduledMs = dueMs - durMs;
    if (!Number.isFinite(scheduledMs) || dueMs <= scheduledMs) {
      if (!silent && elStatus) elStatus.textContent = "Cannot move: computed interval is invalid.";
      return null;
    }

    return {
      previewUuid: pUuid,
      sourceUuid,
      sourceTask,
      dueMs,
      durMs,
      scheduledMs,
    };
  }

  let __nauticalCtxMenu = null;
  let __nauticalCtxPreviewUuid = null;

  function __collectNauticalMovesFromPreviewUuids(previewUuids) {
    const bySource = new Map();
    let invalid = 0;
    let duplicates = 0;
    for (const previewUuid of (previewUuids || [])) {
      const move = __computeNauticalMove(previewUuid, { silent: true });
      if (!move) {
        invalid += 1;
        continue;
      }
      const prev = bySource.get(move.sourceUuid);
      if (!prev) {
        bySource.set(move.sourceUuid, move);
        continue;
      }
      // Same source can only be moved once; keep earliest selected spawn.
      duplicates += 1;
      if (move.dueMs < prev.dueMs) bySource.set(move.sourceUuid, move);
    }
    return {
      moves: Array.from(bySource.values()).sort((a, b) => a.dueMs - b.dueMs),
      invalid,
      duplicates,
    };
  }

  function __collectOverdueNauticalMoves() {
    const nowMs = Date.now();
    const previews = [];
    for (const t of (DATA.tasks || [])) {
      if (!t || !t.nautical_preview || !t.uuid) continue;
      const move = __computeNauticalMove(t.uuid, { silent: true });
      if (!move) continue;

      const sourceIv = effectiveInterval(move.sourceUuid);
      if (!sourceIv || !Number.isFinite(sourceIv.dueMs)) continue;
      if (!(sourceIv.dueMs < nowMs)) continue;
      if (!(move.dueMs > sourceIv.dueMs)) continue;
      previews.push(t.uuid);
    }
    return __collectNauticalMovesFromPreviewUuids(previews).moves;
  }

  function __moveNauticalSourcesWithMoves(moves, emptyStatus, successLabel) {
    if (!moves.length) {
      if (elStatus) elStatus.textContent = String(emptyStatus || "No Nautical source tasks to move.");
      return 0;
    }

    const changes = {};
    for (const move of moves) {
      changes[move.sourceUuid] = {
        scheduledMs: move.scheduledMs,
        dueMs: move.dueMs,
        durMs: move.durMs,
      };
    }

    try { setActiveDayFromUuid(moves[0].previewUuid); } catch (_) {}
    commitPlanMany(changes);

    let applied = 0;
    for (const move of moves) {
      const cur = plan.get(move.sourceUuid);
      if (cur && Number(cur.due_ms) === move.dueMs && Number(cur.dur_ms) === move.durMs) applied += 1;
    }
    if (elStatus) {
      if (applied === moves.length) elStatus.textContent = `${successLabel} ${applied} task(s).`;
      else elStatus.textContent = `${successLabel} ${applied}/${moves.length} task(s).`;
    }
    return applied;
  }

  function __moveAllOverdueNauticalSources() {
    const moves = __collectOverdueNauticalMoves();
    return __moveNauticalSourcesWithMoves(
      moves,
      "No overdue Nautical source tasks with a next spawn in this view.",
      "Moved overdue Nautical sources to next spawn:"
    );
  }

  function __moveSelectedNauticalSources() {
    const selectedPreviewUuids = Array.from(__nauticalSelectedPreviewUuids);
    const packed = __collectNauticalMovesFromPreviewUuids(selectedPreviewUuids);
    const moved = __moveNauticalSourcesWithMoves(
      packed.moves,
      "No selected Nautical ghosts to move.",
      "Moved selected Nautical ghosts:"
    );
    __clearNauticalPreviewSelection();
    if (!moved) return 0;
    if (elStatus && (packed.invalid > 0 || packed.duplicates > 0)) {
      const parts = [];
      if (packed.invalid > 0) parts.push(`${packed.invalid} invalid selection(s) skipped`);
      if (packed.duplicates > 0) parts.push(`${packed.duplicates} duplicate source selection(s) collapsed`);
      if (parts.length) elStatus.textContent = `${elStatus.textContent} (${parts.join(", ")}).`;
    }
    return moved;
  }

  function __closeNauticalContextMenu() {
    if (!__nauticalCtxMenu) return;
    __nauticalCtxPreviewUuid = null;
    __nauticalCtxMenu.hidden = true;
  }

  function __positionNauticalContextMenu(menu, x, y) {
    if (!menu) return;
    const gap = 8;
    const vw = Math.max(320, window.innerWidth || 0);
    const vh = Math.max(180, window.innerHeight || 0);
    let left = Math.round(Number.isFinite(Number(x)) ? Number(x) : gap);
    let top = Math.round(Number.isFinite(Number(y)) ? Number(y) : gap);

    menu.style.left = "0px";
    menu.style.top = "0px";
    menu.hidden = false;

    const rect = menu.getBoundingClientRect();
    if (left + rect.width + gap > vw) left = Math.max(gap, vw - rect.width - gap);
    if (top + rect.height + gap > vh) top = Math.max(gap, vh - rect.height - gap);
    if (left < gap) left = gap;
    if (top < gap) top = gap;

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }

  function __ensureNauticalContextMenu() {
    if (__nauticalCtxMenu) return __nauticalCtxMenu;

    const menu = document.createElement("div");
    menu.className = "nautical-ctx-menu";
    menu.hidden = true;
    menu.innerHTML = `
      <div class="nautical-ctx-title" data-role="title"></div>
      <button type="button" class="nautical-ctx-btn subtle" data-act="mode">Selection mode: Off</button>
      <button type="button" class="nautical-ctx-btn" data-act="toggle-select">Select this ghost</button>
      <button type="button" class="nautical-ctx-btn" data-act="bring-selected">Bring selected ghosts</button>
      <button type="button" class="nautical-ctx-btn" data-act="bring">Bring source task here</button>
      <button type="button" class="nautical-ctx-btn" data-act="bring-overdue">Bring all overdue to next spawn</button>
      <button type="button" class="nautical-ctx-btn subtle" data-act="cancel">Cancel</button>
    `;

    menu.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
    });
    menu.addEventListener("pointerdown", (ev) => {
      ev.stopPropagation();
    });
    menu.addEventListener("click", (ev) => {
      const btn = ev.target && ev.target.closest ? ev.target.closest("button[data-act]") : null;
      const act = btn && btn.dataset ? String(btn.dataset.act || "") : "";
      if (!act) return;
      if (act === "cancel") {
        __closeNauticalContextMenu();
        return;
      }
      if (act === "bring") {
        const pUuid = __nauticalCtxPreviewUuid;
        __closeNauticalContextMenu();
        __moveNauticalSourceTaskToPreview(pUuid);
        return;
      }
      if (act === "mode") {
        const pUuid = __nauticalCtxPreviewUuid;
        const r = menu.getBoundingClientRect();
        __setNauticalSelectionMode(!__nauticalSelectionMode);
        if (elStatus) elStatus.textContent = __nauticalSelectionMode
          ? "Nautical selection mode enabled. Click ghosts to select."
          : "Nautical selection mode disabled.";
        if (pUuid) __openNauticalContextMenu(pUuid, r.left, r.top);
        rerenderAll({ mode: "full", immediate: true });
        return;
      }
      if (act === "toggle-select") {
        const pUuid = __nauticalCtxPreviewUuid;
        if (!pUuid) return;
        __setNauticalSelectionMode(true);
        const on = __toggleNauticalPreviewSelection(pUuid);
        __syncNauticalSelectionBodyState();
        __pulseNauticalPreviewSelection(pUuid);
        if (elStatus) elStatus.textContent = on
          ? "Nautical ghost selected."
          : "Nautical ghost unselected.";
        __openNauticalContextMenu(pUuid, menu.getBoundingClientRect().left, menu.getBoundingClientRect().top);
        rerenderAll({ mode: "full", immediate: true });
        return;
      }
      if (act === "bring-selected") {
        __closeNauticalContextMenu();
        __moveSelectedNauticalSources();
        __setNauticalSelectionMode(false);
        rerenderAll({ mode: "full", immediate: true });
        return;
      }
      if (act === "bring-overdue") {
        __closeNauticalContextMenu();
        __moveAllOverdueNauticalSources();
      }
    });

    document.addEventListener("pointerdown", (ev) => {
      if (!__nauticalCtxMenu || __nauticalCtxMenu.hidden) return;
      if (__nauticalCtxMenu.contains(ev.target)) return;
      __closeNauticalContextMenu();
    }, true);
    document.addEventListener("keydown", (ev) => {
      if (!__nauticalCtxMenu || __nauticalCtxMenu.hidden) return;
      if (String(ev.key || "") !== "Escape") return;
      __closeNauticalContextMenu();
    }, true);
    window.addEventListener("resize", () => __closeNauticalContextMenu(), { passive: true });
    window.addEventListener("scroll", () => __closeNauticalContextMenu(), true);

    document.body.appendChild(menu);
    __nauticalCtxMenu = menu;
    return menu;
  }

  function __openNauticalContextMenu(previewUuid, clientX, clientY) {
    const move = __computeNauticalMove(previewUuid);
    if (!move) {
      __closeNauticalContextMenu();
      return;
    }

    const menu = __ensureNauticalContextMenu();
    __nauticalCtxPreviewUuid = move.previewUuid;

    const titleEl = menu.querySelector('[data-role="title"]');
    if (titleEl) {
      const srcLabel = String(move.sourceTask.description || "").trim() || move.sourceUuid.slice(0,8);
      titleEl.textContent = `${srcLabel} -> ${formatLocalNoOffset(move.dueMs)}`;
    }
    const modeBtn = menu.querySelector('[data-act="mode"]');
    if (modeBtn) modeBtn.textContent = `Selection mode: ${__nauticalSelectionMode ? "On" : "Off"}`;

    const toggleBtn = menu.querySelector('[data-act="toggle-select"]');
    if (toggleBtn) {
      const on = __isNauticalPreviewSelected(move.previewUuid);
      toggleBtn.textContent = on ? "Unselect this ghost" : "Select this ghost";
    }

    const selectedBtn = menu.querySelector('[data-act="bring-selected"]');
    if (selectedBtn) {
      const nSel = __nauticalSelectedPreviewUuids.size;
      selectedBtn.textContent = nSel > 0
        ? `Bring selected ghosts (${nSel})`
        : "Bring selected ghosts";
      selectedBtn.disabled = (nSel <= 0);
    }

    const bulkBtn = menu.querySelector('[data-act="bring-overdue"]');
    if (bulkBtn) {
      const n = __collectOverdueNauticalMoves().length;
      bulkBtn.textContent = n > 0
        ? `Bring all overdue to next spawn (${n})`
        : "Bring all overdue to next spawn";
      bulkBtn.disabled = (n <= 0);
    }

    __positionNauticalContextMenu(menu, clientX, clientY);
  }

  function __moveNauticalSourceTaskToPreview(previewUuid) {
    const move = __computeNauticalMove(previewUuid);
    if (!move) return false;
    __nauticalSelectedPreviewUuids.delete(move.previewUuid);

    try { setActiveDayFromUuid(move.previewUuid); } catch (_) {}
    try { setSelectionOnly(move.sourceUuid); } catch (_) {}

    commitPlanMany({
      [move.sourceUuid]: {
        scheduledMs: move.scheduledMs,
        dueMs: move.dueMs,
        durMs: move.durMs,
      }
    });

    const applied = plan.get(move.sourceUuid);
    if (applied && Number(applied.due_ms) === move.dueMs && Number(applied.dur_ms) === move.durMs) {
      if (elStatus) elStatus.textContent = `Moved ${move.sourceUuid.slice(0,8)} to Nautical spawn ${formatLocalNoOffset(move.dueMs)}.`;
      return true;
    }
    return false;
  }

  function __updateBacklogRow(row, x) {
    const t = x.t;
    if (!t || !t.uuid) return;
    const uuid = String(t.uuid);
    const isPreview = !!(t && t.nautical_preview);
    const previewPicked = isPreview && __isNauticalPreviewSelected(uuid);
    const qk = queuedActionKind(uuid);
    const hintKind = __hintKind(x && x.hint);

    row.className = "item"
      + (selected.has(uuid) ? " selected" : "")
      + (qk ? (` queued-${qk}`) : "")
      + (isPreview ? " nautical-preview" : "")
      + (previewPicked ? " nautical-picked" : "")
      + (isDimmedTask(t) ? " dimmed" : "");
    row.dataset.hintKind = hintKind;
    row.dataset.uuid = uuid;
    if (isPreview) {
      row.dataset.preview = "1";
      row.title = __nauticalSelectionMode
        ? "Selection mode: click to select/unselect ghost. Right-click for options."
        : "Right-click for Nautical options";
    } else {
      delete row.dataset.preview;
      row.removeAttribute("title");
      __nauticalSelectedPreviewUuids.delete(uuid);
    }
    __applyNauticalSelectionVisual(row, isPreview, previewPicked);
    row.draggable = !isPreview;

    const acc = resolveTaskAccent(t);
    if (acc && acc.color && acc.explicit) {
      const rgb = hexToRgb(acc.color);
      if (rgb) {
        row.classList.add("user-colored");
        if (acc.source === "goal") row.classList.add("goal-colored");
        else row.classList.remove("goal-colored");
        row.style.setProperty("--row-accent-rgb", `${rgb.r},${rgb.g},${rgb.b}`);
      } else {
        row.classList.remove("user-colored");
        row.classList.remove("goal-colored");
        row.style.removeProperty("--row-accent-rgb");
      }
    } else {
      row.classList.remove("user-colored");
      row.classList.remove("goal-colored");
      row.style.removeProperty("--row-accent-rgb");
    }

    const tags = (t.tags || []).slice(0, 3).map(v => `<span class="pill">${escapeHtml(v)}</span>`).join(" ");
    const proj = t.project ? `<span class="pill">${escapeHtml(t.project)}</span>` : "";
    const hintPill = `<span class="pill reason ${escapeAttr(hintKind)}">${escapeHtml(x.hint)}</span>`;
    const mainSig = [
      String(t.description || ""),
      String(t.project || ""),
      (t.tags || []).join("|"),
      String(x.hint || ""),
      uuid.slice(0, 8),
      previewPicked ? "picked:1" : "picked:0",
    ].join("\u001f");

    if (row.__scalpelMainSig !== mainSig) {
      const pickedPill = previewPicked
        ? `<span class="pill nautical-picked-pill" style="border-color:rgba(var(--accent-rgb),0.62);background:rgba(var(--accent-rgb),0.24);color:var(--text);font-weight:850;">SELECTED</span>`
        : "";
      row.__scalpelMain.innerHTML = `
        <div class="line1">${escapeHtml(t.description || "(no description)")}</div>
        <div class="line2 item-meta-row">
          <div class="chips">${pickedPill} ${hintPill} ${proj} ${tags}</div>
          <div class="pill">${escapeHtml(uuid.slice(0,8))}</div>
        </div>`;
      row.__scalpelMainSig = mainSig;
    }
  }

  function renderLists(backlog, problems) {
    elBacklogCount.textContent = `${backlog.length}`;
    elProblemCount.textContent = `${problems.length}`;

    const seen = new Set();
    const rows = [];
    for (const x of backlog) {
      const t = x && x.t;
      if (!t || !t.uuid) continue;
      const uuid = String(t.uuid);
      let row = __backlogRowByUuid.get(uuid);
      if (!row) {
        row = __createBacklogRow();
        __backlogRowByUuid.set(uuid, row);
      }
      __updateBacklogRow(row, x);
      rows.push(row);
      seen.add(uuid);
    }

    for (const [uuid, row] of Array.from(__backlogRowByUuid.entries())) {
      if (seen.has(uuid)) continue;
      __backlogRowByUuid.delete(uuid);
      try { if (row && row.parentNode) row.parentNode.removeChild(row); } catch (_) {}
    }
    __replaceChildrenSafe(elBacklog, rows.length ? rows : [__emptyState("Backlog is clear for this view.", "ok")]);

    const pnodes = [];
    for (const x of problems) {
      const t = x.t;
      const div = document.createElement("div");
      div.className = "item problem-item";
      div.style.gridTemplateColumns = "1fr";
      div.innerHTML = `
        <div>
          <div class="line1">${escapeHtml(t.description || "(no description)")}</div>
          <div class="line2 item-meta-row">
            <div class="pill bad">${escapeHtml(x.reason)}</div>
            <div class="pill">${escapeHtml((t.uuid || "").slice(0,8))}</div>
          </div>
        </div>`;
      pnodes.push(div);
    }
    __replaceChildrenSafe(elProblems, pnodes.length ? pnodes : [__emptyState("No interval problems detected.", "neutral")]);
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
          const range = `${fmtHm(seg.startMs)}–${fmtHm(seg.endMs)}`;
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
  function __eventInnerSig(t, ev, subtitle, timeStr, durLabel, previewPicked) {
    return [
      String(t.description || ""),
      subtitle,
      timeStr,
      durLabel,
      previewPicked ? "picked:1" : "picked:0",
      String((t.uuid || "").slice(0, 8)),
      String(ev.startMs),
      String(ev.dueMs),
      String(ev.laneIndex),
      String(ev.laneCount),
    ].join("\u001f");
  }

  function __createEventNode(uuid) {
    const el = document.createElement("div");
    el.dataset.uuid = String(uuid || "");
    el.addEventListener("contextmenu", (ev2) => {
      if (el.dataset.preview !== "1") return;
      const u = el.dataset.uuid;
      if (!u) return;
      ev2.preventDefault();
      ev2.stopPropagation();
      __openNauticalContextMenu(u, ev2.clientX, ev2.clientY);
    });
    el.addEventListener("click", (ev2) => {
      if (drag) return;
      if (el.dataset.preview === "1") {
        const uPrev = el.dataset.uuid;
        if (!uPrev) return;
        if (!__nauticalSelectionMode) return;
        __toggleNauticalPreviewSelection(uPrev);
        __syncNauticalSelectionBodyState();
        __pulseNauticalPreviewSelection(uPrev);
        rerenderAll({ mode: "full", immediate: true });
        ev2.preventDefault();
        ev2.stopPropagation();
        return;
      }
      const u = el.dataset.uuid;
      if (!u) return;
      setActiveDayFromUuid(u);
      if (ev2.ctrlKey || ev2.metaKey) toggleSelection(u);
      else if (ev2.shiftKey) { selected.add(u); selectionLead = u; updateSelectionMeta(); }
      else setSelectionOnly(u);
      rerenderAll({ mode: "selection", immediate: true });
      ev2.preventDefault();
      ev2.stopPropagation();
    });
    el.addEventListener("pointerdown", onPointerDownEvent);
    return el;
  }

  function __updateEventNode(el, ev, t) {
    const isPreview = !!(t && t.nautical_preview);
    const previewPicked = isPreview && __isNauticalPreviewSelected(ev && ev.uuid);
    const startMin = minuteOfDayFromMs(ev.startMs);
    const dueMin = minuteOfDayFromMs(ev.dueMs);

    const topMin = clamp(startMin, WORK_START, WORK_END);
    const botMin = clamp(dueMin, WORK_START, WORK_END);
    const durMin = Math.max(1, botMin - topMin);

    const topPx = (topMin - WORK_START) * pxPerMin;
    const hPx = durMin * pxPerMin;
    const w = 100 / ev.laneCount;
    const leftPct = ev.laneIndex * w;

    const qk = queuedActionKind(ev.uuid);
    let cls = "evt"
      + (selected.has(ev.uuid) ? " selected" : "")
      + (qk ? (` queued-${qk}`) : "")
      + (isPreview ? " nautical-preview" : "")
      + (previewPicked ? " nautical-picked" : "")
      + (isDimmedTask(t) ? " dimmed" : "");

    const acc = resolveTaskAccent(t);
    if (acc && acc.color) {
      el.style.setProperty("--evt-accent", acc.color);
      const rgb = hexToRgb(acc.color);
      if (rgb) el.style.setProperty("--evt-accent-rgb", `${rgb.r},${rgb.g},${rgb.b}`);
      else el.style.removeProperty("--evt-accent-rgb");
      if (acc.explicit) cls += " user-colored";
      if (acc.source === "goal") cls += " goal-colored";
    } else {
      el.style.removeProperty("--evt-accent");
      el.style.removeProperty("--evt-accent-rgb");
    }

    el.className = cls;
    if (isPreview) {
      el.dataset.preview = "1";
      el.title = __nauticalSelectionMode
        ? "Selection mode: click to select/unselect ghost. Right-click for options."
        : "Right-click for Nautical options";
    } else {
      delete el.dataset.preview;
      el.removeAttribute("title");
      __nauticalSelectedPreviewUuids.delete(ev && ev.uuid ? String(ev.uuid) : "");
    }
    __applyNauticalSelectionVisual(el, isPreview, previewPicked);

    el.style.top = `${topPx}px`;
    el.style.height = `${hPx}px`;
    el.style.left = `calc(6px + ${leftPct}%)`;
    el.style.width = `calc(${w}% - 12px)`;

    const timeStr = `${fmtHm(ev.startMs)}–${fmtHm(ev.dueMs)}`;
    const durLabel = fmtDuration((ev.dueMs - ev.startMs) / 60000);
    const subtitle = (t.project ? t.project : "") + ((t.tags && t.tags.length) ? ` • ${t.tags.slice(0,3).join(",")}` : "");

    const sig = __eventInnerSig(t, ev, subtitle, timeStr, durLabel, previewPicked);
    if (el.__scalpelInnerSig !== sig) {
      const pickedPill = previewPicked
        ? `<span class="time-pill nautical-picked-pill" style="border-color:rgba(var(--accent-rgb),0.68);background:rgba(var(--accent-rgb),0.28);color:var(--text);font-weight:850;">SELECTED</span>`
        : "";
      el.innerHTML = `
        <div class="evt-sheen" aria-hidden="true"></div>
        <div class="evt-top">
          <div class="evt-title">${escapeHtml(t.description || "(no description)")}</div>
          <div class="evt-time">
            <span class="time-pill time-range">${escapeHtml(timeStr)}</span>
            <span class="time-pill dur-pill">${escapeHtml(durLabel)}</span>
            ${pickedPill}
          </div>
        </div>
        <div class="evt-bot">
          <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(subtitle)}</div>
          <code>${escapeHtml((t.uuid||"").slice(0,8))}</code>
        </div>
        <div class="resize" title="Resize (changes due)"></div>
      `;
      el.__scalpelInnerSig = sig;
    }
  }

  function renderCalendar(events, allByDay) {
    const byDay = Array.from({length: DAYS}, () => []);
    const eventByUuid = new Map();
    for (const ev of (events || [])) {
      if (!ev || !ev.uuid) continue;
      eventByUuid.set(ev.uuid, ev);
    }
    if (Array.isArray(allByDay) && allByDay.length) {
      for (let di = 0; di < DAYS; di++) {
        const dayItems = allByDay[di] || [];
        for (const item of dayItems) {
          if (!item || !item.uuid) continue;
          const ev = eventByUuid.get(item.uuid);
          if (ev) byDay[di].push(ev);
        }
      }
    } else {
      for (const ev of eventByUuid.values()) {
        const di = dayIndexFromMs(ev.dueMs);
        if (di === null) continue;
        byDay[di].push(ev);
      }
    }

    renderDayLoadsAndConflicts(byDay);

    const dayCols = document.querySelectorAll(".day-col");

    try { renderHeaderNotes(); } catch (e) { /* ignore */ }
  const nCols = Math.min(dayCols.length, DAYS);
  const seenUuids = new Set();
  // scalpel:renderCalendar:v1 clamp to current DAYS (defensive)
    for (let i = 0; i < nCols; i++) {
      const col = dayCols[i];

      try { renderNotesInColumn(i, col); } catch (e) { /* ignore */ }

      renderGapsForDay(i, col, allByDay ? allByDay[i] : []);

      const laidOut = layoutOverlapGroups(byDay[i] || []);

      for (const ev of laidOut) {
        const t = tasksByUuid.get(ev.uuid);
        if (!t) continue;
        let el = __eventNodeByUuid.get(ev.uuid);
        if (!el) {
          el = __createEventNode(ev.uuid);
          __eventNodeByUuid.set(ev.uuid, el);
        }
        __updateEventNode(el, ev, t);
        col.appendChild(el);
        seenUuids.add(ev.uuid);
      }
    }

    try {
      for (const [di, nodes] of Array.from(__scalpelGapNodesByDay.entries())) {
        if (di < nCols) continue;
        for (const n of (nodes || [])) {
          try { if (n && n.parentNode) n.parentNode.removeChild(n); } catch (_) {}
        }
        __scalpelGapNodesByDay.delete(di);
      }
    } catch (_) {}

    for (const [uuid, el] of Array.from(__eventNodeByUuid.entries())) {
      if (seenUuids.has(uuid)) continue;
      __eventNodeByUuid.delete(uuid);
      try { if (el && el.parentNode) el.parentNode.removeChild(el); } catch (_) {}
    }
    for (const u of Array.from(__nauticalSelectedPreviewUuids.values())) {
      if (seenUuids.has(u)) continue;
      if (__backlogRowByUuid.has(u)) continue;
      __nauticalSelectedPreviewUuids.delete(u);
    }
    __syncNauticalSelectionBodyState();

    __scalpelVisibleEventUuids = new Set(seenUuids);
    __selectedVisualUuids.clear();
    for (const u of selected) __selectedVisualUuids.add(u);

    renderNowLine();
  }

  // Task FX helpers
  function pulseTasks(uuids){
    try{
      if (!uuids || !uuids.length) return;
      requestAnimationFrame(() => {
        for (const u of uuids){
          const el = document.querySelector(`.evt[data-uuid="${u}"]`);
          if (!el) continue;
          el.classList.remove("snap-pulse");
          // force reflow
          void el.offsetWidth;
          el.classList.add("snap-pulse");
          setTimeout(() => { try{ el.classList.remove("snap-pulse"); }catch(_){} }, 220);
        }
      });
    }catch(e){ /* noop */ }
  }

  // -----------------------------
'''
