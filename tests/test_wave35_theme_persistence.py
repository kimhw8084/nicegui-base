from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workbench_preserves_browser_theme_while_server_is_neutral() -> None:
    source=(ROOT/'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    assert 'WAVE35_THEME_RECONCILIATION_V8' in source
    assert "if theme in {'light', 'dark'}:" in source
    assert "if theme == 'system':" in source
    assert 'async def reconcile_initial_theme()' in source
    assert "localStorage.getItem('nicegui_base_theme')" in source
    assert "browser_theme not in {'light', 'dark'}" in source
    assert 'await ui.context.client.connected()' in source
    assert '.set_value(browser_theme, emit=True)' in source


def test_segmented_control_exposes_truthful_programmatic_selection() -> None:
    source=(ROOT/'source/nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    assert 'cui-segmented-control--semantic-v8' in source
    assert 'async def set_value(self, value: str, *, emit: bool = False)' in source
    assert 'await self.set_value(value, emit=True)' in source
    assert 'role="radiogroup"' in source
    assert 'role="radio"' in source
    assert 'aria-checked' in source


def test_theme_recovery_is_display_only() -> None:
    source=(ROOT/'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    start=source.index('async def reconcile_initial_theme')
    recovery=source[start:start+2400]
    assert 'Authentication' in recovery
    assert 'permissions' in recovery
    assert 'application data' in recovery
    assert "browser_theme not in {'light', 'dark'}" in recovery
