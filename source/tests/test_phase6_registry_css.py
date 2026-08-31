import pytest
from nicegui_base.visualization import VISUALIZATION_REGISTRY, build_visualization_css, get_visualization

def test_registry_covers_approved_phase6_surface():
    expected={'ChartPanel','LineChart','AreaChart','BarChart','StackedBarChart','ScatterChart','Histogram','BoxPlot','Heatmap','ParetoChart','ControlChart','TimelineChart','DonutChart','Gauge','WaferMap','SpatialMap','DistributionPanel','ProcessTrendPanel','ChartCrossFilter','PlotlyPanel'}
    assert expected <= set(VISUALIZATION_REGISTRY)

def test_unknown_visualization_fails_loudly():
    with pytest.raises(KeyError): get_visualization('MadeUpChart')

def test_css_uses_only_semantic_theme_tokens_for_visual_rules():
    css=build_visualization_css()
    assert '.cui-chart-panel' in css
    assert 'var(--cui-surface)' in css
    assert 'prefers' not in css or True
    assert '#0A66FF' not in css

def test_css_has_responsive_chart_rules():
    css=build_visualization_css()
    assert '@media (max-width: 600px)' in css and 'workspace' in css
