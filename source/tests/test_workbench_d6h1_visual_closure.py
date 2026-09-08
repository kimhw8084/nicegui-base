"""D6H.1 visual/reference closure regressions."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
REPO = ROOT.parent


def test_d6h1_identity_and_required_visual_acceptance_scope():
    from nicegui_base.workbench.update_identity import BUILD_ID

    assert BUILD_ID == 'NGB-20260907-G2.6'
    browser = (REPO / 'tools' / 'verify_development_D6H_browser.py').read_text(encoding='utf-8')
    assert "'/workbench/data'" in browser
    assert "'/analytics'" in browser
    assert "'/layouts'" in browser
    assert "'/recipes'" in browser
    assert "'/applications'" in browser
    assert "'/ai-guide'" in browser
    assert "'NGB-20260906-D6H.1'" in browser


def test_design_reference_has_live_token_teaching_contract():
    source = (ROOT / 'nicegui_base/workbench/design_system_reference.py').read_text(encoding='utf-8')

    for marker in (
        'data-token-specimen', 'Recommended use', "Don't", 'Copy semantic API',
        'cui-d6c-live-specimen', 'cui-d6c-responsive-canvas',
    ):
        assert marker in source


def test_reference_details_prioritize_live_example_and_hide_debug_in_reference_mode():
    source = (ROOT / 'nicegui_base/workbench/capability_studio.py').read_text(encoding='utf-8')
    assert 'cui-studio-header--compact' in source
    assert 'Reference example' in source
    assert "if not reference_only" in source
    assert 'cui-studio-event-log' in source


def test_catalog_filters_are_compact_on_phone_and_full_apps_have_one_title_owner():
    app = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    css = (ROOT / 'nicegui_base/workbench/workbench_css.py').read_text(encoding='utf-8')
    apps = (ROOT / 'nicegui_base/workbench/full_applications.py').read_text(encoding='utf-8')
    assert 'cui-catalog-refine' in app
    assert 'cui-catalog-refine__summary' in css
    assert "_shell('/applications', 'Full Applications'" in app
    assert "with page_class(definition.title, definition.description) as page:" in apps
    assert 'data-full-application' in apps


def test_semantic_visualization_acceptance_checks_rendered_chart_body():
    browser = (REPO / 'tools' / 'verify_development_D6H_browser.py').read_text(encoding='utf-8')
    assert 'data-visual-semantic' in browser
    assert 'chart body' in browser.casefold()
    assert 'canvas' in browser
    assert 'svg' in browser
