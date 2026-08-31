from nicegui_base.design import ThemeMode
from nicegui_base.integrations.nicegui_theme import NiceGUIThemeAdapter


def test_adapter_does_not_import_nicegui_on_module_import():
    adapter = NiceGUIThemeAdapter()
    assert adapter.default_mode is ThemeMode.SYSTEM


def test_theme_dom_sync_is_semantic():
    assert NiceGUIThemeAdapter.set_dom_theme_js(ThemeMode.DARK) == "document.documentElement.dataset.theme='dark'"
