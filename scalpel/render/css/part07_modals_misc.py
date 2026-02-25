# scalpel/render/css/part07_modals_misc.py
from __future__ import annotations

CSS_PART = r'''  .modal {
    width: min(720px, 100%);
    max-height: min(90vh, 920px);
    background:
      linear-gradient(170deg, rgba(255,255,255,0.04), rgba(255,255,255,0.00)),
      var(--code-bg);
    border: 1px solid var(--code-bd);
    border-radius: 16px;
    box-shadow:
      0 24px 72px rgba(0,0,0,0.52),
      0 1px 0 rgba(255,255,255,0.06) inset;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .modal .mh {
    padding: 11px 13px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.00)),
      var(--panel2);
    border-bottom: 1px solid var(--code-bd);
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:10px;
    flex: 0 0 auto;
  }
  .modal .mh .t {
    font-weight: 760;
    letter-spacing: 0.02em;
  }
  .modal .mb {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow: auto;
    min-height: 0;
  }
  .modal .mb .hint{
    margin: 0;
  }
  .modal .mf {
    padding: 10px 12px;
    display:flex;
    justify-content:flex-end;
    align-items: center;
    gap:8px;
    border-top: 1px solid var(--code-bd);
    background: rgba(255,255,255,0.02);
    flex: 0 0 auto;
  }
  .modal .mf .grow{
    flex: 1 1 auto;
  }
  .modal .row{
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .modal .row.wrap{
    flex-wrap: wrap;
  }
  .modal .field{
    display:flex;
    flex-direction:column;
    gap:4px;
    font-size:12px;
    color: var(--muted);
    min-width: 0;
  }
  .modal .field.wide{ flex: 1 1 260px; }
  .modal .field.med{ flex: 1 1 220px; }
  .modal .field.short{ flex: 0 0 96px; }
  .modal .field input,
  .modal .field select{
    width: 100%;
  }
  .modal .check-inline{
    display:flex;
    align-items:center;
    gap:6px;
    font-size:12px;
    color: var(--text);
    user-select:none;
  }
  .modal .check-inline input{
    transform: translateY(1px);
  }
  .modal textarea {
    width: 100%;
    min-height: 220px;
    resize: vertical;
    border-radius: 12px;
    border: 1px solid var(--btn-bd);
    background: var(--surface3);
    color: var(--text);
    padding: 10px 10px;
    outline: none;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 13px;
    line-height: 1.35;
  }
  .modal input[type="text"],
  .modal input[type="number"],
  .modal input[type="date"],
  .modal input[type="time"],
  .modal select{
    border-radius: 10px;
    border: 1px solid var(--input-bd);
    background: var(--input-bg);
    color: var(--text);
    padding: 6px 8px;
    outline:none;
    min-height: 32px;
    min-width: 0;
  }
  .modal input:focus,
  .modal select:focus,
  .modal textarea:focus{
    border-color: rgba(var(--accent-rgb), 0.52);
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.14);
  }
  .modal .ops{
    margin: 0;
  }
  .modal .ai-preview{
    max-height: 220px;
    overflow: auto;
    margin: 0;
  }

  /* Global transient status toast */
  .toast{
    position: fixed;
    right: 16px;
    bottom: 16px;
    max-width: min(560px, calc(100vw - 28px));
    border-radius: 12px;
    border: 1px solid rgba(var(--accent-rgb), 0.55);
    background: rgba(10, 18, 28, 0.90);
    color: var(--text);
    padding: 8px 11px;
    font-size: 12px;
    line-height: 1.35;
    box-shadow:
      0 10px 28px rgba(0,0,0,0.34),
      0 0 0 1px rgba(var(--accent-rgb), 0.20) inset;
    opacity: 0;
    transform: translateY(8px);
    pointer-events: none;
    z-index: 11000;
    transition: opacity 150ms ease, transform 150ms ease;
  }
  .toast.show{
    opacity: 1;
    transform: translateY(0);
  }

  /* Help + quick commands */
  .help-modal { width: min(860px, 100%); }
  .helpgrid{
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }
  .helpgrid .hsec{
    border: 1px solid var(--code-bd);
    border-radius: 12px;
    padding: 8px;
    background: rgba(255,255,255,0.02);
  }
  .helpgrid .sh{
    font-weight: 800;
    margin-bottom: 7px;
  }
  .hkrow{
    display:grid;
    grid-template-columns: minmax(120px, auto) 1fr;
    align-items: baseline;
    gap: 8px;
    margin-top: 6px;
    font-size: 12px;
  }
  .hk{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-weight: 700;
    color: var(--text);
    padding: 1px 6px;
    border-radius: 999px;
    border: 1px solid var(--btn-bd);
    background: var(--btn-bg);
    width: fit-content;
    white-space: nowrap;
  }
  .hv{ color: var(--muted); }

  .command-modal { width: min(680px, 100%); }
  .command-modal .mb{ display:flex; flex-direction:column; gap: 8px; }
  .command-modal .cmdk-head{
    min-width: 0;
    display:flex;
    flex-direction:column;
    gap: 6px;
  }
  .command-modal .cmdk-legend{
    display:flex;
    flex-wrap:wrap;
    gap: 6px;
    align-items:center;
  }
  .command-modal .cmdk-chip{
    display:inline-flex;
    align-items:center;
    gap: 6px;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--btn-bd);
    background: var(--btn-bg);
    color: var(--muted);
    font-size: 11px;
    font-weight: 650;
    white-space: nowrap;
  }
  .command-modal .cmdk-chip .k{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 11px;
    color: var(--text);
    letter-spacing: 0.02em;
  }
  .cmdk-list{
    display:flex;
    flex-direction:column;
    gap: 6px;
    max-height: 340px;
    overflow: auto;
    margin-top: 2px;
  }
  .cmdk-item{
    text-align:left;
    display:flex;
    align-items:baseline;
    justify-content:space-between;
    gap: 8px;
    border-radius: 11px;
    border: 1px solid var(--btn-bd);
    background: var(--btn-bg);
    padding: 7px 9px;
  }
  .cmdk-item .l{
    min-width: 0;
    font-weight: 740;
    color: var(--text);
  }
  .cmdk-item .s{
    font-size: 12px;
    color: var(--muted);
    margin-top: 3px;
  }
  .cmdk-item .k{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    color: var(--muted);
    font-size: 12px;
    white-space: nowrap;
  }
  .cmdk-item.active{
    border-color: rgba(var(--accent-rgb), 0.70);
    background: rgba(var(--accent-rgb), 0.14);
    box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.24) inset;
  }
  .cmdk-empty{
    border: 1px dashed var(--btn-bd);
    border-radius: 12px;
    padding: 12px;
    color: var(--muted);
    font-size: 12px;
  }

  .mobile-tabs{
    display: none;
  }

  @media (max-width: 1320px) {
    .layout { grid-template-columns: minmax(250px, 320px) 1fr; grid-template-rows: 1fr 330px; height: calc(100vh - 116px); }
    .layout .card.commands { grid-column: 1 / -1; }
    .layout.panels-collapsed { grid-template-columns: 1fr !important; grid-template-rows: 1fr !important; }
  }
  @media (max-width: 820px) {
    body{ padding-bottom: 66px; }
    .layout{
      grid-template-columns: 1fr;
      grid-template-rows: auto;
      height: auto;
      min-height: 0;
    }
    .layout.mobile-view{
      grid-template-columns: 1fr;
      grid-template-rows: 1fr;
      height: auto;
      min-height: 0;
    }
    .layout.mobile-view > section.card{
      display: none;
    }
    .layout.mobile-view.mobile-panel-left > section.left{
      display: flex;
    }
    .layout.mobile-view.mobile-panel-calendar > section.calendar{
      display: flex;
    }
    .layout.mobile-view.mobile-panel-commands > section.commands{
      display: flex;
    }
    .layout .card.commands{ grid-column: auto; }
    .layout .card{ min-height: 300px; }
    .mobile-tabs{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      position: fixed;
      left: 10px;
      right: 10px;
      bottom: 10px;
      z-index: 95;
      padding: 8px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.00)),
        var(--panel2);
      box-shadow:
        0 14px 28px rgba(0,0,0,0.28),
        0 1px 0 rgba(255,255,255,0.05) inset;
      backdrop-filter: blur(10px);
    }
    .mobile-tabs .mtab{
      border: 1px solid var(--btn-bd);
      background: var(--btn-bg);
      color: var(--muted);
      border-radius: 10px;
      padding: 7px 8px;
      font-size: 12px;
      font-weight: 760;
      text-align: center;
      box-shadow: none;
      transform: none;
    }
    .mobile-tabs .mtab.on{
      color: var(--text);
      border-color: rgba(var(--accent-rgb), 0.65);
      background: rgba(var(--accent-rgb), 0.14);
      box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.22) inset;
    }
    .mobile-tabs .mtab:hover{
      border-color: var(--btn-bd-hover);
      box-shadow: none;
      transform: none;
    }
    .modal-backdrop{
      padding: 10px;
      align-items: flex-end;
    }
    .modal{
      border-radius: 14px;
      width: min(100%, 760px);
      max-height: calc(100vh - 20px);
    }
    .modal .mh,
    .modal .mb,
    .modal .mf{
      padding-left: 10px;
      padding-right: 10px;
    }
    .modal .row{
      flex-direction: column;
      align-items: stretch;
    }
    .modal .field.wide,
    .modal .field.med,
    .modal .field.short{
      flex: 1 1 auto;
    }
    .modal .mf{
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .modal .mf button{
      min-width: 130px;
      flex: 1 1 140px;
    }
    .modal .mf .grow{
      display: none;
    }
    .notegrid, .notegrid2, .themegrid{ grid-template-columns: 1fr; }
    .noterep .repRow{ flex-direction: column; }
    .noterep .repBtns{ flex-wrap: wrap; }
    .helpgrid{ grid-template-columns: 1fr; }
    .hkrow{ grid-template-columns: 1fr; gap: 4px; }
    .command-modal .mh{
      align-items: flex-start;
    }
    .toast{ left: 10px; right: 10px; bottom: 82px; max-width: none; }
  }

/* Selected tasks list (Commands panel) */
.selbox{
  border: 1px solid rgba(154,166,178,0.25);
  border-radius: 12px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.03);
  margin-bottom: 10px;
}
.selhdr{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:10px;
  font-weight: 850;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
  color: var(--text);
}
.selmeta{
  font-size: 12px;
  font-weight: 800;
  color: rgba(154,166,178,0.98);
  border: 1px solid rgba(154,166,178,0.22);
  background: rgba(255,255,255,0.03);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}

.selextra{
  display:none;
  margin: 6px 0 8px 0;
  padding: 8px 9px;
  border-radius: 12px;
  border: 1px solid rgba(154,166,178,0.18);
  background: rgba(255,255,255,0.02);
}
.selex-top{
  display:grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  align-items: baseline;
  font-size: 12px;
  color: rgba(154,166,178,0.98);
}
.selex-top .k{ font-weight: 800; color: var(--text); }
.selex-top .v{ font-weight: 750; color: rgba(154,166,178,0.98); }
.selex-bot{
  margin-top: 8px;
  display:flex;
  flex-wrap:wrap;
  gap: 6px;
}

.sellist{
  display:flex;
  flex-direction:column;
  gap: 6px;
}
.selitem{
  display:grid;
  grid-template-columns: 68px 1fr;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 12px;
  border: 1px solid rgba(154,166,178,0.18);
  background: rgba(255,255,255,0.02);
  cursor: pointer;
}
.selitem:hover{
  border-color: rgba(var(--accent-rgb),0.35);
  background: rgba(var(--accent-rgb),0.06);
}
.selitem .sid{
  font-weight: 900;
  font-size: 12px;
  color: var(--text);
  letter-spacing: 0.2px;
  border: 1px solid rgba(154,166,178,0.22);
  background: rgba(255,255,255,0.02);
  border-radius: 999px;
  height: 22px;
  display:flex;
  align-items:center;
  justify-content:center;
  margin-top: 1px;
}
.selitem .sbody{ min-width: 0; }
.selitem .sdesc{
  font-weight: 850;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.selitem .sline2,
.selitem .sline3{
  margin-top: 4px;
  display:flex;
  flex-wrap:wrap;
  gap: 6px;
  font-size: 12px;
  color: rgba(154,166,178,0.98);
}

/* Next up banner */
.nextup{
  border: 1px solid rgba(154,166,178,0.25);
  border-radius: 14px;
  padding: 8px 10px;
  background: rgba(255,255,255,0.03);
  margin-bottom: 10px;
}
  .nusep{ height:1px; background: rgba(154,166,178,0.22); margin: 8px 0; border-radius: 1px; }
.nuh{
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:10px;
  font-weight: 900;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
  color: var(--text);
}
.nuh small{
  font-size: 12px;
  font-weight: 800;
  color: rgba(154,166,178,0.98);
  border: 1px solid rgba(154,166,178,0.22);
  background: rgba(255,255,255,0.03);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}
.nub{
  display:flex;
  flex-direction:column;
  gap:10px;
}
.nurow{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:10px;
}

.nutxt{
  flex: 1 1 auto;
  min-width: 0;
}
.nutitle{
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nusub{
  margin-top: 2px;
  font-size: 12px;
  color: rgba(154,166,178,0.98);
}

/* Note + Theme modals */
.notegrid, .notegrid2{
  display:grid;
  grid-template-columns: repeat(4, minmax(0,1fr));
  gap: 8px;
  align-items:center;
}
.notegrid2 label{ display:flex; flex-direction:column; gap:4px; font-size:12px; color: var(--muted); }
.notegrid2 input{
  border-radius: 10px;
  border: 1px solid var(--input-bd);
  background: var(--input-bg);
  color: var(--text);
  padding: 6px 8px;
  outline:none;
}
.notegrid .ck{ font-size: 12px; color: var(--text); opacity: 0.92; user-select:none; }
.notegrid .ck input{ transform: translateY(1px); }

.notecolor .clbl{ font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.notecolor .cpal{ display:flex; flex-wrap:wrap; gap: 6px; }
.csw{
  width: 34px;
  height: 26px;
  border-radius: 12px;
  border: 1px solid var(--btn-bd);
  background: var(--btn-bg);
  cursor:pointer;
  padding: 0;
}
.csw.none{ width: auto; padding: 0 10px; height: 26px; font-size: 12px; font-weight: 800; color: var(--muted); background: var(--btn-bg); }
.csw.c1{ background: var(--note-c1-bg); border-color: var(--note-c1-bd); }
.csw.c2{ background: var(--note-c2-bg); border-color: var(--note-c2-bd); }
.csw.c3{ background: var(--note-c3-bg); border-color: var(--note-c3-bd); }
.csw.c4{ background: var(--note-c4-bg); border-color: var(--note-c4-bd); }
.csw.c5{ background: var(--note-c5-bg); border-color: var(--note-c5-bd); }
.csw.c6{ background: var(--note-c6-bg); border-color: var(--note-c6-bd); }
.csw.c7{ background: var(--note-c7-bg); border-color: var(--note-c7-bd); }
.csw.c8{ background: var(--note-c8-bg); border-color: var(--note-c8-bd); }
.csw.sel{ box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.22) inset, 0 0 0 1px rgba(var(--accent-rgb), 0.30); }

.noterep .repRow{ display:flex; gap:10px; align-items:flex-start; justify-content:space-between; }
.noterep .repDays{ display:flex; flex-wrap:wrap; gap:6px 10px; }
.noterep .dow{ font-size: 12px; color: var(--text); opacity: 0.92; user-select:none; }
.noterep .repBtns{ display:flex; gap:6px; }
.noterep .repBtns .small{ padding: 5px 9px; }
.noterep #noteRepeatHint{ margin-top: 6px; }

.notefoot{ display:flex; align-items:center; gap:10px; }

/* Theme manager modal */
.themegrid{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  align-items:end;
}
.themegrid label{ display:flex; flex-direction:column; gap:4px; font-size:12px; color: var(--muted); }
.themegrid select{
  border-radius: 10px;
  border: 1px solid var(--input-bd);
  background: var(--input-bg);
  color: var(--text);
  padding: 6px 8px;
  outline:none;
}
.pill{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid var(--btn-bd);
  background: var(--btn-bg);
  color: var(--text);
  font-weight: 850;
  width: fit-content;
}
.themesw{
  display:flex;
  flex-wrap:wrap;
  gap: 6px;
  margin-top: 0;
}
.themesw .sw{
  width: 30px;
  height: 20px;
  border-radius: 10px;
  border: 1px solid var(--btn-bd);
}
.themesw .sw.c1{ background: var(--note-c1-bg); border-color: var(--note-c1-bd); }
.themesw .sw.c2{ background: var(--note-c2-bg); border-color: var(--note-c2-bd); }
.themesw .sw.c3{ background: var(--note-c3-bg); border-color: var(--note-c3-bd); }
.themesw .sw.c4{ background: var(--note-c4-bg); border-color: var(--note-c4-bd); }
.themesw .sw.c5{ background: var(--note-c5-bg); border-color: var(--note-c5-bd); }
.themesw .sw.c6{ background: var(--note-c6-bg); border-color: var(--note-c6-bd); }
.themesw .sw.c7{ background: var(--note-c7-bg); border-color: var(--note-c7-bd); }
.themesw .sw.c8{ background: var(--note-c8-bg); border-color: var(--note-c8-bd); }
.mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

  /* Theme editor */
  #themeEditModal .modal { width: min(760px, 100%); }
  .themedit-sec{ margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--line); }
  .themedit-sec .sh{ font-weight: 650; margin-bottom: 8px; }
  .themedit-grid{ display: flex; flex-direction: column; gap: 6px; }
  .themedit-grid .r{ display:flex; align-items:center; gap:10px; padding:6px 8px; background: var(--surface4); border:1px solid var(--line); border-radius: 10px; }
  .themedit-grid .r .k{ width: 42px; font-weight: 650; opacity: 0.9; }
  .themedit-grid .r .sw{ width: 22px; height: 22px; border-radius: 6px; border:1px solid var(--line); background: var(--npill-bg); }
  .themedit-grid .r input[type="color"]{ width: 42px; height: 26px; padding:0; border:1px solid var(--line); background: transparent; border-radius: 8px; }
  .themedit-grid .r input[type="text"]{ flex: 1 1 auto; min-width: 220px; }
  .themedit-grid .r input[type="range"]{ flex:1 1 auto; }
  .themedit-grid .r .aval{ width: 44px; text-align: right; opacity: 0.85; }
  .themedit-grid.core .r .k{ width: 120px; font-weight: 600; }
  .themedit-alpha{ display:flex; align-items:center; gap:10px; margin-top:8px; padding:6px 8px; background: var(--surface4); border:1px solid var(--line); border-radius: 10px; }
  .themedit-alpha .lbl{ width: 140px; opacity: 0.85; }
  .themedit-alpha input[type="range"]{ flex: 1 1 auto; }
  #themeEditNameInput{ min-width: 220px; }

'''
