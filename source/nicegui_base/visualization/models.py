from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ChartKind(str, Enum):
    LINE = 'line'
    AREA = 'area'
    BAR = 'bar'
    STACKED_BAR = 'stacked_bar'
    SCATTER = 'scatter'
    HISTOGRAM = 'histogram'
    BOX_PLOT = 'box_plot'
    HEATMAP = 'heatmap'
    PARETO = 'pareto'
    CONTROL = 'control'
    TIMELINE = 'timeline'
    DONUT = 'donut'
    GAUGE = 'gauge'
    WAFER = 'wafer'
    SPATIAL = 'spatial'


class ChartSize(str, Enum):
    COMPACT = 'compact'
    STANDARD = 'standard'
    LARGE = 'large'
    WORKSPACE = 'workspace'


class LegendPosition(str, Enum):
    TOP = 'top'
    BOTTOM = 'bottom'
    LEFT = 'left'
    RIGHT = 'right'
    HIDDEN = 'hidden'


class AxisType(str, Enum):
    CATEGORY = 'category'
    VALUE = 'value'
    TIME = 'time'
    LOG = 'log'


class SelectionMode(str, Enum):
    NONE = 'none'
    SINGLE = 'single'
    MULTIPLE = 'multiple'
    BRUSH = 'brush'


class MarkerShape(str, Enum):
    CIRCLE = 'circle'
    RECT = 'rect'
    TRIANGLE = 'triangle'
    DIAMOND = 'diamond'
    NONE = 'none'


class LineStyle(str, Enum):
    SOLID = 'solid'
    DASHED = 'dashed'
    DOTTED = 'dotted'


class AnnotationIntent(str, Enum):
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    DANGER = 'danger'
    NEUTRAL = 'neutral'


@dataclass(frozen=True, slots=True)
class AxisSpec:
    label: str | None = None
    kind: AxisType = AxisType.VALUE
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    show_grid: bool = True
    inverse: bool = False
    categories: Sequence[Any] = ()

    def __post_init__(self) -> None:
        if self.min_value is not None and self.max_value is not None and self.min_value >= self.max_value:
            raise ValueError('axis min_value must be less than max_value')


@dataclass(frozen=True, slots=True)
class SeriesSpec:
    key: str
    label: str
    data: Sequence[Any]
    kind: ChartKind = ChartKind.LINE
    x_key: str | None = None
    y_key: str | None = None
    stack: str | None = None
    smooth: bool = False
    marker: MarkerShape = MarkerShape.CIRCLE
    line_style: LineStyle = LineStyle.SOLID
    semantic_color: str | None = None
    visible: bool = True
    y_axis_index: int = 0

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('series key is required')
        if not self.label.strip():
            raise ValueError('series label is required')
        if self.y_axis_index < 0:
            raise ValueError('y_axis_index must be >= 0')
        if (self.x_key is None) != (self.y_key is None):
            raise ValueError('x_key and y_key must be provided together')
        if self.x_key is not None:
            for index, item in enumerate(self.data):
                if not isinstance(item, Mapping):
                    raise TypeError(f'series data[{index}] must be a mapping when x_key/y_key are used')
                if self.x_key not in item or self.y_key not in item:
                    raise KeyError(f'series data[{index}] is missing {self.x_key!r} or {self.y_key!r}')


@dataclass(frozen=True, slots=True)
class ThresholdSpec:
    value: float
    label: str
    intent: AnnotationIntent = AnnotationIntent.WARNING
    line_style: LineStyle = LineStyle.DASHED


@dataclass(frozen=True, slots=True)
class SpecLimits:
    lower: float | None = None
    upper: float | None = None
    target: float | None = None
    lower_label: str = 'LSL'
    upper_label: str = 'USL'
    target_label: str = 'Target'

    def __post_init__(self) -> None:
        if self.lower is not None and self.upper is not None and self.lower >= self.upper:
            raise ValueError('lower spec limit must be less than upper spec limit')


@dataclass(frozen=True, slots=True)
class ChartAnnotation:
    x: Any
    label: str
    y: float | None = None
    intent: AnnotationIntent = AnnotationIntent.INFO
    icon: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError('annotation label is required')


@dataclass(frozen=True, slots=True)
class ChartToolbarSpec:
    zoom: bool = True
    reset: bool = True
    fullscreen: bool = True
    export_image: bool = True
    export_data: bool = True
    data_view: bool = True


@dataclass(frozen=True, slots=True)
class ChartPanelSpec:
    title: str
    description: str | None = None
    kind: ChartKind = ChartKind.LINE
    size: ChartSize = ChartSize.STANDARD
    x_axis: AxisSpec = field(default_factory=lambda: AxisSpec(kind=AxisType.CATEGORY))
    y_axis: AxisSpec = field(default_factory=AxisSpec)
    legend: LegendPosition = LegendPosition.TOP
    selection: SelectionMode = SelectionMode.NONE
    toolbar: ChartToolbarSpec = field(default_factory=ChartToolbarSpec)
    empty_message: str = 'No data available'
    error_message: str = 'Unable to load visualization'
    animate: bool = True
    responsive: bool = True

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('chart title is required')

    @property
    def classes(self) -> str:
        return f'cui-chart-panel cui-chart-panel--{self.size.value} cui-chart-panel--{self.kind.value}'


@dataclass(frozen=True, slots=True)
class ChartEvent:
    source_id: str
    event_type: str
    key: str | None = None
    value: Any = None
    payload: Mapping[str, Any] = field(default_factory=dict)


class FilterMutationAction(str, Enum):
    SET = 'set'
    REMOVE = 'remove'


@dataclass(frozen=True, slots=True)
class FilterMutation:
    key: str
    value: Any
    operator: str = 'eq'
    source_id: str | None = None
    action: FilterMutationAction = FilterMutationAction.SET


@dataclass(frozen=True, slots=True)
class CrossFilterBinding:
    source_id: str
    event_type: str
    target_key: str
    operator: str = 'eq'


@dataclass(frozen=True, slots=True)
class WaferPoint:
    x: float
    y: float
    value: float | int | None = None
    die_x: int | None = None
    die_y: int | None = None
    status: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        import math
        for name, value in (('x', self.x), ('y', self.y)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f'{name} must be a finite number')
        if self.value is not None and (isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value))):
            raise ValueError('value must be a finite number or None')


@dataclass(frozen=True, slots=True)
class SpatialPoint:
    x: float
    y: float
    value: float | int | None = None
    label: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        import math
        for name, value in (('x', self.x), ('y', self.y)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f'{name} must be a finite number')
        if self.value is not None and (isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(float(self.value))):
            raise ValueError('value must be a finite number or None')


__all__ = [
    'AnnotationIntent','AxisSpec','AxisType','ChartAnnotation','ChartEvent','ChartKind','ChartPanelSpec','ChartSize',
    'ChartToolbarSpec','CrossFilterBinding','FilterMutation','FilterMutationAction','LegendPosition','LineStyle','MarkerShape','SelectionMode',
    'SeriesSpec','SpatialPoint','SpecLimits','ThresholdSpec','WaferPoint',
]
