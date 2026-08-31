from pathlib import Path

def test_adapter_uses_aggrid_and_semantic_classes():
    src=Path('nicegui_base/integrations/nicegui_data_table.py').read_text()
    assert 'ui.aggrid(options, auto_size_columns=False)' in src
    assert 'cui-table-shell' in src
    assert 'run_grid_method' in src

def test_shell_installs_table_css():
    src=Path('nicegui_base/integrations/nicegui_layout.py').read_text()
    assert 'install_framework_css' in src

def test_theme_adapter_installs_table_css():
    src=Path('nicegui_base/integrations/nicegui_theme.py').read_text()
    assert 'install_framework_css' in src
