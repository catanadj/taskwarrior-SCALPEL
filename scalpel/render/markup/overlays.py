# scalpel/render/markup/overlays.py
from __future__ import annotations

MARKUP = r"""<div id="marquee"></div>
<div id="toast" class="toast" role="status" aria-live="polite"></div>

<div class="modal-backdrop" id="helpModal">
  <div class="modal help-modal">
    <div class="mh">
      <div class="t">Help and shortcuts</div>
      <button class="small btn-soft" id="helpClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint">
        Fast path: <b>Ctrl/Cmd+K</b> opens quick commands. <b>?</b> opens this help.
      </div>

      <div class="helpgrid">
        <div class="hsec">
          <div class="sh">Navigation</div>
          <div class="hkrow"><span class="hk">Arrow keys</span><span class="hv">Move selection focus</span></div>
          <div class="hkrow"><span class="hk">Ctrl/Cmd + Arrow</span><span class="hv">Move selected task(s)</span></div>
          <div class="hkrow"><span class="hk">Alt + Arrow</span><span class="hv">Nudge selected task(s)</span></div>
          <div class="hkrow"><span class="hk">Alt+Shift + Up/Down</span><span class="hv">Resize selected task(s)</span></div>
        </div>
        <div class="hsec">
          <div class="sh">Selection ops</div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+A</span><span class="hv">Align starts</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+E</span><span class="hv">Align ends</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+S</span><span class="hv">Stack</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+D</span><span class="hv">Distribute evenly</span></div>
        </div>
        <div class="hsec">
          <div class="sh">App controls</div>
          <div class="hkrow"><span class="hk">Ctrl/Cmd+K</span><span class="hv">Quick commands</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+N</span><span class="hv">Toggle notes panel</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+M</span><span class="hv">Toggle compact density</span></div>
          <div class="hkrow"><span class="hk">Ctrl+Shift+T</span><span class="hv">Open theme manager</span></div>
          <div class="hkrow"><span class="hk">C / D</span><span class="hv">Queue complete / delete for selection</span></div>
          <div class="hkrow"><span class="hk">Esc</span><span class="hv">Close modal or clear selection</span></div>
        </div>
      </div>
    </div>
    <div class="mf">
      <button class="small btn-primary" id="helpOpenCommands" data-ico="KC">Open quick commands</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="commandModal">
  <div class="modal command-modal">
    <div class="mh">
      <div class="cmdk-head">
        <div class="t">Quick commands</div>
        <div class="cmdk-legend" aria-label="Common quick command codes">
          <span class="cmdk-chip"><span class="k">CP</span>Copy</span>
          <span class="cmdk-chip"><span class="k">DN</span>Density</span>
          <span class="cmdk-chip"><span class="k">TH</span>Theme</span>
          <span class="cmdk-chip"><span class="k">HP</span>Help</span>
        </div>
      </div>
      <button class="small btn-soft" id="commandClose">Close</button>
    </div>
    <div class="mb">
      <input class="search" id="commandQ" placeholder="Type to filter commands..." />
      <div class="hint">
        Enter runs highlighted command. Use <b>Up/Down</b> to change selection.
        With an empty filter, type label codes (for example <b>CP</b>, <b>DN</b>) to jump/run.
      </div>
      <div id="commandList" class="cmdk-list"></div>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="addModal">
  <div class="modal">
    <div class="mh">
      <div class="t">Add tasks</div>
      <button class="small btn-soft" id="addClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint">
        One task per line. New tasks are inserted below the current calendar selection using the default duration (10m unless configured). Add commands are emitted with scheduled/due/duration.
      </div>
      <textarea id="addLines" placeholder="Example:
Buy groceries
Call Alice about weekend
Review PR #142"></textarea>
    </div>
    <div class="mf">
      <button class="small btn-primary" id="addQueue" data-ico="+">Queue add commands</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="noteModal">
  <div class="modal">
    <div class="mh">
      <div class="t" id="noteModalTitle">Note</div>
      <button class="small btn-soft" id="noteClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint" id="noteTzHint"></div>
      <textarea id="noteText" placeholder="Write a note..."></textarea>

      <div class="notegrid">
        <label class="ck"><input type="checkbox" id="notePinned"> Pinned</label>
        <label class="ck"><input type="checkbox" id="noteAllDay"> All-day</label>
        <label class="ck"><input type="checkbox" id="noteRepeat"> Repeat weekly</label>
        <label class="ck"><input type="checkbox" id="noteArchived"> Archived</label>
      </div>

      <div class="notecolor">
        <div class="clbl">Color</div>
        <div class="cpal" id="noteColors">
          <button class="csw none" data-color="" title="No color">None</button>
          <button class="csw c1" data-color="c1" title="Yellow"></button>
          <button class="csw c2" data-color="c2" title="Blue"></button>
          <button class="csw c3" data-color="c3" title="Green"></button>
          <button class="csw c4" data-color="c4" title="Red"></button>
          <button class="csw c5" data-color="c5" title="Purple"></button>
          <button class="csw c6" data-color="c6" title="Teal"></button>
          <button class="csw c7" data-color="c7" title="Gray"></button>
          <button class="csw c8" data-color="c8" title="Pink"></button>
        </div>
      </div>

      <div class="noterep" id="noteRepeatBox" style="display:none;">
        <div class="repRow">
          <div class="repDays" id="noteRepeatDays">
            <label class="dow"><input type="checkbox" data-dow="1">Mon</label>
            <label class="dow"><input type="checkbox" data-dow="2">Tue</label>
            <label class="dow"><input type="checkbox" data-dow="3">Wed</label>
            <label class="dow"><input type="checkbox" data-dow="4">Thu</label>
            <label class="dow"><input type="checkbox" data-dow="5">Fri</label>
            <label class="dow"><input type="checkbox" data-dow="6">Sat</label>
            <label class="dow"><input type="checkbox" data-dow="0">Sun</label>
          </div>
          <div class="repBtns">
            <button class="small" id="noteDowAll">All</button>
            <button class="small" id="noteDowWeekdays">Weekdays</button>
            <button class="small danger" id="noteDowClear">Clear</button>
          </div>
        </div>
        <div class="hint" id="noteRepeatHint">When repeat is enabled, Day is disabled and the note appears on selected weekdays.</div>
      </div>

      <div class="notegrid2">
        <label>Day <input type="date" id="noteDay"></label>
        <label>Start <input type="time" id="noteStart" step="60"></label>
        <label>End <input type="time" id="noteEnd" step="60"></label>
        <button class="small btn-soft" id="noteUnplace">Unplace</button>
      </div>

      <div class="hint">
        Tip: drag a note onto the calendar to place it (drop on a day header for an all-day note).
      </div>
    </div>
    <div class="mf notefoot">
      <button class="small danger" id="noteDelete">Delete</button>
      <div class="grow" aria-hidden="true"></div>
      <button class="small btn-primary" id="noteSave">Save</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="aiPlanModal">
  <div class="modal">
    <div class="mh">
      <div class="t">AI plan</div>
      <button class="small btn-soft" id="aiPlanClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint">
        Uses LM Studio local API. Select tasks first, then describe the change.
      </div>
      <div class="row wrap">
        <label class="field wide">Base URL <input id="aiBaseUrl" type="text" value="http://127.0.0.1:1234" /></label>
        <label class="field med">Model <input id="aiModel" type="text" value="ministral-3-14b-reasoning" /></label>
        <label class="field short">Temp <input id="aiTemp" type="number" min="0" max="2" step="0.1" value="0.2" /></label>
        <label class="check-inline"><input id="aiShowRequest" type="checkbox" /> Show request</label>
      </div>
      <textarea id="aiPrompt" placeholder="Example: move these after lunch, minimize gaps, keep within work hours"></textarea>
      <div class="hint" id="aiStatus"></div>
      <pre id="aiPreview" class="ai-preview"></pre>
    </div>
    <div class="mf">
      <button class="small btn-soft" id="aiPlanApply">Apply</button>
      <button class="small btn-primary" id="aiPlanRun">Run</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="themeModal">
  <div class="modal">
    <div class="mh">
      <div class="t">Theme manager</div>
      <button class="small btn-soft" id="themeClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint">
        Click <b>Theme</b> to cycle built-in themes. Shift+click the Theme button or press <b>Ctrl+Shift+T</b> to open this manager.
      </div>

      <div class="themegrid">
        <label>Theme
          <select id="themePick"></select>
        </label>
        <label>Base
          <div class="pill" id="themeBase">—</div>
        </label>
      </div>

      <div class="themesw" id="themeSwatches"></div>

      <div class="ops">
        <button class="small btn-primary" id="themeApply">Apply</button>
        <button class="small btn-soft" id="themeClone">Clone current…</button>
        <button class="small btn-soft" id="themeEdit">Edit…</button>
        <button class="small btn-soft" id="themeExport">Export JSON</button>
        <button class="small btn-soft" id="themeImport">Import JSON</button>
        <button class="small danger" id="themeDelete">Delete</button>
      </div>

      <div class="hint">
        Custom themes are stored locally in your browser. Export the JSON to version it or copy it to other machines.
        Schema: <span class="mono">scalpel-theme/v1</span>.
      </div>
      <input type="file" id="themeImportFile" accept="application/json" style="display:none" />
    </div>
    <div class="mf">
      <button class="small btn-soft" id="themeClose2">Close</button>
    </div>
  </div>
</div>
<div class="modal-backdrop" id="themeEditModal">
  <div class="modal">
    <div class="mh">
      <div class="t">Theme editor</div>
      <button class="small btn-soft" id="themeEditClose">Close</button>
    </div>
    <div class="mb">
      <div class="hint">
        Edit colors for the selected theme. If a built-in theme is selected, saving will clone it into a custom theme.
      </div>

      <div class="row">
        <span class="mono" id="themeEditTitle"></span>
        <span class="vwlabel">Name</span>
        <input id="themeEditNameInput" type="text" />
        <div class="grow" aria-hidden="true"></div>
        <button class="small btn-soft" id="themeEditReset">Reset</button>
      </div>

      <div class="themedit-sec">
        <div class="sh">Notes palette</div>
        <div class="themedit-grid" id="themeEditNotes"></div>
        <div class="themedit-alpha">
          <span class="lbl">All swatches alpha</span>
          <input type="range" id="themeEditNoteAlpha" min="10" max="100" step="1" />
          <span class="mono" id="themeEditNoteAlphaVal"></span>
        </div>
      </div>

      <div class="themedit-sec">
        <div class="sh">Core</div>
        <div class="themedit-grid core" id="themeEditCore"></div>
      </div>

      <div class="ops">
        <button class="small btn-soft" id="themeEditCancel">Cancel</button>
        <button class="small btn-primary" id="themeEditSave">Save</button>
      </div>
    </div>
  </div>
</div>


"""
