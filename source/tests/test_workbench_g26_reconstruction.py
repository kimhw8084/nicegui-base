"""G2.6 Reference Explorer usability contracts.

These are source-level contracts for the shared presentation authorities.  Browser
qualification remains the proof for geometry and interaction.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / 'nicegui_base' / 'workbench'


def test_g26_identity_and_human_first_gallery_contract():
    from nicegui_base.workbench.explorer_gallery import INTENTS
    from nicegui_base.workbench.update_identity import BUILD_ID

    assert BUILD_ID == 'NGB-20260907-G2.6'
    assert len(INTENTS) == 10
    assert all(item.icon and item.example for item in INTENTS)
    source = (WORKBENCH / 'explorer_gallery.py').read_text(encoding='utf-8')
    assert 'View recommendation' in source
    assert 'Clear recommendation' in source
    assert 'Baseline evidence' not in source


def test_g26_gallery_is_content_driven_and_build_id_is_not_a_toolbar_control():
    css = (WORKBENCH / 'workbench_css.py').read_text(encoding='utf-8')
    app = (WORKBENCH / 'app.py').read_text(encoding='utf-8')
    assert '.cui-explorer-card,.cui-explorer-authority-card{content-visibility:visible' in css
    assert '.cui-explorer-intent-card{min-height:0}' in css
    assert '.cui-d6c-token-family__body{display:grid;grid-template-columns:minmax(0,1fr)' in css
    assert "ui.label(BUILD_ID).classes('cui-workbench-chip cui-build-id')" not in app
    assert "data-build-id=\"{BUILD_ID}\"" in app


def test_g26_design_system_teaches_examples_before_raw_tokens():
    source = (WORKBENCH / 'design_system_reference.py').read_text(encoding='utf-8')
    for marker in ('Tight', 'Related', 'Stack', 'Content', 'Section', 'Page', 'View token details'):
        assert marker in source
    assert 'cui-d6c-type-page-title' in source


def test_g26_detail_tabs_are_capability_driven():
    from nicegui_base.workbench.capability_studio import studio_tabs_for_entry
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind

    divider = WorkbenchEntry('component:divider', WorkbenchKind.COMPONENT, 'Divider', 'Separates content.', '/components/divider', metadata={'component_key': 'divider'}, live_preview=True)
    button = WorkbenchEntry('component:button', WorkbenchKind.COMPONENT, 'Button', 'Runs an action.', '/components/button', metadata={'component_key': 'button'}, live_preview=True)
    assert studio_tabs_for_entry(divider) == ('preview', 'usage', 'inspect', 'code')
    assert 'interactions' in studio_tabs_for_entry(button)
    assert 'configure' in studio_tabs_for_entry(button)


def test_g26_application_gallery_explains_real_domain_compositions():
    from nicegui_base.workbench.full_applications import full_application_entries

    entries = full_application_entries()
    assert len(entries) == 3
    assert len({entry.primary_surface_key for entry in entries}) == 3
    assert all(entry.domain_facets and entry.composition_apis for entry in entries)
    source = (WORKBENCH / 'explorer_gallery.py').read_text(encoding='utf-8')
    assert 'View architecture' in source
    assert 'Create from this' not in source


def test_g26_diagnostics_keeps_deep_readiness_details_out_of_the_first_layer():
    source = (WORKBENCH / 'app.py').read_text(encoding='utf-8')
    assert "with _section('System health'" in source
    assert 'Advanced implementation details' in source
    assert "with ui.element('details').classes('cui-workbench-section cui-diagnostics-advanced')" in source
