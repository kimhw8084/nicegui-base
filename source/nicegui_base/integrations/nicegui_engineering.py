from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from nicegui_base.engineering import (
    BaselineComparison as BaselineComparisonModel,
    CommonalityTableSpec,
    ConfidenceIndicatorSpec,
    DistributionComparisonSpec,
    EngineeringEntityCardSpec,
    InvestigationContextSpec,
    EngineeringEntityKind,
    EngineeringStatus,
    EngineeringTimelineEvent,
    EvidenceCardSpec,
    EvidenceDirection,
    LimitBand,
    ProcessTrendSpec,
    RcaEvidencePanelSpec,
    SpecEvaluation,
    SpecState,
    evaluate_spec,
)
from nicegui_base.visual import Icons, IconSize, render_icon_svg
from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, SeriesSpec
from .nicegui_data_table import DataTable
from .nicegui_visualization import ChartPanel


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render engineering components') from exc
    return ui


_ENTITY_ICONS = {
    EngineeringEntityKind.FAB: Icons.FAB,
    EngineeringEntityKind.AREA: Icons.GRID,
    EngineeringEntityKind.TOOL: Icons.TOOL,
    EngineeringEntityKind.CHAMBER: Icons.CHAMBER,
    EngineeringEntityKind.LOT: Icons.LOT,
    EngineeringEntityKind.WAFER: Icons.WAFER,
    EngineeringEntityKind.DIE: Icons.DIE,
    EngineeringEntityKind.RECIPE: Icons.RECIPE,
    EngineeringEntityKind.PROCESS_STEP: Icons.PROCESS,
    EngineeringEntityKind.ROUTE: Icons.ROUTE,
    EngineeringEntityKind.PARAMETER: Icons.METROLOGY,
    EngineeringEntityKind.MEASUREMENT: Icons.METROLOGY,
    EngineeringEntityKind.DEFECT: Icons.DEFECT,
    EngineeringEntityKind.ALARM: Icons.ALARM,
    EngineeringEntityKind.INVESTIGATION: Icons.RCA,
}


class EngineeringStatusBadge:
    def __init__(self, status: EngineeringStatus, *, label: str | None = None):
        self.status = status
        self.label = label or status.value.replace('_', ' ').title()
        ui = _ui()
        with ui.element('span').classes(f'cui-eng-status cui-eng-status--{status.value}') as self.element:
            ui.element('span').classes('cui-spec__mark')
            ui.label(self.label)


class EngineeringEntityCard:
    def __init__(self, spec: EngineeringEntityCardSpec):
        self.spec = spec
        ui = _ui()
        e = spec.entity
        with ui.element('section').classes('cui-eng-entity') as self.element:
            with ui.element('div').classes('cui-eng-entity__head'):
                with ui.element('div').classes('cui-eng-entity__identity'):
                    icon = _ENTITY_ICONS[e.kind]
                    ui.html(render_icon_svg(icon, size=IconSize.MD, label=None), sanitize=False).classes('cui-eng-entity__icon')
                    with ui.element('div'):
                        ui.label(spec.title or e.display_label).classes('cui-eng-entity__title')
                        secondary = spec.description or e.secondary or f'{e.kind.value.replace("_", " ").title()} · {e.identifier}'
                        ui.label(secondary).classes('cui-eng-entity__secondary')
                if spec.show_status:
                    EngineeringStatusBadge(e.status)
            if spec.properties:
                with ui.element('div').classes('cui-property-grid cui-eng-property-grid'):
                    for key, value in spec.properties:
                        with ui.element('div').classes('cui-eng-property'):
                            ui.label(str(key)).classes('cui-eng-property__label')
                            ui.label('—' if value is None else str(value)).classes('cui-eng-property__value cui-tabular')


class InvestigationContextBar:
    """Compact investigation orientation strip for RCA workspaces."""
    def __init__(self, spec: InvestigationContextSpec):
        self.spec = spec
        ui = _ui()
        with ui.element('section').classes('cui-investigation-context').props('aria-label="Investigation context"') as self.element:
            self._cell(ui, 'Investigation', f'{spec.investigation_id} · {spec.hypothesis}', lead=True)
            self._cell(ui, 'Owner', spec.owner)
            self._cell(ui, 'Stage', spec.stage)
            self._cell(ui, 'Updated', spec.updated)

    @staticmethod
    def _cell(ui, label: str, value: str, *, lead: bool = False) -> None:
        cls='cui-investigation-context__cell' + (' cui-investigation-context__cell--lead' if lead else '')
        with ui.element('div').classes(cls):
            ui.label(label).classes('cui-investigation-context__label')
            ui.label(value).classes('cui-investigation-context__value')


class SpecLimitIndicator:
    def __init__(self, value: float | None = None, *, limits: LimitBand | None = None, evaluation: SpecEvaluation | None = None, decimals: int = 3):
        if evaluation is None:
            if limits is None:
                raise ValueError('limits are required when evaluation is not supplied')
            evaluation = evaluate_spec(value, limits)
        self.evaluation = evaluation
        ui = _ui()
        label = _format_evaluation(evaluation, decimals)
        with ui.element('span').classes(f'cui-spec cui-spec--{evaluation.state.value}') as self.element:
            ui.element('span').classes('cui-spec__mark')
            ui.label(label)


class OutOfSpecIndicator(SpecLimitIndicator):
    def __init__(self, value: float | None = None, *, limits: LimitBand | None = None, evaluation: SpecEvaluation | None = None, decimals: int = 3):
        super().__init__(value, limits=limits, evaluation=evaluation, decimals=decimals)


def _format_evaluation(evaluation: SpecEvaluation, decimals: int) -> str:
    if evaluation.value is None:
        return 'No measurement'
    value = f'{evaluation.value:.{decimals}f}'
    if evaluation.unit:
        value += f' {evaluation.unit}'
    suffix = {
        SpecState.IN_SPEC: 'In spec', SpecState.WATCH_LOW: 'Near lower limit', SpecState.WATCH_HIGH: 'Near upper limit',
        SpecState.OOS_LOW: 'Below LSL', SpecState.OOS_HIGH: 'Above USL', SpecState.MISSING: 'Missing',
    }[evaluation.state]
    return f'{value} · {suffix}'


class BaselineComparison:
    def __init__(self, comparison: BaselineComparisonModel, *, decimals: int = 3):
        self.comparison = comparison
        ui = _ui()
        with ui.element('div').classes('cui-baseline') as self.element:
            _metric('Current', comparison.current, comparison.unit, decimals)
            _metric('Baseline', comparison.baseline, comparison.unit, decimals)
            delta = comparison.delta
            suffix = comparison.unit
            _metric('Delta', delta, suffix, decimals, prefix='+' if delta is not None and delta > 0 else '')


def _metric(label: str, value: Any, unit: str | None, decimals: int, prefix: str = '') -> None:
    ui = _ui()
    with ui.element('div'):
        ui.label(label).classes('cui-baseline__label')
        if isinstance(value, (int, float)):
            text = f'{prefix}{value:.{decimals}f}'
        else:
            text = '—' if value is None else str(value)
        if unit and value is not None:
            text += f' {unit}'
        ui.label(text).classes('cui-baseline__value')


class ConfidenceIndicator:
    def __init__(self, spec: ConfidenceIndicatorSpec):
        self.spec = spec
        ui = _ui()
        with ui.element('div').classes('cui-confidence') as self.element:
            ui.label(spec.display).classes('cui-confidence__label')
            with ui.element('div').classes('cui-confidence__track'):
                pct = 0 if spec.score is None else round(spec.score * 100, 2)
                ui.element('div').classes('cui-confidence__fill').style(f'width:{pct}%')
            if spec.basis:
                ui.label(spec.basis).classes('cui-field-description')


class EvidenceCard:
    def __init__(self, spec: EvidenceCardSpec):
        self.spec = spec
        e = spec.evidence
        ui = _ui()
        with ui.element('article').classes(f'cui-evidence cui-evidence--{e.direction.value}') as self.element:
            with ui.element('div').classes('cui-evidence__meta'):
                ui.label(e.channel.value.replace('_',' ').title())
                ui.label(e.strength.value.title())
                if spec.show_confidence and e.confidence is not None:
                    ui.label(f'Confidence {e.confidence:.0%}')
                if spec.show_source and e.source:
                    ui.label(e.source)
            ui.label(e.title).classes('cui-evidence__title')
            if e.summary:
                ui.label(e.summary).classes('cui-evidence__summary')


class CommonalityTable:
    def __init__(self, spec: CommonalityTableSpec, *, on_select=None):
        self.spec = spec
        self.table = DataTable(spec.rows(), spec=spec.table_spec(), on_select=on_select)
        self.element = self.table.element


class EngineeringProcessTrend:
    def __init__(self, spec: ProcessTrendSpec, **kwargs):
        self.spec = spec
        panel, series, thresholds, chart_limits = spec.chart()
        self.chart = ChartPanel(series, spec=panel, thresholds=thresholds, spec_limits=chart_limits, **kwargs)
        self.element = self.chart.element


class PopulationComparisonPanel:
    def __init__(self, spec: DistributionComparisonSpec, **kwargs):
        self.spec = spec
        comparison = spec.population_comparison()
        ui = _ui()
        with ui.element('section').classes('cui-eng-entity') as self.element:
            ui.label(f'{spec.parameter} · Population Comparison').classes('cui-eng-entity__title')
            with ui.element('div').classes('cui-rca-balance'):
                _summary_box(spec.affected_label, comparison.affected.count, comparison.affected.mean, spec.unit)
                _summary_box(spec.control_label, comparison.control.count, comparison.control.mean, spec.unit)
                _summary_box('Mean Δ', None, comparison.mean_delta, spec.unit)
            categories, series = spec.histogram()
            if series:
                panel = ChartPanelSpec(
                    title='Distribution', kind=ChartKind.BAR,
                    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=categories),
                    y_axis=AxisSpec(kind=AxisType.VALUE, label='Count'),
                )
                self.histogram = ChartPanel(series, spec=panel, **kwargs)
            else:
                self.histogram = None


def _summary_box(label: str, count: int | None, value: float | None, unit: str | None) -> None:
    ui = _ui()
    with ui.element('div'):
        ui.label(label).classes('cui-baseline__label')
        text = '—' if value is None else f'{value:.3f}' + (f' {unit}' if unit else '')
        ui.label(text).classes('cui-baseline__value')
        if count is not None:
            ui.label(f'n={count}').classes('cui-field-description')


class RcaEvidencePanel:
    def __init__(self, spec: RcaEvidencePanelSpec):
        self.spec = spec
        ui = _ui()
        balance = spec.balance
        with ui.element('section').classes('cui-eng-entity') as self.element:
            ui.label(spec.title).classes('cui-eng-entity__title')
            ui.label(spec.hypothesis.title).classes('cui-eng-entity__secondary')
            with ui.element('div').classes('cui-rca-balance'):
                _count_box('Supporting', balance.support_count, 'cui-success')
                _count_box('Contradicting', balance.contradiction_count, 'cui-danger')
                _count_box('Neutral', balance.neutral_count, 'cui-text-secondary')
            items = spec.hypothesis.evidence
            if not spec.show_contradictions:
                items = tuple(e for e in items if e.direction is not EvidenceDirection.CONTRADICTS)
            for evidence in items:
                EvidenceCard(EvidenceCardSpec(evidence))


def _count_box(label: str, count: int, color_var: str) -> None:
    ui = _ui()
    with ui.element('div'):
        ui.label(label).classes('cui-baseline__label')
        ui.label(str(count)).classes('cui-baseline__value').style(f'color:var(--{color_var})')


class EngineeringTimeline:
    def __init__(self, events: Sequence[EngineeringTimelineEvent]):
        self.events = tuple(sorted(events, key=lambda e: e.at, reverse=True))
        ui = _ui()
        with ui.element('div').classes('cui-eng-entity') as self.element:
            for event in self.events:
                with ui.element('div').classes('cui-evidence cui-evidence--neutral'):
                    with ui.element('div').classes('cui-evidence__meta'):
                        ui.label(event.at.isoformat(sep=' ', timespec='minutes'))
                        EngineeringStatusBadge(event.status)
                    ui.label(event.title).classes('cui-evidence__title')
                    if event.description:
                        ui.label(event.description).classes('cui-evidence__summary')


__all__ = [
    'BaselineComparison','CommonalityTable','ConfidenceIndicator','EngineeringEntityCard','EngineeringProcessTrend','InvestigationContextBar',
    'EngineeringStatusBadge','EngineeringTimeline','EvidenceCard','OutOfSpecIndicator','PopulationComparisonPanel',
    'RcaEvidencePanel','SpecLimitIndicator',
]
