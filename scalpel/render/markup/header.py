# scalpel/render/markup/header.py
from __future__ import annotations

MARKUP = r"""<header>
  <div class="header-primary">
    <div class="title-wrap">
      <div class="title"> < < S  C  A  L  P  E  L > ></div>
      <div class="subtitle">Discipline is Freedom</div>
    </div>
    <div class="meta-row">
      <div class="meta" id="meta"></div>
      <div class="meta" id="selMeta"></div>
      <div class="meta" id="ctxMeta"></div>
      <div class="meta pending" id="pendingMeta" title="Local pending changes" role="button" tabindex="0">Local clean</div>
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

      <span class="vwlabel">Overdue</span>
      <select id="vwOverdue"></select>
    </div>
  </div>

  <div class="header-secondary">
    <div class="zoom">
      <span class="zlabel">Zoom</span>
      <input id="zoom" type="range" min="1" max="6" step="0.5" />
      <span class="zval" id="zoomVal"></span>
    </div>
    <div class="btn actionbar">
      <div class="action-main">
      <button id="btnCopy" class="btn-primary" data-ico="CP">Copy commands</button>
      <button id="btnHelp" class="small btn-quiet" data-ico="?" data-key="?" title="Help and shortcuts (?)">Help</button>
      <button id="btnTheme" class="btn-soft" data-ico="TH" data-key="Ctrl+Shift+T" title="Click to cycle theme • Shift+click or Ctrl+Shift+T to manage">Light theme</button>
        <div class="action-overflow" id="actionOverflow">
          <button
            class="small btn-soft"
            id="btnMoreActions"
            data-ico="..."
            type="button"
            aria-haspopup="menu"
            aria-expanded="false"
            aria-controls="overflowMenu"
            title="More planner actions"
          >
            More
          </button>
          <div class="overflow-menu" id="overflowMenu" role="menu" hidden>
            <button id="btnTogglePanels" class="btn-soft" data-ico="PN" role="menuitem">Hide panels</button>
            <button id="btnNotes" class="btn-soft" data-ico="NT" data-key="Ctrl+Shift+N" role="menuitem" title="Toggle notes (Ctrl+Shift+N)">Notes</button>
            <button id="btnNauticalPreview" class="small toggle btn-soft" data-ico="NA" role="menuitem" title="Toggle future Nautical instances">Nautical: Off</button>
            <button id="btnClearSel" class="btn-soft" data-ico="CL" data-key="Esc" role="menuitem">Clear selection</button>
            <button id="btnReset" class="danger" data-ico="RS" role="menuitem">Reset view plan</button>
            <button id="btnCommand" class="small btn-soft" data-ico="KC" data-key="Ctrl/Cmd+K" role="menuitem" title="Quick commands (Ctrl/Cmd+K)">Quick commands</button>
            <button id="btnDensity" class="small toggle btn-soft" data-ico="DN" data-key="Ctrl+Shift+M" role="menuitem" title="Toggle compact density (Ctrl+Shift+M)">Density: Comfort</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</header>"""
