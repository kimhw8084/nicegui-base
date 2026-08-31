from __future__ import annotations

import inspect
import sys
from pathlib import Path

import nicegui_base
from nicegui_base.certification.engine import combined_css
from nicegui_base.certification.mac_coverage import coverage_summary, live_component_coverage
from nicegui_base.certification.mac_lab_css import build_mac_lab_css
from nicegui_base.certification.visual_audit import audit_visual_css
from nicegui_base.design import DENSITIES, RADII, build_constitution_css, build_css
from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, SeriesSpec, build_echarts_options

ROOT = Path(__file__).resolve().parents[1]


def test_v15_design_constitution_has_three_geometry_families_and_real_density():
    assert RADII['xs'] == RADII['sm'] == 10
    assert RADII['md'] == 14
    assert RADII['lg'] == RADII['xl'] == 18
    assert DENSITIES['comfortable']['control_height'] == 44
    assert DENSITIES['compact']['control_height'] == 38
    assert DENSITIES['dense']['control_height'] == 34
    authority_css = build_css()
    for law in (
        '--cui-radius-control: 10px', '--cui-radius-surface: 14px', '--cui-radius-overlay: 18px',
        '--cui-page-gutter: 20px',
    ):
        assert law in authority_css
    constitution = build_constitution_css()
    for law in (
        '.cui-action-row', '.cui-form-stack', '.cui-alert-stack',
        '.cui-button--primary', '.cui-button--secondary', '.cui-field-control.q-field .q-field__control',
    ):
        assert law in constitution
    assert '--cui-radius-control:' not in constitution


def test_live_lab_css_is_audited_with_framework_css_and_has_no_unresolved_tokens():
    css = combined_css() + '\n' + build_mac_lab_css()
    assert audit_visual_css(css) == ()
    source = (ROOT / 'nicegui_base/certification/engine.py').read_text(encoding='utf-8')
    assert "lab_css=css+'\\n'+build_mac_lab_css()" in source
    assert "'lab-visual-css'" in source


def test_reference_lab_helpers_do_not_double_enter_nicegui_contexts():
    source = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    section = source[source.index('def _section'):source.index('@contextmanager\ndef _sample')]
    sample = source[source.index('def _sample'):source.index('def _grid')]
    assert '.__enter__()' not in section
    assert '.__enter__()' not in sample
    assert 'yield host' in section and 'yield host' in sample


def test_public_api_exposes_composition_primitives_and_design_constitution():
    for name in ('build_constitution_css','ActionRow','AlertStack','ButtonCluster','ContentColumn','FormStack','SurfaceGrid','ToolbarGroup'):
        assert hasattr(nicegui_base, name)
        assert name in nicegui_base.__all__


def test_live_visual_coverage_is_complete_and_page_header_is_explicitly_accounted_for():
    summary = coverage_summary()
    assert summary['required_visual_components'] == 183
    assert summary['covered_visual_components'] == 183
    assert summary['uncovered'] == []
    page_header = next(item for item in live_component_coverage() if item.component == 'PageHeader')
    assert page_header.coverage_kind in {'direct','composite'}
    if page_header.coverage_kind == 'composite':
        assert page_header.via == 'PatternPage'


def test_browser_geometry_audit_contains_user_reported_failure_classes():
    source = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for code in (
        'PAGE_GUTTER_MISSING','CONTENT_OVERLAPS_HEADER','CONTENT_OVERLAPS_SIDEBAR','CHILD_EXCEEDS_CONTAINER',
        'TEXT_CLIPPED','SIBLING_OVERLAP','ACTION_GAP_TOO_SMALL','ICON_NOT_CENTERED','BUTTON_RADIUS',
        'FIELD_RADIUS','SURFACE_RADIUS','OVERLAY_RADIUS','DENSITY_CONTROL_HEIGHT',
    ):
        assert code in source
    assert "audit.get('geometryViolationCount')" in source


def test_linux_browser_discovery_supports_chrome_chromium_and_edge(monkeypatch):
    import nicegui_base.certification.live_preflight as module
    lookup = {
        'google-chrome-stable': None, 'google-chrome': None,
        'chromium': '/usr/bin/chromium', 'chromium-browser': None,
        'microsoft-edge-stable': '/usr/bin/microsoft-edge-stable', 'microsoft-edge': None,
    }
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setattr(module.shutil, 'which', lambda value: lookup.get(value))
    monkeypatch.setattr(module, '_browser_version', lambda executable: 'Browser 1.0')
    found = module.discover_browsers()
    assert found['chrome'].executable == '/usr/bin/chromium'
    assert found['msedge'].executable == '/usr/bin/microsoft-edge-stable'


def test_platform_neutral_cli_and_linux_bundle_are_first_class():
    cli = (ROOT / 'nicegui_base/cli.py').read_text(encoding='utf-8')
    for command in ("'doctor'", "'lab'", "'certify'", "'approve-baseline'"):
        assert command in cli
    for name in ('setup_linux.sh','run_lab.sh','certify_linux.sh','approve_visual_baseline.sh','reset_lab.sh'):
        path = ROOT / 'linux_bundle' / name
        assert path.exists()
        assert path.read_text(encoding='utf-8').startswith('#!/usr/bin/env bash')


def test_donut_and_heatmap_options_produce_meaningful_echarts_data():
    donut = build_echarts_options(
        ChartPanelSpec(title='Disposition', kind=ChartKind.DONUT),
        (SeriesSpec('state','State',(('Resolved',42),('Monitoring',18),('Open',9)),kind=ChartKind.DONUT),),
    )
    assert donut['series'][0]['data'][0]['name'] == 'Resolved' and donut['series'][0]['data'][0]['value'] == 42
    assert donut['series'][0]['data'][0]['itemStyle']['color']
    assert donut['series'][0]['radius'] == ['62%', '80%']
    heat = build_echarts_options(
        ChartPanelSpec(title='Heat', kind=ChartKind.HEATMAP, x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Mon','Tue')),
                       y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('ETCH-1','ETCH-2'))),
        (SeriesSpec('heat','Heat',((0,0,2.0),(1,0,4.0),(0,1,3.0),(1,1,5.0)),kind=ChartKind.HEATMAP),),
    )
    assert heat['visualMap']['min'] == 2.0
    assert heat['visualMap']['max'] == 5.0
    assert len(heat['series'][0]['data']) == 4


def test_spatial_views_are_custom_svg_renderers_not_generic_scatter_aliases():
    source = (ROOT / 'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    assert 'class _SpatialSvgPanel' in source
    assert 'class WaferMap(_SpatialSvgPanel)' in source
    assert 'class SpatialMap(_SpatialSvgPanel)' in source
    assert 'cui-wafer-boundary' in source and 'cui-wafer-notch' in source and 'cui-spatial-cell' in source
    assert "window.CompanyUISpatial.zoom" in source and "window.CompanyUISpatial.reset" in source


def test_shell_header_owns_title_subtitle_greeting_settings_and_user_region():
    source = inspect.getsource(nicegui_base.AppShell)
    for token in ('cui-shell-title','cui-shell-subtitle','cui-shell-greeting','_ApplicationMenu','UserMenu'):
        assert token in source
    assert 'Collapse or expand navigation' in source


def test_performance_lab_exposes_real_10k_100k_progress_and_timing():
    source = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    section = source[source.index('def _performance'):source.index('def _reference_about')]
    for token in ('10_000','100_000','generated_ms','Generation','Table mount','Filter benchmark','Cancelled'):
        assert token in section


def test_sbom_uses_live_certification_dependency_contract():
    from nicegui_base.supply_chain import LIVE_CERT_DEPENDENCIES, build_spdx_sbom
    assert LIVE_CERT_DEPENDENCIES == {'playwright':'1.62.0','Pillow':'12.3.0'}
    packages={p['name']:p['versionInfo'] for p in build_spdx_sbom()['packages']}
    assert packages['nicegui']=='3.15.0' and packages['playwright']=='1.62.0' and packages['Pillow']=='12.3.0'
