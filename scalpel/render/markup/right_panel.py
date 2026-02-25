# scalpel/render/markup/right_panel.py
from __future__ import annotations

MARKUP = r"""<section class="card commands">
    <div class="card-h">
      <div>Commands</div>
      <small id="cmdCount"></small>
    </div>
    <div class="card-b">
      <div class="rsec" data-rsec="actions">
        <button class="rsec-h" type="button" data-rsec-toggle="actions" aria-expanded="false" aria-controls="rsecActionsBody">
          <span class="rsec-t">Actions</span>
          <span class="rsec-s">Queue task actions</span>
          <span class="rsec-chev" aria-hidden="true">▸</span>
        </button>
        <div class="rsec-b" id="rsecActionsBody" hidden>
          <div class="ops">
            <button class="small btn-soft" id="actDone" data-ico="OK" data-key="C">Complete selected</button>
            <button class="small danger" id="actDelete" data-ico="DL" data-key="D">Delete selected</button>
            <button class="small btn-primary" id="actAdd" data-ico="+">Add tasks</button>
            <button class="small danger" id="actClearActions" data-ico="CL">Clear actions</button>
          </div>

          <div id="notesWrap" style="display:none;">
            <div class="notesbox" id="notesBox">
              <div class="notes-head" id="notesHead">
                <div class="t">Notes</div>
                <div class="s">
                  <button class="small toggle" id="noteToggleAll">Hide notes</button>
                  <small id="notesMeta"></small>
                  <span class="chev" id="notesChev">▾</span>
                </div>
              </div>
              <div class="notes-body" id="notesBody">
                <div class="notes-new">
                  <input class="search" id="noteNewText" placeholder="New note… (Enter to add)" />
                  <button class="small btn-primary" id="noteAdd" data-ico="+">Add</button>
                </div>
                <div class="ops" style="margin-bottom:8px;">
                  <button class="small btn-soft" id="noteNew" data-ico="ED">Open editor</button>
                  <button class="small btn-soft" id="noteExport" data-ico="EX">Export</button>
                  <button class="small btn-soft" id="noteImport" data-ico="IM">Import</button>
                  <button class="small btn-soft" id="noteClearArchived" data-ico="AR">Clear archived</button>
                </div>
                <input class="search" id="noteQ" placeholder="Search notes…" />
                <div class="space-8" aria-hidden="true"></div>
                <div class="hint">Drag a note onto the calendar to place it. Drop on a day header for an all-day note.</div>
                <div class="space-8" aria-hidden="true"></div>
                <div id="noteList" class="notes-list"></div>
                <input type="file" id="noteImportFile" accept="application/json" style="display:none" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="rsec" data-rsec="arrange">
        <button class="rsec-h" type="button" data-rsec-toggle="arrange" aria-expanded="false" aria-controls="rsecArrangeBody">
          <span class="rsec-t">Arrange</span>
          <span class="rsec-s">Alignment and distribution</span>
          <span class="rsec-chev" aria-hidden="true">▸</span>
        </button>
        <div class="rsec-b" id="rsecArrangeBody" hidden>
          <div class="ops">
            <button class="small btn-soft" id="opAlignStart" data-ico="AS" data-key="Ctrl+Shift+A">Align starts</button>
            <button class="small btn-soft" id="opAlignEnd" data-ico="AE" data-key="Ctrl+Shift+E">Align ends</button>
            <button class="small btn-soft" id="opStack" data-ico="ST" data-key="Ctrl+Shift+S">Stack</button>
            <button class="small btn-soft" id="opDistribute" data-ico="DS" data-key="Ctrl+Shift+D">Distribute</button>
          </div>
          <div class="hint">
            Shortcuts:
            Alt+↑/↓ move • Alt+←/→ day • Alt+Shift+↑/↓ resize • Ctrl+Shift+A align start • Ctrl+Shift+E align end • Ctrl+Shift+S stack • Ctrl+Shift+D distribute • Esc clear
          </div>
        </div>
      </div>

      <div class="rsec" data-rsec="ai">
        <button class="rsec-h" type="button" data-rsec-toggle="ai" aria-expanded="false" aria-controls="rsecAiBody">
          <span class="rsec-t">AI and Plan</span>
          <span class="rsec-s">Import, export, scheduling</span>
          <span class="rsec-chev" aria-hidden="true">▸</span>
        </button>
        <div class="rsec-b" id="rsecAiBody" hidden>
          <div class="ops">
            <button class="small btn-soft" id="btnExportPlan" data-ico="EX">Export plan</button>
            <button class="small btn-soft" id="btnImportPlan" data-ico="IM">Import plan</button>
            <button class="small btn-primary" id="btnAiPlan" data-ico="AI">AI sched</button>
            <input type="file" id="planImportFile" accept="application/json" style="display:none" />
          </div>
        </div>
      </div>

      <div class="rsec" data-rsec="output">
        <button class="rsec-h" type="button" data-rsec-toggle="output" aria-expanded="false" aria-controls="rsecOutputBody">
          <span class="rsec-t">Output</span>
          <span class="rsec-s">Insights and command script</span>
          <span class="rsec-chev" aria-hidden="true">▸</span>
        </button>
        <div class="rsec-b" id="rsecOutputBody" hidden>
          <div class="nextup" id="nextUp" style="">
            <div class="nuh">
              <div>Next up</div>
              <small id="nextUpMeta"></small>
            </div>
            <div class="nub" id="nextUpBody"><div class="nutxt"><div class="nusub">Loading…</div></div></div>
          </div>

          <div class="daybal" id="dayBal" style="display:none;">
            <div class="dbh">
              <div>Day balance</div>
              <small id="dayBalDay"></small>
            </div>
            <div class="dbbar" id="dayBalBar"></div>
            <div class="dbleg" id="dayBalLegend"></div>
          </div>

          <div class="selbox" id="selBox" style="display:none;">
            <div class="selhdr"><span>Selected tasks</span><span class="selmeta" id="selSummary"></span></div>
            <div class="selextra" id="selExtra"></div>
            <div class="sellist" id="selList"></div>
          </div>

          <div class="conflicts" id="conflictsBox"></div>

          <div id="cmdGuide" class="cmd-guide" aria-live="polite"></div>
          <div class="hint">Command output includes schedule changes and queued actions. Times emitted as local time (no offset).</div>
          <div class="space-10" aria-hidden="true"></div>
          <pre id="commands"></pre>
          <div class="space-10" aria-hidden="true"></div>
          <div class="hint" id="status"></div>
        </div>
      </div>
    </div>
  </section>"""
