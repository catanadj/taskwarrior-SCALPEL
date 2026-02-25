# scalpel/render/markup/left_panel.py
from __future__ import annotations

MARKUP = r"""<section class="card left">
    <div class="card-h">
      <div>Backlog</div>
      <small id="backlogCount"></small>
    </div>
    <div class="card-b">
      <input class="search" id="q" placeholder="Filter (project/tag/description)..." />
      <div class="space-10" aria-hidden="true"></div>

      <div class="lsec lsec-focus" data-lsec="focus">
        <button class="lsec-h" type="button" data-lsec-toggle="focus" aria-expanded="true" aria-controls="lsecFocusBody">
          <span class="lsec-t">Focus</span>
          <small id="focusMeta"></small>
          <span class="lsec-chev" aria-hidden="true">▾</span>
        </button>
        <div class="lsec-b" id="lsecFocusBody">
          <div class="focusbar" id="focusBar">
            <div class="frow">
              <button class="seg" data-fmode="all">All</button>
              <button class="seg" data-fmode="goals">Goals</button>
              <button class="seg" data-fmode="projects">Projects</button>
              <button class="seg" data-fmode="tags">Tags</button>
            </div>
            <div class="frow">
              <button class="seg" data-fbeh="dim">Dim</button>
              <button class="seg" data-fbeh="hide">Hide</button>
              <button class="small" id="btnClearFocus">Clear</button>
            </div>
            <div class="fhint">Tip: in Goals/Palette, click a label to focus it.</div>
          </div>
        </div>
      </div>

      <div class="space-10" aria-hidden="true"></div>
      <div class="goals-box" id="goalsBox"></div>

      <div class="lsec lsec-palette" data-lsec="palette">
        <button class="lsec-h" type="button" data-lsec-toggle="palette" aria-expanded="true" aria-controls="lsecPaletteBody">
          <span class="lsec-t">Palette</span>
          <small>Visible tasks</small>
          <span class="lsec-chev" aria-hidden="true">▾</span>
        </button>
        <div class="lsec-b" id="lsecPaletteBody">
          <div class="palette">
            <div class="hint">
              Palette tree is built from calendar-visible tasks. Tag color overrides project. Project colors inherit to subprojects.
            </div>
            <div class="ops palette-ops">
              <button class="small" id="btnClearColors">Clear colors</button>
              <button class="small" id="btnExportColors">Export</button>
              <button class="small" id="btnImportColors">Import</button>
              <input type="file" id="colorsImportFile" accept="application/json" style="display:none" />
            </div>
            <div id="paletteTree" class="ptree"></div>
          </div>
        </div>
      </div>

      <div class="space-12" aria-hidden="true"></div>
      <div class="hint">
        Calendar selection: drag a rectangle on empty calendar space (Shift add, Ctrl/Cmd toggle).
        Backlog selection: use checkboxes.
      </div>
      <div class="space-10" aria-hidden="true"></div>
      <div id="backlog"></div>

      <div class="space-14" aria-hidden="true"></div>
      <div class="lsec lsec-problems" data-lsec="problems">
        <button class="lsec-h" type="button" data-lsec-toggle="problems" aria-expanded="true" aria-controls="lsecProblemsBody">
          <span class="lsec-t">Problems</span>
          <small id="problemCount"></small>
          <span class="lsec-chev" aria-hidden="true">▾</span>
        </button>
        <div class="lsec-b" id="lsecProblemsBody">
          <div class="hint">Invalid intervals (e.g., computed start crosses day).</div>
          <div class="space-10" aria-hidden="true"></div>
          <div id="problems"></div>
        </div>
      </div>
    </div>
  </section>"""
