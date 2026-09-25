from __future__ import annotations

import re
import sys
from types import SimpleNamespace

from nicegui_base.design.hardening_css import build_hardening_css


def test_select_listbox_leaves_viewport_sizing_and_scrolling_to_quasar() -> None:
    css = build_hardening_css()
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    listbox_rules = [(selector, body) for selector, body in rules if ".q-menu[role='listbox']" in selector]

    assert listbox_rules
    assert all(not re.search(r'max-height:[^;{}]*!important', body) for _, body in listbox_rules)
    assert all('overflow:hidden!important' not in body for _, body in listbox_rules)
    assert sum(selector.strip() == ".q-menu[role='listbox']" for selector, _ in listbox_rules) == 1
    assert any('overflow-x:hidden!important' in body for _, body in listbox_rules)
    assert any('overflow-y:auto!important' in body for _, body in listbox_rules)
    assert any('z-index:var(--cui-overlay-z)!important' in body for _, body in listbox_rules)
    assert 'Process area' not in css


class _Chain:
    next_id = 100

    def __init__(self) -> None:
        self.id = _Chain.next_id
        _Chain.next_id += 1
        self.props_calls: list[str] = []
        self.class_calls: list[tuple[tuple, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def props(self, value: str):
        self.props_calls.append(value)
        return self

    def classes(self, *args, **kwargs):
        self.class_calls.append((args, kwargs))
        return self


class _FakeUI:
    def __init__(self) -> None:
        self.select_calls: list[tuple[tuple, dict, _Chain]] = []
        self.javascript: list[str] = []

    def column(self):
        return _Chain()

    def element(self, *_args, **_kwargs):
        return _Chain()

    def label(self, *_args, **_kwargs):
        return _Chain()

    def select(self, *args, **kwargs):
        element = _Chain()
        self.select_calls.append((args, kwargs, element))
        return element

    def run_javascript(self, code: str):
        self.javascript.append(code)


def test_select_family_uses_one_shared_renderer_and_preserves_dict_mapping(monkeypatch) -> None:
    from nicegui_base.integrations import nicegui_components

    fake_ui = _FakeUI()
    monkeypatch.setitem(sys.modules, 'nicegui', SimpleNamespace(ui=fake_ui))
    options = {'etch': 'Etch', 'metrology': 'Metrology'}
    cases = (
        (nicegui_components.Select, 'etch', False, False),
        (nicegui_components.MultiSelect, ('etch',), True, False),
        (nicegui_components.Autocomplete, 'etch', False, True),
        (nicegui_components.Combobox, 'etch', False, True),
    )

    for renderer, value, multiple, searchable in cases:
        before = len(fake_ui.select_calls)
        component = renderer('Process area', options, value=value)

        assert len(fake_ui.select_calls) == before + 1
        _args, kwargs, element = fake_ui.select_calls[-1]
        assert kwargs['options'] == options
        assert kwargs['multiple'] is multiple
        assert kwargs['with_input'] is searchable
        assert kwargs['value'] == (list(value) if multiple else value)
        assert any('cui-select' in str(call) for call in element.class_calls)
        assert sum('aria-label="Process area"' in call for call in element.props_calls) == 1

    assert len(fake_ui.javascript) == len(cases)
    assert all('getElement(rootId)' in code for code in fake_ui.javascript)
    assert all('querySelector(' in code and 'q-menu' not in code for code in fake_ui.javascript)
