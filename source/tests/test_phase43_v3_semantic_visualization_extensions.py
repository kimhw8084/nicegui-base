from __future__ import annotations

import pytest

from nicegui_base import Aggregation, DataEngine, Dataset, Dimension, FilterClause, FilterOperation, Metric
from nicegui_base.extensions import ExtensionDefinition, ExtensionKind, ExtensionRegistry
from nicegui_base.visualization import ChartKind, SemanticVisualSpec, SemanticVisualizationPlanner, VisualIntent


def data() -> Dataset:
    return Dataset(
        'factory',
        (
            {'id': 1, 'month': '2026-01', 'tool': 'A', 'revenue': 100, 'yield': .91},
            {'id': 2, 'month': '2026-01', 'tool': 'B', 'revenue': 150, 'yield': .95},
            {'id': 3, 'month': '2026-02', 'tool': 'A', 'revenue': 200, 'yield': .89},
        ),
        row_key='id',
        dimensions=(Dimension('month'), Dimension('tool')),
        metrics=(
            Metric('revenue', aggregation=Aggregation.SUM),
            Metric('avg_yield', field='yield', aggregation=Aggregation.AVG),
        ),
    )


def test_v3_semantic_visual_planner_maps_intents_to_existing_certified_chart_kinds():
    planner = SemanticVisualizationPlanner(); dataset = data()
    trend = planner.plan(dataset, SemanticVisualSpec('Revenue trend', VisualIntent.TREND, dimensions=('month',), metrics=('revenue',)))
    compare = planner.plan(dataset, SemanticVisualSpec('By tool', VisualIntent.COMPARISON, dimensions=('tool',), metrics=('revenue',)))
    relation = planner.plan(dataset, SemanticVisualSpec('Revenue vs yield', VisualIntent.RELATIONSHIP, metrics=('revenue', 'avg_yield')))
    assert trend.chart_kind is ChartKind.LINE
    assert compare.chart_kind is ChartKind.BAR
    assert relation.chart_kind is ChartKind.SCATTER


def test_v3_semantic_visual_binding_crossfilters_chart_and_kpi_from_same_session_revision():
    engine = DataEngine(); engine.register(data()); session = engine.session('factory')
    planner = SemanticVisualizationPlanner()
    chart = planner.bind(session, SemanticVisualSpec('Revenue by tool', VisualIntent.COMPARISON, dimensions=('tool',), metrics=('revenue',)))
    kpi = planner.bind(session, SemanticVisualSpec('Revenue', VisualIntent.KPI, metrics=('revenue',)))
    session.set_filter(FilterClause('tool', FilterOperation.EQUALS, 'A'))
    assert chart.revision == kpi.revision == session.revision == 1
    assert chart.value.result is not None and chart.value.result.rows == ({'tool': 'A', 'revenue': 300.0},)
    assert kpi.value.value == 300.0


def test_v3_semantic_visual_distribution_uses_raw_metric_source_field_and_validation_rejects_invalid_specs():
    engine = DataEngine(); engine.register(data()); session = engine.session('factory'); planner = SemanticVisualizationPlanner()
    distribution = planner.resolve(session, SemanticVisualSpec('Yield distribution', VisualIntent.DISTRIBUTION, metrics=('avg_yield',)))
    assert distribution.plan.chart_kind is ChartKind.HISTOGRAM
    assert distribution.value == (.91, .95, .89)
    with pytest.raises(ValueError, match='exactly two metrics'):
        planner.plan(data(), SemanticVisualSpec('Bad relation', VisualIntent.RELATIONSHIP, metrics=('revenue',)))


def test_v3_extension_registry_supports_explicit_decorators_creation_listing_and_duplicate_protection():
    registry = ExtensionRegistry()

    @registry.data_source('warehouse', version='2.1', metadata={'owner': 'analytics'})
    def warehouse(name: str):
        return {'name': name}

    registry.register(ExtensionDefinition('special_panel', ExtensionKind.WORKSPACE_PANEL, lambda: 'panel'))
    assert registry.create(ExtensionKind.DATA_SOURCE, 'warehouse', 'fab') == {'name': 'fab'}
    assert registry.create(ExtensionKind.WORKSPACE_PANEL, 'special_panel') == 'panel'
    assert [item.key for item in registry.list()] == ['warehouse', 'special_panel']
    assert registry.require(ExtensionKind.DATA_SOURCE, 'warehouse').metadata['owner'] == 'analytics'
    with pytest.raises(TypeError):
        registry.require(ExtensionKind.DATA_SOURCE, 'warehouse').metadata['owner'] = 'other'
    with pytest.raises(ValueError, match='duplicate'):
        registry.register(ExtensionDefinition('warehouse', ExtensionKind.DATA_SOURCE, lambda: None))


def test_v3_relationship_visual_resolves_raw_paired_measures_not_one_aggregated_point():
    engine = DataEngine(); engine.register(data()); session = engine.session('factory'); planner = SemanticVisualizationPlanner()
    relationship = planner.resolve(session, SemanticVisualSpec('Revenue vs yield', VisualIntent.RELATIONSHIP, metrics=('revenue', 'avg_yield')))
    assert relationship.plan.chart_kind is ChartKind.SCATTER
    assert relationship.value == ((100, .91), (150, .95), (200, .89))
