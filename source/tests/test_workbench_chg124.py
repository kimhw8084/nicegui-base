from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest


class _Node:
    def __init__(self, tag: str, text: str = '') -> None:
        self.tag = tag
        self.text = text
        self.props_calls: list[str] = []
        self.clear_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def classes(self, *_args, **_kwargs):
        return self

    def props(self, value: str):
        self.props_calls.append(value)
        return self

    def on(self, *_args, **_kwargs):
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

    def html(self, *_args, **_kwargs):
        return self._node('html')

    def button(self, text: str = '', *_args, **_kwargs):
        return self._node('button', text)


@pytest.mark.parametrize('icon', [None, 'arrow-right'])
def test_governed_button_set_label_updates_visible_text_and_accessibility_name(monkeypatch, icon):
    from nicegui_base import Button

    fake_ui = _UI()
    monkeypatch.setitem(sys.modules, 'nicegui', SimpleNamespace(ui=fake_ui))

    button = Button('Favorites only', icon=icon, on_click=lambda: None)
    mounted_element = button.element

    button.set_label('All references')

    assert button.spec.label == 'All references'
    assert button.element is mounted_element
    assert button.element.props_calls[-1] == 'aria-label="All references"'
    if icon:
        assert button.label_element.text == 'All references'
    else:
        assert button.element.text == 'All references'


def test_refinement_toggle_updates_one_mounted_action_without_collapsing_disclosure(monkeypatch):
    from nicegui_base.workbench import explorer_gallery
    from nicegui_base.workbench.explorer_state import ExplorerStateStore
    components = importlib.import_module('nicegui_base.integrations.nicegui_components')

    storage: dict[str, object] = {}
    fake_ui = _UI()
    monkeypatch.setitem(
        sys.modules,
        'nicegui',
        SimpleNamespace(ui=fake_ui, app=SimpleNamespace(storage=SimpleNamespace(user=storage))),
    )

    class FakeSearchInput:
        instances: list['FakeSearchInput'] = []

        def __init__(self, *_args, **_kwargs):
            self.element = _Node('search')
            self.__class__.instances.append(self)

    class FakeSelect:
        instances: list['FakeSelect'] = []

        def __init__(self, *_args, **_kwargs):
            self.element = _Node('select')
            self.__class__.instances.append(self)

    class FakeButton:
        instances: list['FakeButton'] = []

        def __init__(self, label, *, on_click=None, **_kwargs):
            self.label = label
            self.visible_text = label
            self.aria_label = label
            self.element = object()
            self.on_click = on_click
            self.__class__.instances.append(self)

        def set_label(self, label):
            self.label = label
            self.visible_text = label
            self.aria_label = label
            return self

    monkeypatch.setattr(components, 'SearchInput', FakeSearchInput)
    monkeypatch.setattr(components, 'Select', FakeSelect)
    monkeypatch.setattr(components, 'Button', FakeButton)

    explorer_gallery.render_reference_gallery((), section='components', intro='Components')

    details = next(node for node in fake_ui.nodes if node.tag == 'details')
    details.open = True
    refinement = FakeButton.instances[0]
    mounted_element = refinement.element
    search = FakeSearchInput.instances[0]
    family = FakeSelect.instances[0]
    store = ExplorerStateStore(storage)

    assert refinement.visible_text == refinement.aria_label == 'Favorites only'
    refinement.on_click()
    assert refinement.visible_text == refinement.aria_label == 'All references'
    assert store.load('components').favorites_only is True
    assert refinement.element is mounted_element
    assert details.open is True

    refinement.on_click()
    assert refinement.visible_text == refinement.aria_label == 'Favorites only'
    assert store.load('components').favorites_only is False
    assert refinement.element is mounted_element
    assert details.open is True
    assert len(FakeButton.instances) == 1
    assert FakeSearchInput.instances == [search]
    assert FakeSelect.instances == [family]
    host = next(node for node in fake_ui.nodes if node.tag == 'div' and node.clear_calls)
    assert host.clear_calls == 3


def test_persisted_favorites_only_filters_the_governed_gallery_and_card_actions_round_trip(monkeypatch):
    from nicegui_base.workbench import explorer_gallery
    from nicegui_base.workbench.explorer_gallery import filtered_entries
    from nicegui_base.workbench.explorer_state import ExplorerState, ExplorerStateStore
    components = importlib.import_module('nicegui_base.integrations.nicegui_components')

    storage: dict[str, object] = {}
    fake_ui = _UI()
    monkeypatch.setitem(
        sys.modules,
        'nicegui',
        SimpleNamespace(ui=fake_ui, app=SimpleNamespace(storage=SimpleNamespace(user=storage))),
    )

    class FakeButton:
        instances: list['FakeButton'] = []

        def __init__(self, label, *, on_click=None, **_kwargs):
            self.label = label
            self.on_click = on_click
            self.__class__.instances.append(self)

    monkeypatch.setattr(components, 'Button', FakeButton)
    monkeypatch.setattr(explorer_gallery, '_preview_image', lambda *_args, **_kwargs: None)

    entries = (
        SimpleNamespace(key='component:one', category='actions'),
        SimpleNamespace(key='component:two', category='actions'),
    )
    store = ExplorerStateStore(storage)
    store.save('components', ExplorerState(favorites_only=True, favorites=('component:one',)))
    assert tuple(entry.key for entry in filtered_entries(entries, store.load('components'))) == ('component:one',)

    entry = SimpleNamespace(
        key='component:one', category='actions', kind=SimpleNamespace(value='component'),
        title='One', description='One reference', live_preview=False, route='/components/one',
        reference_contract=SimpleNamespace(best_for=(), requires=(), avoid_for=()),
    )
    store.save('components', ExplorerState())
    explorer_gallery._gallery_card(entry, section='components', state=store.load('components'), rerender=lambda: None)
    favorite = FakeButton.instances[1]
    assert favorite.label == f'{chr(9734)} Favorite'
    favorite.on_click()
    assert store.load('components').favorites == ('component:one',)

    FakeButton.instances.clear()
    explorer_gallery._gallery_card(entry, section='components', state=store.load('components'), rerender=lambda: None)
    favorite = FakeButton.instances[1]
    assert favorite.label == f'{chr(9733)} Saved'
    favorite.on_click()
    assert store.load('components').favorites == ()
