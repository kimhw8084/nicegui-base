from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_g26_identity_is_new_candidate_and_d6_state_remains_golden():
    from nicegui_base.workbench.update_identity import BUILD_ID
    assert BUILD_ID == 'NGB-20260907-G2.6'
    root_state = ROOT.parent / 'G2_STATE.json'
    assert root_state.exists()
    d6 = ROOT.parent / 'D6_STATE.json'
    if d6.exists():
        assert '"status": "GOLDEN"' in d6.read_text(encoding='utf-8')


def test_navigation_is_grouped_without_changing_primary_destination_set():
    from nicegui_base.workbench.app import workbench_navigation
    nav = workbench_navigation()
    assert tuple(section.label for section in nav.sections) == (
        'DISCOVER', 'FOUNDATIONS', 'COMPOSE', 'SEMICONDUCTOR', 'DEVELOP', 'SYSTEM'
    )
    labels = tuple(item.label for section in nav.sections for item in section.items)
    assert labels == (
        'Start Here', 'Design System', 'Components', 'Data & Tables', 'Visualizations',
        'Layouts', 'Application Patterns', 'Semiconductor Recipes', 'Full Applications',
        'AI Development Guide', 'Diagnostics',
    )
    assert all(item.route != '/build' for section in nav.sections for item in section.items)


def test_explorer_state_is_bounded_deterministic_and_section_scoped():
    from nicegui_base.workbench.explorer_state import ExplorerStateStore, MAX_COMPARE, MAX_RECENTS
    storage = {}
    store = ExplorerStateStore(storage)
    store.prime('analytics', query='spc', category='spc')
    for key in ('a', 'b', 'c', 'd'):
        store.toggle_compare('analytics', key)
    for i in range(20):
        store.add_recent('analytics', f'k{i}')
    state = store.load('analytics')
    assert state.query == 'spc' and state.category == 'spc'
    assert len(state.compare) == MAX_COMPARE and state.compare == ('b', 'c', 'd')
    assert len(state.recents) == MAX_RECENTS and state.recents[0] == 'k19'
    assert store.load('components').query == ''


def test_preview_assets_cover_golden_visual_discovery_families():
    from nicegui_base.workbench.preview_catalog import asset_for_key, data_uri
    from nicegui_base.workbench.catalog import analytics_entries, all_entries, recipe_entries
    from nicegui_base.workbench.models import WorkbenchKind

    components = tuple(entry for entry in all_entries() if entry.kind is WorkbenchKind.COMPONENT)
    patterns = tuple(entry for entry in all_entries() if entry.kind is WorkbenchKind.PATTERN)
    assert len(components) == 34 and len(patterns) == 10 and len(analytics_entries()) == 58 and len(recipe_entries()) == 8
    keys = [
        *(f"component:{entry.metadata['component_key']}" for entry in components),
        *(f"pattern:{entry.metadata['pattern_key']}" for entry in patterns),
        *(f"analytic:{entry.metadata['surface_key']}" for entry in analytics_entries()),
        *(f"recipe:{entry.metadata['recipe_key']}" for entry in recipe_entries()),
    ]
    assert all(asset_for_key(key) is not None for key in keys)
    assert data_uri('analytic:spc_i_mr').startswith('data:image/webp;base64,')


def test_gallery_filter_uses_canonical_entries_and_favorites_without_duplication():
    from nicegui_base.workbench.catalog import analytics_entries
    from nicegui_base.workbench.explorer_gallery import filtered_entries
    from nicegui_base.workbench.explorer_state import ExplorerState

    source = analytics_entries()
    spc = filtered_entries(source, ExplorerState(query='spc', category='spc'))
    assert spc and all(entry.category == 'spc' for entry in spc)
    keys = tuple(entry.key for entry in spc)
    fav = filtered_entries(source, ExplorerState(favorites_only=True, favorites=(keys[0],)))
    assert tuple(entry.key for entry in fav) == (keys[0],)
    assert len({entry.key for entry in source}) == len(source)


def test_reference_explorer_source_uses_gallery_and_preserves_scroll_state():
    app_source = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    css_source = (ROOT / 'nicegui_base/workbench/workbench_css.py').read_text(encoding='utf-8')
    assert 'render_reference_gallery' in app_source
    assert 'render_start_here' in app_source
    assert 'EXPLORER_BROWSER_STATE_SCRIPT' in app_source
    assert 'max-width:none!important' in css_source
    assert 'cui-explorer-gallery-grid' in css_source
    assert 'cui-nav-section+.cui-nav-section' in css_source


def test_package_data_declares_preview_assets():
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert '"nicegui_base.workbench"' in pyproject
    assert 'preview_assets/*.webp' in pyproject
    assert 'preview_assets/index.json' in pyproject
