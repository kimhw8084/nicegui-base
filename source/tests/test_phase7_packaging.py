from pathlib import Path

def test_pyproject_declares_visual_package_data():
    text=Path('pyproject.toml').read_text()
    assert '[tool.setuptools.package-data]' in text
    assert 'icons/**/*.svg' in text and 'manifest/*.json' in text

def test_theme_adapter_installs_visual_css():
    text=Path('nicegui_base/integrations/nicegui_theme.py').read_text()
    assert 'build_visual_asset_css' in text
