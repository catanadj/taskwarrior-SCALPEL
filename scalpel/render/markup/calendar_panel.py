# scalpel/render/markup/calendar_panel.py
from __future__ import annotations

MARKUP = r"""<section class="card calendar">
    <div class="card-h">
      <div>Week</div>
      <small id="range"></small>
    </div>
    <div class="selection-bar" id="selectionBar" role="toolbar" aria-label="Selected task actions" hidden>
      <div class="selection-bar-summary" id="selectionBarSummary" aria-live="polite"></div>
      <div class="selection-bar-actions">
        <button class="small btn-primary" id="selectionComplete" type="button" data-ico="OK">Complete</button>
        <button class="small danger" id="selectionDelete" type="button" data-ico="DL">Delete</button>
        <button class="small btn-soft" id="selectionArrange" type="button" data-ico="AR">Arrange</button>
        <button class="small btn-soft" id="selectionFocus" type="button" data-ico="FS">Start focus</button>
        <button class="small btn-quiet" id="selectionClear" type="button" data-ico="CL">Clear</button>
      </div>
    </div>
    <div class="card-b" style="padding:0">
      <div class="cal-wrap" id="calendar"></div>
    </div>
  </section>"""
