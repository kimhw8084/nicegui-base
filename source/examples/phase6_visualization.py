"""Phase 6 semantic visualization example.

This file intentionally shows the API Gemma/OpenCode should compose. It does not
contain ECharts styling, colors, grid geometry, or raw NiceGUI option dictionaries.
"""
from nicegui_base import (
    AxisSpec, AxisType, ChartEvent, CrossFilterBinding, CrossFilterEngine, LinkedAnalysisController,
    LineChart, SeriesSpec, SpecLimits,
)

trend = SeriesSpec('pressure', 'Pressure', [1.02, 1.01, 1.03, 1.08, 1.04])
limits = SpecLimits(lower=.95, upper=1.10, target=1.02)

# In a NiceGUI runtime:
# chart = LineChart(
#     'Chamber pressure',
#     [trend],
#     x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('08:00','08:05','08:10','08:15','08:20')),
#     y_axis=AxisSpec(label='Pressure', unit='Torr'),
#     spec_limits=limits,
# )

engine = CrossFilterEngine([CrossFilterBinding('excursion_pareto', 'click', 'tool')])
linked = LinkedAnalysisController(engine)
linked.register_target('tool', lambda mutation: print('filter table and KPIs by', mutation.value))
linked.dispatch(ChartEvent('excursion_pareto', 'click', value='ETCH-021'))
