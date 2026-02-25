# scalpel/render/css/part01_tokens_theme.py
from __future__ import annotations

CSS_PART = r'''
:root {
    /* Core surfaces */
    --bg: #0a131d;
    --panel: #0f1b2a;
    --panel2: #122033;
    --surface3: #101c2b;
    --surface4: #0b1522;
    --surface-pop: rgba(255,255,255,0.02);

    /* Calendar surfaces */
    --cal-surface: #0d1724;

    /* Text */
    --text: #e7eff8;
    --muted: #9ab0c5;

    /* Lines / shadows */
    --line: #29435d;
    --shadow: rgba(2,8,18,0.40);
    --radius: 14px;
    --header-glow: rgba(52,200,255,0.18);

    /* Accents */
    --accent: #34c8ff;
    --accent-rgb: 52,200,255;
    --warn: #ffb86a;
    --warn-rgb: 255,184,106;
    --bad: #ff6678;
    --bad-rgb: 255,102,120;

    /* Task blocks */
    --block: #173048;
    --block2: #1a3d59;
    --task-border: rgba(var(--accent-rgb), 0.20);
    --task-selected: rgba(var(--accent-rgb), 0.75);
    --task-title-text: var(--text);
    --task-body-text: #cee2f4;
    --task-code-text: #d5f4ff;
    --task-resize-glow: rgba(var(--accent-rgb), 0.15);

    /* Task hover ring (prominent hover affordance; can be disabled per theme) */
    --task-hover-ring-ms: 900ms;
    --task-hover-outline-alpha: 0.32;
    --task-hover-outline-offset: 10px;
    --task-hover-inset-alpha: 0.26;
    --task-hover-outer-alpha: 0.12;

    /* Task FX (optional) */
    --task-z: 2;
    --task-hover-z: 20;
    --task-drag-z: 50;
    --task-hover-sheen-opacity: 0.10;
    --task-hover-sheen-ms: 420ms;
    --task-snap-pulse-opacity: 0.30;
    --task-snap-pulse-ms: 180ms;

    /* Buttons / inputs */
    --hdr-top: #112233;
    --hdr-bot: #0a131d;
    --btn-bg: #182a3f;
    --btn-bd: #2f4d6d;
    --btn-bd-hover: #48729f;
    --btn-disabled-bg: rgba(255,255,255,0.03);
    --btn-disabled-bd: rgba(154,166,178,0.18);
    --btn-disabled-text: rgba(154,166,178,0.55);
    --danger-bd: rgba(var(--bad-rgb), 0.55);
    --danger-bd-hover: rgba(var(--bad-rgb), 0.85);
    --danger-text: #ffd9d9;

    --input-bg: var(--surface3);
    --input-bd: var(--btn-bd);
    --input-bg-soft: rgba(255,255,255,0.05);
    --input-bd-soft: rgba(47,77,109,0.55);

    /* Code / blocks */
    --code-bg: var(--surface4);
    --code-bd: rgba(41,67,93,0.65);
    --code-text: #d7e6f3;

    /* Grid lines */
    --grid-hour: rgba(154,166,178,0.30);
    --grid-qtr: rgba(154,166,178,0.05);
    --tick: rgba(154,166,178,0.36);
    --weekend-col-bg: rgba(154,166,178,0.05);
    --weekend-col-hover-bg: rgba(var(--accent-rgb), 0.06);
    --weekend-header-bg: rgba(154,166,178,0.05);
    --weekend-header-bd: rgba(154,166,178,0.24);

    /* Load bar */
    --loadfill: rgba(var(--accent-rgb), 0.55);
    --loadfill-over: rgba(var(--bad-rgb), 0.70);

    /* Now line */
    --now-line: rgba(var(--warn-rgb), 0.80);
    --now-glow: rgba(var(--warn-rgb), 0.24);
    --now-label-bg: rgba(12,16,22,0.85);

    /* Sticky note pills (all-day) */
    --npill-bg: rgba(var(--warn-rgb), 0.10);
    --npill-bd: rgba(var(--warn-rgb), 0.30);
    --npill-text: rgba(232,237,242,0.92);
    --npill-more-bg: rgba(255,255,255,0.03);
    --npill-more-bd: rgba(154,166,178,0.25);
    --npill-more-text: rgba(154,166,178,0.98);

    /* Sticky notes (timed overlays) */
    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.18), rgba(var(--warn-rgb),0.08));
    --note-bd: rgba(var(--warn-rgb), 0.30);
    --note-text: rgba(232,237,242,0.95);
    --note-meta: rgba(154,166,178,0.98);
    --note-handle-bg: rgba(255,255,255,0.06);
    --note-handle-bd: rgba(154,166,178,0.16);
    --note-pinned-bd: rgba(var(--warn-rgb), 0.48);

    /* Note palette swatches (c1..c8) */
    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.20), rgba(var(--warn-rgb),0.08));
    --note-c1-bd: rgba(var(--warn-rgb),0.32);

    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.16), rgba(var(--accent-rgb),0.06));
    --note-c2-bd: rgba(var(--accent-rgb),0.32);

    --note-c3-bg: linear-gradient(180deg, rgba(74,222,128,0.14), rgba(74,222,128,0.05));
    --note-c3-bd: rgba(74,222,128,0.30);

    --note-c4-bg: linear-gradient(180deg, rgba(var(--bad-rgb),0.14), rgba(var(--bad-rgb),0.05));
    --note-c4-bd: rgba(var(--bad-rgb),0.30);

    --note-c5-bg: linear-gradient(180deg, rgba(167,139,250,0.14), rgba(167,139,250,0.05));
    --note-c5-bd: rgba(167,139,250,0.30);

    --note-c6-bg: linear-gradient(180deg, rgba(45,212,191,0.14), rgba(45,212,191,0.05));
    --note-c6-bd: rgba(45,212,191,0.30);

    --note-c7-bg: linear-gradient(180deg, rgba(148,163,184,0.12), rgba(148,163,184,0.04));
    --note-c7-bd: rgba(148,163,184,0.28);

    --note-c8-bg: linear-gradient(180deg, rgba(244,114,182,0.13), rgba(244,114,182,0.04));
    --note-c8-bd: rgba(244,114,182,0.28);

    /* Layout constants */
    --day-header-h: 78px;

    --work-start-mod60: 0;
    --work-start-mod15: 0;

    --hour-shift: calc(var(--work-start-mod60) * var(--px-per-min) * 1px);
    --qtr-shift:  calc(var(--work-start-mod15) * var(--px-per-min) * 1px);
  }

  body.theme-dark,
  body.theme-muted,
  body.theme-vivid,
  body.theme-contrast{ color-scheme: dark; }

  body.theme-light{
    color-scheme: light;
    --bg: #eef4fb;
    --panel: #ffffff;
    --panel2: #edf3fa;
    --surface3: #ffffff;
    --surface4: #eef3f8;
    --cal-surface: #edf3fa;
    --surface-pop: rgba(15,23,42,0.03);

    --text: #102136;
    --muted: #48637e;
    --line: rgba(16,33,54,0.20);
    --shadow: rgba(15,23,42,0.11);
    --header-glow: rgba(37,99,235,0.14);

    --accent: #0d80d8;
    --accent-rgb: 13,128,216;
    --warn: #cc7a1f;
    --warn-rgb: 204,122,31;
    --bad: #d93d52;
    --bad-rgb: 217,61,82;

    --block: rgba(15,23,42,0.04);
    --block2: rgba(15,23,42,0.06);
    --task-border: rgba(var(--accent-rgb), 0.22);
    --task-selected: rgba(var(--accent-rgb), 0.55);
    --task-title-text: var(--text);
    --task-body-text: rgba(16,33,54,0.88);
    --task-code-text: rgba(13,128,216,0.95);
    --task-resize-glow: rgba(var(--accent-rgb), 0.10);

    --task-hover-ring-ms: 850ms;
    --task-hover-outline-alpha: 0.30;
    --task-hover-outline-offset: 10px;
    --task-hover-inset-alpha: 0.22;
    --task-hover-outer-alpha: 0.12;

    --hdr-top: #f8fbff;
    --hdr-bot: #edf3fa;
    --btn-bg: var(--panel2);
    --btn-bd: rgba(15,23,42,0.18);
    --btn-bd-hover: rgba(15,23,42,0.22);
    --btn-disabled-bg: rgba(15,23,42,0.03);
    --btn-disabled-bd: rgba(15,23,42,0.10);
    --btn-disabled-text: rgba(15,23,42,0.40);
    --danger-bd: rgba(var(--bad-rgb), 0.35);
    --danger-bd-hover: rgba(var(--bad-rgb), 0.55);
    --danger-text: var(--bad);

    --input-bg: var(--panel);
    --input-bd: rgba(15,23,42,0.18);
    --input-bg-soft: rgba(15,23,42,0.04);
    --input-bd-soft: rgba(15,23,42,0.18);

    --code-bg: var(--panel2);
    --code-bd: rgba(15,23,42,0.18);
    --code-text: var(--text);

    --grid-hour: rgba(15,23,42,0.16);
    --grid-qtr: rgba(15,23,42,0.035);
    --tick: rgba(15,23,42,0.24);
    --weekend-col-bg: rgba(15,23,42,0.035);
    --weekend-col-hover-bg: rgba(15,23,42,0.055);
    --weekend-header-bg: rgba(15,23,42,0.045);
    --weekend-header-bd: rgba(15,23,42,0.16);

    --loadfill: rgba(var(--accent-rgb), 0.45);
    --loadfill-over: rgba(var(--bad-rgb), 0.55);

    --now-line: rgba(var(--warn-rgb), 0.70);
    --now-glow: rgba(var(--warn-rgb), 0.22);
    --now-label-bg: rgba(241,245,249,0.85);

    --npill-bg: rgba(var(--warn-rgb), 0.06);
    --npill-bd: rgba(var(--warn-rgb), 0.28);
    --npill-text: rgba(15,23,42,0.92);
    --npill-more-bg: rgba(0,0,0,0.03);
    --npill-more-bd: rgba(71,85,105,0.30);
    --npill-more-text: rgba(71,85,105,0.95);

    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.10), rgba(var(--warn-rgb),0.05));
    --note-bd: rgba(var(--warn-rgb), 0.28);
    --note-text: rgba(15,23,42,0.92);
    --note-meta: rgba(71,85,105,0.95);
    --note-handle-bg: rgba(0,0,0,0.03);
    --note-handle-bd: rgba(71,85,105,0.16);
    --note-pinned-bd: rgba(var(--warn-rgb), 0.40);

    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.10), rgba(var(--warn-rgb),0.05));
    --note-c1-bd: rgba(var(--warn-rgb),0.28);

    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.08), rgba(var(--accent-rgb),0.03));
    --note-c2-bd: rgba(var(--accent-rgb),0.24);

    --note-c3-bg: linear-gradient(180deg, rgba(22,163,74,0.08), rgba(22,163,74,0.03));
    --note-c3-bd: rgba(22,163,74,0.24);

    --note-c4-bg: linear-gradient(180deg, rgba(var(--bad-rgb),0.07), rgba(var(--bad-rgb),0.03));
    --note-c4-bd: rgba(var(--bad-rgb),0.22);

    --note-c5-bg: linear-gradient(180deg, rgba(109,40,217,0.07), rgba(109,40,217,0.03));
    --note-c5-bd: rgba(109,40,217,0.22);

    --note-c6-bg: linear-gradient(180deg, rgba(13,148,136,0.07), rgba(13,148,136,0.03));
    --note-c6-bd: rgba(13,148,136,0.22);

    --note-c7-bg: linear-gradient(180deg, rgba(71,85,105,0.05), rgba(71,85,105,0.02));
    --note-c7-bd: rgba(71,85,105,0.18);

    --note-c8-bg: linear-gradient(180deg, rgba(219,39,119,0.07), rgba(219,39,119,0.03));
    --note-c8-bd: rgba(219,39,119,0.22);
  }

  body.theme-paper{
    color-scheme: light;
    --bg: #f7f1e5;
    --panel: #fffdf8;
    --panel2: #f5ecdc;
    --surface3: #fffdf8;
    --surface4: #f3e9d6;
    --cal-surface: #f4ead9;
    --surface-pop: rgba(59,48,32,0.04);

    --text: #2f2418;
    --muted: #6f5d49;
    --line: rgba(47,36,24,0.20);
    --shadow: rgba(68,52,31,0.11);
    --header-glow: rgba(176,108,37,0.14);

    --accent: #b06c25;
    --accent-rgb: 176,108,37;
    --warn: #ca7a24;
    --warn-rgb: 202,122,36;
    --bad: #bf3f3f;
    --bad-rgb: 191,63,63;

    --block: rgba(88,61,26,0.08);
    --block2: rgba(88,61,26,0.13);
    --task-border: rgba(var(--accent-rgb), 0.24);
    --task-selected: rgba(var(--accent-rgb), 0.52);
    --task-title-text: var(--text);
    --task-body-text: rgba(47,36,24,0.88);
    --task-code-text: rgba(132,78,24,0.95);
    --task-resize-glow: rgba(var(--accent-rgb), 0.11);

    --task-hover-ring-ms: 850ms;
    --task-hover-outline-alpha: 0.26;
    --task-hover-outline-offset: 10px;
    --task-hover-inset-alpha: 0.20;
    --task-hover-outer-alpha: 0.11;

    --hdr-top: #fdf8ee;
    --hdr-bot: #f5ecdc;
    --btn-bg: #f5ead8;
    --btn-bd: rgba(74,56,35,0.25);
    --btn-bd-hover: rgba(74,56,35,0.35);
    --btn-disabled-bg: rgba(74,56,35,0.04);
    --btn-disabled-bd: rgba(74,56,35,0.14);
    --btn-disabled-text: rgba(74,56,35,0.44);
    --danger-bd: rgba(var(--bad-rgb), 0.34);
    --danger-bd-hover: rgba(var(--bad-rgb), 0.54);
    --danger-text: var(--bad);

    --input-bg: #fffdf8;
    --input-bd: rgba(74,56,35,0.22);
    --input-bg-soft: rgba(74,56,35,0.05);
    --input-bd-soft: rgba(74,56,35,0.20);

    --code-bg: #f3e9d6;
    --code-bd: rgba(74,56,35,0.22);
    --code-text: #3a2d20;

    --grid-hour: rgba(74,56,35,0.18);
    --grid-qtr: rgba(74,56,35,0.04);
    --tick: rgba(74,56,35,0.26);
    --weekend-col-bg: rgba(74,56,35,0.04);
    --weekend-col-hover-bg: rgba(74,56,35,0.06);
    --weekend-header-bg: rgba(74,56,35,0.045);
    --weekend-header-bd: rgba(74,56,35,0.18);

    --loadfill: rgba(var(--accent-rgb), 0.45);
    --loadfill-over: rgba(var(--bad-rgb), 0.55);

    --now-line: rgba(var(--warn-rgb), 0.74);
    --now-glow: rgba(var(--warn-rgb), 0.22);
    --now-label-bg: rgba(255,250,240,0.90);

    --npill-bg: rgba(var(--warn-rgb), 0.09);
    --npill-bd: rgba(var(--warn-rgb), 0.28);
    --npill-text: rgba(47,36,24,0.92);
    --npill-more-bg: rgba(47,36,24,0.04);
    --npill-more-bd: rgba(111,93,73,0.30);
    --npill-more-text: rgba(111,93,73,0.95);

    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.11), rgba(var(--warn-rgb),0.06));
    --note-bd: rgba(var(--warn-rgb), 0.30);
    --note-text: rgba(47,36,24,0.92);
    --note-meta: rgba(111,93,73,0.95);
    --note-handle-bg: rgba(47,36,24,0.04);
    --note-handle-bd: rgba(111,93,73,0.22);
    --note-pinned-bd: rgba(var(--warn-rgb), 0.42);

    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.14), rgba(var(--warn-rgb),0.06));
    --note-c1-bd: rgba(var(--warn-rgb),0.30);

    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.11), rgba(var(--accent-rgb),0.04));
    --note-c2-bd: rgba(var(--accent-rgb),0.25);

    --note-c3-bg: linear-gradient(180deg, rgba(51,130,86,0.10), rgba(51,130,86,0.03));
    --note-c3-bd: rgba(51,130,86,0.24);

    --note-c4-bg: linear-gradient(180deg, rgba(var(--bad-rgb),0.10), rgba(var(--bad-rgb),0.03));
    --note-c4-bd: rgba(var(--bad-rgb),0.24);

    --note-c5-bg: linear-gradient(180deg, rgba(128,95,155,0.10), rgba(128,95,155,0.03));
    --note-c5-bd: rgba(128,95,155,0.24);

    --note-c6-bg: linear-gradient(180deg, rgba(45,126,126,0.10), rgba(45,126,126,0.03));
    --note-c6-bd: rgba(45,126,126,0.24);

    --note-c7-bg: linear-gradient(180deg, rgba(94,89,84,0.08), rgba(94,89,84,0.03));
    --note-c7-bd: rgba(94,89,84,0.20);

    --note-c8-bg: linear-gradient(180deg, rgba(169,78,104,0.09), rgba(169,78,104,0.03));
    --note-c8-bd: rgba(169,78,104,0.22);
  }

  /* Muted: softer accent + calmer note palette (dark scheme) */
  body.theme-muted{
    --accent: #89a6c3;
    --accent-rgb: 137,166,195;
    --warn: #d6b36a;
    --warn-rgb: 214,179,106;
    --bad: #e27a7a;
    --bad-rgb: 226,122,122;

    --task-border: rgba(var(--accent-rgb), 0.16);
    --task-selected: rgba(var(--accent-rgb), 0.55);
    --loadfill: rgba(var(--accent-rgb), 0.45);

    --npill-bg: rgba(var(--warn-rgb), 0.08);
    --npill-bd: rgba(var(--warn-rgb), 0.24);

    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.14), rgba(var(--warn-rgb),0.06));
    --note-bd: rgba(var(--warn-rgb), 0.24);

    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.16), rgba(var(--warn-rgb),0.06));
    --note-c1-bd: rgba(var(--warn-rgb),0.26);

    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.12), rgba(var(--accent-rgb),0.05));
    --note-c2-bd: rgba(var(--accent-rgb),0.26);

    /* Task FX: calmer */
    --task-hover-sheen-opacity: 0.12;
    --task-snap-pulse-opacity: 0.28;

    /* Task hover ring: calmer */
    --task-hover-ring-ms: 900ms;
    --task-hover-outline-alpha: 0.22;
    --task-hover-outline-offset: 10px;
    --task-hover-inset-alpha: 0.20;
    --task-hover-outer-alpha: 0.10;

  }

  /* Vivid: higher saturation + more presence (dark scheme) */
  body.theme-vivid{
    --accent: #4cc3ff;
    --accent-rgb: 76,195,255;
    --warn: #ffd27a;
    --warn-rgb: 255,210,122;
    --bad: #ff4d5a;
    --bad-rgb: 255,77,90;

    --task-border: rgba(var(--accent-rgb), 0.26);
    --task-selected: rgba(var(--accent-rgb), 0.85);
    --loadfill: rgba(var(--accent-rgb), 0.70);
    --loadfill-over: rgba(var(--bad-rgb), 0.78);

    --npill-bg: rgba(var(--warn-rgb), 0.14);
    --npill-bd: rgba(var(--warn-rgb), 0.38);

    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.26), rgba(var(--warn-rgb),0.10));
    --note-bd: rgba(var(--warn-rgb), 0.40);
    --note-pinned-bd: rgba(var(--warn-rgb), 0.62);

    /* Note palette (c1..c8): more vivid, higher alpha */
    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.40), rgba(var(--warn-rgb),0.16));
    --note-c1-bd: rgba(var(--warn-rgb),0.60);

    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.34), rgba(var(--accent-rgb),0.14));
    --note-c2-bd: rgba(var(--accent-rgb),0.58);

    --note-c3-bg: linear-gradient(180deg, rgba(34,197,94,0.30), rgba(34,197,94,0.12));
    --note-c3-bd: rgba(34,197,94,0.54);

    --note-c4-bg: linear-gradient(180deg, rgba(var(--bad-rgb),0.30), rgba(var(--bad-rgb),0.12));
    --note-c4-bd: rgba(var(--bad-rgb),0.54);

    --note-c5-bg: linear-gradient(180deg, rgba(167,139,250,0.30), rgba(167,139,250,0.12));
    --note-c5-bd: rgba(167,139,250,0.54);

    --note-c6-bg: linear-gradient(180deg, rgba(45,212,191,0.30), rgba(45,212,191,0.12));
    --note-c6-bd: rgba(45,212,191,0.54);

    --note-c7-bg: linear-gradient(180deg, rgba(148,163,184,0.20), rgba(148,163,184,0.07));
    --note-c7-bd: rgba(148,163,184,0.40);

    --note-c8-bg: linear-gradient(180deg, rgba(236,72,153,0.28), rgba(236,72,153,0.11));
    --note-c8-bd: rgba(236,72,153,0.52);

    /* Task FX: more presence */
    --task-hover-sheen-opacity: 0.32;
    --task-snap-pulse-opacity: 0.55;

    /* Task hover ring: more presence */
    --task-hover-ring-ms: 1250ms;
    --task-hover-outline-alpha: 0.72;
    --task-hover-outline-offset: 16px;
    --task-hover-inset-alpha: 0.60;
    --task-hover-outer-alpha: 0.28;

  }

  /* High contrast: sharp edges + strong readability (dark scheme) */
  body.theme-contrast{
    --bg: #000000;
    --panel: #0a0a0a;
    --panel2: #0e0e0e;
    --surface3: #0a0a0a;
    --surface4: #0e0e0e;
    --cal-surface: #0b0b0b;

    --text: #ffffff;
    --muted: rgba(255,255,255,0.72);
    --line: rgba(255,255,255,0.22);

    --accent: #00b7ff;
    --accent-rgb: 0,183,255;
    --warn: #ffcc00;
    --warn-rgb: 255,204,0;
    --bad: #ff3355;
    --bad-rgb: 255,51,85;

    --block: rgba(0,183,255,0.06);
    --block2: rgba(0,183,255,0.10);
    --task-border: rgba(var(--accent-rgb), 0.40);
    --task-selected: rgba(var(--accent-rgb), 0.92);
    --task-title-text: rgba(255,255,255,0.97);
    --task-body-text: rgba(255,255,255,0.92);
    --task-code-text: rgba(0,183,255,0.95);

    /* Task hover ring: strong */
    --task-hover-ring-ms: 950ms;
    --task-hover-outline-alpha: 0.70;
    --task-hover-outline-offset: 14px;
    --task-hover-inset-alpha: 0.50;
    --task-hover-outer-alpha: 0.26;

    --btn-bg: #141414;
    --btn-bd: rgba(255,255,255,0.22);
    --btn-bd-hover: rgba(255,255,255,0.32);
    --input-bg-soft: rgba(255,255,255,0.06);
    --input-bd-soft: rgba(255,255,255,0.22);

    --code-bg: #0f0f0f;
    --code-bd: rgba(255,255,255,0.22);
    --code-text: rgba(255,255,255,0.92);

    --grid-hour: rgba(255,255,255,0.18);
    --grid-qtr: rgba(255,255,255,0.05);
    --tick: rgba(255,255,255,0.24);
    --weekend-col-bg: rgba(255,255,255,0.04);
    --weekend-col-hover-bg: rgba(var(--accent-rgb), 0.08);
    --weekend-header-bg: rgba(255,255,255,0.06);
    --weekend-header-bd: rgba(255,255,255,0.24);

    --npill-bg: rgba(var(--warn-rgb), 0.16);
    --npill-bd: rgba(var(--warn-rgb), 0.46);
    --npill-text: rgba(255,255,255,0.94);

    --note-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.26), rgba(var(--warn-rgb),0.12));
    --note-bd: rgba(var(--warn-rgb), 0.46);
    --note-text: rgba(255,255,255,0.94);
    --note-meta: rgba(255,255,255,0.74);
    --note-handle-bg: rgba(255,255,255,0.08);
    --note-handle-bd: rgba(255,255,255,0.20);
    --note-pinned-bd: rgba(var(--warn-rgb), 0.70);

    --note-c1-bg: linear-gradient(180deg, rgba(var(--warn-rgb),0.34), rgba(var(--warn-rgb),0.14));
    --note-c1-bd: rgba(var(--warn-rgb),0.56);
    --note-c2-bg: linear-gradient(180deg, rgba(var(--accent-rgb),0.28), rgba(var(--accent-rgb),0.12));
    --note-c2-bd: rgba(var(--accent-rgb),0.56);
    --note-c4-bg: linear-gradient(180deg, rgba(var(--bad-rgb),0.26), rgba(var(--bad-rgb),0.12));
    --note-c4-bd: rgba(var(--bad-rgb),0.52);
  }

  body.theme-light .dimmed,
  body.theme-paper .dimmed{ opacity: 0.30; }

* { box-sizing: border-box; }
'''
