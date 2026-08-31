from pathlib import Path

from nicegui_base.certification.visual_audit import audit_framework_visual_sources, audit_visual_css, unresolved_custom_properties
from nicegui_base.integrations.nicegui_theme import build_framework_css

ROOT = Path(__file__).resolve().parents[1]


def test_all_company_css_custom_properties_resolve():
    assert unresolved_custom_properties(build_framework_css()) == ()


def test_required_quasar_and_ag_grid_normalizers_are_present():
    assert audit_visual_css(build_framework_css()) == ()


def test_framework_does_not_use_stock_visual_runtime_paths():
    assert audit_framework_visual_sources(ROOT) == ()


def test_ag_grid_is_themed_against_real_ag_dom():
    css = build_framework_css()
    for selector in ('.ag-root-wrapper', '.ag-header-cell', '.ag-row-selected', '.ag-paging-panel', '.ag-menu', '.ag-tooltip'):
        assert selector in css


def test_forced_colors_and_pattern_layouts_are_first_class():
    css = build_framework_css()
    assert '@media (forced-colors: active)' in css
    for pattern in ('dashboard','data_explorer','master_detail','crud','monitoring','search','settings','wizard','comparison','analysis_workspace'):
        assert f'.cui-pattern--{pattern}' in css


def test_live_browser_gold_gate_detects_stock_visual_leakage():
    source = (ROOT/'nicegui_base/certification/live_checks.py').read_text()
    for token in ('stockVisualLeakCount', 'unapprovedMaterialIconCount', "'.q-notification'", "'.ag-root-wrapper'", "'.q-checkbox'", "'.q-tabs'", "'.q-stepper'", "'.q-uploader'"):
        assert token in source
    assert "audit['stockVisualLeakCount'] == 0" in source
    assert "audit['unapprovedMaterialIconCount'] == 0" in source


def test_visual_laws_are_embedded_for_ai_scaffold():
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    assert 'ZERO_STOCK_NICEGUI_VISUAL_LAWS.md' in GUIDE_NAMES
    assert (ROOT/'nicegui_base/ai/guides/ZERO_STOCK_NICEGUI_VISUAL_LAWS.md').exists()
