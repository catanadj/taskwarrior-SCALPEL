# scalpel/render/css/part04_panels_palette.py
from __future__ import annotations

CSS_PART = r'''
  .card {
    background:
      linear-gradient(165deg, rgba(255,255,255,0.025), rgba(255,255,255,0.00)),
      var(--panel);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow:
      0 12px 24px var(--shadow),
      0 1px 0 rgba(255,255,255,0.04) inset;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
    backdrop-filter: blur(9px);
  }
  .card .card-h {
    padding: 11px 13px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.00)),
      var(--panel2);
    border-bottom: 1px solid var(--line);
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .card .card-h small {
    color: var(--muted);
    font-weight: 600;
    letter-spacing: 0.01em;
    text-transform: none;
    font-size: 12px;
  }
  .card .card-b {
    padding: 10px 12px;
    overflow: auto;
    min-height: 0;
    scrollbar-color: rgba(var(--accent-rgb), 0.40) transparent;
  }
  .card .card-b::-webkit-scrollbar{ width: 10px; height: 10px; }
  .card .card-b::-webkit-scrollbar-thumb{
    background: rgba(var(--accent-rgb), 0.35);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
  }
  .card .card-b::-webkit-scrollbar-track{ background: transparent; }

  .search {
    width: 100%;
    padding: 9px 11px;
    border-radius: 10px;
    border: 1px solid var(--input-bd);
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)), var(--input-bg);
    color: var(--text);
    outline: none;
    box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset;
  }
  .search::placeholder{ color: rgba(154,166,178,0.88); }
  .search:focus{
    border-color: rgba(var(--accent-rgb), 0.48);
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.12);
  }

  /* Palette tree */
  .palette { border: 1px solid var(--code-bd); border-radius: 12px; background: var(--code-bg); padding: 10px; box-shadow: 0 8px 18px rgba(0,0,0,0.10) inset; }
  .palette .hint { color: var(--muted); font-size: 12px; margin-bottom: 10px; }
  .ptree { font-size: 13px; }
  .pnode { display:flex; align-items:center; justify-content:space-between; gap:10px; padding: 6px 6px; border-radius: 10px; }
  .pnode:hover { background: rgba(255,255,255,0.03); }
  .pnode .left { display:flex; align-items:center; gap:8px; min-width:0; }
  .pnode .twisty { width: 18px; height: 18px; border-radius: 6px; border: 1px solid rgba(154,166,178,0.25); display:grid; place-items:center; color: var(--muted); font-size: 12px; user-select:none; cursor:pointer; flex: 0 0 auto; }
  .pnode .label { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .pnode .count { color: var(--muted); font-size: 12px; flex: 0 0 auto; }
  .pnode .right { display:flex; align-items:center; gap:8px; flex: 0 0 auto; }
  .pnode input[type="color"] { width: 34px; height: 26px; padding: 0; background: transparent; border: 1px solid rgba(154,166,178,0.25); border-radius: 8px; cursor: pointer; }
  .pnode .clear { font-size: 12px; color: var(--muted); border: 1px solid rgba(154,166,178,0.20); background: rgba(255,255,255,0.02); padding: 4px 8px; border-radius: 10px; cursor: pointer; }
  .pnode .clear:hover { border-color: rgba(154,166,178,0.35); }
  .pchildren { margin-left: 18px; border-left: 1px dashed rgba(154,166,178,0.18); padding-left: 10px; }
  .palette-ops{ margin-bottom: 8px; }


  /* Goals panel */
  .goals-box{
    border: 1px solid rgba(154,166,178,0.18);
    border-radius: 12px;
    background: rgba(255,255,255,0.02);
    padding: 10px;
    margin-bottom: 10px;
  }
  .goals-box.collapsed .goals-body{ display:none; }
  .goals-head{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:10px;
    cursor:pointer;
    user-select:none;
    padding: 4px 6px;
    border-radius: 10px;
    border: 1px solid rgba(154,166,178,0.12);
    background: rgba(0,0,0,0.10);
  }
  .goals-head:hover{ border-color: rgba(154,166,178,0.22); }
  .goals-head .t{ font-weight: 900; }

  .focusbar{
    border: 1px solid rgba(154,166,178,0.18);
    border-radius: 12px;
    background: rgba(255,255,255,0.02);
    padding: 10px;
    margin: 8px 0 10px 0;
  }
  .focusbar .fhead{
    display:flex;
    align-items:baseline;
    justify-content:space-between;
    gap:10px;
    margin-bottom: 8px;
  }
  .focusbar .ftitle{ font-weight: 900; letter-spacing: 0.2px; }
  .focusbar .fmeta{
    font-size: 12px;
    font-weight: 800;
    color: rgba(154,166,178,0.98);
    border: 1px solid rgba(154,166,178,0.22);
    background: rgba(255,255,255,0.03);
    border-radius: 999px;
    padding: 2px 8px;
    white-space: nowrap;
    min-height: 18px;
  }
  .focusbar .frow{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom: 8px; }
  .focusbar .seg{
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid var(--btn-bd);
    background: var(--btn-bg);
    color: var(--text);
    font-weight: 850;
    cursor:pointer;
  }
  .focusbar .seg:hover{
    border-color: var(--btn-bd-hover);
    background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.00)), var(--btn-bg);
  }
  .focusbar .seg:focus-visible{
    outline: 2px solid rgba(var(--accent-rgb), 0.64);
    outline-offset: 1px;
  }
  .focusbar .seg.on{
    border-color: rgba(var(--accent-rgb),0.60);
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb),0.18) inset;
    background: rgba(var(--accent-rgb),0.10);
    color: var(--text);
  }
  .focusbar .fhint{
    font-size: 12px;
    color: rgba(154,166,178,0.92);
    line-height: 1.25;
  }

  .lsec-focus .focusbar{
    border: 0;
    border-radius: 0;
    background: transparent;
    padding: 0;
    margin: 0;
  }
  .lsec-focus .focusbar .frow:last-of-type{
    margin-bottom: 6px;
  }

  .lsec{
    border: 1px solid var(--code-bd);
    border-radius: 12px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
      var(--surface-pop);
    overflow: hidden;
  }
  .lsec-h{
    width: 100%;
    border: 0;
    border-bottom: 1px solid rgba(154,166,178,0.16);
    border-radius: 0;
    margin: 0;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
      var(--panel2);
    padding: 8px 10px;
    display:grid;
    grid-template-columns: 1fr auto auto;
    align-items:center;
    gap:10px;
    text-align:left;
    box-shadow:none;
  }
  .lsec-h:hover{
    transform: none;
    box-shadow: none;
    border-bottom-color: rgba(var(--accent-rgb), 0.30);
  }
  .lsec-h:focus-visible{
    outline: 2px solid rgba(var(--accent-rgb), 0.68);
    outline-offset: -2px;
    position: relative;
    z-index: 1;
  }
  .lsec-h .lsec-t{
    font-weight: 820;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    font-size: 12px;
  }
  .lsec-h small{
    color: var(--muted);
    font-weight: 700;
    letter-spacing: 0.01em;
    font-size: 12px;
    white-space: nowrap;
  }
  .lsec-h .lsec-chev{
    color: var(--muted);
    font-size: 12px;
    transition: transform 120ms ease;
  }
  .lsec.open .lsec-h .lsec-chev{
    transform: rotate(90deg);
  }
  .lsec-b{
    padding: 10px;
    overflow: hidden;
    transform: translateY(0);
    opacity: 1;
    transition:
      max-height 160ms cubic-bezier(0.2, 0.7, 0.2, 1),
      opacity 120ms ease,
      transform 120ms ease;
  }
  .lsec-b.anim-open{
    opacity: 1;
    transform: translateY(0);
  }
  .lsec-b.anim-close{
    opacity: 0;
    transform: translateY(-4px);
  }
  .lsec-b[hidden]{
    display:none;
  }
  .lsec-problems .hint{
    margin: 0;
  }
  .lsec-palette .palette{
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    padding: 0;
  }
  .lsec-palette .palette .hint{
    margin-bottom: 8px;
  }

  .dimmed{
    opacity: 0.18 !important;
    filter: saturate(0.30) contrast(0.95);
  }

  .gitem.focused{
    border-color: rgba(var(--accent-rgb),0.55) !important;
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb),0.14) inset;
    background: rgba(var(--accent-rgb),0.06);
  }

  .pnode.focused{
    border-color: rgba(var(--accent-rgb),0.50) !important;
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb),0.12) inset;
    background: rgba(var(--accent-rgb),0.05);
  }
  .pnode .label.clickable{ cursor:pointer; }
  .pnode .label.clickable:hover{ text-decoration: underline; text-underline-offset: 3px; }

  .goals-head .s{ color: var(--muted); font-size: 12px; }
  .goals-body{ padding: 10px 6px 2px 6px; }
  .glist{ display:flex; flex-direction:column; gap:8px; }
  .gitem{
    display:grid;
    grid-template-columns: 18px 18px 1fr auto;
    gap:10px;
    align-items:center;
    padding: 8px 8px;
    border-radius: 10px;
    border: 1px solid rgba(154,166,178,0.14);
    background: rgba(255,255,255,0.02);
  }
  .gitem:hover{ border-color: rgba(154,166,178,0.25); }
  .gswatch{
    width: 14px; height: 14px; border-radius: 5px;
    border: 1px solid rgba(255,255,255,0.20);
    box-shadow: 0 0 12px rgba(0,0,0,0.25);
  }
  .gname{ font-weight: 850; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .gmeta{ font-size: 12px; color: var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .gcount{ font-size: 12px; color: var(--muted); font-weight: 800; }

  /* Extra emphasis for goal-colored tasks (in addition to neon envelope) */
  .evt.goal-colored{
    background:
      linear-gradient(180deg, rgba(var(--evt-accent-rgb, 99,179,255), 0.14), rgba(var(--evt-accent-rgb, 99,179,255), 0.06)),
      linear-gradient(180deg, var(--block), var(--block2));
  }
  .item.goal-colored{
    background:
      linear-gradient(90deg, rgba(var(--row-accent-rgb, 99,179,255), 0.14), rgba(var(--row-accent-rgb, 99,179,255), 0.04));
  }

  /* Calendar grid */


/* Notes panel */
.notesbox{
  border: 1px solid rgba(154,166,178,0.18);
  border-radius: 12px;
  background: rgba(255,255,255,0.02);
  padding: 10px 10px;
  margin-bottom: 10px;
}
.notesbox.collapsed .notes-body{ display:none; }
.notes-head{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:10px;
  cursor:pointer;
  user-select:none;
  padding: 6px 8px;
  border-radius: 10px;
  border: 1px solid rgba(154,166,178,0.12);
  background: var(--surface-pop);
}
.notes-head:hover{ border-color: rgba(154,166,178,0.22); }
.notes-head .t{ font-weight: 900; }
.notes-head .s{ color: var(--muted); font-size: 12px; display:flex; align-items:center; gap:8px; }
.notes-head .chev{ color: var(--muted); font-size: 12px; }
.notes-body{ padding: 10px 6px 2px 6px; }
.notes-new{ display:flex; gap:8px; align-items:center; margin-bottom: 8px; }
.notes-new input{ flex: 1 1 auto; }
.notes-list{ display:flex; flex-direction:column; gap:8px; }
.nghdr{
  margin-top: 10px;
  margin-bottom: 6px;
  font-weight: 900;
  color: var(--text);
  display:flex;
  justify-content:space-between;
  align-items:baseline;
  gap:10px;
}
.nghdr small{
  font-size: 12px;
  font-weight: 800;
  color: rgba(154,166,178,0.98);
  border: 1px solid rgba(154,166,178,0.22);
  background: var(--surface-pop);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}
.nitem{
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-pop);
  padding: 8px 10px;
  display:flex;
  gap:10px;
  align-items:flex-start;
  cursor: grab;
  user-select:none;
}


.nitem .sw{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 1px solid rgba(154,166,178,0.22);
  background: var(--surface-pop);
  flex: 0 0 auto;
  margin-top: 4px;
}
.nitem .sw.none{ background: var(--surface-pop); border-color: var(--btn-bd); opacity: 0.65; }
.nitem .sw.c1{ background: var(--note-c1-bg); border-color: var(--note-c1-bd); }
.nitem .sw.c2{ background: var(--note-c2-bg); border-color: var(--note-c2-bd); }
.nitem .sw.c3{ background: var(--note-c3-bg); border-color: var(--note-c3-bd); }
.nitem .sw.c4{ background: var(--note-c4-bg); border-color: var(--note-c4-bd); }
.nitem .sw.c5{ background: var(--note-c5-bg); border-color: var(--note-c5-bd); }
.nitem .sw.c6{ background: var(--note-c6-bg); border-color: var(--note-c6-bd); }
.nitem .sw.c7{ background: var(--note-c7-bg); border-color: var(--note-c7-bd); }
.nitem .sw.c8{ background: var(--note-c8-bg); border-color: var(--note-c8-bd); }
.nitem:active{ cursor: grabbing; }
.nitem.pinned{
  border-color: var(--note-pinned-bd);
  box-shadow: 0 0 0 2px rgba(var(--warn-rgb),0.08) inset;
}
.nitem .txt{ flex: 1 1 auto; min-width:0; }
.nitem .line1{ font-weight: 850; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nitem .line2{ margin-top: 3px; font-size: 12px; color: var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.nitem .acts{ flex: 0 0 auto; display:flex; gap:6px; }
.iconbtn{
  width: 28px;
  height: 26px;
  border-radius: 10px;
  padding: 0;
  display:grid;
  place-items:center;
  font-weight: 900;
}


  /* -----------------------------
     Day balance (right panel)
     ----------------------------- */
  .daybal{
    margin-top: 10px;
    padding: 10px 10px 8px 10px;
    border-radius: 14px;
    background: rgba(0,0,0,0.10);
    border: 1px solid rgba(255,255,255,0.06);
  }
  [data-theme="light"] .daybal{
    background: rgba(0,0,0,0.04);
    border-color: rgba(15,23,42,0.10);
  }

  .daybal .dbh{
    display:flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }
  .daybal .dbh > div{
    font-weight: 700;
    letter-spacing: 0.2px;
  }
  .daybal .dbh small{
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }

  .daybal .dbbar{
    height: 10px;
    border-radius: 999px;
    overflow: hidden;
    display:flex;
    background: rgba(255,255,255,0.06);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
  }
  [data-theme="light"] .daybal .dbbar{
    background: rgba(15,23,42,0.08);
    box-shadow: inset 0 0 0 1px rgba(15,23,42,0.08);
  }

  .daybal .dbseg{
    height: 100%;
  }

  .daybal .dbleg{
    margin-top: 10px;
    display:flex;
    flex-direction: column;
    gap: 6px;
  }
  .daybal .dbrow{
    display:flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    font-size: 12px;
    line-height: 1.15;
  }
  .daybal .dbrow .left{
    display:flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .daybal .dbrow .sw{
    width: 10px;
    height: 10px;
    border-radius: 3px;
    border: 1px solid rgba(0,0,0,0.15);
    box-shadow: 0 1px 0 rgba(255,255,255,0.12) inset;
    flex: 0 0 auto;
  }
  [data-theme="light"] .daybal .dbrow .sw{
    border-color: rgba(15,23,42,0.18);
    box-shadow: 0 1px 0 rgba(255,255,255,0.55) inset;
  }
  .daybal .dbrow .lbl{
    overflow:hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
  }
  .daybal .dbrow .val{
    color: var(--muted);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

'''
