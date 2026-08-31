import importlib
from pathlib import Path

from nicegui_base.version import FRAMEWORK_VERSION


def test_engineering_adapter_imports_without_nicegui_runtime():
    mod=importlib.import_module('nicegui_base.integrations.nicegui_engineering')
    assert hasattr(mod,'EngineeringEntityCard') and hasattr(mod,'RcaEvidencePanel')


def test_adapter_uses_packaged_visual_resources():
    source=Path('nicegui_base/integrations/nicegui_engineering.py').read_text()
    assert 'render_icon_svg' in source and '_ENTITY_ICONS' in source
    assert 'http://' not in source and 'https://' not in source


def test_phase9_package_version_and_nicegui_pin():
    text=Path('pyproject.toml').read_text()
    assert f'version = "{FRAMEWORK_VERSION}"' in text and 'nicegui==3.15.0' in text
