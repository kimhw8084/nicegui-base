from __future__ import annotations

import inspect
from pathlib import Path

from nicegui_base import OverlayLayer
from nicegui_base.integrations import nicegui_interactions
from nicegui_base.integrations.nicegui_theme import build_framework_css

ROOT = Path(__file__).resolve().parents[1]


def test_overlay_layer_contract_is_strictly_ordered():
    assert OverlayLayer.STICKY < OverlayLayer.APP_CHROME < OverlayLayer.LOCAL_POPUP
    assert OverlayLayer.LOCAL_POPUP < OverlayLayer.POPOVER < OverlayLayer.BACKDROP
    assert OverlayLayer.BACKDROP < OverlayLayer.MODAL < OverlayLayer.TOOLTIP < OverlayLayer.TOAST
    assert int(OverlayLayer.MODAL) == 3100


def test_overlay_css_owns_one_governed_global_layer_authority_and_local_table_controls():
    css = build_framework_css()
    compact = css.replace(' ', '')
    for rule in (
        '--cui-layer-sticky:100', '--cui-sidebar-z:500', '--cui-app-header-z:600',
        '--cui-local-popup-z:900', '--cui-overlay-z:2000', '--cui-overlay-backdrop-z:3000',
        '--cui-modal-z:3100', '--cui-tooltip-z:3200', '--cui-toast-z:4000', '--cui-skip-link-z:4100',
        '.cui-table-toolbar,.cui-chart-toolbar,.cui-image-viewer__toolbar',
        '.q-dialog{z-index:var(--cui-modal-z)!important;}',
    ):
        assert rule in compact
    assert compact.count('--cui-modal-z:3100') == 1
    assert 'z-index:9999' not in compact


def test_dismissible_dialogs_and_drawers_are_not_forced_persistent():
    source = inspect.getsource(nicegui_interactions)
    assert "persistent: bool = False" in source
    assert "persistent=(persistent or not dismissible)" in source
    assert "if self.spec.persistent: self.dialog.props('persistent')" in source
    assert "if not self.spec.dismissible: self.dialog.props('persistent')" in source
    assert "ui.dialog().props('persistent transition-show=fade transition-hide=fade')" not in source


def test_all_framework_tooltips_use_company_transient_manager():
    integration_files = sorted((ROOT / 'nicegui_base/integrations').glob('nicegui_*.py'))
    offenders = []
    for path in integration_files:
        text = path.read_text(encoding='utf-8')
        if '.tooltip(' in text:
            offenders.append(path.name)
    assert offenders == []
    source = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    assert 'window.__companyUiTooltip' in source
    assert "document.addEventListener('cui:overlay-open', hide)" in source
    assert "addEventListener('scroll', hide" in source
    assert "target.addEventListener('mouseleave', manager.hide)" in source


def test_toast_has_manual_close_and_pauseable_lifetime_gauge():
    source = (ROOT / 'nicegui_base/integrations/nicegui_feedback_runtime.py').read_text(encoding='utf-8')
    assert "close.className = 'cui-toast__close'" in source
    assert "close.setAttribute('aria-label', 'Dismiss notification')" in source
    assert "bar.className = 'cui-toast__lifetime-bar'" in source
    assert "animation = bar.animate" in source
    assert "toast.addEventListener('mouseenter', () => animation?.pause())" in source
    assert "toast.addEventListener('mouseleave', () => animation?.play())" in source


def test_dialog_and_drawer_close_buttons_route_through_company_close_path():
    source = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    assert "ui.button(on_click=self.close).props('flat round aria-label=\"Close\" data-cui-overlay-close')" in source
    assert "if self.spec.close_on_primary: self.close()" in source
    assert "if self.spec.close_on_secondary: self.close()" in source
    assert "cui-dialog__confirmation-input" in source
    assert 'autofocus aria-label="Type {phrase} to confirm"' in source


def test_app_info_dialog_is_dismissible_and_has_real_close_path():
    source = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    start = source.index('class AppInfoDialog')
    end = source.index('\n\nclass SegmentedControl', start)
    block = source[start:end]
    assert ".props('persistent')" not in block
    assert 'on_click=self.close' in block
    assert 'def close(self)' in block
    assert 'cui-overlay-surface--dialog' in block


def test_browser_certification_exercises_real_overlay_interactions():
    source = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for phrase in (
        'confirm dialog cancel did not close modal',
        'confirm dialog primary action did not close modal',
        'danger confirmation input is not editable',
        'danger dialog primary action did not enable after exact phrase',
        'drawer X did not close',
        'dismissible drawer did not close with Escape',
        'toast lifetime gauge missing',
        'toast close button missing',
        'Company tooltip remained visible after pointer left target',
        'APP_CONTROL_ABOVE_MODAL',
        'POPOVER_ABOVE_MODAL',
    ):
        assert phrase in source
