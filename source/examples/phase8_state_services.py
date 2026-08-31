"""Phase 8 semantic usage example; no raw NiceGUI storage/service calls required."""
from __future__ import annotations

from nicegui_base import (
    AsyncAction, AutoRefreshController, KeyboardShortcut, KeyboardShortcutRegistry,
    PreferenceService, StateStore, UrlField, UrlState,
)

page_state = StateStore({'selected_tool': None, 'filters': {}})
preferences = PreferenceService({})
url = UrlState([UrlField('area'), UrlField('tool', str, multiple=True), UrlField('critical', bool)])

run_analysis = AsyncAction(timeout=30)
refresh = AutoRefreshController(lambda: {'status': 'fresh'}, interval_seconds=60)

shortcuts = KeyboardShortcutRegistry()
shortcuts.register(KeyboardShortcut('ctrl+k', lambda: 'open-command-palette', 'Open command palette'))
shortcuts.register(KeyboardShortcut('/', lambda: 'focus-search', 'Focus search'))

query = url.encode({'area': 'ETCH', 'tool': ['ETCH-01', 'ETCH-02'], 'critical': True})
assert url.decode(query)['critical'] is True
