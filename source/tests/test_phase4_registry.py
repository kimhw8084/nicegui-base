import pytest
from nicegui_base import INTERACTION_REGISTRY, get_interaction


def test_interaction_registry_covers_phase4_families():
    for key in ('form','filter_bar','filter_drawer','detail_drawer','form_drawer','dialog','danger_dialog','popover','menu','toast','alert','banner','state_view','async_content'):
        assert key in INTERACTION_REGISTRY


def test_interaction_registry_is_lookup_safe():
    assert get_interaction('detail_drawer').public_name == 'DetailDrawer'
    with pytest.raises(KeyError):
        get_interaction('invented_surface')
