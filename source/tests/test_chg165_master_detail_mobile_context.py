from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from nicegui_base.integrations.nicegui_master_detail import (
    MASTER_DETAIL_CONTEXT_RUNTIME,
    OVERLAY_MANAGER_RUNTIME,
    set_master_detail_context_state,
)
from nicegui_base.layouts import build_layout_css
from nicegui_base.patterns import MasterDetailPage, PagePattern, get_pattern


ROOT = Path(__file__).resolve().parents[1]


def test_master_detail_phone_contract_is_explicit_and_desktop_tablet_stay_inline():
    definition = get_pattern(PagePattern.MASTER_DETAIL)
    assert 'simultaneously visible' in definition.desktop_behavior
    assert 'narrow' in definition.tablet_behavior or 'stacks' in definition.tablet_behavior
    assert 'full-screen contextual surface' in definition.phone_behavior

    css = build_layout_css()
    desktop_rules = css.split('@media (max-width: 899px)', 1)[0]
    assert '.cui-pattern--master_detail .cui-pattern-slot--data { grid-column:1 / 8; }' in desktop_rules
    assert '.cui-pattern--master_detail .cui-pattern-slot--details { grid-column:8 / -1; }' in desktop_rules
    assert '.cui-pattern--master_detail:has(.cui-master-detail-context[data-cui-context-state="closed"])' in css
    assert 'position:fixed !important' in css
    assert 'height:100dvh' in css
    assert 'overflow:hidden' in css
    assert 'var(--cui-overlay-backdrop-z)' in css
    assert 'var(--cui-modal-z)' in css


def test_master_detail_page_exposes_backward_compatible_open_close_authority():
    assert callable(MasterDetailPage.open_detail)
    assert callable(MasterDetailPage.close_detail)
    assert inspect.signature(MasterDetailPage).parameters.keys() == {'title', 'description', 'breadcrumbs'}
    source = (ROOT / 'nicegui_base/patterns/pages.py').read_text(encoding='utf-8')
    assert 'data-cui-master-detail-context' in source
    assert 'Back to master list' in source
    assert 'LayoutSlot.DETAILS' in source


def test_master_detail_runtime_proves_semantic_modal_focus_and_context_preservation():
    for token in (
        'role', 'aria-modal', 'aria-hidden', 'data-cui-overlay-close', 'Escape',
        'focusin', "event.key !== 'Tab'", 'inert', 'cuiScrollLocked', 'origin',
        'master-detail-context', 'cuiContextClosedSelection',
    ):
        assert token in MASTER_DETAIL_CONTEXT_RUNTIME or token in OVERLAY_MANAGER_RUNTIME, token
    assert 'document.dispatchEvent(new CustomEvent(\'cui:overlay-open\'' in MASTER_DETAIL_CONTEXT_RUNTIME
    assert 'document.dispatchEvent(new CustomEvent(\'cui:overlay-close\'' in MASTER_DETAIL_CONTEXT_RUNTIME


def test_master_detail_runtime_preserves_touch_keyboard_and_motion_contracts():
    assert '.ag-row,[role="row"]' in MASTER_DETAIL_CONTEXT_RUNTIME
    assert "event.key === 'Enter' || event.key === ' '" in MASTER_DETAIL_CONTEXT_RUNTIME
    css = build_layout_css()
    assert 'min-height:var(--cui-control-height)' in css
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert 'scroll-behavior:auto' in css


def test_master_detail_runtime_state_helper_is_strict_and_non_destructive():
    class FakeUI:
        def __init__(self):
            self.calls = []

        def run_javascript(self, value):
            self.calls.append(value)
            return value

    ui = FakeUI()
    result = set_master_detail_context_state(ui, 17, 'open', force=True)
    assert result == ui.calls[0]
    assert 'getHtmlElement(17)' in result and '.open' in result and 'true' in result
    with pytest.raises(ValueError):
        set_master_detail_context_state(ui, 17, 'reset')


def test_master_detail_docs_describe_public_mobile_contract():
    for relative in ('docs/APP_PATTERNS.md', 'nicegui_base/ai/guides/APP_PATTERNS.md'):
        text = (ROOT / relative).read_text(encoding='utf-8')
        assert 'MasterDetail responsive contract' in text
        assert 'page.open_detail()' in text
        assert 'page.close_detail()' in text
        assert 'Back to master list' in text
