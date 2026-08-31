import pytest

from nicegui_base import (
    ActiveFilter, FilterBarSpec, FilterDefinition, FilterKind, FilterPersistence, FilterPreset, SavedFilterViewSpec,
)


def test_filter_definition_requires_identity():
    with pytest.raises(ValueError):
        FilterDefinition('', 'Area', FilterKind.SELECT)


def test_filter_bar_counts_active_filters():
    active = (ActiveFilter('area', 'Area', 'ETCH', 'ETCH'), ActiveFilter('status', 'Status', 'Critical', 'critical'))
    spec = FilterBarSpec(active=active)
    assert spec.active_count == 2


def test_filter_bar_detects_advanced_filters():
    spec = FilterBarSpec(filters=(FilterDefinition('recipe', 'Recipe', FilterKind.SELECT, advanced=True),))
    assert spec.has_advanced is True


def test_filter_bar_compact_threshold_validates():
    with pytest.raises(ValueError):
        FilterBarSpec(compact_after=0)


def test_filter_preset_values_are_immutable_mapping():
    preset = FilterPreset('critical', 'Critical only', {'status': 'critical'})
    with pytest.raises(TypeError):
        preset.values['status'] = 'normal'


def test_saved_filter_view_identifies_default():
    view = SavedFilterViewSpec('mine', 'My Tools', {'owner': 'me'}, is_default=True)
    assert view.is_default is True


def test_filter_persistence_has_url_mode():
    assert FilterPersistence.URL.value == 'url'
