import pytest
from nicegui_base.convenience_registry import CONVENIENCE_REGISTRY, get_convenience


def test_convenience_registry_covers_phase8_families():
    assert {'state_store','user_preferences','url_state','async_action','cancelable_task','auto_refresh','debouncer','stale_response_guard','notification_service','preference_service','keyboard_shortcuts','error_service'} <= set(CONVENIENCE_REGISTRY)


def test_convenience_registry_unknown_fails_loudly():
    with pytest.raises(KeyError): get_convenience('magic')
