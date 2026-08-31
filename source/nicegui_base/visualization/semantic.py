from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from nicegui_base.data_engine import DataBinding, DataQuery, DataResult, DataSession, Dataset, SortClause

from .models import ChartKind


class VisualIntent(str, Enum):
    KPI = 'kpi'
    TREND = 'trend'
    COMPARISON = 'comparison'
    RANKING = 'ranking'
    DISTRIBUTION = 'distribution'
    RELATIONSHIP = 'relationship'
    PART_TO_WHOLE = 'part_to_whole'


@dataclass(frozen=True, slots=True)
class SemanticVisualSpec:
    title: str
    intent: VisualIntent
    dimensions: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    preferred_kind: ChartKind | None = None
    sort_descending: bool = False
    limit: int | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('visual title must not be empty')
        if self.limit is not None and self.limit < 1:
            raise ValueError('visual limit must be >= 1')


@dataclass(frozen=True, slots=True)
class SemanticVisualPlan:
    spec: SemanticVisualSpec
    chart_kind: ChartKind | None
    query: DataQuery
    x_field: str | None
    y_fields: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class SemanticVisualData:
    plan: SemanticVisualPlan
    result: DataResult | None
    value: Any = None


class SemanticVisualizationPlanner:
    """Governed visual-selection layer over the v3 semantic data engine.

    This planner deliberately returns existing NiceGUI Base ChartKind values instead
    of replacing chart renderers. That means v3 can improve authoring and linked
    analysis while retaining the already-certified v2 chart visuals and adapters.
    """

    def plan(self, dataset: Dataset, spec: SemanticVisualSpec) -> SemanticVisualPlan:
        self._validate(dataset, spec)
        kind = spec.preferred_kind or self._select_kind(spec)
        if spec.intent is VisualIntent.KPI:
            query = DataQuery(metrics=spec.metrics)
            return SemanticVisualPlan(spec, None, query, None, spec.metrics, 'Single governed metric rendered as a KPI.')
        if spec.intent is VisualIntent.DISTRIBUTION:
            metric = dataset.metrics[spec.metrics[0]]
            source = metric.source_field
            query = DataQuery(limit=spec.limit)
            return SemanticVisualPlan(spec, kind, query, source, (source,) if source else (), 'Raw metric values rendered as a distribution.')
        if spec.intent is VisualIntent.RELATIONSHIP:
            left = dataset.metrics[spec.metrics[0]].source_field
            right = dataset.metrics[spec.metrics[1]].source_field
            query = DataQuery(limit=spec.limit)
            return SemanticVisualPlan(spec, kind, query, left, (right,) if right else (), 'Raw paired measures rendered as a relationship without pre-aggregation.')
        sorts = ()
        if spec.sort_descending and spec.metrics:
            sorts = (SortClause(spec.metrics[0], descending=True),)
        query = DataQuery(
            dimensions=spec.dimensions,
            metrics=spec.metrics,
            sorts=sorts,
            limit=spec.limit,
        )
        x_field = spec.dimensions[0] if spec.dimensions else None
        return SemanticVisualPlan(spec, kind, query, x_field, spec.metrics, self._rationale(spec, kind))

    def resolve(self, session: DataSession, spec: SemanticVisualSpec) -> SemanticVisualData:
        plan = self.plan(session.dataset, spec)
        if spec.intent is VisualIntent.KPI:
            return SemanticVisualData(plan, None, session.metric(spec.metrics[0]))
        if spec.intent is VisualIntent.DISTRIBUTION:
            result = session.query(plan.query)
            field = plan.x_field
            values = tuple(row.get(field) for row in result.rows) if field is not None else ()
            return SemanticVisualData(plan, result, values)
        if spec.intent is VisualIntent.RELATIONSHIP:
            result = session.query(plan.query)
            x_field = plan.x_field; y_field = plan.y_fields[0] if plan.y_fields else None
            pairs = tuple((row.get(x_field), row.get(y_field)) for row in result.rows) if x_field and y_field else ()
            return SemanticVisualData(plan, result, pairs)
        return SemanticVisualData(plan, session.query(plan.query))

    def bind(self, session: DataSession, spec: SemanticVisualSpec) -> DataBinding[SemanticVisualData]:
        # Validation is performed before installing a live binding so an invalid
        # specification cannot leave behind a partially registered watcher.
        self.plan(session.dataset, spec)
        return session.bind(lambda current: self.resolve(current, spec))

    @staticmethod
    def _select_kind(spec: SemanticVisualSpec) -> ChartKind | None:
        if spec.intent is VisualIntent.KPI:
            return None
        if spec.intent is VisualIntent.TREND:
            return ChartKind.LINE
        if spec.intent in {VisualIntent.COMPARISON, VisualIntent.RANKING}:
            return ChartKind.BAR
        if spec.intent is VisualIntent.DISTRIBUTION:
            return ChartKind.HISTOGRAM
        if spec.intent is VisualIntent.RELATIONSHIP:
            return ChartKind.SCATTER
        if spec.intent is VisualIntent.PART_TO_WHOLE:
            return ChartKind.DONUT
        raise ValueError(f'unsupported visual intent {spec.intent!r}')

    @staticmethod
    def _validate(dataset: Dataset, spec: SemanticVisualSpec) -> None:
        missing_dimensions = [key for key in spec.dimensions if key not in dataset.dimensions]
        missing_metrics = [key for key in spec.metrics if key not in dataset.metrics]
        if missing_dimensions:
            raise KeyError(f'unknown visual dimensions: {missing_dimensions}')
        if missing_metrics:
            raise KeyError(f'unknown visual metrics: {missing_metrics}')
        if spec.intent is VisualIntent.KPI and (len(spec.metrics) != 1 or spec.dimensions):
            raise ValueError('KPI visuals require exactly one metric and no dimensions')
        if spec.intent is VisualIntent.TREND and (len(spec.dimensions) != 1 or not spec.metrics):
            raise ValueError('trend visuals require one dimension and at least one metric')
        if spec.intent in {VisualIntent.COMPARISON, VisualIntent.RANKING, VisualIntent.PART_TO_WHOLE} and (len(spec.dimensions) != 1 or not spec.metrics):
            raise ValueError(f'{spec.intent.value} visuals require one dimension and at least one metric')
        if spec.intent is VisualIntent.DISTRIBUTION and (spec.dimensions or len(spec.metrics) != 1):
            raise ValueError('distribution visuals require exactly one metric and no dimensions')
        if spec.intent is VisualIntent.RELATIONSHIP and (spec.dimensions or len(spec.metrics) != 2):
            raise ValueError('relationship visuals require exactly two metrics and no dimensions')

    @staticmethod
    def _rationale(spec: SemanticVisualSpec, kind: ChartKind | None) -> str:
        if spec.preferred_kind is not None:
            return f'Explicit governed chart override: {spec.preferred_kind.value}.'
        descriptions = {
            VisualIntent.TREND: 'Trend intent maps to a line chart to preserve ordered change.',
            VisualIntent.COMPARISON: 'Comparison intent maps to a bar chart for categorical magnitude comparison.',
            VisualIntent.RANKING: 'Ranking intent maps to a descending bar chart.',
            VisualIntent.RELATIONSHIP: 'Relationship intent maps to a scatter chart for paired quantitative measures.',
            VisualIntent.PART_TO_WHOLE: 'Part-to-whole intent maps to the governed donut renderer.',
        }
        return descriptions.get(spec.intent, f'Governed semantic mapping to {kind.value if kind else "non-chart"}.')


__all__ = [
    'SemanticVisualData', 'SemanticVisualPlan', 'SemanticVisualSpec', 'SemanticVisualizationPlanner', 'VisualIntent',
]
