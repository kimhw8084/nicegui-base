from __future__ import annotations

import inspect
from pathlib import Path

import nicegui_base
from nicegui_base.certification.mac_lab import ROUTES
from nicegui_base.design.hardening_css import build_hardening_css
from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, SeriesSpec, build_echarts_options

ROOT = Path(__file__).resolve().parents[1]


def test_main_canvas_uses_real_sidebar_width_math_and_full_outer_page_canvas():
    css = build_hardening_css()
    assert 'margin-left:var(--cui-shell-sidebar-width)!important' in css
    assert 'width:calc(100% - var(--cui-shell-sidebar-width))!important' in css
    assert 'margin-left:var(--cui-shell-sidebar-compact-width)!important' in css
    assert 'width:calc(100% - var(--cui-shell-sidebar-compact-width))!important' in css
    assert '.cui-page--reading,.cui-page--standard,.cui-page--wide,.cui-page--full' in css
    outer = css[css.index('.cui-page--reading,.cui-page--standard,.cui-page--wide,.cui-page--full'):]
    assert 'width:100%!important' in outer[:500]
    assert 'max-width:none!important' in outer[:500]
    # Shell offset is not implemented as page padding: gutters belong to .cui-page only.
    sidebar_rule = css[css.index('.cui-app-main--with-sidebar{'):css.index("html[data-sidebar='compact'] .cui-app-main--with-sidebar{")]
    assert 'padding-left:var(--cui-shell-sidebar-width)' not in sidebar_rule


def test_browser_certification_blocks_canvas_asymmetry_and_gutter_regressions():
    source = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for code in ('MAIN_CANVAS_WIDTH_MISMATCH','PAGE_CANVAS_NOT_FULL_WIDTH','PAGE_GUTTER_MISSING','PAGE_TOP_GUTTER_MISMATCH'):
        assert code in source


def test_shell_owns_one_desktop_collapse_control_and_frozen_support_footer():
    source = inspect.getsource(nicegui_base.AppShell)
    assert source.count('aria-label="Collapse or expand navigation"') == 1
    assert "ui.element('aside').classes('cui-app-sidebar')" in source
    assert 'MobileNavigationDrawer' in source
    assert '_render_support_footer' in source
    css = build_hardening_css()
    assert '.cui-sidebar-footer{flex:0 0 auto;margin-top:auto' in css
    assert ".cui-app-sidebar:not(.q-drawer)" in css


def test_shell_primitives_route_uses_canonical_responsive_shell_without_competing_mobile_demo():
    source = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    section = source[source.index('def _shell_primitives'):source.index('def _overview')]
    assert "shell = _shell(" in section
    assert 'Open mobile navigation' not in section
    assert 'one navigation affordance' in section.lower()


def test_data_table_updates_rows_in_place_and_lab_has_real_inspection_export_and_double_click():
    table_source = (ROOT / 'nicegui_base/integrations/nicegui_data_table.py').read_text(encoding='utf-8')
    assert 'async def replace_rows' in table_source
    assert "run_grid_method('setGridOption','rowData',self.rows)" in table_source
    lab = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    data = lab[lab.index('def _data'):lab.index('def _charts')]
    for token in ('inspect_measurement','InspectorDrawer','row_double_click','on_row_double_click=row_double_click','ui.download.content','Exported'):
        assert token in data


def test_engineering_metadata_uses_contained_property_cells():
    source = (ROOT / 'nicegui_base/integrations/nicegui_engineering.py').read_text(encoding='utf-8')
    css = build_hardening_css()
    for cls in ('cui-eng-property-grid','cui-eng-property','cui-eng-property__label','cui-eng-property__value'):
        assert cls in source
        assert f'.{cls}' in css
    assert 'overflow-wrap:anywhere' in css


def test_image_viewer_lab_uses_meaningful_local_engineering_evidence_image():
    lab = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    assert 'def _synthetic_inspection_image' in lab
    assert 'Wafer 12 · CD residual evidence' in lab
    assert "ImageViewer(_synthetic_inspection_image()" in lab
    assert 'Lower-right excursion cluster' in lab


def test_select_family_does_not_double_transform_nicegui_option_model():
    source = (ROOT / 'nicegui_base/integrations/nicegui_components.py').read_text(encoding='utf-8')
    assert 'emit-value map-options' not in source
    assert 'with_input=' in source


def test_chart_zoom_targets_explicit_datazoom_and_export_is_one_menu():
    source = (ROOT / 'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    assert "'dataZoomId':self.IDS[a]" in source
    toolbar = source[source.index('class ChartToolbar'):source.index('class ChartPanel')]
    assert toolbar.count("ui.label('Export')") <= 1
    assert 'Image · PNG' in toolbar and 'Data · CSV' in toolbar


def test_phase19_lab_still_has_all_routes_and_visual_laboratories():
    assert len(ROUTES) == 21
    paths = {route.path for route in ROUTES}
    assert {'/shell','/controls','/forms','/data','/charts','/content','/engineering','/performance'} <= paths


def test_analytical_echarts_supports_direct_2d_zoom_without_hidden_modifier_gesture():
    options = build_echarts_options(
        ChartPanelSpec(title='Trend',kind=ChartKind.LINE,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('A','B','C')),y_axis=AxisSpec(label='CD',kind=AxisType.VALUE)),
        (SeriesSpec('cd','CD',(39.5,40.2,41.0),kind=ChartKind.LINE),),
    )
    zoom=options['dataZoom']
    assert zoom[0]['xAxisIndex'] == 0 and zoom[0]['zoomOnMouseWheel'] is True
    assert zoom[1]['yAxisIndex'] == 0 and zoom[1]['zoomOnMouseWheel'] is True
    assert zoom[0]['moveOnMouseMove'] is True and zoom[1]['moveOnMouseMove'] is True
    assert options['yAxis']['nameGap'] >= 46


def test_browser_geometry_blocks_missing_spacing_offscreen_overlays_and_toast_collision():
    source=(ROOT/'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for code in ('VERTICAL_GAP_TOO_SMALL','GRID_GAP_TOO_SMALL','SURFACE_PADDING_MISSING','OVERLAY_OUTSIDE_VIEWPORT','TOAST_HEADER_COLLISION'):
        assert code in source
    for phrase in ('sidebar did not physically collapse','Operator Note is not editable','table row double-click did not open inspector','chart zoom control did not change dataZoom range'):
        assert phrase in source


def test_semiconductor_native_visualization_set_includes_comparison_and_radial_profile():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    registry=(ROOT/'nicegui_base/visualization/registry.py').read_text(encoding='utf-8')
    lab=(ROOT/'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    for name in ('WaferComparisonMap','RadialProfilePlot'):
        assert f'class {name}' in source
        assert name in registry and name in lab
        assert hasattr(nicegui_base,name) and name in nicegui_base.__all__
    assert 'SAME COLOR SCALE' in source
    assert 'CENTER · r/R 0.0' in source and 'EDGE · r/R 1.0' in source
    assert 'cui-radial-profile--affected' in build_hardening_css()


def test_live_visual_coverage_expands_with_new_custom_engineering_renderers():
    from nicegui_base.certification.mac_coverage import coverage_summary
    summary=coverage_summary()
    assert summary['required_visual_components'] == 183
    assert summary['covered_visual_components'] == 183
    assert summary['uncovered'] == []


def test_canonical_reference_apps_keep_grid_geometry_inside_full_width_canvas():
    css=build_hardening_css()
    assert '.cui-page.cui-pattern{display:grid!important' in css
    assert '.cui-pattern--wizard .cui-pattern-slot--content' in css
    assert '.cui-pattern--data_explorer .cui-pattern-slot--data' in css
    assert 'width:100%!important;max-width:none!important' in css


def test_browser_certification_proves_top_right_menus_and_overlay_alignment():
    source=(ROOT/'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for code in ('DIALOG_HEADER_ALIGNMENT','FIELD_APPEND_OUTSIDE_CONTROL'):
        assert code in source
    for phrase in ('application settings menu did not become visible','user menu did not become visible','application settings menu collided with header','user menu collided with header'):
        assert phrase in source


def test_manual_linux_lab_does_not_require_chromium_or_curl():
    cli=(ROOT/'nicegui_base/cli.py').read_text(encoding='utf-8')
    setup=(ROOT/'linux_bundle/setup_linux.sh').read_text(encoding='utf-8')
    run=(ROOT/'linux_bundle/run_lab.sh').read_text(encoding='utf-8')
    assert "--no-require-browser" in cli
    assert 'doctor --runtime-only --ignore-port --port 8080 --no-require-browser' in setup
    assert 'doctor --runtime-only --port 8080 --no-require-browser' in run
    assert 'required_cmd in sha256sum curl' not in setup
    assert 'urllib.request' in run
