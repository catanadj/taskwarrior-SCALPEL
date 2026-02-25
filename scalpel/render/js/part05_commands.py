# scalpel/render/js/part05_commands.py
from __future__ import annotations

JS_PART = r'''// Commands (diff-only schedule + actions)
  // -----------------------------
  function getIdentifier(t) {
    return (t.uuid || "").slice(0,8);
  }

  function buildScheduleCommands() {
    const cmds = [];
    for (const t of (DATA.tasks || [])) {
      const b = baseline.get(t.uuid) || { scheduled_ms: null, due_ms: null };
      const cur = plan.get(t.uuid) || { scheduled_ms: null, due_ms: null, dur_ms: DEFAULT_DUR * 60000 };
      const bd = baselineDur.get(t.uuid) ?? (DEFAULT_DUR * 60000);

      const changed = (cur.due_ms !== b.due_ms) || (cur.scheduled_ms !== b.scheduled_ms) || (cur.dur_ms !== bd);
      if (!changed) continue;

      if (!Number.isFinite(cur.due_ms) || !Number.isFinite(cur.dur_ms) || cur.dur_ms <= 0) continue;

      const schMs = cur.due_ms - cur.dur_ms;
      if (!Number.isFinite(schMs) || cur.due_ms <= schMs) continue;

      const ident = getIdentifier(t);
      const sch = formatLocalNoOffset(schMs);
      const due = formatLocalNoOffset(cur.due_ms);
      const durMin = Math.max(1, Math.round(cur.dur_ms / 60000));

      cmds.push({ when: schMs, line: `task ${ident} modify scheduled:${sch} due:${due} duration:${durMin}min` });
    }
    cmds.sort((a,b) => a.when - b.when);
    return cmds.map(x => x.line);
  }

  const planTaskUpdates = Object.create(null); // uuid -> patch

  function buildPlanResult() {
    const overrides = {};
    const added = [];
    for (const t of (DATA.tasks || [])) {
      if (!t || !t.uuid) continue;
      const b = baseline.get(t.uuid) || { scheduled_ms: null, due_ms: null };
      const cur = plan.get(t.uuid) || { scheduled_ms: null, due_ms: null, dur_ms: DEFAULT_DUR * 60000 };
      const bd = baselineDur.get(t.uuid) ?? (DEFAULT_DUR * 60000);

      const changed = (cur.due_ms !== b.due_ms) || (cur.scheduled_ms !== b.scheduled_ms) || (cur.dur_ms !== bd);
      if (!changed && !t.local) continue;

      if (!Number.isFinite(cur.due_ms) || !Number.isFinite(cur.dur_ms) || cur.dur_ms <= 0) continue;
      const schMs = cur.due_ms - cur.dur_ms;
      if (!Number.isFinite(schMs) || cur.due_ms <= schMs) continue;

      const durMin = Math.max(1, Math.round(cur.dur_ms / 60000));
      overrides[t.uuid] = {
        start_ms: Math.round(schMs),
        due_ms: Math.round(cur.due_ms),
        duration_min: durMin,
      };

      if (t.local) {
        added.push({
          uuid: t.uuid,
          description: String(t.description || ""),
          status: "pending",
          tags: Array.isArray(t.tags) ? t.tags : [],
          project: String(t.project || ""),
          scheduled_ms: Math.round(schMs),
          due_ms: Math.round(cur.due_ms),
          duration_min: durMin,
        });
      }
    }

    return {
      schema: "scalpel.plan.v1",
      overrides,
      added_tasks: added,
      task_updates: planTaskUpdates,
      warnings: [],
      notes: [],
      model_id: "ui-manual",
    };
  }

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
    }catch(e){ console.error("Plan export failed", e); }
  }

  function renderCommands() {
    const scheduleLines = buildScheduleCommands();

    // Local adds are rendered as `task add` lines derived from the current plan (so they stay correct if you move them).
    const localAddLines = localAdds.map(x => buildAddCommandForLocal(x.uuid, x.desc)).filter(Boolean);

    // Other queued actions are plain strings (done/delete/etc.)
    const actionLines = localAddLines.concat(actionQueue.slice());

    const blocks = [];
    blocks.push(`# Schedule changes (${scheduleLines.length})`);
    blocks.push(scheduleLines.length ? scheduleLines.join("\n") : "# None");
    blocks.push("");
    blocks.push(`# Actions (${actionLines.length})`);
    blocks.push(actionLines.length ? actionLines.join("\n") : "# None");

    elCommands.textContent = blocks.join("\n");
    elCmdCount.textContent = `${scheduleLines.length + actionLines.length} total`;
    if (typeof globalThis.__scalpel_updateActionButtonStates === "function") {
      try { globalThis.__scalpel_updateActionButtonStates(); } catch (_) {}
    }

    const hint = "Review, then paste into your shell.";
    const cur = String((elStatus && elStatus.textContent) || "").trim();
    if (!cur) elStatus.textContent = hint;
  }

  const elBtnExportPlan = document.getElementById("btnExportPlan");
  if (elBtnExportPlan) elBtnExportPlan.addEventListener("click", () => {
    const plan = buildPlanResult();
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    _downloadJSON(plan, `scalpel-plan-${stamp}.json`);
  });

  function _applyPlanOverridesToUI(overrides) {
    if (!overrides || typeof overrides !== "object") return;
    const valid = new Set();
    try {
      for (const t of (DATA.tasks || [])) {
        if (t && t.uuid) valid.add(String(t.uuid));
      }
    } catch (_) {}
    for (const [uuid, ov] of Object.entries(overrides)) {
      if (!uuid || (valid.size && !valid.has(uuid))) continue;
      if (!ov || typeof ov !== "object") continue;
      const startMs = Number(ov.start_ms);
      const dueMs = Number(ov.due_ms);
      const durMin = Number.isFinite(Number(ov.duration_min)) ? Number(ov.duration_min) : null;
      if (!Number.isFinite(startMs) || !Number.isFinite(dueMs) || dueMs <= startMs) continue;
      const durMs = (durMin && durMin > 0) ? Math.round(durMin * 60000) : Math.round(dueMs - startMs);
      plan.set(uuid, { scheduled_ms: startMs, due_ms: dueMs, dur_ms: durMs });
      __scalpelDropEffectiveIntervalCache(uuid);
    }
  }

  function _addTaskFromPlan(t, ov) {
    if (!t || typeof t !== "object") return;
    const uuid = String(t.uuid || "");
    if (!uuid || tasksByUuid.has(uuid)) return;

    const desc = String(t.description || "").trim();
    if (!desc) return;

    const startMs = Number(ov && ov.start_ms);
    const dueMs = Number(ov && ov.due_ms);
    const durMin = Number.isFinite(Number(ov && ov.duration_min)) ? Number(ov.duration_min) : null;
    if (!Number.isFinite(startMs) || !Number.isFinite(dueMs) || dueMs <= startMs) return;

    const durMs = (durMin && durMin > 0) ? Math.round(durMin * 60000) : Math.round(dueMs - startMs);
    if (!Number.isFinite(durMs) || durMs <= 0) return;

    const task = {
      uuid,
      id: null,
      description: desc,
      project: String(t.project || ""),
      tags: Array.isArray(t.tags) ? t.tags : [],
      scheduled_ms: Math.round(startMs),
      due_ms: Math.round(dueMs),
      duration_min: Math.max(1, Math.round(durMs / 60000)),
      local: true,
    };

    if (typeof __scalpelIndexTaskForSearch === "function") __scalpelIndexTaskForSearch(task);
    DATA.tasks.push(task);
    tasksByUuid.set(uuid, task);
    baseline.set(uuid, { scheduled_ms: task.scheduled_ms, due_ms: task.due_ms });
    baselineDur.set(uuid, durMs);
    plan.set(uuid, { scheduled_ms: task.scheduled_ms, due_ms: task.due_ms, dur_ms: durMs });
    __scalpelDropEffectiveIntervalCache(uuid);
    localAdds.push({ uuid, desc });
  }

  function _applyPlanResultToUI(planObj) {
    if (!planObj || typeof planObj !== "object") return;
    const overrides = planObj.overrides || {};
    const added = Array.isArray(planObj.added_tasks) ? planObj.added_tasks : [];
    const updates = planObj.task_updates || {};

    for (const [uuid, patch] of Object.entries(updates)) {
      if (!uuid) continue;
      const t = tasksByUuid.get(uuid);
      if (!t || !patch || typeof patch !== "object") continue;
      for (const [k, v] of Object.entries(patch)) {
        if (k === "uuid") continue;
        t[k] = v;
      }
      if (typeof __scalpelIndexTaskForSearch === "function") __scalpelIndexTaskForSearch(t);
      planTaskUpdates[uuid] = Object.assign({}, planTaskUpdates[uuid] || {}, patch);

      // If updates include schedule-like fields, reflect them in plan.
      const startMs = Number(patch.start_calc_ms ?? patch.scheduled_ms);
      const dueMs = Number(patch.end_calc_ms ?? patch.due_ms);
      const durMin = Number.isFinite(Number(patch.duration_min)) ? Number(patch.duration_min) : null;
      if (Number.isFinite(startMs) && Number.isFinite(dueMs) && dueMs > startMs) {
        const durMs = (durMin && durMin > 0) ? Math.round(durMin * 60000) : Math.round(dueMs - startMs);
        plan.set(uuid, { scheduled_ms: startMs, due_ms: dueMs, dur_ms: durMs });
        __scalpelDropEffectiveIntervalCache(uuid);
      }
    }

    for (const t of added) {
      const u = t && t.uuid ? String(t.uuid) : "";
      _addTaskFromPlan(t, overrides[u]);
    }

    _applyPlanOverridesToUI(overrides);
    try { setRangeMeta(); } catch (_) {}
    try { updateSelectionMeta(); } catch (_) {}
    try { rerenderAll(); } catch (_) {}
  }

  const elBtnImportPlan = document.getElementById("btnImportPlan");
  const elPlanImportFile = document.getElementById("planImportFile");
  if (elBtnImportPlan && elPlanImportFile) elBtnImportPlan.addEventListener("click", () => {
    try { elPlanImportFile.value = ""; } catch (_) {}
    elPlanImportFile.click();
  });
  if (elPlanImportFile) elPlanImportFile.addEventListener("change", async () => {
    try{
      const f = (elPlanImportFile.files && elPlanImportFile.files[0]) ? elPlanImportFile.files[0] : null;
      if (!f) return;
      const txt = await f.text();
      const parsed = JSON.parse(txt);
      _applyPlanResultToUI(parsed);
    }catch(e){
      console.error("Plan import failed", e);
      alert("Plan import failed. Please ensure the file is valid JSON.");
    }
  });

  const elAiModal = document.getElementById("aiPlanModal");
  const elAiClose = document.getElementById("aiPlanClose");
  const elBtnAiPlan = document.getElementById("btnAiPlan");
  const elAiPrompt = document.getElementById("aiPrompt");
  const elAiStatus = document.getElementById("aiStatus");
  const elAiPreview = document.getElementById("aiPreview");
  const elAiBaseUrl = document.getElementById("aiBaseUrl");
  const elAiModel = document.getElementById("aiModel");
  const elAiTemp = document.getElementById("aiTemp");
  const elAiShowRequest = document.getElementById("aiShowRequest");
  const elAiRun = document.getElementById("aiPlanRun");
  const elAiApply = document.getElementById("aiPlanApply");

  let lastAiPlan = null;
  let lastAiSelected = null;
  let lastAiSelectedFull = null;
  let lastAiUuidMap = null;

  function openAiPlanModal() {
    if (!elAiModal) return;
    elAiModal.style.display = "flex";
    if (elAiStatus) elAiStatus.textContent = "";
    if (elAiPreview) elAiPreview.textContent = "";
  }

  function closeAiPlanModal() {
    if (!elAiModal) return;
    elAiModal.style.display = "none";
  }

  function _aiPlanSchema() {
    return {
      name: "scalpel_plan_v2",
      strict: true,
          schema: {
            type: "object",
            additionalProperties: true,
            properties: {
              schema: { type: "string", const: "scalpel.plan.v2" },
              ops: {
                type: "array",
                items: {
                  type: "object",
                  additionalProperties: false,
                  properties: {
                    op: { type: "string", enum: ["place"] },
                    target: { type: "string" },
                    start_iso: { type: "string" },
                    due_iso: { type: "string" }
                  },
                  required: ["op", "target", "start_iso", "due_iso"]
                }
              },
              reasoning: { type: "object" },
              confidence: { type: "number" },
              ambiguities: { type: "array", items: { type: "string" } },
              suggestions: { type: "array", items: { type: "string" } },
              warnings: { type: "array", items: { type: "string" } },
              alternatives: { type: "array", items: { type: "string" } },
              notes: { type: "array", items: { type: "string" } },
              model_id: { type: ["string", "null"] }
            },
            required: ["schema", "ops"]
          }
    };
  }

  function _fixJsonText(raw) {
    let s = String(raw || "");
    s = s.replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
    s = s.replace(/,\s*([}\]])/g, "$1");

    let out = "";
    let inStr = false;
    let esc = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (inStr) {
        if (esc) {
          out += ch;
          esc = false;
          continue;
        }
        if (ch === "\\") {
          out += ch;
          esc = true;
          continue;
        }
        if (ch === "\"") {
          out += ch;
          inStr = false;
          continue;
        }
        if (ch === "\n" || ch === "\r") {
          out += "\\n";
          continue;
        }
        if (ch === "\t") {
          out += "\\t";
          continue;
        }
        out += ch;
        continue;
      }
      if (ch === "\"") {
        out += ch;
        inStr = true;
        continue;
      }
      out += ch;
    }
    return out;
  }

  function _extractJsonFromText(text) {
    const t = String(text || "").trim();
    try { return JSON.parse(t); } catch (_) {}
    const fence = /```(?:json)?\s*([\s\S]*?)```/i.exec(t);
    if (fence && fence[1]) {
      const inner = fence[1].trim();
      try { return JSON.parse(inner); } catch (_) {}
      const fixed = _fixJsonText(inner);
      return JSON.parse(fixed);
    }
    function firstBalancedObject(s) {
      let start = -1;
      let depth = 0;
      let inStr = false;
      let esc = false;
      for (let i = 0; i < s.length; i++) {
        const ch = s[i];
        if (inStr) {
          if (esc) { esc = false; continue; }
          if (ch === "\\") { esc = true; continue; }
          if (ch === "\"") { inStr = false; continue; }
          continue;
        }
        if (ch === "\"") { inStr = true; continue; }
        if (ch === "{") {
          if (depth === 0) start = i;
          depth += 1;
          continue;
        }
        if (ch === "}") {
          if (depth > 0) depth -= 1;
          if (depth === 0 && start >= 0) return s.slice(start, i + 1);
        }
      }
      return null;
    }
    const raw = firstBalancedObject(t);
    if (!raw) throw new Error("No JSON object found");
    try { return JSON.parse(raw); } catch (_) {}
    const fixed = _fixJsonText(raw);
    return JSON.parse(fixed);
  }

  function _salvagePlanFromText(text) {
    const t = String(text || "");
    const ops = [];
    const re = /"op"\s*:\s*"place"/g;
    const positions = [];
    let m;
    while ((m = re.exec(t)) !== null) {
      positions.push(m.index);
    }
    for (let i = 0; i < positions.length; i++) {
      const start = positions[i];
      const end = (i + 1 < positions.length) ? positions[i + 1] : t.length;
      const chunk = t.slice(start, end);
      const mTarget = /"(target|uuid)"\s*:\s*"([^"]+)"/.exec(chunk);
      const mStartIso = /"start_iso"\s*:\s*"([^"]+)"/.exec(chunk);
      const mDueIso = /"due_iso"\s*:\s*"([^"]+)"/.exec(chunk);
      const mStartYmd = /"start_ymd"\s*:\s*"([^"]+)"/.exec(chunk);
      const mStartMin = /"start_min"\s*:\s*(\d+)/.exec(chunk);
      const mDurMin = /"duration_min"\s*:\s*(\d+)/.exec(chunk);

      const target = mTarget ? mTarget[2] : "";
      if (!target) continue;

      let startIso = mStartIso ? mStartIso[1] : "";
      let dueIso = mDueIso ? mDueIso[1] : "";

      if ((!startIso || !dueIso) && mStartYmd && mStartMin && mDurMin) {
        const ymd = mStartYmd[1];
        const startMin = parseInt(mStartMin[1], 10);
        const durMin = parseInt(mDurMin[1], 10);
        if (Number.isFinite(startMin) && Number.isFinite(durMin)) {
          const hh = pad2(Math.floor(startMin / 60));
          const mm = pad2(startMin % 60);
          startIso = `${ymd}T${hh}:${mm}`;
          const dueMs = parseLocalNoOffset(startIso) + (durMin * 60000);
          if (Number.isFinite(dueMs)) {
            dueIso = formatLocalNoOffset(dueMs);
          }
        }
      }

      if (!startIso || !dueIso) continue;
      ops.push({ op: "place", target, start_iso: startIso, due_iso: dueIso });
    }

    if (!ops.length) return null;
    return { schema: "scalpel.plan.v2", ops };
  }

  function _aiSelectedTasks() {
    const uuids = getSelectedAnyUuids();
    const out = [];
    for (const u of uuids) {
      const t = tasksByUuid.get(u);
      if (!t) continue;
      const cur = plan.get(u) || {};
      const b = baseline.get(u) || {};
      const durMs = Number.isFinite(cur.dur_ms) ? cur.dur_ms : (baselineDur.get(u) ?? (DEFAULT_DUR * 60000));
      const dueMs = Number.isFinite(cur.due_ms) ? cur.due_ms : (Number.isFinite(b.due_ms) ? b.due_ms : null);
      const startMs = Number.isFinite(dueMs) ? (dueMs - durMs) : (Number.isFinite(cur.scheduled_ms) ? cur.scheduled_ms : b.scheduled_ms);
      out.push({
        uuid: u,
        description: t.description,
        status: t.status,
        project: t.project,
        tags: t.tags,
        scheduled_ms: Number.isFinite(startMs) ? Math.round(startMs) : null,
        due_ms: Number.isFinite(dueMs) ? Math.round(dueMs) : null,
        duration_min: Number.isFinite(durMs) ? Math.max(1, Math.round(durMs / 60000)) : null,
        start_calc_ms: Number.isFinite(startMs) ? Math.round(startMs) : null,
        end_calc_ms: Number.isFinite(dueMs) ? Math.round(dueMs) : null
      });
    }
    return { uuids, tasks: out };
  }

  function _buildAiPayload(sel, prompt, maxLen) {
    const cfg = DATA.cfg || {};
    const nowMs = Date.now();
    const todayYmd = ymdFromMs(nowMs);

    let minimalTasks = false;

    function buildUuidMap(uuids) {
      const shortToFull = {};
      const fullToShort = {};
      const list = Array.isArray(uuids) ? uuids.slice() : [];
      const len = 8;
      for (const u of list) {
        const s = String(u).slice(0, len);
        if (shortToFull[s] && shortToFull[s] !== u) {
          return { shortToFull: {}, fullToShort: {}, shortLen: 36 };
        }
        shortToFull[s] = u;
        fullToShort[u] = s;
      }
      return { shortToFull, fullToShort, shortLen: len };
    }

    const uuidMap = buildUuidMap(sel.uuids);

    function buildTasks() {
      return sel.tasks.map(t => {
        const short = uuidMap.fullToShort[t.uuid] || t.uuid;
        if (minimalTasks) {
          return { uuid: short, description: t.description };
        }
        const out = {
          uuid: short,
          description: t.description,
          status: t.status,
          project: t.project,
          tags: t.tags,
          duration_min: t.duration_min
        };
        if (Number.isFinite(t.scheduled_ms)) out.scheduled_iso = formatLocalNoOffset(t.scheduled_ms);
        if (Number.isFinite(t.due_ms)) out.due_iso = formatLocalNoOffset(t.due_ms);
        return out;
      });
    }

    function buildPayload(busyData) {
      const payload = {
        instruction: (
          "Return ONLY JSON matching the plan v2 schema. Use schema 'scalpel.plan.v2'. " +
          "Only allowed op is 'place'. Do NOT use JSON Patch or any other op types. " +
          "Use only place ops for existing tasks. You may return ops for only a subset of selected_uuids. " +
          "Each place must include target, start_iso, due_iso (YYYY-MM-DDTHH:MM). " +
          "Do NOT use start_ymd/start_min/duration_min. " +
          "Choose times that avoid busy blocks (busy_by_day) and respect work hours. " +
          "Use the 8-char short task IDs provided in selected_uuids and tasks. " +
          "Include reasoning, confidence, ambiguities, and suggestions to explain interpretation and tradeoffs. " +
          "If the request is unclear, no valid time slots exist, or multiple interpretations exist, " +
          "return an empty ops list and include warnings and/or alternatives arrays explaining why."
        ),
        schema: "scalpel.plan.v2",
        selected_uuids: sel.uuids.map(u => uuidMap.fullToShort[u] || u),
        now_ms: Math.round(nowMs),
        today_ymd: String(todayYmd),
        now_iso: formatLocalNoOffset(nowMs),
        view_range: {
          start_ymd: ymdFromMs(dayStarts[0]),
          end_ymd: ymdFromMs(dayStarts[dayStarts.length - 1])
        },
        cfg: {
          tz: cfg.tz,
          display_tz: cfg.display_tz,
          work_start_min: cfg.work_start_min,
          work_end_min: cfg.work_end_min,
          snap_min: cfg.snap_min,
          default_duration_min: cfg.default_duration_min,
          max_infer_duration_min: cfg.max_infer_duration_min
        },
        tasks: buildTasks(),
        busy_by_day: busyData.busyByDay,
        uuid_format: "short",
        uuid_short_len: uuidMap.shortLen,
        user_prompt: prompt,
        output_example: {
          schema: "scalpel.plan.v2",
          ops: [
            {
              op: "place",
              target: "<uuid>",
              start_iso: "YYYY-MM-DDTHH:MM",
              due_iso: "YYYY-MM-DDTHH:MM"
            }
          ],
          reasoning: {
            understanding: "One-line summary of the request",
            interpretation: {
              target_date: "YYYY-MM-DD",
              time_of_day: "morning|afternoon|evening",
              affected_tasks: [
                { uuid: "<uuid>", match_reason: "why this task was chosen" }
              ]
            },
            constraints_applied: ["work hours", "busy blocks", "snap_min"],
            decisions: [
              { uuid: "<uuid>", scheduled_at: "YYYY-MM-DDTHH:MM", rationale: "why this slot" }
            ],
            alternatives_considered: [
              { option: "brief alternative", rejected_because: "why not chosen" }
            ]
          },
          confidence: 0.7,
          ambiguities: [],
          suggestions: [],
          warnings: [],
          alternatives: [],
          notes: []
        }
      };
      return payload;
    }

    let busyData = _buildBusyByDayForSelection(sel.uuids);
    let payload = buildPayload(busyData);
    let text = JSON.stringify(payload);

    if (text.length > maxLen && !minimalTasks) {
      minimalTasks = true;
      payload = buildPayload(busyData);
      text = JSON.stringify(payload);
    }

    if (text.length > maxLen) {
      payload.busy_by_day = {};
      text = JSON.stringify(payload);
    }

    return { payload, busyData, uuidMap, textLen: text.length };
  }

  async function runAiPlan() {
    if (!elAiStatus || !elAiPreview) return;
    const sel = _aiSelectedTasks();
    if (!sel.uuids.length) {
      elAiStatus.textContent = "Select tasks first.";
      return;
    }

    const baseUrl = (elAiBaseUrl && elAiBaseUrl.value) ? String(elAiBaseUrl.value).trim() : "http://127.0.0.1:1234";
    const model = (elAiModel && elAiModel.value) ? String(elAiModel.value).trim() : "ministral-3-14b-reasoning";
    const temp = elAiTemp && elAiTemp.value !== "" ? Number(elAiTemp.value) : 0.2;
    const prompt = elAiPrompt ? String(elAiPrompt.value || "") : "";

    const built = _buildAiPayload(sel, prompt, 10000);
    const payload = built.payload;

    const body = {
      model,
      messages: [
        { role: "system", content: "You are a scheduling assistant that outputs strict JSON only." },
        { role: "user", content: JSON.stringify(payload, null, 2) }
      ],
      temperature: Number.isFinite(temp) ? temp : 0.2,
      max_tokens: 1200,
      response_format: { type: "json_schema", json_schema: _aiPlanSchema() }
    };

    elAiStatus.textContent = "Running...";
    elAiPreview.textContent = "";
    if (elAiShowRequest && elAiShowRequest.checked) {
      elAiPreview.textContent = JSON.stringify(payload, null, 2);
    }

    try {
      const res = await fetch(baseUrl.replace(/\/+$/, "") + "/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }
      const data = await res.json();
      const choices = data && data.choices ? data.choices : [];
      const msg = choices[0] && choices[0].message ? choices[0].message : null;
      const content = msg && typeof msg.content === "string" ? msg.content : "";
      if (!content || !content.trim()) {
        elAiPreview.textContent = "Empty model response. Raw response:\n" + JSON.stringify(data, null, 2);
        throw new Error("Empty model response");
      }
      let plan = null;
      try {
        plan = _extractJsonFromText(content);
      } catch (e) {
        plan = _salvagePlanFromText(content);
        if (!plan) {
          elAiPreview.textContent = String(content || "");
          throw e;
        }
      }
      const result = _computePlanV2Changes(plan);
      if (result.errs.length) {
        elAiPreview.textContent = "Received plan:\n" + JSON.stringify(plan, null, 2) +
          "\n\nErrors:\n- " + result.errs.join("\n- ") +
          (result.warns && result.warns.length ? ("\n\nWarnings:\n- " + result.warns.join("\n- ")) : "");
        elAiStatus.textContent = "Invalid plan. Fix prompt or model.";
        return;
      }

      lastAiPlan = plan;
      lastAiSelected = Array.isArray(payload.selected_uuids) ? payload.selected_uuids.slice() : null;
      lastAiSelectedFull = Array.isArray(sel.uuids) ? sel.uuids.slice() : null;
      lastAiUuidMap = built.uuidMap || null;
      const computedData = _changesWithIso(result.changes || {});
      const warn = Array.isArray(plan.warnings) ? plan.warnings : [];
      const alts = Array.isArray(plan.alternatives) ? plan.alternatives : [];
      const warn2 = result.warns || [];
      const ambiguities = Array.isArray(plan.ambiguities) ? plan.ambiguities : [];
      const suggestions = Array.isArray(plan.suggestions) ? plan.suggestions : [];
      const confidence = typeof plan.confidence === "number" ? plan.confidence : null;
      const reasoning = plan.reasoning && typeof plan.reasoning === "object" ? plan.reasoning : null;
      elAiPreview.textContent = "Received plan:\n" + JSON.stringify(plan, null, 2) +
        "\n\nComputed changes:\n" + JSON.stringify(computedData, null, 2) +
        ((warn.length || warn2.length) ? ("\n\nWarnings:\n- " + warn.concat(warn2).join("\n- ")) : "") +
        (alts.length ? ("\n\nAlternatives:\n- " + alts.join("\n- ")) : "") +
        (ambiguities.length ? ("\n\nAmbiguities:\n- " + ambiguities.join("\n- ")) : "") +
        (suggestions.length ? ("\n\nSuggestions:\n- " + suggestions.join("\n- ")) : "") +
        (confidence !== null ? ("\n\nConfidence: " + String(confidence)) : "") +
        (reasoning ? ("\n\nReasoning:\n" + JSON.stringify(reasoning, null, 2)) : "");
      elAiStatus.textContent = "Plan ready. Review then apply.";
    } catch (e) {
      console.error("AI plan failed", e);
      elAiStatus.textContent = "AI plan failed. Check console for details.";
    }
  }

  function _changesWithIso(changes) {
    const out = {};
    for (const u of Object.keys(changes || {})) {
      const c = changes[u] || {};
      const schedMs = Number.isFinite(c.scheduledMs) ? Math.round(c.scheduledMs) : null;
      const dueMs = Number.isFinite(c.dueMs) ? Math.round(c.dueMs) : null;
      const durMs = Number.isFinite(c.durMs) ? Math.round(c.durMs) : null;
      out[u] = {
        scheduled_ms: schedMs,
        due_ms: dueMs,
        dur_ms: durMs,
        scheduled_iso: Number.isFinite(schedMs) ? formatLocalNoOffset(schedMs) : null,
        due_iso: Number.isFinite(dueMs) ? formatLocalNoOffset(dueMs) : null
      };
    }
    return out;
  }

  function _unionIntervals(intervals) {
    if (!intervals.length) return [];
    const sorted = intervals.slice().sort((a, b) => a[0] - b[0]);
    const out = [];
    let cur = [sorted[0][0], sorted[0][1]];
    for (let i = 1; i < sorted.length; i++) {
      const iv = sorted[i];
      if (iv[0] <= cur[1]) {
        cur[1] = Math.max(cur[1], iv[1]);
      } else {
        out.push(cur);
        cur = [iv[0], iv[1]];
      }
    }
    out.push(cur);
    return out;
  }

  function _buildBusyByDayForSelection(selectedUuids) {
    const selected = new Set(selectedUuids || []);
    const busy = [];
    for (const [u, t] of tasksByUuid.entries()) {
      if (!u || selected.has(u)) continue;
      const st = String(t && t.status ? t.status : "").toLowerCase();
      if (st === "completed" || st === "deleted") continue;
      const eff = effectiveInterval(u);
      if (!eff) continue;
      busy.push([eff.startMs, eff.dueMs]);
    }
    const busyUnion = _unionIntervals(busy);

    const busyByDay = new Map();
    for (let i = 0; i < dayStarts.length; i++) {
      const dayStart = dayStarts[i];
      const w0 = dayStart + (WORK_START * 60000);
      const w1 = dayStart + (WORK_END * 60000);
      if (w1 <= w0) continue;

      const blocks = [];
      for (const iv of busyUnion) {
        if (iv[1] <= w0) continue;
        if (iv[0] >= w1) break;
        blocks.push([Math.max(iv[0], w0), Math.min(iv[1], w1)]);
      }
      const dayKey = ymdFromMs(dayStart);
      const slim = blocks.slice(0, 80).map(iv => ({
        start_iso: formatLocalNoOffset(iv[0]),
        due_iso: formatLocalNoOffset(iv[1])
      }));
      busyByDay.set(dayKey, slim);
    }

    const busyByDayObj = {};
    for (const [k, v] of busyByDay.entries()) busyByDayObj[k] = v;
    return { busyByDay: busyByDayObj };
  }

  function _computePlanV2Changes(plan) {
    const errs = [];
    const changes = {};
    const warns = [];
    if (!plan || typeof plan !== "object") {
      return { errs: ["plan must be an object"], changes };
    }
    if (plan.schema && plan.schema !== "scalpel.plan.v2") {
      errs.push("schema must be scalpel.plan.v2");
    }

    const ops = plan.ops;
    if (!Array.isArray(ops)) {
      errs.push("ops must be a list");
      return { errs, changes };
    }

    const selected = new Set(Array.isArray(lastAiSelected) ? lastAiSelected : getSelectedAnyUuids());
    const selectedFull = new Set(Array.isArray(lastAiSelectedFull) ? lastAiSelectedFull : getSelectedAnyUuids());
    for (const op of ops) {
      if (!op || typeof op !== "object") {
        errs.push("ops entries must be objects");
        continue;
      }
      const kind = typeof op.op === "string" ? op.op : "";
      if (kind !== "place") {
        errs.push(`unsupported op: ${kind || "<missing>"}`);
        continue;
      }
      const rawTarget = typeof op.target === "string" ? op.target : (typeof op.uuid === "string" ? op.uuid : "");
      const targetRaw = rawTarget ? rawTarget.trim() : "";
      if (!targetRaw) {
        errs.push("place must include target");
        continue;
      }
      let targetShort = targetRaw;
      let targetFull = targetRaw;
      if (lastAiUuidMap && typeof lastAiUuidMap === "object") {
        const s2f = lastAiUuidMap.shortToFull || {};
        const f2s = lastAiUuidMap.fullToShort || {};
        if (s2f[targetRaw]) {
          targetShort = targetRaw;
          targetFull = s2f[targetRaw];
        } else if (f2s[targetRaw]) {
          targetShort = f2s[targetRaw];
          targetFull = targetRaw;
        }
      } else if (targetRaw.length === 8) {
        const matches = Array.from(selectedFull).filter(u => String(u).startsWith(targetRaw));
        if (matches.length === 1) {
          targetFull = matches[0];
          targetShort = targetRaw;
        }
      }
      if (!selected.has(targetShort) && !selectedFull.has(targetFull)) {
        warns.push(`place target not selected: ${targetRaw}`);
        continue;
      }
      let startMs = NaN;
      let dueMs = NaN;
      const startIso = typeof op.start_iso === "string" ? op.start_iso : "";
      const dueIso = typeof op.due_iso === "string" ? op.due_iso : "";
      if (!startIso || !dueIso) {
        errs.push("place must include start_iso and due_iso");
        continue;
      }
      startMs = parseLocalNoOffset(startIso);
      dueMs = parseLocalNoOffset(dueIso);
      if (!Number.isFinite(startMs) || !Number.isFinite(dueMs)) {
        errs.push(`invalid time for target: ${targetRaw}`);
        continue;
      }
      if (dueMs <= startMs) {
        errs.push(`due must be after start for target: ${targetRaw}`);
        continue;
      }
      changes[targetFull] = {
        scheduledMs: Math.round(startMs),
        dueMs: Math.round(dueMs),
        durMs: Math.round(dueMs - startMs)
      };
    }

    if (!Object.keys(changes).length && warns.length) {
      errs.push("no valid place ops after filtering");
    }
    return { errs, warns, changes };
  }

  function _applyPlanV2(plan) {
    const result = _computePlanV2Changes(plan);
    if (result.errs.length) return false;
    commitPlanMany(result.changes || {});
    return true;
  }

  function applyAiPlan() {
    if (!lastAiPlan) {
      if (elAiStatus) elAiStatus.textContent = "No plan to apply.";
      return;
    }
    const ok = _applyPlanV2(lastAiPlan);
    if (elAiStatus) elAiStatus.textContent = ok ? "Plan applied." : "Invalid plan. Nothing applied.";
  }

  if (elBtnAiPlan) elBtnAiPlan.addEventListener("click", openAiPlanModal);
  if (elAiClose) elAiClose.addEventListener("click", closeAiPlanModal);
  if (elAiModal) elAiModal.addEventListener("click", (ev) => { if (ev.target === elAiModal) closeAiPlanModal(); });
  if (elAiRun) elAiRun.addEventListener("click", runAiPlan);
  if (elAiApply) elAiApply.addEventListener("click", applyAiPlan);

// -----------------------------
  // Commit (batch)
  // -----------------------------
  function commitPlanMany(changes) {
    const uuids = Object.keys(changes || {});
    if (!uuids.length) return;

    let applied = 0;
    let skipped = 0;
    let outOfView = 0;

    const valid = {};
    for (const uuid of uuids) {
      const ch = changes[uuid];
      if (!tasksByUuid.has(uuid)) { skipped++; continue; }
      if (!Number.isFinite(ch.scheduledMs) || !Number.isFinite(ch.dueMs) || ch.dueMs <= ch.scheduledMs) { skipped++; continue; }
      if (!Number.isFinite(ch.durMs) || ch.durMs <= 0) { skipped++; continue; }
      if (startOfLocalDayMs(ch.scheduledMs) !== startOfLocalDayMs(ch.dueMs)) { skipped++; continue; }

      const di = dayIndexFromMs(ch.dueMs);
      if (di === null) { outOfView++; }

      const sMin = minuteOfDayFromMs(ch.scheduledMs);
      const dMin = minuteOfDayFromMs(ch.dueMs);
      if (sMin < WORK_START || dMin > WORK_END) { skipped++; continue; }

      valid[uuid] = ch;
    }

    for (const uuid of Object.keys(valid)) {
      const ch = valid[uuid];
      plan.set(uuid, { scheduled_ms: ch.scheduledMs, due_ms: ch.dueMs, dur_ms: ch.durMs });
      __scalpelDropEffectiveIntervalCache(uuid);
      applied++;
    }

    if (applied) saveEdits();
    rerenderAll();
    if (applied) { try{ setTimeout(() => pulseTasks(Object.keys(valid)), 0); }catch(e){} }

    if (skipped && applied) elStatus.textContent = `Applied ${applied} change(s); skipped ${skipped} (invalid).`;
    else if (skipped && !applied) elStatus.textContent = `No changes applied (all ${skipped} invalid).`;
    else if (outOfView) elStatus.textContent = `Applied ${applied} change(s); ${outOfView} out of view.`;
  }

  // -----------------------------
'''
