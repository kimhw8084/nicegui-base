from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / 'nicegui_base/workbench/explorer_gallery.py'
APP = ROOT / 'nicegui_base/workbench/app.py'
CSS = ROOT / 'nicegui_base/workbench/workbench_css.py'


def _controls_source() -> str:
    source = GALLERY.read_text(encoding='utf-8')
    start = source.index("with ui.element('section').classes('cui-explorer-controls')")
    return source[start:source.index('    def render()', start)]


def test_desktop_refinement_is_native_open_before_summary_is_hidden() -> None:
    controls = _controls_source()
    css = CSS.read_text(encoding='utf-8')

    assert "with ui.element('details').classes('cui-explorer-refine').props('open'):" in controls
    assert "with ui.element('summary').props('tabindex=\"0\"'):" in controls
    assert "with ui.element('div').classes('cui-explorer-refine__body'):" in controls
    assert '.cui-explorer-refine,.cui-explorer-refine__body{display:contents}' in css
    assert '.cui-explorer-refine>summary{display:none}' in css


def test_mobile_refinement_keeps_native_closed_open_disclosure_contract() -> None:
    css = CSS.read_text(encoding='utf-8')
    mobile = css[css.rindex('@media(max-width:680px)'):]

    assert '.cui-explorer-refine{display:block}' in mobile
    assert '.cui-explorer-refine>summary{display:flex' in mobile
    assert '.cui-explorer-refine__body{display:none' in mobile
    assert '.cui-explorer-refine[open] .cui-explorer-refine__body{display:grid}' in mobile


def test_explorer_keeps_one_search_and_one_secondary_control_authority() -> None:
    controls = _controls_source()

    assert controls.count("search = SearchInput('Search'") == 1
    assert controls.count("Select('Family'") == 1
    assert controls.count("Button('All references' if state.favorites_only else 'Favorites only'") == 1
    assert controls.index("search = SearchInput('Search'") < controls.index("with ui.element('details').classes('cui-explorer-refine')")
    assert controls.index("Select('Family'") > controls.index("with ui.element('details').classes('cui-explorer-refine')")
    assert controls.index("Button('All references' if state.favorites_only else 'Favorites only'") > controls.index("with ui.element('details').classes('cui-explorer-refine')")


def test_workbench_responsive_sync_is_singleton_idempotent_and_focus_safe() -> None:
    source = APP.read_text(encoding='utf-8')
    script = source[source.index("_EXPLORER_REFINE_RESPONSIVE_SCRIPT ="):source.index("\n\n\ndef _imports", source.index("_EXPLORER_REFINE_RESPONSIVE_SCRIPT ="))]

    assert script.count("__niceguiBaseExplorerRefineResponsive") == 1
    assert 'if (window[key]) {' in script
    assert 'const mounted = new WeakSet();' in script
    assert "window.matchMedia('(max-width: 680px)')" in script
    assert 'details.open = !media.matches;' in script
    assert "media.addEventListener('change', changed)" in script
    assert 'new MutationObserver(() => state.scan())' in script
    assert 'const focusInside = media.matches && details.contains(document.activeElement);' in script
    assert "details.querySelector(':scope > summary')?.focus();" in script


def test_responsive_sync_is_installed_once_by_workbench_presentation_root() -> None:
    source = APP.read_text(encoding='utf-8')

    assert source.count('ui.add_head_html(_EXPLORER_REFINE_RESPONSIVE_SCRIPT, shared=True)') == 1
    assert source.count("ui.add_head_html(EXPLORER_BROWSER_STATE_SCRIPT, shared=True)") == 1
