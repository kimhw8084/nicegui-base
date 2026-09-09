from __future__ import annotations

"""Production-facing examples for Reference Explorer Code tabs.

Every component example uses the stable public ``nicegui_base`` API. The
Reference Explorer harness remains a separate, explicitly secondary artifact.
"""

from typing import Any

_COMPONENT_EXAMPLES: dict[str, str] = {
    "button_group": """from nicegui_base import Button, ButtonGroup, ButtonIntent

with ButtonGroup():
    Button("Run", intent=ButtonIntent.PRIMARY)
    Button("Pause")
    Button("Reset", intent=ButtonIntent.TERTIARY)
""",
    "split_button": """from nicegui_base import SplitButton

SplitButton(
    "Export CSV",
    {"Export JSON": lambda: print("json"), "Export PNG": lambda: print("png")},
    on_click=lambda: print("csv"),
)
""",
    "divider": """from nicegui_base import Divider

Divider()
""",
    "collapsible_panel": """from nicegui_base import CollapsiblePanel, TextInput

with CollapsiblePanel("Advanced settings", open=True):
    TextInput("Owner", value="Engineer")
""",
    "accordion": """from nicegui_base import Accordion, TextInput

with Accordion() as accordion:
    with accordion.item("Sampling", open=True):
        TextInput("Sampling plan", value="Every 10 wafers")
""",
    "chip": """from nicegui_base import Chip, Icons

Chip("Lot A12", selected=True, icon=Icons.LOT)
""",
    "count_badge": """from nicegui_base import CountBadge

CountBadge(24)
""",
    "severity_indicator": """from nicegui_base import SeverityIndicator, StatusIntent

SeverityIndicator("High severity", intent=StatusIntent.DANGER)
""",
    "freshness_indicator": """from nicegui_base import FreshnessIndicator

FreshnessIndicator("Updated 2 min ago", stale=False)
""",
    "data_quality_badge": """from nicegui_base import DataQuality, DataQualityBadge

DataQualityBadge(DataQuality.COMPLETE)
""",
    "button": """from nicegui_base import Button, ButtonIntent, Icons

Button("Run analysis", intent=ButtonIntent.PRIMARY, icon=Icons.PLAY)
""",
    "action_button": """from nicegui_base import ActionButton, Icons

ActionButton("Save changes", icon=Icons.SAVE, success_message="Saved")
""",
    "icon_button": """from nicegui_base import IconButton, Icons

IconButton(Icons.REFRESH, label="Refresh data")
""",
    "surface": """from nicegui_base import Card, Panel, Well

with Panel():
    pass  # compose governed NiceGUI Base content here
with Card():
    pass
with Well():
    pass
""",
    "badge": """from nicegui_base import Icons, StatusBadge, StatusIntent

StatusBadge("Healthy", intent=StatusIntent.SUCCESS, icon=Icons.CHECK)
StatusBadge("Warning", intent=StatusIntent.WARNING, icon=Icons.WARNING)
""",
    "text_input": """from nicegui_base import TextInput

TextInput("Lot ID", value="LOT-2409", clearable=True)
""",
    "number_input": """from nicegui_base import NumberInput

NumberInput("Upper limit", value=42.5, minimum=0, maximum=100, step=0.1, unit="nm")
""",
    "textarea": """from nicegui_base import TextArea

TextArea("Engineering note", value="Investigate chamber drift.", rows=3)
""",
    "search_input": """from nicegui_base import SearchInput

SearchInput("Search lots", value="LOT", debounce_ms=250)
""",
    "select": """from nicegui_base import Select

Select("Process area", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
       value="metrology", searchable=True)
""",
    "multi_select": """from nicegui_base import MultiSelect

MultiSelect("Process areas", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
            value=("etch", "metrology"))
""",
    "autocomplete": """from nicegui_base import Autocomplete

Autocomplete("Tool", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
             value="metrology")
""",
    "combobox": """from nicegui_base import Combobox

Combobox("Tag", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
         value="etch")
""",
    "checkbox": """from nicegui_base import Checkbox

Checkbox("Include rework lots", checked=True, description="Independent boolean choice")
""",
    "checkbox_group": """from nicegui_base import CheckboxGroup, SelectOption

CheckboxGroup(
    "Signals",
    (SelectOption("etch", "Etch"), SelectOption("deposition", "Deposition"),
     SelectOption("metrology", "Metrology")),
    selected=("etch", "metrology"),
)
""",
    "radio_group": """from nicegui_base import RadioGroup, SelectOption

RadioGroup(
    "Mode",
    (SelectOption("etch", "Etch"), SelectOption("deposition", "Deposition"),
     SelectOption("metrology", "Metrology")),
    selected="metrology",
)
""",
    "switch": """from nicegui_base import Switch

Switch("Auto refresh", checked=True, description="Applies immediately")
""",
    "slider": """from nicegui_base import Slider

Slider("Threshold", value=65, minimum=0, maximum=100, step=5, unit="%")
""",
    "range_slider": """from nicegui_base import RangeSlider

RangeSlider("Window", low=20, high=80, minimum=0, maximum=100, step=5, unit="%")
""",
    "date_picker": """from nicegui_base import DatePicker

DatePicker("Effective date", value="2026-09-05")
""",
    "date_range_picker": """from nicegui_base import DateRangePicker

DateRangePicker("Analysis period", start="2026-09-01", end="2026-09-05")
""",
    "time_picker": """from nicegui_base import TimePicker

TimePicker("Cutoff time", value="14:30")
""",
    "datetime_picker": """from nicegui_base import DateTimePicker

DateTimePicker("Scheduled run", value="2026-09-05T14:30")
""",
    "file_upload": """from nicegui_base import FileUpload

FileUpload(label="Upload process data", accept=(".csv", ".json"), max_file_size_mb=10)
""",
}

def production_example_code(entry: Any) -> str:
    metadata = getattr(entry, "metadata", {}) or {}
    component_key = str(metadata.get("component_key") or "")
    if component_key in _COMPONENT_EXAMPLES:
        return _COMPONENT_EXAMPLES[component_key].rstrip() + "\n"
    surface_key = str(metadata.get("surface_key") or "")
    if surface_key:
        return production_analytic_example(surface_key)
    contract = getattr(entry, "reference_contract", None)
    code = str(getattr(contract, "recommended_code", "") or "")
    return code.rstrip() + "\n" if code.strip() else (
        "import nicegui_base\n\n"
        f"# Canonical authority: {getattr(entry, 'source_authority', 'NiceGUI Base')}\n"
    )

def production_analytic_example(surface_key: str) -> str:
    """Return a concrete public-API composition for one governed surface.

    The examples intentionally show the framework renderer and semantic models,
    rather than exposing the Workbench fixture or raw ECharts options.  They are
    short enough to adapt, but contain the actual constructor contract used by
    the live reference.
    """
    common = "from nicegui_base import AxisSpec, AxisType, SeriesSpec\n"
    chart = {
        'spc_i_mr': """from nicegui_base import ControlChart, SpecLimits

values = (40.0, 40.3, 39.7, 40.8, 40.1)
ControlChart(
    "Individuals chart",
    (SeriesSpec("individuals", "Individuals", values),),
    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(str(i + 1) for i in range(len(values))), label="Sample order"),
    y_axis=AxisSpec(label="Measurement", unit="nm"),
    spec_limits=SpecLimits(lower=39.2, upper=40.8, target=40.0),
)
""",
        'spc_xbar_r': """from nicegui_base import ControlChart

subgroup_means = (40.0, 40.2, 40.1, 40.4)
subgroup_ranges = (0.8, 0.6, 0.9, 0.7)
ControlChart("Xbar", (SeriesSpec("xbar", "Subgroup mean", subgroup_means),), y_axis=AxisSpec(label="Mean", unit="nm"))
ControlChart("Range", (SeriesSpec("range", "Within-subgroup range", subgroup_ranges),), y_axis=AxisSpec(label="Range", unit="nm"))
""",
        'spc_xbar_s': """from nicegui_base import ControlChart

means = (40.0, 40.2, 40.1, 40.4)
standard_deviations = (0.22, 0.18, 0.25, 0.20)
ControlChart("Xbar", (SeriesSpec("xbar", "Subgroup mean", means),), y_axis=AxisSpec(label="Mean", unit="nm"))
ControlChart("Standard deviation", (SeriesSpec("s", "Subgroup standard deviation", standard_deviations),), y_axis=AxisSpec(label="Standard deviation", unit="nm"))
""",
        'spc_p': """from nicegui_base import ControlChart

proportions = (0.020, 0.017, 0.027, 0.026)
ControlChart("p chart", (SeriesSpec("p", "Nonconforming proportion", proportions),), y_axis=AxisSpec(label="Proportion"))
""",
        'spc_np': """from nicegui_base import ControlChart

counts = (4, 3, 5, 4)
ControlChart("np chart", (SeriesSpec("np", "Nonconforming count", counts),), y_axis=AxisSpec(label="Count"))
""",
        'spc_c': """from nicegui_base import ControlChart

defects = (2, 4, 3, 5)
ControlChart("c chart", (SeriesSpec("c", "Defect count", defects),), y_axis=AxisSpec(label="Defects"))
""",
        'spc_u': """from nicegui_base import ControlChart

defects_per_unit = (0.18, 0.20, 0.16, 0.25)
ControlChart("u chart", (SeriesSpec("u", "Defects per unit", defects_per_unit),), y_axis=AxisSpec(label="Defects / unit"))
""",
        'spc_ewma': """from nicegui_base import ControlChart

ewma = (39.9, 40.0, 40.1, 40.3, 40.4)
ControlChart("EWMA", (SeriesSpec("ewma", "EWMA statistic", ewma),), y_axis=AxisSpec(label="EWMA", unit="nm"))
""",
        'spc_cusum': """from nicegui_base import ControlChart

cusum = (-0.2, -0.1, 0.3, 0.8, 1.2)
ControlChart("CUSUM", (SeriesSpec("cusum", "Cumulative deviation", cusum),), y_axis=AxisSpec(label="CUSUM statistic"))
""",
        'capability_histogram': """from nicegui_base import Histogram, SpecLimits

measurements = (39.4, 39.8, 40.0, 40.1, 40.5)
Histogram(
    "Capability distribution",
    (SeriesSpec("count", "Count", (1, 1, 1, 1, 1)),),
    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("39.4", "39.8", "40.0", "40.1", "40.5"), label="Measurement", unit="nm"),
    y_axis=AxisSpec(label="Count"),
    spec_limits=SpecLimits(lower=38.5, upper=41.5, target=40.0),
)
""",
        'qq_probability': """from nicegui_base import ScatterChart

points = ((-1.2, 39.2), (0.0, 40.0), (1.2, 40.8))
ScatterChart("Normal probability plot", (SeriesSpec("observed", "Observed", points, x_key="x", y_key="y"),), x_axis=AxisSpec(label="Theoretical quantile"), y_axis=AxisSpec(label="Observed measurement", unit="nm"))
""",
        'ecdf': """from nicegui_base import LineChart

points = ((39.2, 0.2), (40.0, 0.6), (40.8, 1.0))
LineChart("Empirical cumulative distribution", (SeriesSpec("ecdf", "ECDF", points, x_key="x", y_key="y"),), x_axis=AxisSpec(label="Observed value", unit="nm"), y_axis=AxisSpec(label="Cumulative probability"))
""",
        'box_distribution': """from nicegui_base import BoxPlot

groups = ((39.2, 39.8, 40.0, 40.3, 40.8), (39.7, 40.1, 40.4, 40.7, 41.2))
BoxPlot("Distribution comparison", (SeriesSpec("groups", "Population quartiles", groups),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("Control", "Affected"), label="Population"), y_axis=AxisSpec(label="Measurement", unit="nm"))
""",
        'violin_distribution': """from nicegui_base import LineChart

density = ({"value": 39.2, "density": 0.1}, {"value": 40.0, "density": 0.8}, {"value": 40.8, "density": 0.2})
LineChart("Violin distribution", (SeriesSpec("density", "Control density", density, x_key="value", y_key="density", smooth=True),), x_axis=AxisSpec(label="Measurement", unit="nm"), y_axis=AxisSpec(label="Density"))
""",
        'ridge_distribution': """from nicegui_base import LineChart

density = ({"value": 39.2, "density": 0.1}, {"value": 40.0, "density": 0.8}, {"value": 40.8, "density": 0.2})
LineChart("Ridge distribution", (SeriesSpec("density", "Chamber density", density, x_key="value", y_key="density", smooth=True),), x_axis=AxisSpec(label="Measurement", unit="nm"), y_axis=AxisSpec(label="Offset density"))
""",
        'yield_pareto': """from nicegui_base import ParetoChart

ParetoChart("Yield-loss Pareto", ("Scratch", "CD", "Particle"), (42, 28, 16), (0.49, 0.82, 1.0))
""",
        'bin_pareto': """from nicegui_base import ParetoChart

ParetoChart("Failing-bin Pareto", ("Bin 12", "Bin 7", "Bin 3"), (42, 28, 16), (0.49, 0.82, 1.0))
""",
        'weibull_reliability': """from nicegui_base import ScatterChart

failures = ((120.0, 0.12), (180.0, 0.27), (260.0, 0.55))
censored = ((300.0, 0.55),)
ScatterChart("Weibull reliability", (SeriesSpec("failures", "Failures", failures, x_key="time", y_key="probability"), SeriesSpec("censored", "Censored", censored, x_key="time", y_key="probability")), x_axis=AxisSpec(label="Exposure time"), y_axis=AxisSpec(label="Cumulative failure probability"))
""",
        'doe_main_effects': """from nicegui_base import LineChart

LineChart("DOE main effects", (SeriesSpec("rf_bias", "RF bias", (39.4, 40.1, 41.3)), SeriesSpec("pressure", "Pressure", (40.9, 40.2, 39.5))), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("Low", "Center", "High"), label="Factor level"), y_axis=AxisSpec(label="Mean response"))
""",
        'doe_interactions': """from nicegui_base import LineChart

LineChart("DOE interactions", (SeriesSpec("pressure_low", "Pressure low", (39.4, 40.1, 41.2)), SeriesSpec("pressure_high", "Pressure high", (41.0, 40.5, 39.7))), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("RF low", "RF center", "RF high"), label="Factor A level"), y_axis=AxisSpec(label="Mean response"))
""",
        'doe_response_surface': """from nicegui_base import Heatmap

response = ((0, 0, 39.4), (1, 0, 40.1), (0, 1, 40.9), (1, 1, 40.5))
Heatmap("DOE response surface", (SeriesSpec("response", "Response", response),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("Low", "High"), label="Factor A"), y_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("Low", "High"), label="Factor B"))
""",
    }
    specialized = {
        'ecdf': """from nicegui_base.integrations.nicegui_visualization import EmpiricalCDFChart

points = ((39.2, 0.2), (40.0, 0.6), (40.8, 1.0))
EmpiricalCDFChart("Empirical cumulative distribution", points)
""",
        'violin_distribution': """from nicegui_base import SeriesSpec
from nicegui_base.integrations.nicegui_visualization import ViolinPlot

ViolinPlot("Violin distribution", (SeriesSpec("control", "Control", (0.2, 0.8, 0.3)),), labels=("Control",))
""",
        'ridge_distribution': """from nicegui_base import SeriesSpec
from nicegui_base.integrations.nicegui_visualization import RidgePlot

RidgePlot("Ridge distribution", (SeriesSpec("chamber", "Chamber", (0.2, 0.8, 0.3)),), labels=("Low", "Center", "High"))
""",
        'wafer_contour': """from nicegui_base.integrations.nicegui_visualization import WaferContourPlot

WaferContourPlot("Wafer contour", (39.2, 39.8, 40.0, 40.8, 41.2))
""",
        'wafer_comparison': """from nicegui_base import WaferPoint
from nicegui_base.integrations.nicegui_visualization import WaferComparisonMap

affected = (WaferPoint(0, 0, 40.2), WaferPoint(1, 0, 40.4))
control = (WaferPoint(0, 0, 40.0), WaferPoint(1, 0, 40.1))
WaferComparisonMap("Affected vs control wafer", affected, control)
""",
        'wafer_radial': """from nicegui_base import RadialProfilePlot

RadialProfilePlot("Wafer radial profile", (40.0, 40.2, 40.4), (39.9, 40.0, 40.1), unit="nm")
""",
        'fdc_chamber_fingerprint': """from nicegui_base.integrations.nicegui_visualization import ChamberFingerprintMatrix

ChamberFingerprintMatrix("Chamber fingerprint", ("ETCH-03/A", "ETCH-07/B"), ("Slope", "Noise"), ((0.2, -0.1), (0.7, 0.4)))
""",
        'fdc_sensor_fingerprint': """from nicegui_base.integrations.nicegui_visualization import ChamberFingerprintMatrix

ChamberFingerprintMatrix("Sensor fingerprint", ("Pressure", "RF bias"), ("Slope", "Noise"), ((0.2, -0.1), (0.7, 0.4)))
""",
        'rca_commonality_matrix': """from nicegui_base.integrations.nicegui_visualization import CommonalityMatrix

CommonalityMatrix("Commonality matrix", ("CH-3", "Recipe R18"), ("Affected", "Control"), ((0.94, 0.18), (0.88, 0.31)))
""",
        'rca_evidence_matrix': """from nicegui_base.integrations.nicegui_visualization import CommonalityMatrix

CommonalityMatrix("Evidence matrix", ("CH-3 drift", "Recipe mismatch"), ("Supports", "Contradicts"), ((0.90, 0.0), (0.0, 0.61)))
""",
        'rca_sankey': """from nicegui_base.integrations.nicegui_visualization import SankeyDiagram

SankeyDiagram("Process flow", ("Lot", "Wafer", "Chamber", "Review"), (("Lot", "Wafer", 48), ("Wafer", "Chamber", 48), ("Chamber", "Review", 48)))
""",
        'rca_genealogy_graph': """from nicegui_base.integrations.nicegui_visualization import RelationshipGraph

nodes = (("lot", "LOT-2471", 0, 0), ("wafer", "W08", 1, 0), ("tool", "ETCH-021", 2, 0))
RelationshipGraph("Lot genealogy", nodes, (("lot", "wafer"), ("wafer", "tool")))
""",
        'rca_cause_tree': """from nicegui_base.integrations.nicegui_visualization import FaultTreeDiagram

FaultTreeDiagram("Cause tree", {"name": "CD excursion", "children": ({"name": "Equipment"}, {"name": "Process"})}, renderer_type="cause_tree")
""",
        'rca_fault_tree': """from nicegui_base.integrations.nicegui_visualization import FaultTreeDiagram

FaultTreeDiagram("Fault tree", {"name": "OOS event", "children": ({"name": "OR", "gate": "OR", "children": ({"name": "Pressure"}, {"name": "RF"})},)})
""",
        'rca_contribution_waterfall': """from nicegui_base.integrations.nicegui_visualization import WaterfallDiagram

WaterfallDiagram("Contribution waterfall", ("CH-3", "Recipe", "PM age"), (2.2, -0.4, 1.1))
""",
        'yield_waterfall': """from nicegui_base.integrations.nicegui_visualization import WaterfallDiagram

WaterfallDiagram("Yield waterfall", ("Scratch", "CD", "Recovery"), (-0.04, -0.02, 0.01))
""",
    }
    if surface_key in specialized:
        return specialized[surface_key].rstrip() + "\n"
    if surface_key in chart:
        return common + chart[surface_key].rstrip() + "\n"
    # Spatial and matrix families use the public chart/spatial primitives. The
    # fixture-specific field mapping remains intentionally visible and adaptable.
    if surface_key.startswith('wafer_') or surface_key in {'lot_wafer_strip'}:
        return """from nicegui_base import WaferMap, WaferPoint

points = tuple(WaferPoint(x, y, value, metadata={"wafer": "W08"}) for x, y, value in ((-1, 0, 39.8), (0, 0, 40.0), (1, 0, 40.3)))
WaferMap("Wafer signature", points, legend_title="Measurement", description="Clipped die-level spatial response.")
"""
    if surface_key in {'fdc_chamber_fingerprint', 'fdc_sensor_fingerprint', 'rca_commonality_matrix', 'rca_evidence_matrix', 'rca_correlation_matrix', 'doe_response_surface'}:
        return """from nicegui_base import Heatmap

cells = ((0, 0, 0.82), (1, 0, 0.31), (0, 1, -0.44), (1, 1, 0.61))
Heatmap("Governed matrix", (SeriesSpec("matrix", "Score", cells),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("A", "B"), label="Column"), y_axis=AxisSpec(kind=AxisType.CATEGORY, categories=("A", "B"), label="Row"))
"""
    if surface_key.startswith('fdc_') or surface_key.startswith('rca_'):
        return """from nicegui_base import BarChart, LineChart, SeriesSpec, AxisSpec, AxisType

labels = ("Baseline", "Affected", "Review")
BarChart("Governed engineering analysis", (SeriesSpec("value", "Value", (0.2, 0.8, 0.4)),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=labels, label="Entity"), y_axis=AxisSpec(label="Normalized value"))
"""
    return """from nicegui_base import LineChart, AxisSpec, SeriesSpec

LineChart("Governed analytical surface", (SeriesSpec("value", "Value", (1.0, 1.2, 1.1)),), x_axis=AxisSpec(label="Sample order"), y_axis=AxisSpec(label="Value"))
"""


__all__ = ["production_example_code", "production_analytic_example"]
