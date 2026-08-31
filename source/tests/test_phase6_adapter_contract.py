from pathlib import Path
import nicegui_base
from nicegui_base.integrations import nicegui_visualization

def test_public_integration_classes_exist_without_importing_nicegui():
    for name in ['ChartPanel','LineChart','ControlChart','WaferMap','SpatialMap','PlotlyPanel','ChartCrossFilter']:
        assert hasattr(nicegui_visualization,name)

def test_adapter_uses_nicegui_echart_and_point_click_path():
    source=Path(nicegui_visualization.__file__).read_text()
    assert 'ui.echart' in source
    assert 'on_point_click' in source
    assert "chart:brushSelected" in source

def test_theme_adapter_installs_visualization_css():
    import nicegui_base.integrations.nicegui_theme as t
    source=Path(t.__file__).read_text()
    assert 'install_framework_css' in source

def test_root_public_api_exposes_phase6_semantics():
    for name in ['ChartKind','ChartPanelSpec','SeriesSpec','SpecLimits','CrossFilterEngine','LinkedAnalysisController','LineChart','ParetoChart','WaferMap','PlotlyPanel']:
        assert hasattr(nicegui_base,name), name
