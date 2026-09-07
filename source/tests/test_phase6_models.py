import pytest
from nicegui_base.visualization import (
    AxisSpec, AxisType, ChartKind, ChartPanelSpec, ChartSize, LegendPosition, SelectionMode,
    SeriesSpec, SpecLimits, WaferPoint, SpatialPoint,
)

def test_axis_rejects_invalid_bounds():
    with pytest.raises(ValueError): AxisSpec(min_value=5,max_value=5)

def test_spec_limits_reject_invalid_bounds():
    with pytest.raises(ValueError): SpecLimits(lower=3,upper=2)

def test_chart_title_required():
    with pytest.raises(ValueError): ChartPanelSpec('   ')

def test_series_key_and_label_required():
    with pytest.raises(ValueError): SeriesSpec('', 'x', [])
    with pytest.raises(ValueError): SeriesSpec('x', '', [])

def test_chart_classes_are_semantic():
    s=ChartPanelSpec('Trend',size=ChartSize.LARGE)
    assert s.classes=='cui-chart-panel cui-chart-panel--large cui-chart-panel--line'

def test_chart_enums_are_stable():
    assert ChartKind.CONTROL.value=='control'
    assert LegendPosition.HIDDEN.value=='hidden'
    assert SelectionMode.BRUSH.value=='brush'
    assert AxisType.TIME.value=='time'

def test_spatial_models_hold_metadata():
    assert WaferPoint(1,2,status='fail').status=='fail'
    assert SpatialPoint(1,2,label='A').label=='A'
