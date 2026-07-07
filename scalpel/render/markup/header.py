# scalpel/render/markup/header.py
from __future__ import annotations

MARKUP = r"""<header>
  <div class="header-toolbar">
    <div class="title-wrap">
      <div class="title"> < < S  C  A  L  P  E  L > ></div>
      <div class="subtitle">Discipline is Freedom</div>
    </div>
    <div class="meta-row">
      <div class="meta" id="ctxMeta"></div>
      <div class="meta pending" id="pendingMeta" title="Local pending changes" role="button" tabindex="0">Local clean</div>
      <div class="meta meta-detail" id="meta"></div>
      <div class="meta meta-detail" id="selMeta"></div>
    </div>
    <div class="viewwin" id="viewwin">
      <button class="icon" id="vwPrevPage" title="Back one window">«</button>
      <button class="icon" id="vwPrevDay" title="Back one day">‹</button>
      <button class="small" id="vwToday" title="Jump to today">Today</button>
      <button class="icon" id="vwNextDay" title="Forward one day">›</button>
      <button class="icon" id="vwNextPage" title="Forward one window">»</button>

      <span class="vwlabel">Start</span>
      <input id="vwStart" type="date" />

      <span class="vwlabel">Days</span>
      <select id="vwDays"></select>
    </div>
    <div class="btn actionbar">
      <div class="action-main">
        <button id="btnToggleBacklog" class="small toggle btn-soft on" data-ico="BL" type="button" aria-pressed="true" title="Show or hide Backlog">Backlog</button>
        <button id="btnCopy" class="btn-primary" data-ico="CP">Copy commands</button>
        <button id="btnToggleCommands" class="small toggle btn-soft" data-ico="CM" type="button" aria-pressed="false" title="Show or hide Commands">Commands</button>
        <div class="action-overflow" id="actionOverflow">
          <button
            class="small btn-soft"
            id="btnMoreActions"
            data-ico="..."
            type="button"
            aria-haspopup="dialog"
            aria-expanded="false"
            aria-controls="overflowMenu"
            title="More planner actions"
          >
            More
          </button>
          <div class="overflow-menu" id="overflowMenu" role="dialog" aria-label="Planner controls" hidden>
            <div class="overflow-control zoom">
              <span class="zlabel">Zoom</span>
              <input id="zoom" type="range" min="1" max="6" step="0.5" />
              <span class="zval" id="zoomVal"></span>
            </div>
            <label class="overflow-field">
              <span>Overdue days</span>
              <select id="vwOverdue"></select>
            </label>
            <button id="btnHelp" class="small btn-quiet" data-ico="?" data-key="?" title="Help and shortcuts (?)">Help</button>
            <button id="btnTheme" class="btn-soft" data-ico="TH" data-key="Ctrl+Shift+T" title="Click to cycle theme • Shift+click or Ctrl+Shift+T to manage">Light theme</button>
            <button id="btnTogglePanels" class="btn-soft" data-ico="PN">Hide sidebars</button>
            <button id="btnNotes" class="btn-soft" data-ico="NT" data-key="Ctrl+Shift+N" title="Toggle notes (Ctrl+Shift+N)">Notes</button>
            <button id="btnRefresh" class="btn-soft" data-ico="RF" title="Refresh data from Taskwarrior">Refresh data</button>
            <button id="btnUndo" class="btn-soft" data-ico="UN" data-key="Ctrl/Cmd+Z" title="Undo last local change (Ctrl/Cmd+Z)">Undo</button>
            <button id="btnRedo" class="btn-soft" data-ico="RD" data-key="Ctrl/Cmd+Shift+Z" title="Redo last undone change (Ctrl/Cmd+Shift+Z)">Redo</button>
            <button id="btnNauticalPreview" class="small toggle btn-soft" data-ico="NA" title="Toggle future Nautical instances">Nautical: Off</button>
            <button id="btnShowCompleted" class="small toggle btn-soft" data-ico="DN" type="button" aria-pressed="false" title="Show or hide completed tasks included in this payload">Completed: Off</button>
            <button id="btnTimeBands" class="small toggle btn-soft on" data-ico="TB" type="button" aria-pressed="true" title="Show or hide planning bands in the calendar">Bands: On</button>
            <button id="btnBandEditor" class="small btn-soft" data-ico="BE" type="button" title="Edit planning band titles and times">Edit bands</button>
            <button id="btnClearSel" class="btn-soft" data-ico="CL" data-key="Esc">Clear selection</button>
            <button id="btnReset" class="danger" data-ico="RS">Reset view plan</button>
            <button id="btnCommand" class="small btn-soft" data-ico="KC" data-key="Ctrl/Cmd+K" title="Search and commands (Ctrl/Cmd+K)">Search</button>
            <button id="btnDensity" class="small toggle btn-soft" data-ico="DN" data-key="Ctrl+Shift+M" title="Toggle compact density (Ctrl+Shift+M)">Density: Comfort</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</header>"""
