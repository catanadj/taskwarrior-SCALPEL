# scalpel/render/markup/layout_close.py
from __future__ import annotations

MARKUP = r"""
</div>
<nav class="mobile-tabs" id="mobileTabs" aria-label="Mobile sections">
  <button class="mtab" id="tabBacklog" type="button" data-mobile-panel="left" aria-selected="false">Backlog</button>
  <button class="mtab" id="tabCalendar" type="button" data-mobile-panel="calendar" aria-selected="false">Calendar</button>
  <button class="mtab" id="tabCommands" type="button" data-mobile-panel="commands" aria-selected="false">Commands</button>
</nav>
"""
