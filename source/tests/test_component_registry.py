import pytest
from nicegui_base import COMPONENT_REGISTRY, get_component


def test_registry_has_phase3_core_coverage():
    required = {
        'button','action_button','icon_button','surface','badge','text_input','number_input','textarea',
        'search_input','select','multi_select','autocomplete','combobox','checkbox','checkbox_group',
        'radio_group','switch','slider','range_slider','date_picker','date_range_picker','time_picker',
        'datetime_picker','file_upload',
    }
    assert required.issubset(COMPONENT_REGISTRY)


def test_registry_definitions_include_ai_friendly_metadata():
    for definition in COMPONENT_REGISTRY.values():
        assert definition.key
        assert definition.category
        assert definition.public_name
        assert definition.purpose
        assert definition.preferred_for


def test_registry_unknown_component_fails_loudly():
    with pytest.raises(KeyError, match='Unknown component'):
        get_component('made_up_widget')
