from pathlib import Path


def test_adapter_is_lazy_and_semantic():
    source = (Path(__file__).parents[1] / 'nicegui_base/integrations/nicegui_components.py').read_text()
    assert "from nicegui import ui" in source
    assert 'cui-button' not in source or '.classes(self.spec.classes)' in source
    assert 'ButtonIntent' in source
    assert 'SelectOption' in source


def test_app_shell_installs_component_css():
    source = (Path(__file__).parents[1] / 'nicegui_base/integrations/nicegui_layout.py').read_text()
    assert 'install_framework_css' in source
