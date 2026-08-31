from pathlib import Path

import nicegui_base
from nicegui_base.version import FRAMEWORK_VERSION
from nicegui_base.integrations import NiceGUIStateServices

ROOT = Path(__file__).parents[1]


def test_public_api_contains_phase8_surface():
    for name in ['StateStore','UserPreferences','UrlState','AsyncAction','AutoRefreshController','PreferenceService','KeyboardShortcutRegistry','NiceGUIStateServices']:
        assert hasattr(nicegui_base, name), name


def test_nicegui_state_adapter_uses_current_storage_contract():
    text=(ROOT/'nicegui_base/integrations/nicegui_state.py').read_text()
    assert 'app.storage.user' in text
    assert 'app.storage.tab' in text
    assert 'app.storage.client' in text
    assert 'app.storage.browser' in text  # documented explicitly as intentionally avoided


def test_package_version_phase8():
    text=(ROOT/'pyproject.toml').read_text(); assert f'version = "{FRAMEWORK_VERSION}"' in text and 'nicegui==3.15.0' in text


def test_nicegui_keyboard_adapter_uses_typed_event_contract():
    text=(ROOT/'nicegui_base/integrations/nicegui_state.py').read_text()
    assert 'event.modifiers.ctrl' in text and 'event.key.name' in text
    assert 'ui.keyboard' in text and 'repeating=False' in text
