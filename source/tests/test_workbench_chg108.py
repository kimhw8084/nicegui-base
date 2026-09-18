from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def test_gallery_search_is_primary_and_refinement_remains_secondary() -> None:
    source = (ROOT / 'nicegui_base/workbench/explorer_gallery.py').read_text(encoding='utf-8')
    controls = source[source.index("with ui.element('section').classes('cui-explorer-controls')"):source.index('    def render()', source.index("with ui.element('section').classes('cui-explorer-controls')"))]

    assert controls.count("search = SearchInput('Search'") == 1
    assert controls.index("search = SearchInput('Search'") < controls.index("with ui.element('details').classes('cui-explorer-refine')")
    refinement = controls[controls.index("with ui.element('details').classes('cui-explorer-refine')"):]
    assert "Select('Family'" in refinement
    assert "Button('All references' if state.favorites_only else 'Favorites only'" in refinement
    assert "search = SearchInput('Search'" not in refinement


def test_gallery_search_keeps_one_filtered_entry_authority_and_secondary_filters() -> None:
    from nicegui_base.workbench.catalog import entries_for
    from nicegui_base.workbench.explorer_gallery import filtered_entries
    from nicegui_base.workbench.explorer_state import ExplorerState
    from nicegui_base.workbench.models import WorkbenchKind

    entries = entries_for(WorkbenchKind.COMPONENT)
    matches = filtered_entries(entries, ExplorerState(query='MultiSelect'))
    assert matches
    assert tuple(entry.title for entry in matches) == ('MultiSelect',)
    favorite = str(matches[0].key)
    assert tuple(entry.key for entry in filtered_entries(
        entries, ExplorerState(query='select', favorites_only=True, favorites=(favorite,))
    )) == (matches[0].key,)
    assert all(entry.category == matches[0].category for entry in filtered_entries(
        entries, ExplorerState(query='select', category=matches[0].category)
    ))


def test_code_viewer_labels_native_copy_button(monkeypatch) -> None:
    from nicegui_base.integrations import nicegui_content

    class FakeButton:
        def __init__(self) -> None:
            self.props_calls: list[str] = []

        def props(self, value: str):
            self.props_calls.append(value)
            return self

    class FakeCode:
        def __init__(self) -> None:
            self.copy_button = FakeButton()

        def classes(self, *_args, **_kwargs):
            return self

    fake_code = FakeCode()
    monkeypatch.setitem(__import__('sys').modules, 'nicegui', SimpleNamespace(ui=SimpleNamespace(code=lambda *_args, **_kwargs: fake_code)))

    viewer = nicegui_content.CodeViewer('print(1)', language='python')

    assert viewer.element is fake_code
    assert fake_code.copy_button.props_calls == ['aria-label="Copy code"']


def test_select_focus_hook_targets_actual_quasar_combobox_and_shared_field_semantics(monkeypatch) -> None:
    from nicegui_base.integrations import nicegui_components

    class Chain:
        next_id = 100

        def __init__(self, value=None) -> None:
            self.id = Chain.next_id
            Chain.next_id += 1
            self.value = value
            self.props_calls: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def classes(self, *_args, **_kwargs):
            return self

        def props(self, value: str):
            self.props_calls.append(value)
            return self

    class FakeUI:
        def __init__(self) -> None:
            self.javascript: list[str] = []

        def column(self):
            return Chain()

        def element(self, *_args, **_kwargs):
            return Chain()

        def label(self, *_args, **_kwargs):
            return Chain()

        def select(self, *args, **kwargs):
            return Chain(kwargs.get('value'))

        def run_javascript(self, code: str):
            self.javascript.append(code)

    fake_ui = FakeUI()
    monkeypatch.setitem(__import__('sys').modules, 'nicegui', SimpleNamespace(ui=fake_ui))

    select = nicegui_components.Select(
        'Status', {'ready': 'Ready', 'blocked': 'Blocked'}, description='Current state', error='Choose a valid state',
    )

    props = select.element.props_calls[0]
    assert 'outlined dense options-dense hide-bottom-space' in props
    assert 'aria-label="Status"' in props
    assert 'aria-describedby="cui-field-' in props and '-description cui-field-' in props and '-error"' in props
    assert 'aria-invalid="true"' in props
    assert len(fake_ui.javascript) == 1
    hook = fake_ui.javascript[0]
    assert 'getElement(rootId)' in hook
    assert "'.q-select__focus-target, .q-field__input[role=\"combobox\"]'" in hook
    assert 'aria-label' in hook and 'Status' in hook
    assert 'description' in hook and 'error' in hook
    assert 'MutationObserver' in hook
