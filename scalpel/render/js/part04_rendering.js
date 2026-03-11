  // -----------------------------
  const __backlogRowByUuid = new Map();
  const __eventNodeByUuid = new Map();
  const __selectedVisualUuids = new Set();
  const __nauticalSelectedPreviewUuids = new Set();
  const __taskWarningKinds = new Map();
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

  function __taskIdentifierForCommand(task) {
    if (!task) return "";
    return String((task.uuid || "").slice(0, 8));
  }

  function __taskFieldValue(value) {
    if (value == null) return "";
    let raw = "";
    if (typeof value === "string") raw = value;
    else if (typeof value === "number" || typeof value === "boolean") raw = String(value);
    else if (Array.isArray(value)) raw = value.map(v => String(v == null ? "" : v)).join(",");
    else {
      try { raw = JSON.stringify(value); } catch (_) { raw = String(value); }
    }
    return String(raw || "").replace(/\s+/g, " ").trim();
  }

  function __taskFieldPreview(value) {
    const s = __taskFieldValue(value);
    if (!s) return "";
    return (s.length > 84) ? (s.slice(0, 81) + "...") : s;
  }

  function __taskUdaEntries(task) {
    if (!task || typeof task !== "object") return [];
    const builtin = new Set([
      "id", "uuid", "description", "status", "project", "tags", "priority",
      "entry", "modified", "start", "end", "scheduled", "due", "wait", "until",
      "recur", "mask", "imask", "parent", "depends", "annotations", "urgency",
      "scheduled_ms", "due_ms", "duration_min", "local",
      "nautical_preview", "nautical_source_uuid", "nauticalSourceUuid",
      "nautical_source", "nauticalSource",
    ]);
    const out = [];
    for (const [k, v] of Object.entries(task)) {
      const key = String(k || "").trim();
      if (!key || builtin.has(key) || key.startsWith("_")) continue;
      const val = __taskFieldValue(v);
      if (!val) continue;
      out.push({ key, val });
    }
    out.sort((a, b) => String(a.key || "").localeCompare(String(b.key || "")));
    return out;
  }

  function __twQuotedAtom(value) {
    const s = String(value == null ? "" : value).trim();
    if (!s) return "";
    if (!/[\s"'\\]/.test(s)) return s;
    return `"${s.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }

  function __taskParseTagList(raw) {
    const seen = new Set();
    const out = [];
    const parts = String(raw || "").split(/[,\s]+/);
    for (const p of parts) {
      const tag = String(p || "").trim().replace(/^[+-]+/, "");
      if (!tag || seen.has(tag)) continue;
      seen.add(tag);
      out.push(tag);
    }
    return out;
  }

  function __isTaskEditModalOpen() {
    return !!(elTaskEditModal && elTaskEditModal.style.display === "flex");
  }

  let __taskEditState = null; // { uuid, ident, local, fields, custom_rows }

  function __newTaskEditCustomRow(key, val) {
    return { key: String(key || "").trim(), val: String(val || "").trim() };
  }

  function __ensureTaskEditCustomRows() {
    if (!__taskEditState) return [];
    if (!Array.isArray(__taskEditState.custom_rows)) __taskEditState.custom_rows = [];
    return __taskEditState.custom_rows;
  }

  function __syncTaskEditCustomRowsFromDom() {
    if (!__taskEditState || !elTaskEditCustomRows) return;
    const keyNodes = elTaskEditCustomRows.querySelectorAll('[data-custom-kind="key"]');
    const rows = [];
    keyNodes.forEach((node) => {
      const idx = String((node && node.getAttribute && node.getAttribute("data-custom-idx")) || "");
      const valNode = elTaskEditCustomRows.querySelector(`[data-custom-idx="${idx}"][data-custom-kind="val"]`);
      const key = String((node && node.value) || "").trim();
      const val = String((valNode && valNode.value) || "").trim();
      rows.push(__newTaskEditCustomRow(key, val));
    });
    __taskEditState.custom_rows = rows;
  }

  function __addTaskEditCustomRow(key, val, focusKey) {
    if (!__taskEditState) return;
    __syncTaskEditCustomRowsFromDom();
    const rows = __ensureTaskEditCustomRows();
    rows.push(__newTaskEditCustomRow(key, val));
    __renderTaskEditCustomRows();
    if (!focusKey) return;
    setTimeout(() => {
      try {
        const idx = rows.length - 1;
        const sel = focusKey ? `[data-custom-idx="${idx}"][data-custom-kind="key"]` : `[data-custom-idx="${idx}"][data-custom-kind="val"]`;
        const el = elTaskEditCustomRows && elTaskEditCustomRows.querySelector(sel);
        if (el) el.focus();
      } catch (_) {}
    }, 0);
  }

  function __taskEditFieldDefs(detailsTask, fallbackTask) {
    const rows = [];
    const desc = String(detailsTask.description ?? fallbackTask.description ?? "").trim();
    const proj = String(detailsTask.project ?? fallbackTask.project ?? "").trim();
    const pri = String(detailsTask.priority ?? fallbackTask.priority ?? "").trim();
    const tagsArr = Array.isArray(detailsTask.tags) ? detailsTask.tags : (Array.isArray(fallbackTask.tags) ? fallbackTask.tags : []);
    const tags = tagsArr.map(v => String(v || "").trim()).filter(Boolean).join(", ");

    rows.push({ key: "description", kind: "description", label: "description", value: desc });
    rows.push({ key: "project", kind: "scalar", label: "project", value: proj });
    rows.push({ key: "priority", kind: "scalar", label: "priority", value: pri });
    rows.push({ key: "tags", kind: "tags", label: "tags", value: tags });

    const udaEntries = __taskUdaEntries(detailsTask);
    for (const it of udaEntries) rows.push({ key: it.key, kind: "scalar", label: it.key, value: String(it.val || "") });
    return rows;
  }

  function __renderTaskEditGrid() {
    if (!elTaskEditGrid) return;
    const fields = (__taskEditState && Array.isArray(__taskEditState.fields)) ? __taskEditState.fields : [];
    const frag = document.createDocumentFragment();

    for (let i = 0; i < fields.length; i++) {
      const f = fields[i] || {};
      const row = document.createElement("div");
      row.className = "task-edit-row";

      const k = document.createElement("div");
      k.className = "k mono";
      k.textContent = String(f.label || f.key || "");

      const v = document.createElement("div");
      v.className = "v";

      let inp = null;
      if (f.kind === "description") {
        inp = document.createElement("textarea");
        inp.rows = 2;
      } else {
        inp = document.createElement("input");
        inp.type = "text";
      }
      inp.value = String(f.value || "");
      inp.setAttribute("data-field-idx", String(i));
      inp.setAttribute("data-field-key", String(f.key || ""));
      inp.setAttribute("data-field-kind", String(f.kind || ""));
      v.appendChild(inp);

      row.appendChild(k);
      row.appendChild(v);
      frag.appendChild(row);
    }

    elTaskEditGrid.textContent = "";
    elTaskEditGrid.appendChild(frag);
    __renderTaskEditCustomRows();
  }

  function __renderTaskEditCustomRows() {
    if (!elTaskEditCustomRows) return;
    const rows = __ensureTaskEditCustomRows();
    const frag = document.createDocumentFragment();

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i] || {};
      const row = document.createElement("div");
      row.className = "task-edit-custom-row";

      const inpKey = document.createElement("input");
      inpKey.type = "text";
      inpKey.placeholder = "uda_field";
      inpKey.value = String(r.key || "");
      inpKey.setAttribute("data-custom-idx", String(i));
      inpKey.setAttribute("data-custom-kind", "key");

      const inpVal = document.createElement("input");
      inpVal.type = "text";
      inpVal.placeholder = "value";
      inpVal.value = String(r.val || "");
      inpVal.setAttribute("data-custom-idx", String(i));
      inpVal.setAttribute("data-custom-kind", "val");

      const bRm = document.createElement("button");
      bRm.type = "button";
      bRm.className = "small danger rm";
      bRm.textContent = "−";
      bRm.title = "Remove row";
      bRm.addEventListener("click", () => {
        __syncTaskEditCustomRowsFromDom();
        const cur = __ensureTaskEditCustomRows();
        if (i < 0 || i >= cur.length) return;
        cur.splice(i, 1);
        if (!cur.length) cur.push(__newTaskEditCustomRow("", ""));
        __renderTaskEditCustomRows();
      });

      row.appendChild(inpKey);
      row.appendChild(inpVal);
      row.appendChild(bRm);
      frag.appendChild(row);
    }

    elTaskEditCustomRows.textContent = "";
    elTaskEditCustomRows.appendChild(frag);
  }

  function __closeTaskEditModal() {
    if (!elTaskEditModal) return;
    elTaskEditModal.style.display = "none";
    __taskEditState = null;
  }

  function __resetTaskEditModal() {
    const st = __taskEditState;
    if (!st || !Array.isArray(st.fields) || !elTaskEditGrid) return;
    for (let i = 0; i < st.fields.length; i++) {
      const f = st.fields[i] || {};
      const inp = elTaskEditGrid.querySelector(`[data-field-idx="${i}"]`);
      if (!inp) continue;
      inp.value = String(f.value || "");
    }
    st.custom_rows = [__newTaskEditCustomRow("", "")];
    __renderTaskEditCustomRows();
    if (elStatus && st.ident) elStatus.textContent = `Reset edits for ${st.ident}.`;
  }

  function __collectTaskEditArgs() {
    const st = __taskEditState;
    if (!st || !Array.isArray(st.fields) || !elTaskEditGrid) return { args: [], error: "Task editor is not ready." };
    const args = [];

    for (let i = 0; i < st.fields.length; i++) {
      const f = st.fields[i] || {};
      const key = String(f.key || "").trim();
      if (!key) continue;

      const inp = elTaskEditGrid.querySelector(`[data-field-idx="${i}"]`);
      const cur = String((inp && inp.value) || "").trim();
      const old = String(f.value || "").trim();

      if (String(f.kind || "") === "description") {
        if (cur === old) continue;
        if (!cur) return { args: [], error: "Description cannot be empty." };
        args.push(`description:${__twQuotedAtom(cur)}`);
        continue;
      }

      if (String(f.kind || "") === "tags") {
        const oldTags = __taskParseTagList(old);
        const newTags = __taskParseTagList(cur);
        const oldSet = new Set(oldTags);
        const newSet = new Set(newTags);
        for (const tag of oldTags) if (!newSet.has(tag)) args.push(`-${tag}`);
        for (const tag of newTags) if (!oldSet.has(tag)) args.push(`+${tag}`);
        continue;
      }

      if (cur === old) continue;
      if (!cur) args.push(`${key}:`);
      else args.push(`${key}:${__twQuotedAtom(cur)}`);
    }

    const existingKeys = new Set(st.fields.map(f => String((f && f.key) || "").trim().toLowerCase()).filter(Boolean));
    const seenCustom = new Set();
    const customRows = __ensureTaskEditCustomRows();
    for (let i = 0; i < customRows.length; i++) {
      const inpKey = elTaskEditCustomRows && elTaskEditCustomRows.querySelector(`[data-custom-idx="${i}"][data-custom-kind="key"]`);
      const inpVal = elTaskEditCustomRows && elTaskEditCustomRows.querySelector(`[data-custom-idx="${i}"][data-custom-kind="val"]`);
      const key = String((inpKey && inpKey.value) || "").trim();
      const val = String((inpVal && inpVal.value) || "").trim();
      if (!key && !val) continue;
      if (!key) return { args: [], error: "Custom UDA row has a value but no field name." };

      const keyLc = key.toLowerCase();
      if (existingKeys.has(keyLc)) return { args: [], error: `Custom UDA '${key}' is already shown above.` };
      if (seenCustom.has(keyLc)) return { args: [], error: `Custom UDA '${key}' is repeated.` };
      seenCustom.add(keyLc);

      if (!val) args.push(`${key}:`);
      else args.push(`${key}:${__twQuotedAtom(val)}`);
    }

    return { args, error: "" };
  }

  function __applyLocalTaskEdit() {
    const st = __taskEditState;
    if (!st || !st.uuid || !elTaskEditGrid) return false;
    const t = tasksByUuid.get(st.uuid);
    if (!t) return false;

    const out = __collectTaskEditArgs();
    if (out.error) {
      if (elStatus) elStatus.textContent = out.error;
      return false;
    }
    const args = Array.isArray(out.args) ? out.args : [];
    if (!args.length) {
      if (elStatus) elStatus.textContent = `No field changes detected for ${st.ident}.`;
      return false;
    }

    try {
      if (typeof globalThis.__scalpel_recordUndoSnapshot === "function") {
        globalThis.__scalpel_recordUndoSnapshot(`edit local placeholder ${st.ident}`);
      }
    } catch (_) {}

    for (let i = 0; i < st.fields.length; i++) {
      const f = st.fields[i] || {};
      const key = String(f.key || "").trim();
      if (!key) continue;
      const inp = elTaskEditGrid.querySelector(`[data-field-idx="${i}"]`);
      const cur = String((inp && inp.value) || "").trim();
      if (String(f.kind || "") === "tags") {
        t.tags = __taskParseTagList(cur);
        f.value = Array.isArray(t.tags) ? t.tags.join(", ") : "";
        continue;
      }
      if (key === "description" && !cur) {
        if (elStatus) elStatus.textContent = "Description cannot be empty.";
        return false;
      }
      if (cur) t[key] = cur;
      else if (key === "project" || key === "priority") t[key] = "";
      else delete t[key];
      f.value = String(t[key] || "");
    }

    const existingKeys = new Set(st.fields.map(f => String((f && f.key) || "").trim().toLowerCase()).filter(Boolean));
    const customRows = __ensureTaskEditCustomRows();
    const keepKeys = new Set();
    for (let i = 0; i < customRows.length; i++) {
      const inpKey = elTaskEditCustomRows && elTaskEditCustomRows.querySelector(`[data-custom-idx="${i}"][data-custom-kind="key"]`);
      const inpVal = elTaskEditCustomRows && elTaskEditCustomRows.querySelector(`[data-custom-idx="${i}"][data-custom-kind="val"]`);
      const key = String((inpKey && inpKey.value) || "").trim();
      const val = String((inpVal && inpVal.value) || "").trim();
      if (!key || existingKeys.has(key.toLowerCase())) continue;
      keepKeys.add(key);
      if (val) t[key] = val;
      else delete t[key];
    }

    for (const key of Object.keys(t)) {
      if (keepKeys.has(key)) continue;
      if ([
        "id", "uuid", "description", "status", "project", "tags", "priority",
        "scheduled_ms", "due_ms", "duration", "duration_min", "local",
      ].includes(String(key))) continue;
      if (String(key || "").startsWith("_")) continue;
      if (!existingKeys.has(String(key || "").toLowerCase())) delete t[key];
    }

    const localRow = localAdds.find(x => x && x.uuid === st.uuid);
    if (localRow) localRow.desc = String(t.description || "").trim();
    if (typeof __scalpelIndexTaskForSearch === "function") __scalpelIndexTaskForSearch(t);
    try { renderCommands(); } catch (_) {}
    try { rerenderAll(); } catch (_) {}
    if (elStatus) elStatus.textContent = `Updated local placeholder ${st.ident}.`;
    __closeTaskEditModal();
    return true;
  }

  function __queueTaskEditSave() {
    const st = __taskEditState;
    if (!st || !st.ident) return false;
    if (st.local) return __applyLocalTaskEdit();

    const out = __collectTaskEditArgs();
    if (out.error) {
      if (elStatus) elStatus.textContent = out.error;
      return false;
    }
    const args = Array.isArray(out.args) ? out.args : [];
    if (!args.length) {
      if (elStatus) elStatus.textContent = `No field changes detected for ${st.ident}.`;
      return false;
    }

    const line = `task ${st.ident} modify ${args.join(" ")}`;
    if (typeof queueAction === "function") queueAction(line);
    else {
      actionQueue.push(line);
      try { saveActions(); } catch (_) {}
      try { renderCommands(); } catch (_) {}
    }

    if (elStatus) elStatus.textContent = `Queued modify for ${st.ident} (${args.length} change${args.length === 1 ? "" : "s"}).`;
    __closeTaskEditModal();
    return true;
  }

  async function __fetchFreshTaskForEdit(uuid) {
    const u = String(uuid || "").trim();
    if (!u) return null;
    const canHttp = /^https?:$/i.test(String(location.protocol || ""));
    if (!canHttp) return null;
    const res = await fetch(`/task?uuid=${encodeURIComponent(u)}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
      cache: "no-store",
    });
    let body = null;
    try { body = await res.json(); } catch (_) {}
    if (!res.ok || !body || body.ok !== true || !body.task || typeof body.task !== "object") return null;
    return body.task;
  }

  async function __openTaskEditModal(uuid) {
    const u = String(uuid || "").trim();
    if (!u) return false;
    const t = tasksByUuid.get(u);
    if (!t) return false;
    if (t.nautical_preview) return false;
    if (queuedActionKind(u)) {
      if (elStatus) elStatus.textContent = "Task already has queued done/delete action. Clear final actions first.";
      return false;
    }

    const ident = __taskIdentifierForCommand(t);
    if (!ident) {
      if (elStatus) elStatus.textContent = "Cannot edit task: missing task identifier.";
      return false;
    }
    if (!elTaskEditModal || !elTaskEditGrid) {
      if (elStatus) elStatus.textContent = "Task editor modal is unavailable in this build.";
      return false;
    }

    let detailsTask = t;
    let usedFreshTask = false;
    if (!t.local) {
      try {
        if (elStatus) elStatus.textContent = `Loading task attributes for ${ident}...`;
        const fresh = await __fetchFreshTaskForEdit(u);
        if (fresh && typeof fresh === "object") {
          detailsTask = fresh;
          usedFreshTask = true;
        }
      } catch (_) {}
    }

    const iv = effectiveInterval(u);
    const sch = (iv && Number.isFinite(iv.startMs)) ? formatLocalNoOffset(iv.startMs) : "-";
    const due = (iv && Number.isFinite(iv.dueMs)) ? formatLocalNoOffset(iv.dueMs) : "-";
    const dur = (iv && Number.isFinite(iv.durMs)) ? fmtDuration(iv.durMs / 60000) : "-";
    const rows = __taskEditFieldDefs(detailsTask, t);
    const udaCount = rows.filter(r => String(r && r.key || "").toLowerCase() !== "description"
      && String(r && r.key || "").toLowerCase() !== "project"
      && String(r && r.key || "").toLowerCase() !== "priority"
      && String(r && r.key || "").toLowerCase() !== "tags").length;

    __taskEditState = { uuid: u, ident, local: !!t.local, fields: rows, custom_rows: [__newTaskEditCustomRow("", "")] };
    if (elTaskEditTitle) elTaskEditTitle.textContent = `Edit task ${ident}`;
    if (elTaskEditMeta) {
      elTaskEditMeta.textContent = t.local
        ? `Source: local placeholder draft • Scheduled: ${sch} • Due: ${due} • Duration: ${dur} • UDAs: ${udaCount}`
        : (`Source: ${usedFreshTask ? "fresh task export" : "cached payload"} • `
          + `Scheduled: ${sch} • Due: ${due} • Duration: ${dur} • `
          + `UDAs: ${udaCount}`);
    }

    __renderTaskEditGrid();
    if (elTaskEditSave) elTaskEditSave.textContent = t.local ? "Save local draft" : "Queue modify";
    elTaskEditModal.style.display = "flex";
    setTimeout(() => {
      try {
        const first = elTaskEditGrid.querySelector("[data-field-idx='0']");
        if (first) first.focus();
      } catch (_) {}
    }, 0);
    return true;
  }

  (function __bindTaskEditModal(){
    if (!elTaskEditModal) return;
    if (elTaskEditClose) elTaskEditClose.addEventListener("click", __closeTaskEditModal);
    if (elTaskEditReset) elTaskEditReset.addEventListener("click", __resetTaskEditModal);
    if (elTaskEditSave) elTaskEditSave.addEventListener("click", __queueTaskEditSave);
    if (elTaskEditAddCustom) {
      elTaskEditAddCustom.addEventListener("click", () => {
        __addTaskEditCustomRow("", "", true);
      });
    }
    elTaskEditModal.addEventListener("click", (ev) => {
      if (ev.target === elTaskEditModal) __closeTaskEditModal();
    });
    if (elTaskEditGrid) {
      elTaskEditGrid.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
          __queueTaskEditSave();
          ev.preventDefault();
          ev.stopPropagation();
        }
      });
    }
    document.addEventListener("keydown", (ev) => {
      if (!__isTaskEditModalOpen()) return;
      if (ev.key === "Escape") {
        __closeTaskEditModal();
        ev.preventDefault();
        ev.stopPropagation();
        return;
      }
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
        __queueTaskEditSave();
        ev.preventDefault();
        ev.stopPropagation();
      }
    }, true);
  })();

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

    row.addEventListener("dblclick", async (ev) => {
      const uuid = row.dataset ? row.dataset.uuid : null;
      if (!uuid || row.dataset.preview === "1") return;
      if (ev.target && ev.target.closest && ev.target.closest(".selbox2")) return;
      ev.preventDefault();
      ev.stopPropagation();
      try { setActiveDayFromUuid(uuid); } catch (_) {}
      try { setSelectionOnly(uuid); } catch (_) {}
      rerenderAll({ mode: "selection", immediate: true });
      try { await __openTaskEditModal(uuid); } catch (_) {}
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
      if (cur && Number(cur.due_ms) === move.dueMs && Number(cur.dur_ms) === move.durMs) {
        applied += 1;
        try { markNauticalPreviewConsumed(move.sourceUuid, move.dueMs); } catch (_) {}
      }
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
      try { markNauticalPreviewConsumed(move.sourceUuid, move.dueMs); } catch (_) {}
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
    for (const day of (allConflictByDay || [])) {
      total += Number(day && day.issueCount) || 0;
    }

    const summary = total ? `${total} issue${total===1?"":"s"}` : "Clean";

    let body = "";
    if (!total) {
      body = `<div class="hint">No overlaps, overload, or out-of-hours issues detected.</div>`;
    } else {
      for (let di = 0; di < DAYS; di++) {
        const day = allConflictByDay[di];
        if (!day || !day.issueCount) continue;

        const lab = fmtDayLabel(dayStarts[di]);
        const sumBits = Array.isArray(day.summaryBits) ? day.summaryBits : [];
        body += `<div class="conf-day">
          <div class="dh">
            <div>
              <div class="d">${escapeHtml(lab.top)} <span style="color:var(--muted);font-weight:500">${escapeHtml(lab.bot)}</span></div>
              <div class="s">${escapeHtml(sumBits.join(" • "))}</div>
            </div>
            <div class="n">${day.issueCount} issue${day.issueCount===1?"":"s"}</div>
          </div>`;

        if (Number(day.overloadMin) > 0) {
          const uu = JSON.stringify(day.allUuids || []);
          const jumpMin = Number.isFinite(day.firstMinute) ? day.firstMinute : WORK_START;
          body += `
            <div class="conf-item issue-overload">
              <div class="top">
                <div class="range">Overbooked</div>
                <div class="count">${escapeHtml(fmtDuration(day.overloadMin))}</div>
              </div>
              <div class="bots">Planned load ${escapeHtml(fmtDuration(day.loadMin))} against ${escapeHtml(fmtDuration(CAL_MINUTES))} available work time.</div>
              <div class="acts">
                <button class="small" onclick='window.__scalpel_select_conflict(${uu}, ${di}, ${jumpMin})'>Select day</button>
                <button class="small" onclick='window.__scalpel_jump(${di}, ${jumpMin})'>Jump</button>
              </div>
            </div>`;
        }

        for (const seg of (day.overlapSegments || [])) {
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
            <div class="conf-item issue-overlap">
              <div class="top">
                <div class="range">Overlap ${escapeHtml(range)}</div>
                <div class="count">${count} task${count===1?"":"s"}</div>
              </div>
              <div class="bots">${bots}</div>
              <div class="acts">
                <button class="small" onclick='window.__scalpel_select_conflict(${uu}, ${di}, ${jumpMin})'>Select</button>
                <button class="small" onclick='window.__scalpel_jump(${di}, ${jumpMin})'>Jump</button>
              </div>
            </div>`;
        }

        for (const issue of (day.outOfHours || [])) {
          const t = tasksByUuid.get(issue.uuid);
          const label = t ? t.description : String(issue.uuid || "").slice(0, 8);
          const uu = JSON.stringify([issue.uuid]);
          const jumpMin = minuteOfDayFromMs(issue.startMs);
          body += `
            <div class="conf-item issue-out-hours">
              <div class="top">
                <div class="range">Outside workhours ${escapeHtml(fmtHm(issue.startMs))}–${escapeHtml(fmtHm(issue.endMs))}</div>
                <div class="count">${escapeHtml(fmtDuration((issue.endMs - issue.startMs) / 60000))}</div>
              </div>
              <div class="bots">${escapeHtml(label)}</div>
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
        <div class="t">Planning warnings</div>
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

  function __computeDayIssueSummary(dayEvents, dayIndex) {
    const events = Array.isArray(dayEvents) ? dayEvents.filter(ev => ev && ev.uuid && Number.isFinite(ev.startMs) && Number.isFinite(ev.dueMs) && ev.dueMs > ev.startMs) : [];
    const overlapSegments = computeConflictSegments(events);
    const dayStart = dayStarts[dayIndex];
    const workStartMs = dayStart + WORK_START * 60000;
    const workEndMs = dayStart + WORK_END * 60000;
    const outOfHours = [];
    let loadMin = 0;
    const allUuids = [];

    for (const ev of events) {
      allUuids.push(ev.uuid);
      loadMin += Math.max(0, (ev.dueMs - ev.startMs) / 60000);

      if (ev.startMs < workStartMs) {
        outOfHours.push({
          uuid: ev.uuid,
          startMs: ev.startMs,
          endMs: Math.min(ev.dueMs, workStartMs),
        });
      }
      if (ev.dueMs > workEndMs) {
        outOfHours.push({
          uuid: ev.uuid,
          startMs: Math.max(ev.startMs, workEndMs),
          endMs: ev.dueMs,
        });
      }
    }

    const overloadMin = Math.max(0, Math.round(loadMin - CAL_MINUTES));
    const summaryBits = [];
    if (overloadMin > 0) summaryBits.push(`Overbooked ${fmtDuration(overloadMin)}`);
    if (overlapSegments.length) summaryBits.push(`${overlapSegments.length} overlap${overlapSegments.length===1?"":"s"}`);
    if (outOfHours.length) summaryBits.push(`${outOfHours.length} out of hours`);

    let firstMinute = null;
    if (events.length) {
      const firstMs = Math.min.apply(null, events.map(ev => ev.startMs));
      firstMinute = minuteOfDayFromMs(firstMs);
    }

    return {
      loadMin: Math.round(loadMin),
      overlapSegments,
      outOfHours,
      overloadMin,
      summaryBits,
      issueCount: overlapSegments.length + outOfHours.length + (overloadMin > 0 ? 1 : 0),
      firstMinute,
      allUuids,
    };
  }

  function renderDayLoadsAndConflicts(byDay) {
    const headers = document.querySelectorAll(".day-h");
    const daySummaries = [];
    __taskWarningKinds.clear();

    for (let i = 0; i < DAYS; i++) {
      const dayEvents = byDay[i] || [];
      const day = __computeDayIssueSummary(dayEvents, i);
      const util = CAL_MINUTES > 0 ? (day.loadMin / CAL_MINUTES) : 0;
      daySummaries.push(day);

      for (const seg of day.overlapSegments) {
        for (const uuid of (seg.uuids || [])) {
          if (!__taskWarningKinds.has(uuid)) __taskWarningKinds.set(uuid, new Set());
          __taskWarningKinds.get(uuid).add("overlap");
        }
      }
      for (const issue of day.outOfHours) {
        if (!__taskWarningKinds.has(issue.uuid)) __taskWarningKinds.set(issue.uuid, new Set());
        __taskWarningKinds.get(issue.uuid).add("out_of_hours");
      }

      const h = headers[i];
      if (h) {
        const fill = h.querySelector(".loadfill");
        const txt = h.querySelector(".loadtxt");
        const warn = h.querySelector(".daywarn");
        const pct = Math.min(200, Math.round(util * 100));
        if (fill) {
          fill.style.width = `${Math.min(100, pct)}%`;
          if (util > 1.0) fill.classList.add("over");
          else fill.classList.remove("over");
        }
        h.classList.toggle("has-warning", day.issueCount > 0);
        h.classList.toggle("has-overload", day.overloadMin > 0);
        h.classList.toggle("has-overlap", day.overlapSegments.length > 0);
        h.classList.toggle("has-out-hours", day.outOfHours.length > 0);
        if (txt) {
          txt.textContent = `${fmtDuration(day.loadMin)} / ${fmtDuration(CAL_MINUTES)}`;
        }
        if (warn) {
          warn.textContent = day.summaryBits.length ? day.summaryBits.join(" • ") : "Clean";
        }
      }
    }

    renderConflicts(daySummaries);
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
    el.addEventListener("dblclick", async (ev2) => {
      if (drag) return;
      const u = el.dataset.uuid;
      if (!u || el.dataset.preview === "1") return;
      ev2.preventDefault();
      ev2.stopPropagation();
      setActiveDayFromUuid(u);
      setSelectionOnly(u);
      rerenderAll({ mode: "selection", immediate: true });
      try { await __openTaskEditModal(u); } catch (_) {}
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
    const warnKinds = __taskWarningKinds.get(ev.uuid);
    let cls = "evt"
      + (selected.has(ev.uuid) ? " selected" : "")
      + (qk ? (` queued-${qk}`) : "")
      + (isPreview ? " nautical-preview" : "")
      + (previewPicked ? " nautical-picked" : "")
      + (isDimmedTask(t) ? " dimmed" : "");
    if (warnKinds && warnKinds.has("overlap")) cls += " warn-overlap";

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
    const byDayAll = Array.from({length: DAYS}, () => []);
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
          byDayAll[di].push({
            uuid: item.uuid,
            startMs: item.startMs,
            dueMs: item.dueMs,
          });
          const ev = eventByUuid.get(item.uuid);
          if (ev) byDay[di].push(ev);
        }
      }
    } else {
      for (const ev of eventByUuid.values()) {
        const di = dayIndexFromMs(ev.dueMs);
        if (di === null) continue;
        byDay[di].push(ev);
        byDayAll[di].push({
          uuid: ev.uuid,
          startMs: ev.startMs,
          dueMs: ev.dueMs,
        });
      }
    }

    renderDayLoadsAndConflicts(byDayAll);

    const dayCols = document.querySelectorAll(".day-col");

    try { renderHeaderNotes(); } catch (e) { /* ignore */ }
  const nCols = Math.min(dayCols.length, DAYS);
  const seenUuids = new Set();
  // scalpel:renderCalendar:v1 clamp to current DAYS (defensive)
    for (let i = 0; i < nCols; i++) {
      const col = dayCols[i];

      try { renderNotesInColumn(i, col); } catch (e) { /* ignore */ }

      renderGapsForDay(i, col, byDayAll[i]);

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
