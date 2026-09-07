from __future__ import annotations

import ast
from pathlib import Path

import nicegui_base
from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.integrations.nicegui_theme import build_framework_css
from nicegui_base.patterns import PATTERN_REGISTRY, PatternSurface

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/'nicegui_base/certification/mac_lab.py'


def _pattern_function_sources() -> dict[str,str]:
    source=LAB.read_text(encoding='utf-8'); tree=ast.parse(source)
    out={}
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name.startswith('_pattern_'):
            out[node.name]=ast.get_source_segment(source,node) or ''
    return out


def test_phase27_all_ten_patterns_remain_registered_and_pattern_surface_is_public():
    assert len(PATTERN_REGISTRY)==10
    assert nicegui_base.PatternSurface is PatternSurface
    assert {x.value for x in PatternSurface}=={'plain','subtle','surface','inspector'}


def test_phase27_reference_apps_use_production_shell_without_lab_controlbar():
    functions=_pattern_function_sources()
    canonical={k:v for k,v in functions.items() if k in {
        '_pattern_dashboard','_pattern_explorer','_pattern_master_detail','_pattern_crud','_pattern_monitoring',
        '_pattern_search','_pattern_settings','_pattern_wizard','_pattern_comparison','_pattern_analysis',
    }}
    assert len(canonical)==10
    for name,body in canonical.items():
        assert '_reference_shell(' in body, name
        assert '_control_bar()' not in body, name
        assert "on_settings=lambda:_toast('Settings')" not in body, name


def test_phase27_reference_apps_exercise_real_phase1_through_phase6_behaviors():
    functions=_pattern_function_sources()
    assert 'FormDrawer(' in functions['_pattern_crud']
    assert 'InspectorDrawer(' in functions['_pattern_search']
    assert 'PreviewDialog(' in functions['_pattern_wizard']
    assert 'WaferComparisonMap(' in functions['_pattern_comparison']
    assert 'InvestigationContextBar(' in functions['_pattern_analysis']
    assert 'CommonalityMatrix(' in functions['_pattern_analysis']
    assert 'PatternSurface.INSPECTOR' in functions['_pattern_master_detail']
    assert 'PatternSurface.INSPECTOR' in functions['_pattern_analysis']


def test_phase27_pattern_grid_is_twelve_column_and_responsive():
    css=build_framework_css()
    assert 'grid-template-columns:repeat(12,minmax(0,1fr))' in css
    assert '.cui-pattern--dashboard .cui-pattern-slot--primary' in css and 'grid-column:1 / 9' in css
    assert '.cui-pattern--master_detail .cui-pattern-slot--data' in css and 'grid-column:1 / 8' in css
    assert '.cui-pattern--search .cui-pattern-slot--filters' in css and 'grid-column:1 / 4' in css
    assert '.cui-pattern--settings .cui-pattern-slot--content' in css and 'grid-column:4 / -1' in css
    assert '.cui-pattern--wizard .cui-pattern-slot--content' in css and 'grid-column:3 / 11' in css
    assert '.cui-pattern--analysis_workspace .cui-pattern-slot--details' in css and 'grid-column:9 / -1' in css
    assert 'grid-column:1 / -1 !important; grid-row:auto !important' in css
    assert '.cui-pattern-slot.is-sticky' in css


def test_phase27_pattern_slots_have_governed_surface_anatomy():
    source=(ROOT/'nicegui_base/patterns/pages.py').read_text(encoding='utf-8')
    assert 'data-cui-slot-surface' in source
    assert 'slot already rendered' in source
    assert 'PatternSurface.SUBTLE' in source
    assert 'PatternSurface.SURFACE' in source
    css=build_framework_css()
    for cls in ('cui-pattern-slot--subtle','cui-pattern-slot--surface','cui-pattern-slot--inspector'):
        assert f'.{cls}' in css


def test_phase27_reference_app_browser_contract_covers_all_ten_routes_and_tablet():
    source=(ROOT/'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    assert 'REFERENCE_ROUTES =' in source
    assert "KEY_ROUTES+REFERENCE_ROUTES" in source
    assert "elif route in REFERENCE_ROUTES:" in source
    for route in ('dashboard','explorer','master-detail','crud','monitoring','search','settings','wizard','comparison','analysis'):
        assert f"'/patterns/{route}'" in source
    assert 'reference application leaked certification control bar' in source
    assert 'desktop composition did not preserve side-by-side hierarchy' in source
    assert 'mobile composition did not collapse to one column' in source


def test_phase27_visual_coverage_remains_complete():
    summary=coverage_summary()
    assert summary['covered_visual_components']==summary['required_visual_components']==185
    assert summary['uncovered']==[]
