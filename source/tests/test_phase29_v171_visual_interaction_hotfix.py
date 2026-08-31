from pathlib import Path

from nicegui_base.version import FRAMEWORK_VERSION
from nicegui_base.visualization.models import AxisSpec, AxisType, ChartKind, ChartPanelSpec, LegendPosition, SeriesSpec, ChartToolbarSpec
from nicegui_base.visualization.options import build_echarts_options

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text()


def test_v171_identity_and_runtime_pin_are_preserved():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert f'version = "{FRAMEWORK_VERSION}"' in _text('pyproject.toml')
    assert 'nicegui==3.15.0' in _text('requirements.txt')


def test_environment_badge_is_company_owned_and_semantically_distinct():
    source = _text('nicegui_base/integrations/nicegui_layout.py')
    region = source[source.index('class EnvironmentBadge:'):source.index('class AppHeader', source.index('class EnvironmentBadge:'))]
    assert "ui.element('span').classes(f'cui-environment-badge" in region
    assert "_ui().badge(" not in region
    assert 'cui-environment-badge__dot' in region
    css = _text('nicegui_base/design/hardening_css.py')
    for tone in ('development','staging','production'):
        assert f'.cui-environment-badge--{tone}' in css
    assert '.cui-environment-badge::before{display:none!important' in css


def test_compact_sidebar_footer_is_native_icon_dock_and_callbacks_are_awaited():
    source = _text('nicegui_base/integrations/nicegui_layout.py')
    footer = source[source.index('def _render_support_footer'):source.index('@dataclass', source.index('def _render_support_footer'))]
    assert "ui.element('button').classes('cui-sidebar-footer__action')" in footer
    assert 'cui-sidebar-footer__action-label' in footer
    assert 'ui.button(on_click=on_support)' not in footer
    assert 'async def _toggle_mobile' in source and 'await self.mobile_drawer.toggle()' in source
    assert 'async def _toggle_sidebar' in source and 'return await _ui().run_javascript' in source
    css = _text('nicegui_base/design/hardening_css.py')
    assert "html[data-sidebar='compact'] .cui-sidebar-footer__action-label{display:none!important;}" in css
    assert "html[data-sidebar='compact'] .cui-sidebar-footer__action" in css
    assert "width:36px!important;height:36px!important" in css
    assert "transform:translate(-50%,-50%)!important" in css


def test_switch_and_range_slider_share_company_owned_geometry():
    source = _text('nicegui_base/integrations/nicegui_components.py')
    region = source[source.index('class RangeSlider:'):source.index('class _NativeTemporalField', source.index('class RangeSlider:'))]
    assert 'ui.range(' not in region
    assert region.count("type=\"range\"") >= 1
    assert 'data-cui-range-handle="low"' in region and 'data-cui-range-handle="high"' in region
    css = _text('nicegui_base/design/hardening_css.py')
    assert '.cui-choice-row--switch .cui-switch-track{position:relative!important;box-sizing:border-box!important;width:51px!important;height:31px!important' in css
    assert '.cui-native-range__track{' in css and '.cui-native-range__input::-webkit-slider-thumb' in css


def test_progress_is_company_owned_and_has_reliable_indeterminate_animation():
    source = _text('nicegui_base/integrations/nicegui_interactions.py')
    region = source[source.index('class ProgressBar:'):source.index('class Spinner:', source.index('class ProgressBar:'))]
    assert 'linear_progress' not in region
    assert "ui.element('div').classes(classes)" in region
    assert "ui.element('span').classes('cui-progress__bar')" in region
    content = _text('nicegui_base/integrations/nicegui_content.py')
    assert "ProgressBar(value=pct, label=label)" in content
    css = _text('nicegui_base/design/hardening_css.py')
    assert '@keyframes cui-v171-progress-indeterminate' in css
    assert '.cui-progress.is-indeterminate .cui-progress__bar' in css


def test_detail_form_and_inspector_drawers_are_edge_anchored_side_sheets():
    source = _text('nicegui_base/integrations/nicegui_interactions.py')
    assert ".classes('cui-drawer-host')" in source
    css = _text('nicegui_base/design/hardening_css.py')
    assert '.q-dialog__inner:has(.cui-drawer){padding:0!important' in css
    assert 'justify-content:flex-end!important' in css
    assert 'height:100dvh!important' in css
    assert 'border-radius:var(--cui-radius-overlay) 0 0 var(--cui-radius-overlay)!important' in css
    assert '@keyframes cui-v171-drawer-right' in css


def test_donut_uses_per_category_colors_and_stacked_bar_joins_are_continuous():
    donut = ChartPanelSpec('Disposition', kind=ChartKind.DONUT, legend=LegendPosition.TOP, toolbar=ChartToolbarSpec())
    donut_options = build_echarts_options(
        donut,
        (SeriesSpec('state','State',(('Resolved',42),('Monitoring',18),('Open',9)), kind=ChartKind.DONUT),),
    )
    colors = [item['itemStyle']['color'] for item in donut_options['series'][0]['data']]
    assert len(set(colors)) == 3

    stacked = ChartPanelSpec(
        'Affected vs control', ChartKind.STACKED_BAR,
        x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('A','B')),
        toolbar=ChartToolbarSpec(),
    )
    options = build_echarts_options(stacked, (
        SeriesSpec('affected','Affected',(18,24),kind=ChartKind.STACKED_BAR,stack='population'),
        SeriesSpec('control','Control',(42,38),kind=ChartKind.STACKED_BAR,stack='population'),
    ))
    assert options['series'][0]['itemStyle']['borderRadius'] == [0,0,5,5]
    assert options['series'][1]['itemStyle']['borderRadius'] == [5,5,0,0]


def test_workflow_has_only_one_connector_system():
    css = _text('nicegui_base/design/hardening_css.py')
    assert '.cui-progress-step::after{content:none!important;display:none!important;}' in css
    assert '.cui-progress-step__rail::after' in css


def test_command_palette_uses_native_search_and_native_action_buttons():
    source = _text('nicegui_base/integrations/nicegui_content.py')
    region = source[source.index('class CommandPalette:'):source.index('class BackgroundTaskIndicator:', source.index('class CommandPalette:'))]
    assert "ui.element('input').classes('cui-command-palette__search-input')" in region
    assert "ui.element('button').classes('cui-command-palette__item')" in region
    assert 'ui.input(' not in region
    assert 'ui.button(on_click=run)' not in region
    assert region.index('self.close()') < region.index("await _invoke(lambda: self.registry.execute(c.key))")


def test_engineering_entity_metadata_has_single_containment_geometry():
    css = _text('nicegui_base/design/hardening_css.py')
    assert '.cui-eng-entity{box-sizing:border-box!important;border-radius:var(--cui-radius-surface)!important;padding:18px!important;overflow:hidden!important;}' in css
    assert '.cui-eng-property-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important' in css
    assert 'border:0!important;border-radius:0!important;background:transparent!important' in css
    assert '.cui-eng-property{box-sizing:border-box!important;width:100%!important;min-width:0!important;min-height:72px!important;padding:12px 13px!important;border-radius:var(--cui-radius-control)!important;' in css
    assert '@container (max-width:760px){.cui-eng-property-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;}}' in css


def test_header_title_and_profile_hierarchy_are_materially_stronger():
    css = _text('nicegui_base/design/hardening_css.py')
    assert '.cui-shell-title{font-size:var(--cui-type-app_identity-size)!important;line-height:var(--cui-type-app_identity-line)!important;font-weight:var(--cui-type-app_identity-weight)!important' in css
    assert '.cui-shell-title-block::before' in css
    assert '.cui-shell-greeting__name{font-size:var(--cui-type-profile_name-size)!important;line-height:var(--cui-type-profile_name-line)!important;font-weight:var(--cui-type-profile_name-weight)!important;color:var(--cui-text-primary)!important;}' in css


def test_browser_certification_guards_all_screenshot_regressions():
    source = _text('nicegui_base/certification/mac_browser.py')
    for phrase in (
        'environment metadata still uses Quasar badge anatomy',
        'collapsed sidebar footer leaked text labels',
        'detail drawer rendered as floating popup instead of full-height side sheet',
        'range slider still exposes Quasar slider anatomy',
        'determinate progress rendered text inside track',
        'indeterminate progress animation is inactive',
        'obsolete workflow connector pseudo-element is still visible',
        'command palette search still exposes Quasar field anatomy',
        'donut categories still render with one color',
        'stacked bar outer/interior corner geometry is not differentiated',
        'application title lacks required 17px/750 hierarchy',
    ):
        assert phrase in source
    assert "'/feedback'" not in source.split('KEY_ROUTES =',1)[1].split('\n',1)[0]
    assert "elif route=='/feedback'" not in source
    forms_block = source[source.index("elif route=='/forms'"):source.index("elif route=='/controls'")]
    assert 'determinate progress rendered text inside track' in forms_block


def test_no_raw_range_or_linear_progress_in_canonical_surfaces():
    roots = [ROOT / "nicegui_base" / "integrations", ROOT / "nicegui_base" / "certification" / "mac_lab.py"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in roots
        for path in ([root] if root.is_file() else root.glob("*.py"))
    )
    assert "ui.range(" not in text
    assert "ui.linear_progress(" not in text


def test_historical_hotfix_guide_is_preserved_but_not_seeded_to_current_agents():
    source = (ROOT / "docs" / "V171_VISUAL_INTERACTION_HOTFIX.md").read_text(encoding="utf-8")
    embedded = (ROOT / "nicegui_base" / "ai" / "guides" / "V171_VISUAL_INTERACTION_HOTFIX.md").read_text(encoding="utf-8")
    scaffold = (ROOT / "nicegui_base" / "ai" / "scaffold.py").read_text(encoding="utf-8")
    assert source == embedded
    assert "\'V171_VISUAL_INTERACTION_HOTFIX.md\'" not in scaffold


def test_mac_bundle_is_not_legacy_and_separates_runtime_from_browser_certification():
    setup = (ROOT / "mac_bundle" / "setup_mac.sh").read_text(encoding="utf-8")
    run_lab = (ROOT / "mac_bundle" / "run_lab.sh").read_text(encoding="utf-8")
    cert = (ROOT / "mac_bundle" / "certify_mac.sh").read_text(encoding="utf-8")
    installer = (ROOT / "mac_bundle" / "install_certification_deps.sh").read_text(encoding="utf-8")
    assert f"nicegui_base-{FRAMEWORK_VERSION}-" in setup and "1.5.0" not in setup
    assert 'pip install -r "$REQ"' in setup
    assert 'pip install --no-deps "$WHEEL"' in setup
    assert "runtime-contract" in setup and "runtime-smoke" in setup
    assert "--no-require-browser" in setup and "--no-require-browser" in run_lab
    assert "requirements-certification.txt" in installer
    assert "install_certification_deps.sh" in cert
