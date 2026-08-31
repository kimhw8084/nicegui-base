from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class VisualizationDefinition:
    name: str
    category: str
    purpose: str

_NAMES = {
'ChartPanel':('container','Standard themed analytical visualization surface'),
'LineChart':('chart','Trend over ordered/time axis'),'AreaChart':('chart','Trend with magnitude emphasis'),
'BarChart':('chart','Categorical comparison'),'StackedBarChart':('chart','Composition across categories'),
'ScatterChart':('chart','Relationship/correlation'),'Histogram':('chart','Distribution frequency'),
'BoxPlot':('chart','Distribution summary'),'Heatmap':('chart','Matrix/intensity distribution'),
'ParetoChart':('engineering','Ranked contributors with cumulative percentage'),'ControlChart':('engineering','Process trend with control/spec context'),
'TimelineChart':('chart','Events or values over time'),'DonutChart':('chart','Small-part composition only'),
'Gauge':('chart','Single bounded measure'),'WaferMap':('engineering','Wafer spatial data'),
'SpatialMap':('engineering','2D spatial engineering data'),'WaferComparisonMap':('engineering','Affected/control wafer comparison on a shared measurement scale'),'ChamberFingerprintMatrix':('engineering','Normalized chamber/process fingerprint matrix'),'CommonalityMatrix':('engineering','RCA factor commonality across populations'),'RadialProfilePlot':('engineering','Center-to-edge wafer radial signature comparison'),'DistributionPanel':('composite','Distribution chart plus statistical context'),
'ProcessTrendPanel':('composite','Process trend plus limit/annotation context'),
'ChartCrossFilter':('interaction','Semantic chart-to-filter linking'),
'PlotlyPanel':('escape_hatch','Specialist Plotly figure within NiceGUI Base panel anatomy'),
}
VISUALIZATION_REGISTRY={k:VisualizationDefinition(k,*v) for k,v in _NAMES.items()}

def get_visualization(name: str) -> VisualizationDefinition:
    try: return VISUALIZATION_REGISTRY[name]
    except KeyError as exc: raise KeyError(f'Unknown visualization: {name}') from exc

__all__=['VISUALIZATION_REGISTRY','VisualizationDefinition','get_visualization']
