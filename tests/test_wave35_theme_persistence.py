from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workbench_preserves_browser_theme_while_server_is_neutral() -> None:
    source=(ROOT/'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    assert 'WAVE35_THEME_RECONCILIATION_V8' in source
    assert "requested==='system'" in source
    assert "matchMedia?.('(prefers-color-scheme: dark)')" in source
    assert "root.dataset.theme=resolved" in source
    assert "media.addEventListener?.('change'" in source
    assert "localStorage.setItem('nicegui_base_theme',requested)" in source


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
    assert "document.body?.classList.toggle('q-dark'" in source
    assert "document.body?.classList.toggle('body--dark'" in source
    assert 'Authentication' not in source[source.index('def _display_control_bar'):source.index('def workbench_navigation')]
