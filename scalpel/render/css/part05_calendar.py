# scalpel/render/css/part05_calendar.py
from __future__ import annotations

CSS_PART = r'''  .cal-wrap {
    display: grid;
    grid-template-columns: 68px 1fr;
    min-height: 0;
    height: 100%;
    background: var(--cal-surface);
  }

  .time-col {
    border-right: 1px solid var(--line);
    background:
      linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
      var(--cal-surface);
    position: relative;
  }
  .time-head {
    height: var(--day-header-h);
    border-bottom: 1px solid var(--line);
    background: var(--cal-surface);
  }
  .time-body {
    position: relative;
    height: calc(var(--cal-minutes) * var(--px-per-min) * 1px);
    will-change: transform;
  }
  .time-tick {
    position: absolute;
    left: 0;
    right: 0;
    height: 0;
    border-top: 2px solid var(--tick);
  }
  .time-tick .lbl {
    position: absolute;
    top: -10px;
    left: 8px;
    padding: 0 4px;
    font-size: 12px;
    color: var(--muted);
    background: var(--cal-surface);
    border-radius: 6px;
    letter-spacing: 0.2px;
  }

  .days-col { overflow: auto; position: relative; }
  .days-col.selecting { user-select: none; cursor: crosshair; }
  .days-header {
    position: sticky;
    top: 0;
    z-index: 5;
    display: grid;
    grid-template-columns: repeat(var(--days), 1fr);
    background:
      linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
      var(--cal-surface);
    border-bottom: 1px solid var(--line);
    height: var(--day-header-h);
    box-shadow: 0 5px 12px rgba(0,0,0,0.10);
  }
  .day-h {
    padding: 8px 10px;
    border-right: 1px solid rgba(38,49,65,0.35);
    font-weight: 680;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    height: var(--day-header-h);
    justify-content: center;
  }
  .day-h.weekend:not(.today){
    background:
      linear-gradient(180deg, var(--weekend-header-bg), rgba(0,0,0,0)),
      linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00));
    border-bottom: 1px solid var(--weekend-header-bd);
  }
  .day-h.today{
    background:
      linear-gradient(180deg, rgba(var(--warn-rgb), 0.26), rgba(0,0,0,0)),
      linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.00));
    border-bottom: 1px solid rgba(var(--warn-rgb), 0.54);
    box-shadow:
      inset 0 -1px 0 rgba(var(--warn-rgb), 0.35),
      0 0 0 1px rgba(var(--warn-rgb), 0.16);
  }
  .day-h.today .dtop { font-weight: 800; }
  .day-h.today .dtop span { color: rgba(var(--warn-rgb), 0.95); }
  .day-h.active-day:not(.today){
    background:
      linear-gradient(180deg, rgba(var(--accent-rgb), 0.20), rgba(0,0,0,0)),
      linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.00));
    border-bottom: 1px solid rgba(var(--accent-rgb), 0.50);
    box-shadow:
      inset 0 -1px 0 rgba(var(--accent-rgb), 0.30),
      0 0 0 1px rgba(var(--accent-rgb), 0.16);
  }
  .day-h.active-day .dtop{
    font-weight: 780;
  }
  .day-h.active-day .dtop span{
    color: rgba(var(--accent-rgb), 0.95);
  }
  .day-h.today.active-day{
    box-shadow:
      inset 0 -1px 0 rgba(var(--warn-rgb), 0.34),
      0 0 0 1px rgba(var(--warn-rgb), 0.18),
      0 0 0 2px rgba(var(--accent-rgb), 0.16);
  }
  .day-h .dtop { display:flex; justify-content:space-between; gap:8px; align-items:baseline; }
  .day-h .dtop span { color: var(--muted); font-weight: 500; font-size: 12px; }
  .day-h .loadrow { display:flex; gap:8px; align-items:center; min-width:0; }
  .loadbar {
    height: 8px;
    flex: 1;
    border-radius: 999px;
    border: 1px solid rgba(154,166,178,0.25);
    background: rgba(255,255,255,0.03);
    overflow: hidden;
    min-width: 60px;
  }
  .loadfill {
    height: 100%;
    width: 0%;
    background: var(--loadfill);
  }
  .loadfill.over { background: var(--loadfill-over); }
  .loadtxt {
    color: var(--muted);
    font-size: 12px;
    white-space: nowrap;
    flex: 0 0 auto;
  }

  .days-body {
    display: grid;
    grid-template-columns: repeat(var(--days), 1fr);
    height: calc(var(--cal-minutes) * var(--px-per-min) * 1px);
  }

  .day-col {
    position: relative;
    border-right: 1px solid rgba(38,49,65,0.35);
    background-color: rgba(255,255,255,0.01);
    background-image:
      linear-gradient(to bottom, var(--grid-hour) 2px, transparent 2px),
      linear-gradient(to bottom, var(--grid-qtr) 1px, transparent 1px);
    background-size:
      100% calc(var(--px-per-min) * 60px),
      100% calc(var(--px-per-min) * 15px);
    background-position:
      0 calc(-1 * var(--hour-shift)),
      0 calc(-1 * var(--qtr-shift));
    background-repeat: repeat;
    transition: background-color 120ms ease, box-shadow 120ms ease;
  }
  .day-col:hover{
    background-color: rgba(var(--accent-rgb), 0.04);
  }
  .day-col.weekend{
    background-color: var(--weekend-col-bg);
  }
  .day-col.weekend:hover{
    background-color: var(--weekend-col-hover-bg);
  }
  .day-col.active-day{
    box-shadow: inset 0 0 0 1px rgba(var(--accent-rgb), 0.30);
    background-color: rgba(var(--accent-rgb), 0.08);
  }
  .day-col.weekend.active-day{
    background-color: rgba(var(--accent-rgb), 0.10);
  }

  .day-col .drop-hint {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0;
    outline: 2px dashed rgba(99,179,255,0.7);
    outline-offset: -6px;
    border-radius: 10px;
    margin: 6px;
    transition: opacity 120ms ease;
  }
  .day-col.dragover .drop-hint { opacity: 1; }

  /* Free gap overlays */
  .gap {
    position: absolute;
    left: 6px;
    right: 6px;
    border-radius: 10px;
    border: 1px dashed var(--grid-hour);
    background: rgba(var(--accent-rgb),0.06);
    pointer-events: none;
    overflow: hidden;
  }
  .gap .gap-label {
    position: absolute;
    top: 6px;
    left: 8px;
    right: 8px;
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Now line */
  .now-line {
    position: absolute;
    left: 0;
    right: 0;
    height: 0;
    border-top: 2px solid var(--now-line);
    box-shadow:
      0 0 0 1px rgba(var(--warn-rgb), 0.22),
      0 0 8px var(--now-glow),
      0 0 12px rgba(var(--warn-rgb), 0.18);
    pointer-events: none;
    z-index: 4;
  }
  .now-line .now-label {
    position: absolute;
    right: 10px;
    top: -14px;
    font-size: 13px;
    font-weight: 700;
    color: rgba(var(--warn-rgb), 0.95);
    background: var(--now-label-bg);
    border: 1px solid rgba(var(--warn-rgb),0.40);
    border-radius: 999px;
    padding: 2px 10px;
    letter-spacing: 0.2px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.22);
  }

  /* Marquee */
  #marquee {
    position: fixed;
    pointer-events: none;
    z-index: 9999;
    border: 1px solid rgba(var(--accent-rgb), 0.90);
    background: rgba(var(--accent-rgb), 0.12);
    border-radius: 8px;
    display: none;
  }

  /* Task blocks */
  .evt {
    position: absolute;
    left: 6px;
    right: 6px;
    border-radius: 12px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.00)),
      linear-gradient(180deg, var(--block), var(--block2));
    border: 1px solid var(--task-border);
    border-left: 5px solid var(--evt-accent, rgba(var(--accent-rgb), 0.75));
    box-shadow:
      0 8px 14px rgba(0,0,0,0.20),
      0 1px 0 rgba(255,255,255,0.04) inset;
    outline: 1px solid rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.00);
    outline-offset: 0px;
    transition:
      outline-color var(--task-hover-ring-ms, 1250ms) cubic-bezier(0.19, 1, 0.22, 1),
      outline-offset var(--task-hover-ring-ms, 1250ms) cubic-bezier(0.19, 1, 0.22, 1),
      box-shadow var(--task-hover-ring-ms, 1250ms) cubic-bezier(0.19, 1, 0.22, 1),
      transform 150ms ease;
    overflow: hidden;
    user-select: none;
    touch-action: none;
  }
  /* Selected task: stronger visual affordance (ring + glow + slight lift)
     - designed to be easily trackable when keyboard-navigating
     - respects prefers-reduced-motion below
  */
  .evt.selected{
    outline: 2px solid var(--task-selected);
    outline-offset: -2px;
    box-shadow:
      0 0 0 1px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.55) inset,
      0 0 0 2px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.18),
      0 0 26px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.22),
      0 16px 26px rgba(0,0,0,0.32);
    transform: translateZ(0) scale(var(--task-selected-scale, 1.015));
  }
  .evt.selected:not(.dragging){
    animation: none;
  }

  .evt:not(.selected):not(.dragging):hover {
    outline-color: rgba(var(--evt-accent-rgb, var(--accent-rgb)), var(--task-hover-outline-alpha, 0.55));
    outline-offset: var(--task-hover-outline-offset, 15px);
    box-shadow:
      inset 0 0 20px rgba(var(--evt-accent-rgb, var(--accent-rgb)), var(--task-hover-inset-alpha, 0.50)),
      0 0 20px rgba(var(--evt-accent-rgb, var(--accent-rgb)), var(--task-hover-outer-alpha, 0.20)),
      0 10px 18px rgba(0,0,0,0.28);
  }

  /* Neon envelope for explicitly-colored tasks */
  .evt.user-colored {
    box-shadow:
      0 0 0 1px rgba(var(--evt-accent-rgb, 99,179,255), 0.65) inset,
      0 0 20px rgba(var(--evt-accent-rgb, 99,179,255), 0.25),
      0 12px 20px rgba(0,0,0,0.28);
    border-color: rgba(var(--evt-accent-rgb, 99,179,255), 0.40);
  }
  .evt.user-colored::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
      radial-gradient(120% 80% at 10% 10%, rgba(var(--evt-accent-rgb, 99,179,255), 0.18), transparent 60%),
      linear-gradient(180deg, rgba(var(--evt-accent-rgb, 99,179,255), 0.10), rgba(0,0,0,0));
    pointer-events: none;
  }

  .evt.nautical-preview{
    border-style: dashed;
    border-color: rgba(var(--warn-rgb), 0.55);
    background: linear-gradient(180deg, rgba(var(--warn-rgb), 0.10), rgba(0,0,0,0.18));
    box-shadow: 0 6px 12px rgba(0,0,0,0.18);
    opacity: 0.78;
    pointer-events: auto;
    cursor: context-menu;
  }
  .evt.nautical-preview .evt-title,
  .evt.nautical-preview .evt-time,
  .evt.nautical-preview .evt-bot,
  .evt.nautical-preview .evt-bot code {
    color: rgba(var(--warn-rgb), 0.95);
    text-shadow: 0 0 8px rgba(var(--warn-rgb), 0.85);
  }
  .evt.nautical-preview .evt-time .time-pill{
    color: rgba(var(--warn-rgb), 0.95);
    border-color: rgba(var(--warn-rgb), 0.45);
    background: rgba(var(--warn-rgb), 0.08);
  }
  .evt.nautical-preview .evt-sheen{ display: none; }
  .evt.nautical-preview .resize{ display: none; }
  .evt.nautical-preview.nautical-picked{
    border-style: solid;
    border-color: rgba(var(--accent-rgb), 0.92);
    border-left-color: rgba(var(--accent-rgb), 0.98);
    outline: 3px solid rgba(var(--accent-rgb), 0.62);
    outline-offset: -2px;
    background:
      linear-gradient(180deg, rgba(var(--accent-rgb), 0.22), rgba(var(--accent-rgb), 0.06)),
      linear-gradient(180deg, rgba(var(--warn-rgb), 0.12), rgba(0,0,0,0.16));
    box-shadow:
      0 0 0 2px rgba(var(--accent-rgb), 0.40) inset,
      0 0 26px rgba(var(--accent-rgb), 0.30),
      0 12px 22px rgba(0,0,0,0.30);
    opacity: 1;
  }
  .evt.nautical-preview.nautical-picked::after{
    content: "SELECTED";
    position: absolute;
    top: 0;
    right: 0;
    z-index: 5;
    padding: 2px 8px;
    border-bottom-left-radius: 9px;
    background: rgba(var(--accent-rgb), 0.98);
    color: rgba(8,14,18,0.98);
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 0.4px;
    text-shadow: none;
    pointer-events: none;
  }
  .evt.nautical-preview.nautical-picked .evt-title,
  .evt.nautical-preview.nautical-picked .evt-time,
  .evt.nautical-preview.nautical-picked .evt-bot,
  .evt.nautical-preview.nautical-picked .evt-bot code {
    color: var(--text);
    text-shadow: none;
  }
  .evt.nautical-preview.nautical-picked .evt-time .time-pill{
    border-color: rgba(var(--accent-rgb), 0.52);
    background: rgba(var(--accent-rgb), 0.16);
  }

  /* Preserve the user-colored neon envelope while also applying the hover ring */
  .evt.user-colored:not(.selected):not(.dragging):hover {
    outline-color: rgba(var(--evt-accent-rgb, var(--accent-rgb)), var(--task-hover-outline-alpha, 0.55));
    outline-offset: var(--task-hover-outline-offset, 15px);
    box-shadow:
      0 0 0 1px rgba(var(--evt-accent-rgb, 99,179,255), 0.65) inset,
      0 0 20px rgba(var(--evt-accent-rgb, 99,179,255), 0.25),
      inset 0 0 20px rgba(var(--evt-accent-rgb, 99,179,255), var(--task-hover-inset-alpha, 0.50)),
      0 0 20px rgba(var(--evt-accent-rgb, 99,179,255), var(--task-hover-outer-alpha, 0.20)),
      0 10px 18px rgba(0,0,0,0.28);
  }

  .evt .evt-top {
    padding: 6px 8px;
    border-bottom: 1px solid rgba(38,49,65,0.30);
    background: linear-gradient(180deg, rgba(0,0,0,0.18), rgba(0,0,0,0.06));
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: relative;
    z-index: 1;
  }
  .evt.user-colored .evt-top {
    background: rgba(var(--evt-accent-rgb, 99,179,255), 0.08);
    border-bottom-color: rgba(var(--evt-accent-rgb, 99,179,255), 0.18);
  }

  .evt .evt-title {
    color: var(--task-title-text, var(--text));
    font-weight: 700;
    font-size: 13px;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .evt .evt-time {
    color: var(--muted);
    font-size: 12px;
    line-height: 1.15;
    white-space: nowrap;
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .evt .evt-time .time-pill {
    border: 1px solid rgba(154,166,178,0.30);
    border-radius: 999px;
    padding: 1px 7px;
    font-size: 12px;
    color: var(--muted);
    background: rgba(255,255,255,0.04);
  }
  .evt.user-colored .evt-time .time-pill {
    border-color: rgba(var(--evt-accent-rgb, 99,179,255), 0.30);
    background: rgba(var(--evt-accent-rgb, 99,179,255), 0.08);
    color: #d9efff;
  }

  .evt .evt-bot {
    padding: 6px 8px 8px 8px;
    color: var(--task-body-text);
    font-size: 12px;
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: center;
    position: relative;
    z-index: 1;
  }
  .evt .evt-bot code { color: var(--task-code-text); font-size: 12px; }

  .evt .resize {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 10px;
    cursor: ns-resize;
    background: linear-gradient(to bottom, transparent, var(--task-resize-glow));
    /* Must sit above the body/text so the bottom-edge resize is reliably grab-able. */
    z-index: 3;
    pointer-events: auto;
  }
  .evt.dragging { opacity: 0.90; outline: 2px solid rgba(var(--accent-rgb), 0.65); }

  /* Task FX (optional; controlled by theme tokens)
     - sheen sweep on hover
     - snap pulse after commit
     - z-index ladder for hover/drag (see bottom override)
  */
  .evt .evt-sheen{
    position: absolute;
    inset: -40% -60%;
    pointer-events: none;
    opacity: 0;
    transform: translateX(-120%) rotate(12deg);
    background: linear-gradient(90deg,
      rgba(255,255,255,0.00) 0%,
      rgba(255,255,255,0.00) 35%,
      rgba(255,255,255,0.18) 50%,
      rgba(255,255,255,0.00) 65%,
      rgba(255,255,255,0.00) 100%);
    filter: blur(0.2px);
    mix-blend-mode: screen;
    will-change: transform, opacity;
    transition: opacity 150ms ease;
    z-index: 0;
  }
  .evt:hover .evt-sheen{
    opacity: var(--task-hover-sheen-opacity, 0);
    animation: task_sheen_sweep var(--task-hover-sheen-ms, 520ms) ease-out 1;
  }
  .evt.snap-pulse{
    animation: task_snap_pulse var(--task-snap-pulse-ms, 180ms) ease-out 1;
  }

  @keyframes task_sheen_sweep{
    0%   { transform: translateX(-120%) rotate(12deg); }
    100% { transform: translateX(120%) rotate(12deg); }
  }
  @keyframes task_snap_pulse{
    0%   { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.0), 0 10px 18px rgba(0,0,0,0.28); }
    40%  { box-shadow: 0 0 0 2px rgba(var(--accent-rgb), var(--task-snap-pulse-opacity, 0.45)), 0 10px 18px rgba(0,0,0,0.28); }
    100% { box-shadow: 0 0 0 0 rgba(var(--accent-rgb), 0.0), 0 10px 18px rgba(0,0,0,0.28); }
  }
  @keyframes nautical_pick_pulse{
    0%   { transform: scale(1); filter: brightness(1); }
    35%  { transform: scale(1.02); filter: brightness(1.24); }
    100% { transform: scale(1); filter: brightness(1); }
  }
  @keyframes nautical_pick_selected_glow{
    0%{
      box-shadow:
        0 0 0 2px rgba(var(--accent-rgb), 0.30) inset,
        0 0 16px rgba(var(--accent-rgb), 0.18),
        0 12px 22px rgba(0,0,0,0.30);
      filter: brightness(1.00) saturate(1.00);
    }
    50%{
      box-shadow:
        0 0 0 2px rgba(var(--accent-rgb), 0.46) inset,
        0 0 26px rgba(var(--accent-rgb), 0.30),
        0 14px 24px rgba(0,0,0,0.34);
      filter: brightness(1.08) saturate(1.10);
    }
    100%{
      box-shadow:
        0 0 0 2px rgba(var(--accent-rgb), 0.30) inset,
        0 0 16px rgba(var(--accent-rgb), 0.18),
        0 12px 22px rgba(0,0,0,0.30);
      filter: brightness(1.00) saturate(1.00);
    }
  }

  @keyframes task_selected_pulse{
    0%{
      box-shadow:
        0 0 0 1px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.52) inset,
        0 0 0 2px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.14),
        0 0 18px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.18),
        0 12px 22px rgba(0,0,0,0.32);
    }
    50%{
      box-shadow:
        0 0 0 1px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.70) inset,
        0 0 0 2px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.22),
        0 0 30px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.28),
        0 14px 26px rgba(0,0,0,0.36);
    }
    100%{
      box-shadow:
        0 0 0 1px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.52) inset,
        0 0 0 2px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.14),
        0 0 18px rgba(var(--evt-accent-rgb, var(--accent-rgb)), 0.18),
        0 12px 22px rgba(0,0,0,0.32);
    }
  }

  /* Keep strong motion feedback as an intentional opt-in visual style. */
  body.theme-vivid .evt.selected:not(.dragging){
    animation: task_selected_pulse var(--task-selected-pulse-ms, 1600ms) ease-in-out infinite;
  }
  body.nautical-selection-mode.nautical-selection-has-picked .evt.nautical-preview:not(.nautical-picked){
    opacity: 0.70;
    filter: saturate(0.86) brightness(0.95);
  }
  body.nautical-selection-mode.nautical-selection-has-picked .item.nautical-preview:not(.nautical-picked){
    opacity: 0.74;
    filter: saturate(0.90) brightness(0.96);
  }
  body.nautical-selection-mode.nautical-selection-has-picked .evt.nautical-preview.nautical-picked{
    opacity: 1;
    animation: nautical_pick_selected_glow 1800ms ease-in-out infinite;
  }
  body.nautical-selection-mode.nautical-selection-has-picked .item.nautical-preview.nautical-picked{
    opacity: 1;
    animation: nautical_pick_selected_glow 1800ms ease-in-out infinite;
  }
  .evt.nautical-picked-pulse{
    animation: nautical_pick_pulse 700ms cubic-bezier(0.19, 1, 0.22, 1) 1;
  }
  .item.nautical-picked-pulse{
    animation: nautical_pick_pulse 700ms cubic-bezier(0.19, 1, 0.22, 1) 1;
  }

  @media (prefers-reduced-motion: reduce){
    .evt{ transition: none; }
    .evt:hover .evt-sheen{ animation: none; }
    .evt.snap-pulse{ animation: none; }
    .evt.selected:not(.dragging){ animation: none; }
    body.nautical-selection-mode.nautical-selection-has-picked .evt.nautical-preview.nautical-picked{ animation: none; }
    body.nautical-selection-mode.nautical-selection-has-picked .item.nautical-preview.nautical-picked{ animation: none; }
    .evt.nautical-picked-pulse{ animation: none; }
    .item.nautical-picked-pulse{ animation: none; }
  }


  /* Queued final actions (UI-only) */
  .evt.queued-done {
    opacity: 0.58;
    border-left-color: rgba(154,166,178,0.70);
  }
  .evt.queued-delete {
    opacity: 0.32;
    border-left-color: var(--bad);
    background:
      repeating-linear-gradient(135deg, rgba(var(--bad-rgb),0.10), rgba(var(--bad-rgb),0.10) 8px, rgba(0,0,0,0) 8px, rgba(0,0,0,0) 16px),
      linear-gradient(180deg, var(--block), var(--block2));
  }

  .evt.queued-done .evt-title,
  .evt.queued-delete .evt-title { text-decoration: line-through; }

  .evt.queued-done .resize,
  .evt.queued-delete .resize { display: none; }

  .evt.queued-done::after,
  .evt.queued-delete::after {
    position: absolute;
    top: 6px;
    right: 6px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    padding: 2px 7px;
    border-radius: 999px;
    border: 1px solid rgba(154,166,178,0.30);
    background: rgba(0,0,0,0.20);
    color: var(--muted);
    content: "DONE";
    z-index: 3;
    pointer-events: none;
  }
  .evt.queued-delete::after{
    content: "DELETE";
    border-color: rgba(var(--bad-rgb),0.35);
    color: var(--bad);
    background: rgba(var(--bad-rgb),0.10);
  }

  .item.queued-done,
  .item.queued-delete { position: relative; }
  .item.queued-done {
    opacity: 0.60;
    border-style: dashed;
  }
  .item.queued-delete {
    opacity: 0.40;
    border-color: rgba(var(--bad-rgb),0.35);
    background:
      repeating-linear-gradient(135deg, rgba(var(--bad-rgb),0.08), rgba(var(--bad-rgb),0.08) 8px, rgba(0,0,0,0) 8px, rgba(0,0,0,0) 16px),
      var(--surface3);
  }

  .item.queued-done .line1,
  .item.queued-delete .line1 { text-decoration: line-through; }

  .item.queued-done::after,
  .item.queued-delete::after {
    position: absolute;
    top: 8px;
    right: 10px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    padding: 1px 7px;
    border-radius: 999px;
    border: 1px solid rgba(154,166,178,0.30);
    background: rgba(0,0,0,0.15);
    color: var(--muted);
    content: "DONE";
    pointer-events: none;
  }
  .item.queued-delete::after {
    content: "DELETE";
    border-color: rgba(var(--bad-rgb),0.35);
    color: var(--bad);
    background: rgba(var(--bad-rgb),0.10);
  }

  /* Lists */
  .item {
    position: relative;
    padding: 9px 10px;
    border: 1px solid rgba(38,49,65,0.45);
    border-radius: 12px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
      var(--surface3);
    margin-bottom: 8px;
    cursor: grab;
    display: grid;
    grid-template-columns: 18px 1fr;
    gap: 8px;
    align-items: start;
    transition: border-color 130ms ease, box-shadow 130ms ease, transform 130ms ease;
  }
  .item:hover{
    border-color: rgba(var(--accent-rgb),0.35);
    box-shadow: 0 10px 18px rgba(0,0,0,0.14);
    transform: translateY(-1px);
  }
  .item::before{
    content: "";
    position: absolute;
    left: 0;
    top: 6px;
    bottom: 6px;
    width: 3px;
    border-radius: 999px;
    background: transparent;
    opacity: 0.8;
    pointer-events: none;
  }
  .item[data-hint-kind="missing"]::before{
    background: rgba(var(--bad-rgb), 0.72);
  }
  .item[data-hint-kind="work"]::before{
    background: rgba(var(--warn-rgb), 0.78);
  }
  .item[data-hint-kind="window"]::before{
    background: rgba(var(--accent-rgb), 0.78);
  }
  .item.nautical-preview{
    border-style: dashed;
    border-color: rgba(var(--warn-rgb), 0.35);
    opacity: 0.75;
    cursor: default;
  }
  .item.nautical-preview:hover{
    transform: none;
    box-shadow: none;
  }
  .item.nautical-preview.nautical-picked{
    border-style: solid;
    border-color: rgba(var(--accent-rgb), 0.78);
    background:
      linear-gradient(180deg, rgba(var(--accent-rgb), 0.16), rgba(var(--accent-rgb), 0.05)),
      var(--surface3);
    box-shadow:
      0 0 0 2px rgba(var(--accent-rgb), 0.26) inset,
      0 0 18px rgba(var(--accent-rgb), 0.20);
    opacity: 1;
  }
  .item.nautical-preview.nautical-picked::before{
    background: rgba(var(--accent-rgb), 0.95);
    opacity: 1;
  }
  .item.nautical-preview.nautical-picked::after{
    content: "SELECTED";
    position: absolute;
    right: 10px;
    top: 7px;
    font-size: 10px;
    font-weight: 850;
    letter-spacing: 0.35px;
    color: rgba(var(--accent-rgb), 0.98);
    background: rgba(var(--accent-rgb), 0.12);
    border: 1px solid rgba(var(--accent-rgb), 0.40);
    border-radius: 999px;
    padding: 1px 7px;
    pointer-events: none;
  }
  .item.nautical-preview .selbox2{ display: none; }
  .item:active { cursor: grabbing; }
  .item.selected { border-color: rgba(var(--accent-rgb),0.55); box-shadow: 0 0 0 2px rgba(var(--accent-rgb),0.12) inset; }
  .item.user-colored {
    border-color: rgba(var(--row-accent-rgb, 99,179,255), 0.35);
    box-shadow:
      0 0 0 1px rgba(var(--row-accent-rgb, 99,179,255), 0.35) inset,
      0 0 18px rgba(var(--row-accent-rgb, 99,179,255), 0.12);
    background:
      linear-gradient(180deg, rgba(var(--row-accent-rgb, 99,179,255), 0.08), rgba(14,19,25,1));
  }

  .item .selbox2 {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid rgba(154,166,178,0.35);
    background: rgba(0,0,0,0.15);
    display: grid;
    place-items: center;
    cursor: pointer;
    user-select: none;
    margin-top: 1px;
  }
  .item .selbox2 .tick { opacity: 0; font-size: 12px; color: var(--task-code-text); transform: translateY(-0.5px); }
  .item.selected .selbox2 { border-color: rgba(var(--accent-rgb),0.55); background: rgba(var(--accent-rgb),0.10); }
  .item.selected .selbox2 .tick { opacity: 1; }

  .item .line1 {
    font-weight: 650;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item .line2 {
    color: var(--muted);
    font-size: 12px;
    margin-top: 3px;
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: center;
  }
  .item .line2.item-meta-row{
    align-items: flex-start;
    gap: 10px;
  }
  .item .line2 .chips{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
    min-width: 0;
  }
  .pill {
    border: 1px solid rgba(154,166,178,0.30);
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.02em;
    color: var(--muted);
    white-space: nowrap;
  }
  .pill.bad { border-color: rgba(var(--bad-rgb),0.45); color: var(--bad); }
  .pill.warn { border-color: rgba(var(--warn-rgb),0.45); color: var(--warn); }
  .pill.reason{
    font-weight: 760;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .pill.reason.missing{
    border-color: rgba(var(--bad-rgb),0.45);
    color: var(--bad);
    background: rgba(var(--bad-rgb),0.10);
  }
  .pill.reason.work{
    border-color: rgba(var(--warn-rgb),0.45);
    color: var(--warn);
    background: rgba(var(--warn-rgb),0.12);
  }
  .pill.reason.window{
    border-color: rgba(var(--accent-rgb),0.45);
    color: var(--text);
    background: rgba(var(--accent-rgb),0.11);
  }
  .pill.reason.other{
    border-color: rgba(154,166,178,0.35);
  }
  .problem-item{
    border-color: rgba(var(--bad-rgb), 0.25);
  }
  .problem-item::before{
    background: rgba(var(--bad-rgb), 0.68);
  }
  .empty-state{
    border: 1px dashed rgba(154,166,178,0.28);
    border-radius: 12px;
    padding: 10px 11px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.35;
    background: rgba(255,255,255,0.02);
  }
  .empty-state.ok{
    border-color: rgba(var(--accent-rgb),0.34);
    background: rgba(var(--accent-rgb),0.06);
    color: var(--text);
  }

  /* Commands */
  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    padding: 10px;
    background: var(--code-bg);
    border: 1px solid var(--code-bd);
    border-radius: 12px;
    color: var(--code-text);
    min-height: 120px;
    box-shadow:
      0 1px 0 rgba(255,255,255,0.04) inset,
      0 8px 18px rgba(0,0,0,0.16);
  }
  .hint { color: var(--muted); font-size: 12px; line-height: 1.35; }
  .cmd-guide{
    border: 1px solid var(--code-bd);
    border-radius: 11px;
    padding: 7px 9px;
    margin-bottom: 10px;
    font-size: 12px;
    color: var(--muted);
    background: var(--surface-pop);
  }
  .cmd-guide.ready{
    color: var(--text);
    border-color: rgba(var(--accent-rgb), 0.48);
    background: rgba(var(--accent-rgb), 0.12);
  }
  .cmd-guide.focus{
    border-color: rgba(var(--warn-rgb), 0.48);
    background: rgba(var(--warn-rgb), 0.12);
  }
  .ops {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .rsec{
    border: 1px solid var(--code-bd);
    border-radius: 12px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
      var(--surface-pop);
    margin-bottom: 10px;
    overflow: hidden;
    transition: border-color 140ms ease, box-shadow 140ms ease;
  }
  .rsec.open{
    border-color: rgba(var(--accent-rgb), 0.42);
    box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.14) inset;
  }
  .rsec-h{
    width: 100%;
    border: 0;
    border-bottom: 1px solid rgba(154,166,178,0.16);
    border-radius: 0;
    margin: 0;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.00)),
      var(--panel2);
    padding: 9px 10px;
    display: grid;
    grid-template-columns: 1fr auto auto;
    align-items: center;
    gap: 10px;
    text-align: left;
    box-shadow: none;
  }
  .rsec-h:hover{
    transform: none;
    box-shadow: none;
    border-bottom-color: rgba(var(--accent-rgb), 0.32);
  }
  .rsec-h:focus-visible{
    outline: 2px solid rgba(var(--accent-rgb), 0.68);
    outline-offset: -2px;
    position: relative;
    z-index: 1;
  }
  .rsec-h .rsec-t{
    font-weight: 820;
    letter-spacing: 0.02em;
  }
  .rsec-h .rsec-s{
    font-size: 11px;
    color: var(--muted);
    white-space: nowrap;
  }
  .rsec-h .rsec-chev{
    color: var(--muted);
    font-size: 12px;
    transition: transform 120ms ease;
  }
  .rsec.open .rsec-h .rsec-chev{
    transform: rotate(90deg);
  }
  .rsec-b{
    padding: 10px;
    overflow: hidden;
    transform: translateY(0);
    opacity: 1;
    transition:
      max-height 170ms cubic-bezier(0.2, 0.7, 0.2, 1),
      opacity 130ms ease,
      transform 130ms ease;
  }
  .rsec-b.anim-open{
    opacity: 1;
    transform: translateY(0);
  }
  .rsec-b.anim-close{
    opacity: 0;
    transform: translateY(-4px);
  }
  .rsec-b[hidden]{
    display: none;
  }
  .rsec-b .ops:last-child{
    margin-bottom: 0;
  }

  .conflicts {
    border: 1px solid var(--code-bd);
    border-radius: 12px;
    background: var(--code-bg);
    padding: 10px;
    margin-bottom: 10px;
    box-shadow: 0 10px 22px rgba(0,0,0,0.14) inset;
  }
  .conflicts .ctitle { display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-bottom: 6px; }
  .conflicts .ctitle .t { font-weight: 650; }
  .conflicts .ctitle .s { color: var(--muted); font-size: 12px; }

  .conflicts .ctitle { cursor: pointer; user-select: none; }
  .conflicts .ctitle .chev { color: var(--muted); font-size: 12px; }
  .conflicts .conf-body { margin-top: 8px; }
  .conflicts.collapsed .conf-body { display: none; }

  .conf-day { margin-top: 10px; }
  .conf-day:first-child { margin-top: 0; }
  .conf-day .dh { display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px; }
  .conf-day .dh .d { font-weight: 650; }
  .conf-day .dh .n { color: var(--muted); font-size: 12px; }

  .conf-item {
    border: 1px solid var(--code-bd);
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
    padding: 8px 10px;
    margin-bottom: 8px;
  }
  .conf-item:last-child { margin-bottom: 0; }
  .conf-item .top { display:flex; justify-content:space-between; gap:10px; align-items:center; }
  .conf-item .top .range { color: #ffd9d9; }
  .conf-item .top .count { color: var(--muted); font-size: 12px; }
  .conf-item .bots { margin-top: 6px; color: var(--muted); font-size: 12px; }
  .conf-item .acts { display:flex; gap:8px; margin-top: 8px; }

  /* Add tasks modal */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.60);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    padding: 20px;
  }

  .nautical-ctx-menu{
    position: fixed;
    z-index: 13000;
    min-width: 240px;
    max-width: min(92vw, 420px);
    border-radius: 12px;
    padding: 8px;
    border: 1px solid rgba(var(--warn-rgb), 0.45);
    background: linear-gradient(180deg, rgba(15,20,26,0.98), rgba(11,15,20,0.98));
    box-shadow:
      0 12px 26px rgba(0,0,0,0.42),
      0 0 0 1px rgba(var(--warn-rgb), 0.14) inset;
  }
  .nautical-ctx-menu[hidden]{
    display: none;
  }
  .nautical-ctx-title{
    font-size: 12px;
    line-height: 1.3;
    color: rgba(var(--warn-rgb), 0.98);
    font-weight: 700;
    padding: 4px 6px 8px 6px;
    border-bottom: 1px solid rgba(var(--warn-rgb), 0.20);
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .nautical-ctx-btn{
    width: 100%;
    text-align: left;
    border: 1px solid rgba(154,166,178,0.26);
    border-radius: 9px;
    color: var(--text);
    background: rgba(255,255,255,0.03);
    padding: 7px 9px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 650;
    margin: 0 0 6px 0;
  }
  .nautical-ctx-btn:hover{
    border-color: rgba(var(--warn-rgb), 0.40);
    background: rgba(var(--warn-rgb), 0.13);
  }
  .nautical-ctx-btn:disabled{
    opacity: 0.55;
    cursor: default;
    border-color: rgba(154,166,178,0.20);
    background: rgba(255,255,255,0.015);
  }
  .nautical-ctx-btn:disabled:hover{
    border-color: rgba(154,166,178,0.20);
    background: rgba(255,255,255,0.015);
  }
  .nautical-ctx-btn:last-child{
    margin-bottom: 0;
  }
  .nautical-ctx-btn.subtle{
    color: var(--muted);
    background: rgba(255,255,255,0.01);
  }
  .nautical-ctx-btn.subtle:hover{
    color: var(--text);
    background: rgba(255,255,255,0.05);
    border-color: rgba(154,166,178,0.36);
  }


  /* Sticky notes */
  .day-notes{
    margin-top: 6px;
    display:flex;
    align-items:center;
    gap:6px;
    flex-wrap:nowrap;
    overflow:hidden;
  }
  .npill{
    font-size: 11px;
    font-weight: 850;
    border-radius: 999px;
    padding: 1px 7px;
    border: 1px solid var(--note-bd);
    background: var(--npill-bg);
    color: var(--npill-text);
    max-width: 180px;
    white-space: nowrap;
    overflow:hidden;
    text-overflow:ellipsis;--pill-tilt: 0deg;
--pill-hover: 1.5deg;
transform: translateY(0px) rotate(var(--pill-tilt));
transition: transform 150ms ease, box-shadow 150ms ease, outline-color 150ms ease;
will-change: transform;

    cursor:pointer;
    user-select:none;
  }
  .npill.more{ border-color: var(--npill-more-bd); background: var(--npill-more-bg); color: var(--npill-more-text); }

/* Sticky note pill micro-interactions */
.npill:hover{
  transform: translateY(-1px) rotate(calc(var(--pill-tilt) + var(--pill-hover)));
  box-shadow: 0 10px 18px rgba(0,0,0,0.16);
}
.npill.is-dragging{
  transform: translateY(-2px) rotate(var(--pill-tilt)) scale(1.02, 0.98);
  box-shadow: 0 12px 22px rgba(0,0,0,0.18);
  cursor: grabbing;
}
.npill.snap-pulse{
  outline: 2px solid rgba(var(--accent-rgb), 0.40);
  outline-offset: -2px;
}


  /* Sticky notes (calendar overlays) */
  .note{
    position: absolute;
    left: 8px;
    right: 8px;
    border-radius: 10px;
    background:
      var(--note-bg);
    border: 1px solid var(--note-bd);
    box-shadow: 0 8px 16px rgba(0,0,0,0.18);
    padding: 6px 8px 14px 8px; /* extra bottom room for resize handle */
    font-size: 12px;
    color: var(--note-text);
    overflow: hidden;
    z-index: 1;--note-tilt: 0deg;
--note-hover: 1.5deg;
--note-r: var(--note-tilt);
--note-ty: 0px;
--note-sx: 1;
--note-sy: 1;
transform: translateY(var(--note-ty)) rotate(var(--note-r)) scale(var(--note-sx), var(--note-sy));
transform-origin: center center;
transition: transform 150ms ease, box-shadow 150ms ease, outline-color 150ms ease;
will-change: transform;

    cursor: grab;
    user-select: none;
    display:flex;
    flex-direction:column;
    gap:6px;
  }
  .note:active { cursor: grabbing; }

/* Sticky notes: tactile micro-interactions */
.note::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  background-image: repeating-linear-gradient(135deg, rgba(255,255,255,0.03) 0 2px, rgba(0,0,0,0.00) 2px 7px);
  opacity: 0.55;
}
.note::after{
  content:"";
  position:absolute;
  right:-6px;
  bottom:-6px;
  width: 26px;
  height: 26px;
  pointer-events:none;
  background: radial-gradient(circle at 10px 10px, rgba(255,255,255,0.16), rgba(255,255,255,0.00) 70%);
  opacity: 0.65;
}

.note:hover{
  --note-ty: -1px;
  --note-r: calc(var(--note-tilt) + var(--note-hover));
  box-shadow: 0 12px 20px rgba(0,0,0,0.22);
}

.note.is-dragging{
  --note-ty: -2px;
  --note-sx: 1.02;
  --note-sy: 0.98;
  --note-r: var(--note-tilt);
  box-shadow: 0 14px 24px rgba(0,0,0,0.25);
  cursor: grabbing;
}
.note.is-resizing{
  --note-ty: -1px;
  --note-sx: 1.01;
  --note-sy: 0.99;
  --note-r: var(--note-tilt);
  box-shadow: 0 12px 22px rgba(0,0,0,0.23);
}

.note.snap-pulse{
  outline: 2px solid rgba(var(--accent-rgb), 0.40);
  outline-offset: -2px;
}

body.theme-light .note::before,
body.theme-paper .note::before{
  background-image: repeating-linear-gradient(135deg, rgba(0,0,0,0.03) 0 2px, rgba(0,0,0,0.00) 2px 7px);
  opacity: 0.38;
}
body.theme-light .note::after,
body.theme-paper .note::after{
  background: radial-gradient(circle at 10px 10px, rgba(0,0,0,0.08), rgba(0,0,0,0.00) 70%);
  opacity: 0.40;
}


  /* Header line (meta/time/repeat) */
  .note .nhdr{
    flex: 0 0 auto;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    font-size: 11px;
    font-weight: 900;
    color: var(--note-meta);
    white-space: nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
  }
  .note .nhdr .lhs{ min-width:0; overflow:hidden; text-overflow:ellipsis; }
  .note .nhdr .rhs{ flex: 0 0 auto; opacity: 0.95; }

  /* Body text (centered, wrapping) */
  .note .nbody{
    flex: 1 1 auto;
    min-height: 0;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    overflow:hidden;
  }
  .note .ntxt{
    font-weight: 900;
    line-height: 1.25;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  /* Resize handle */
  .note .nrsz{
    position:absolute;
    left: 6px;
    right: 6px;
    bottom: 4px;
    height: 9px;
    border-radius: 999px;
    cursor: ns-resize;
    opacity: 0.70;
    background: var(--note-handle-bg);
    border: 1px solid var(--note-handle-bd);
  }
  .note .nrsz:before{
    content:"";
    position:absolute;
    left: 50%;
    top: 50%;
    width: 16px;
    height: 3px;
    transform: translate(-50%, -50%);
    border-top: 1px solid rgba(154,166,178,0.55);
    border-bottom: 1px solid rgba(154,166,178,0.55);
  }
  .note:hover .nrsz{ opacity: 0.95; }

  .note.pinned{
    border-color: var(--note-pinned-bd);
    box-shadow: 0 0 0 2px rgba(var(--warn-rgb),0.12) inset, 0 8px 16px rgba(0,0,0,0.18);
  }

  /* Optional note colors */
  .note.c1{ background: var(--note-c1-bg); border-color: var(--note-c1-bd); }
  .note.c2{ background: var(--note-c2-bg); border-color: var(--note-c2-bd); }
  .note.c3{ background: var(--note-c3-bg); border-color: var(--note-c3-bd); }
  .note.c4{ background: var(--note-c4-bg); border-color: var(--note-c4-bd); }
  .note.c5{ background: var(--note-c5-bg); border-color: var(--note-c5-bd); }
  .note.c6{ background: var(--note-c6-bg); border-color: var(--note-c6-bd); }
  .note.c7{ background: var(--note-c7-bg); border-color: var(--note-c7-bd); }
  .note.c8{ background: var(--note-c8-bg); border-color: var(--note-c8-bd); }

  /* Ensure tasks remain above notes */
  .evt{ z-index: var(--task-z, 2); }
  .evt:hover{ z-index: var(--task-hover-z, 20); }
  .evt.selected{ z-index: var(--task-selected-z, 30); }
  .evt.selected:hover{ z-index: var(--task-selected-hover-z, 35); }
  .evt.dragging{ z-index: var(--task-drag-z, 50); }
  .note .nhdr, .note .nbody, .note .nrsz{ position: relative; z-index: 1; }

'''
