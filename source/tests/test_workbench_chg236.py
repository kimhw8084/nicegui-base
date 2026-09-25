from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_explorer_search_requires_each_query_term_and_composes_filters() -> None:
    from nicegui_base.workbench.catalog import entries_for
    from nicegui_base.workbench.explorer_gallery import filtered_entries
    from nicegui_base.workbench.explorer_state import ExplorerState
    from nicegui_base.workbench.models import WorkbenchKind

    entries = entries_for(WorkbenchKind.COMPONENT)
    match = filtered_entries(entries, ExplorerState(query='MultiSelect'))
    assert tuple(entry.title for entry in match) == ('MultiSelect',)
    assert filtered_entries(entries, ExplorerState(query='zzzz-no-such-component-2026')) == ()
    assert len(filtered_entries(entries, ExplorerState())) == 34

    key = str(match[0].key)
    category = match[0].category
    combined = filtered_entries(
        entries,
        ExplorerState(query='MultiSelect', category=category, favorites_only=True, favorites=(key,)),
    )
    assert tuple(entry.key for entry in combined) == (match[0].key,)
    assert filtered_entries(
        entries,
        ExplorerState(query='MultiSelect', category=category, favorites_only=True, favorites=('component:unrelated',)),
    ) == ()


class _Node:
    def __init__(self, tag: str, text: str = '') -> None:
        self.tag = tag
        self.text = text
        self.classes_seen: list[str] = []
        self.props_calls: list[str] = []
        self.clear_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def classes(self, *values, **_kwargs):
        self.classes_seen.extend(value for value in values if isinstance(value, str))
        return self

    def props(self, value: str):
        self.props_calls.append(value)
        return self

    def clear(self):
        self.clear_calls += 1

    def set_text(self, value: str):
        self.text = value
        return self


class _UI:
    def __init__(self) -> None:
        self.nodes: list[_Node] = []

    def _node(self, tag: str, text: str = '') -> _Node:
        node = _Node(tag, text)
        self.nodes.append(node)
        return node

    def element(self, tag: str, *_args, **_kwargs):
        return self._node(tag)

    def label(self, text: str = '', *_args, **_kwargs):
        return self._node('label', text)


def test_gallery_sequential_search_events_render_current_projection_and_truthful_empty(monkeypatch) -> None:
    from nicegui_base.workbench import explorer_gallery
    from nicegui_base.workbench.catalog import entries_for
    from nicegui_base.workbench.explorer_state import ExplorerStateStore
    from nicegui_base.workbench.models import WorkbenchKind

    components = importlib.import_module('nicegui_base.integrations.nicegui_components')
    storage: dict[str, object] = {}
    fake_ui = _UI()
    monkeypatch.setitem(
        importlib.import_module('sys').modules,
        'nicegui',
        SimpleNamespace(ui=fake_ui, app=SimpleNamespace(storage=SimpleNamespace(user=storage))),
    )

    class FakeSearchInput:
        instances: list['FakeSearchInput'] = []

        def __init__(self, *_args, on_change=None, **_kwargs):
            self.element = _Node('search')
            self.on_change = on_change
            self.__class__.instances.append(self)

    class FakeSelect:
        instances: list['FakeSelect'] = []

        def __init__(self, *_args, on_change=None, **_kwargs):
            self.element = _Node('select')
            self.on_change = on_change
            self.__class__.instances.append(self)

    class FakeButton:
        instances: list['FakeButton'] = []

        def __init__(self, label, *, on_click=None, **_kwargs):
            self.label = label
            self.on_click = on_click
            self.element = _Node('button')
            self.__class__.instances.append(self)

        def set_label(self, label):
            self.label = label

    monkeypatch.setattr(components, 'SearchInput', FakeSearchInput)
    monkeypatch.setattr(components, 'Select', FakeSelect)
    monkeypatch.setattr(components, 'Button', FakeButton)
    monkeypatch.setattr(explorer_gallery, '_comparison', lambda *_args, **_kwargs: None)

    rendered_keys: list[str] = []
    monkeypatch.setattr(
        explorer_gallery,
        '_gallery_card',
        lambda entry, **_kwargs: rendered_keys.append(str(entry.key)),
    )
    entries = entries_for(WorkbenchKind.COMPONENT)
    explorer_gallery.render_reference_gallery(entries, section='components', intro='Components')
    store = ExplorerStateStore(storage)
    search = FakeSearchInput.instances[0]
    family = FakeSelect.instances[0]
    status = next(node for node in fake_ui.nodes if node.tag == 'label' and node.text.startswith('34 of 34 visible'))

    assert len(rendered_keys) == 34
    rendered_keys.clear()
    search.on_change(SimpleNamespace(value='MultiSelect'))
    assert store.load('components').query == 'MultiSelect'
    assert len(rendered_keys) == 1
    assert status.text.startswith('1 of 34 visible')

    rendered_keys.clear()
    search.on_change(SimpleNamespace(value='zzzz-no-such-component-2026'))
    assert store.load('components').query == 'zzzz-no-such-component-2026'
    assert rendered_keys == []
    assert status.text.startswith('0 of 34 visible')
    empty = next(node for node in fake_ui.nodes if 'cui-workbench-preview-empty' in node.classes_seen)
    assert 'role="status" aria-live="polite"' in empty.props_calls

    rendered_keys.clear()
    search.on_change(SimpleNamespace(value=''))
    assert store.load('components').query == ''
    assert len(rendered_keys) == 34
    assert status.text.startswith('34 of 34 visible')
    assert FakeSearchInput.instances == [search]
    assert FakeSelect.instances == [family]


def test_gallery_search_is_single_primary_control_outside_refinement() -> None:
    source = (ROOT / 'nicegui_base/workbench/explorer_gallery.py').read_text(encoding='utf-8')
    start = source.index("with ui.element('section').classes('cui-explorer-controls')")
    end = source.index('    def render()', start)
    controls = source[start:end]
    assert controls.count("SearchInput('Search'") == 1
    assert controls.index("SearchInput('Search'") < controls.index("ui.element('details').classes('cui-explorer-refine')")
    assert "SearchInput('Search'" not in controls[controls.index("ui.element('details').classes('cui-explorer-refine')"):]


def test_patterns_remains_the_distinct_unified_chooser() -> None:
    source = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    start = source.index('def patterns_page() -> None:')
    end = source.index('\ndef ai_guide_page()', start)
    route = source[start:end]
    assert 'data-unified-pattern-explorer' in route
    assert 'render_pattern(key' in route
    assert 'render_reference_gallery' not in route
    assert 'SearchInput' not in route
    assert 'cui-explorer-refine' not in route


def test_responsive_focus_sync_transfers_restores_and_preserves_external_focus() -> None:
    playwright_module = pytest.importorskip('playwright.sync_api')
    source = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    script_start = source.index("_EXPLORER_REFINE_RESPONSIVE_SCRIPT = r'''<script>")
    script_start = source.index('<script>', script_start) + len('<script>')
    script_end = source.index('</script>\'\'\'', script_start)
    script = source[script_start:script_end]
    html = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
.cui-explorer-refine,.cui-explorer-refine__body{display:contents}
.cui-explorer-refine>summary{display:none}
@media(max-width:680px){
 .cui-explorer-refine{display:block}
 .cui-explorer-refine>summary{display:flex}
 .cui-explorer-refine__body{display:none}
 .cui-explorer-refine[open] .cui-explorer-refine__body{display:grid}
}
</style>
<input id="search" aria-label="Search">
<details class="cui-explorer-refine" open>
 <summary tabindex="0">Refine references</summary>
 <div class="cui-explorer-refine__body">
  <div class="q-select" aria-label="Family"><input id="family" class="q-select__focus-target" aria-label="Family"></div>
  <button id="favorites" class="cui-button q-btn">Favorites only</button>
 </div>
</details>'''

    with playwright_module.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.set_content(html)
        page.evaluate('''(() => {
  const original = MediaQueryList.prototype.addEventListener;
  window.__refineChangeListeners = 0;
  MediaQueryList.prototype.addEventListener = function(type, listener, options) {
    if (type === 'change' && this.media === '(max-width: 680px)') window.__refineChangeListeners += 1;
    return original.call(this, type, listener, options);
  };
        })()''')
        page.add_script_tag(content=script)
        page.evaluate('window.__firstRefineResponsiveState = window.__niceguiBaseExplorerRefineResponsive')
        page.add_script_tag(content=script)
        assert page.evaluate('window.__refineChangeListeners') == 1
        assert page.evaluate('window.__niceguiBaseExplorerRefineResponsive === window.__firstRefineResponsiveState')
        assert page.locator('.cui-explorer-refine').evaluate('(details) => details.open') is True
        assert page.locator('.cui-explorer-refine > summary').is_visible() is False

        for _ in range(3):
            page.locator('#family').focus()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.wait_for_function("!document.querySelector('.cui-explorer-refine').open")
            assert page.locator('.cui-explorer-refine').evaluate('(details) => !details.open') is True
            assert page.locator('.cui-explorer-refine > summary').is_visible() is True
            assert page.evaluate('document.activeElement.tagName') == 'SUMMARY'
            page.locator('.cui-explorer-refine > summary').click()
            page.locator('#family').focus()
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.wait_for_function("document.querySelector('.cui-explorer-refine').open && document.activeElement.id === 'family'")
            assert page.locator('.cui-explorer-refine').evaluate('(details) => details.open') is True
            assert page.evaluate('document.activeElement.id') == 'family'
            assert page.locator('.cui-explorer-refine > summary').is_visible() is False

        page.locator('#search').focus()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.wait_for_function("matchMedia('(max-width: 680px)').matches")
        assert page.evaluate('document.activeElement.id') == 'search'
        page.set_viewport_size({'width': 1440, 'height': 900})
        page.wait_for_function("!matchMedia('(max-width: 680px)').matches")
        assert page.evaluate('document.activeElement.id') == 'search'

        page.set_viewport_size({'width': 390, 'height': 844})
        page.wait_for_function("matchMedia('(max-width: 680px)').matches && !document.querySelector('.cui-explorer-refine').open")
        page.locator('.cui-explorer-refine > summary').focus()
        assert page.evaluate('document.activeElement.tagName') == 'SUMMARY'
        page.locator('#family').evaluate('(element) => element.disabled = true')
        page.set_viewport_size({'width': 1440, 'height': 900})
        page.wait_for_function("!matchMedia('(max-width: 680px)').matches && document.activeElement.id === 'favorites'")
        assert page.evaluate('document.activeElement.id') == 'favorites'
        assert page.evaluate('document.activeElement.tagName') != 'BODY'
        browser.close()
