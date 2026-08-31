from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from nicegui_base.data_table import ColumnKind, DataTableSpec, SelectionMode, TableColumn, TableDensity
from nicegui_base.visualization import (
    AxisSpec, AxisType, ChartKind, ChartPanelSpec, ChartSize, LegendPosition, SeriesSpec,
    SpecLimits as ChartSpecLimits, ThresholdSpec,
)

from .analytics import compare_populations, evidence_balance, summarize_population
from .models import (
    CommonalityObservation, ConfidenceIndicatorSpec, ControlLimits, EngineeringEntityCardSpec, EvidenceItem,
    LimitBand, MeasurementPoint, PopulationComparison, PopulationRole, RcaHypothesis,
)


@dataclass(frozen=True, slots=True)
class ProcessTrendSpec:
    parameter: str
    points: tuple[MeasurementPoint, ...]
    unit: str | None = None
    spec_limits: LimitBand | None = None
    control_limits: ControlLimits | None = None
    title: str | None = None
    description: str | None = None

    def chart(self) -> tuple[ChartPanelSpec, tuple[SeriesSpec, ...], tuple[ThresholdSpec, ...], ChartSpecLimits | None]:
        title = self.title or self.parameter
        series = (SeriesSpec(
            key=self.parameter,
            label=self.parameter,
            data=tuple(p.value for p in self.points),
            kind=ChartKind.CONTROL,
            smooth=False,
        ),)
        spec = ChartPanelSpec(
            title=title,
            description=self.description,
            kind=ChartKind.CONTROL,
            size=ChartSize.STANDARD,
            x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(str(p.x) for p in self.points)),
            y_axis=AxisSpec(kind=AxisType.VALUE, unit=self.unit),
            legend=LegendPosition.HIDDEN,
        )
        thresholds: list[ThresholdSpec] = []
        if self.control_limits:
            if self.control_limits.lower_control is not None:
                thresholds.append(ThresholdSpec(self.control_limits.lower_control, 'LCL'))
            if self.control_limits.upper_control is not None:
                thresholds.append(ThresholdSpec(self.control_limits.upper_control, 'UCL'))
            if self.control_limits.centerline is not None:
                thresholds.append(ThresholdSpec(self.control_limits.centerline, 'Center'))
        chart_limits = None
        if self.spec_limits:
            chart_limits = ChartSpecLimits(
                lower=self.spec_limits.lower_spec,
                upper=self.spec_limits.upper_spec,
                target=self.spec_limits.target,
            )
        return spec, series, tuple(thresholds), chart_limits


@dataclass(frozen=True, slots=True)
class DistributionComparisonSpec:
    affected_values: tuple[float, ...]
    control_values: tuple[float, ...]
    parameter: str
    unit: str | None = None
    affected_label: str = 'Affected'
    control_label: str = 'Control'
    spec_limits: LimitBand | None = None

    def population_comparison(self) -> PopulationComparison:
        affected = summarize_population(self.affected_label, PopulationRole.AFFECTED, self.affected_values, unit=self.unit)
        control = summarize_population(self.control_label, PopulationRole.CONTROL, self.control_values, unit=self.unit)
        return compare_populations(affected, control)

    def histogram(self, bins: int = 12) -> tuple[tuple[str, ...], tuple[SeriesSpec, ...]]:
        if bins < 1:
            raise ValueError('bins must be >= 1')
        all_values = list(self.affected_values) + list(self.control_values)
        if not all_values:
            return (), ()
        lo, hi = min(all_values), max(all_values)
        if lo == hi:
            label = f'{lo:g}'
            return (label,), (
                SeriesSpec('affected', self.affected_label, (len(self.affected_values),), kind=ChartKind.BAR),
                SeriesSpec('control', self.control_label, (len(self.control_values),), kind=ChartKind.BAR),
            )
        width = (hi - lo) / bins
        labels = tuple(f'{lo+i*width:.3g}–{lo+(i+1)*width:.3g}' for i in range(bins))
        def counts(values: tuple[float, ...]) -> tuple[int, ...]:
            result=[0]*bins
            for value in values:
                idx=min(int((value-lo)/width),bins-1)
                result[idx]+=1
            return tuple(result)
        return labels, (
            SeriesSpec('affected', self.affected_label, counts(self.affected_values), kind=ChartKind.BAR),
            SeriesSpec('control', self.control_label, counts(self.control_values), kind=ChartKind.BAR),
        )


@dataclass(frozen=True, slots=True)
class CommonalityTableSpec:
    observations: tuple[CommonalityObservation, ...]
    title: str = 'Commonality Analysis'
    density: TableDensity = TableDensity.COMPACT

    def table_spec(self) -> DataTableSpec:
        columns = (
            TableColumn('label','Commonality',ColumnKind.TEXT,min_width=180),
            TableColumn('kind','Type',ColumnKind.TEXT,min_width=110),
            TableColumn('affected_rate','Affected',ColumnKind.PERCENT,decimals=1,min_width=100),
            TableColumn('control_rate','Control',ColumnKind.PERCENT,decimals=1,min_width=100),
            TableColumn('rate_difference','Δ Rate',ColumnKind.PERCENT,decimals=1,min_width=90),
            TableColumn('risk_ratio','Risk Ratio',ColumnKind.FLOAT,decimals=2,min_width=100),
            TableColumn('interpretation','Interpretation',ColumnKind.STATUS,min_width=125),
        )
        return DataTableSpec(columns=columns,row_key='key',title=self.title,density=self.density,selection=SelectionMode.SINGLE)

    def rows(self) -> tuple[Mapping[str, Any], ...]:
        return tuple({
            'key': o.key, 'label': o.label, 'kind': o.kind.value,
            'affected_rate': None if o.affected_rate is None else o.affected_rate * 100, 'control_rate': None if o.control_rate is None else o.control_rate * 100,
            'rate_difference': None if o.rate_difference is None else o.rate_difference * 100, 'risk_ratio': o.risk_ratio,
            'interpretation': o.interpretation.value,
        } for o in self.observations)


@dataclass(frozen=True, slots=True)
class EvidenceCardSpec:
    evidence: EvidenceItem
    show_source: bool = True
    show_confidence: bool = True


@dataclass(frozen=True, slots=True)
class RcaEvidencePanelSpec:
    hypothesis: RcaHypothesis
    title: str = 'Root Cause Evidence'
    show_contradictions: bool = True
    group_by_channel: bool = True

    @property
    def balance(self):
        return evidence_balance(self.hypothesis.evidence)


@dataclass(frozen=True, slots=True)
class RcaWorkspaceSpec:
    hypotheses: tuple[RcaHypothesis, ...]
    selected_key: str | None = None
    candidate_limit: int = 10

    def __post_init__(self) -> None:
        if self.candidate_limit < 1:
            raise ValueError('candidate_limit must be >= 1')
        if self.selected_key is not None and self.selected_key not in {h.key for h in self.hypotheses}:
            raise ValueError('selected_key must match a hypothesis key')


@dataclass(frozen=True, slots=True)
class EngineeringSummarySpec:
    entity_card: EngineeringEntityCardSpec
    baseline: Any | None = None
    confidence: ConfidenceIndicatorSpec | None = None
    notes: tuple[str, ...] = ()


__all__ = [
    'CommonalityTableSpec','DistributionComparisonSpec','EngineeringSummarySpec','EvidenceCardSpec','ProcessTrendSpec',
    'RcaEvidencePanelSpec','RcaWorkspaceSpec',
]
