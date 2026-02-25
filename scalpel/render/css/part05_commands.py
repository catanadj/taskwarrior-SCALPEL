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
    elStatus.textContent = "Review, then paste into your shell.";
  }

// -----------------------------
  // Commit (batch)
  // -----------------------------
  function commitPlanMany(changes) {
    const uuids = Object.keys(changes || {});
    if (!uuids.length) return;

    let applied = 0;
    let skipped = 0;

    const valid = {};
    for (const uuid of uuids) {
      const ch = changes[uuid];
      if (!tasksByUuid.has(uuid)) { skipped++; continue; }
      if (!Number.isFinite(ch.scheduledMs) || !Number.isFinite(ch.dueMs) || ch.dueMs <= ch.scheduledMs) { skipped++; continue; }
      if (!Number.isFinite(ch.durMs) || ch.durMs <= 0) { skipped++; continue; }
      if (startOfLocalDayMs(ch.scheduledMs) !== startOfLocalDayMs(ch.dueMs)) { skipped++; continue; }

      const di = dayIndexFromMs(ch.dueMs);
      if (di === null) { skipped++; continue; }

      const sMin = minuteOfDayFromMs(ch.scheduledMs);
      const dMin = minuteOfDayFromMs(ch.dueMs);
      if (sMin < WORK_START || dMin > WORK_END) { skipped++; continue; }

      valid[uuid] = ch;
    }

    for (const uuid of Object.keys(valid)) {
      const ch = valid[uuid];
      plan.set(uuid, { scheduled_ms: ch.scheduledMs, due_ms: ch.dueMs, dur_ms: ch.durMs });
      applied++;
    }

    if (applied) saveEdits();
    rerenderAll();

    if (skipped && applied) elStatus.textContent = `Applied ${applied} change(s); skipped ${skipped} (out of bounds).`;
    else if (skipped && !applied) elStatus.textContent = `No changes applied (all ${skipped} out of bounds).`;
  }

  // -----------------------------
'''
