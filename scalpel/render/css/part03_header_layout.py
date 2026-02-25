# scalpel/render/css/part03_header_layout.py
from __future__ import annotations

CSS_PART = r'''  header {
    position: sticky;
    top: 0;
    z-index: 80;
    padding: 12px clamp(12px, 1.7vw, 20px);
    border-bottom: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
    background:
      radial-gradient(90% 180% at 0% 0%, var(--header-glow), transparent 55%),
      linear-gradient(180deg, var(--hdr-top), var(--hdr-bot));
    box-shadow: 0 7px 16px rgba(2,10,20,0.20);
    backdrop-filter: blur(10px);
  }

  header .header-primary{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  header .header-secondary{
    display: flex;
    align-items: center;
    gap: 10px;
    padding-top: 8px;
    border-top: 1px solid rgba(154,166,178,0.18);
    flex-wrap: wrap;
  }

  header .title-wrap{
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 225px;
  }
  header .title{
    font-weight: 760;
    font-size: 18px;
    line-height: 1.1;
  }
  header .subtitle{
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.9;
  }
  header .meta-row{
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  header .meta {
    color: var(--muted);
    font-size: 12px;
    white-space: nowrap;
    padding: 3px 9px;
    border-radius: 999px;
    border: 1px solid rgba(154,166,178,0.24);
    background: var(--surface-pop);
  }
  header .meta.pending{
    cursor: pointer;
  }
  header #ctxMeta{
    border-color: rgba(var(--accent-rgb), 0.32);
    background: rgba(var(--accent-rgb), 0.10);
    color: var(--text);
    font-weight: 700;
  }
  header .meta.pending.dirty{
    color: var(--text);
    border-color: rgba(var(--warn-rgb), 0.50);
    background: rgba(var(--warn-rgb), 0.18);
    box-shadow: 0 0 0 1px rgba(var(--warn-rgb), 0.18) inset;
  }
  header .btn {
    margin-left: auto;
  }
  header .action-main{
    display: flex;
    gap: 7px;
    flex-wrap: wrap;
    justify-content: flex-end;
    align-items: center;
  }
  header .action-overflow{
    position: relative;
  }
  header .action-overflow.open > #btnMoreActions{
    border-color: rgba(var(--accent-rgb), 0.65);
    background: rgba(var(--accent-rgb), 0.16);
    box-shadow:
      0 0 0 1px rgba(var(--accent-rgb), 0.26) inset,
      0 8px 18px rgba(var(--accent-rgb), 0.22);
  }
  header .overflow-menu{
    position: absolute;
    right: 0;
    top: calc(100% + 8px);
    min-width: 240px;
    padding: 8px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background:
      linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.00)),
      var(--panel2);
    box-shadow:
      0 20px 38px rgba(2,10,20,0.35),
      0 1px 0 rgba(255,255,255,0.04) inset;
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 90;
    max-height: min(65vh, 520px);
    overflow: auto;
  }
  header .overflow-menu[hidden]{
    display: none;
  }
  header .overflow-menu button{
    width: 100%;
    text-align: left;
    justify-content: flex-start;
    box-shadow: none;
  }
  header .overflow-menu button[data-key]{
    justify-content: space-between;
  }
  header .overflow-menu button[data-ico]::before{
    min-width: 1.8em;
  }
  header .overflow-menu button:hover{
    transform: none;
    box-shadow: 0 6px 14px rgba(0,0,0,0.16);
  }

  button {
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.00)), var(--btn-bg);
    color: var(--text);
    border: 1px solid var(--btn-bd);
    border-radius: 11px;
    padding: 8px 10px;
    cursor: pointer;
    font-weight: 650;
    box-shadow: 0 2px 6px rgba(0,0,0,0.16);
  }
  button:hover {
    border-color: var(--btn-bd-hover);
    transform: translateY(-1px);
    box-shadow: 0 5px 11px rgba(0,0,0,0.16);
  }
  button:active { transform: translateY(0); box-shadow: 0 2px 6px rgba(0,0,0,0.16); }
  button.small { padding: 6px 8px; border-radius: 9px; font-size: 12px; }
  button:disabled {
    background: var(--btn-disabled-bg);
    border-color: var(--btn-disabled-bd);
    color: var(--btn-disabled-text);
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
  }
  button[data-ico]{
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  button[data-ico]::before{
    content: attr(data-ico);
    display: inline-grid;
    place-items: center;
    min-width: 1.7em;
    height: 1.45em;
    padding: 0 0.28em;
    border-radius: 999px;
    border: 1px solid rgba(154,166,178,0.30);
    background: rgba(255,255,255,0.03);
    color: var(--muted);
    font-size: 10px;
    font-weight: 780;
    letter-spacing: 0.03em;
    line-height: 1;
  }
  button[data-key]{
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  button[data-key]::after{
    content: attr(data-key);
    margin-left: auto;
    display: inline-grid;
    place-items: center;
    padding: 0 0.5em;
    min-height: 1.5em;
    border-radius: 8px;
    border: 1px solid rgba(154,166,178,0.32);
    background: rgba(255,255,255,0.03);
    color: var(--muted);
    font-size: 10px;
    font-weight: 740;
    letter-spacing: 0.02em;
    line-height: 1;
    white-space: nowrap;
  }
  button[data-key]:hover::after{
    border-color: rgba(var(--accent-rgb), 0.45);
    color: var(--text);
  }
  button.btn-soft{
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)), var(--btn-bg);
  }
  button.btn-quiet{
    background: var(--surface-pop);
    box-shadow: none;
  }
  button.btn-quiet:hover{
    box-shadow: 0 3px 8px rgba(0,0,0,0.12);
  }
  button.btn-primary{
    border-color: rgba(var(--accent-rgb), 0.62);
    background:
      linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.00)),
      rgba(var(--accent-rgb), 0.18);
    box-shadow:
      0 0 0 1px rgba(var(--accent-rgb), 0.24) inset,
      0 7px 16px rgba(var(--accent-rgb), 0.16);
  }
  button.btn-primary::before{
    border-color: rgba(var(--accent-rgb), 0.50);
    background: rgba(var(--accent-rgb), 0.16);
    color: var(--text);
  }
  button.btn-primary:hover{
    border-color: rgba(var(--accent-rgb), 0.78);
    box-shadow:
      0 0 0 1px rgba(var(--accent-rgb), 0.32) inset,
      0 9px 20px rgba(var(--accent-rgb), 0.22);
  }
  button.danger::before{
    border-color: rgba(var(--bad-rgb), 0.45);
    background: rgba(var(--bad-rgb), 0.12);
    color: var(--danger-text);
  }

  button.toggle.on{
    border-color: rgba(var(--accent-rgb), 0.65);
    background: rgba(var(--accent-rgb), 0.16);
    color: var(--text);
    box-shadow:
      0 0 0 1px rgba(var(--accent-rgb), 0.26) inset,
      0 8px 18px rgba(var(--accent-rgb), 0.22);
  }

  button.danger { border-color: var(--danger-bd); color: var(--danger-text); }
  button.danger:hover { border-color: var(--danger-bd-hover); }

  .zoom {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border: 1px solid var(--input-bd-soft);
    border-radius: 12px;
    background: var(--surface-pop);
    backdrop-filter: blur(8px);
  }
  .zoom .zlabel { color: var(--muted); font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; }
  .zoom .zval { color: var(--muted); font-size: 12px; width: 76px; text-align: right; font-weight: 620; }
  .zoom input[type="range"] { width: 160px; accent-color: var(--accent); }

  .viewwin{
    display:flex;
    align-items:center;
    gap:6px;
    margin-left: auto;
    padding: 7px 10px;
    border: 1px solid var(--input-bd-soft);
    border-radius: 12px;
    background: var(--surface-pop);
    flex-wrap: wrap;
    backdrop-filter: blur(8px);
  }
  .viewwin .vwlabel{
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-left: 2px;
  }
  .viewwin input[type="date"], .viewwin select{
    height: 26px;
    border-radius: 8px;
    border: 1px solid var(--input-bd-soft);
    background: var(--input-bg-soft);
    color: var(--text);
    padding: 0 8px;
    font-size: 12px;
    outline: none;
  }
  .viewwin select{ padding-right: 18px; }
  .viewwin button.icon{
    width: 28px;
    padding: 0;
    height: 26px;
    line-height: 24px;
    border-radius: 8px;
  }

  .layout {
    display: grid;
    grid-template-columns: minmax(250px, 330px) minmax(0, 1fr) minmax(320px, 460px);
    gap: 14px;
    padding: 14px;
    height: calc(100vh - 84px);
  }

  .layout.panels-collapsed {
    grid-template-columns: 1fr !important;
    grid-template-rows: 1fr !important;
  }
  .layout.panels-collapsed section.left,
  .layout.panels-collapsed section.commands {
    display: none !important;
  }

  @media (max-width: 1050px){
    header{ padding: 10px 12px; gap: 8px; }
    header .title-wrap{ min-width: 0; }
    header .header-primary,
    header .header-secondary{
      width: 100%;
    }
    .viewwin{ margin-left: 0; width: 100%; }
    .zoom{ width: 100%; }
    header .btn{ width: 100%; margin-left: 0; }
    header .action-main{ justify-content: flex-start; }
  }

  @media (max-width: 760px){
    header{
      position: static;
      border-bottom-color: rgba(154,166,178,0.26);
    }
    header .title{ font-size: 17px; }
    header .subtitle{ letter-spacing: 0.06em; }
    .meta-row,
    .zoom,
    .viewwin{
      width: 100%;
    }
    .viewwin{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, max-content));
      justify-content: start;
      row-gap: 6px;
      overflow-x: auto;
    }
    header .action-main{
      width: 100%;
      align-items: stretch;
    }
    header .action-overflow{
      width: 100%;
    }
    header .action-overflow.open .overflow-menu{
      position: static;
      margin-top: 6px;
      width: 100%;
    }
    .layout{
      height: auto;
      min-height: 0;
      padding: 10px;
      gap: 10px;
    }
  }
'''
