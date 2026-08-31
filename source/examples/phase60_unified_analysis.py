"""Golden Wave 60 shared-analysis composition.

This example intentionally keeps page-local state out of the composition. A real
NiceGUI route can render DataSourceTable/AnalyticalPanel/NiceGUIWorkspace around the
same owned runtime objects.
"""
from __future__ import annotations

from nicegui_base import (
    ApplicationRuntime, Comparison, ComparisonOperator, DataSchema, FieldRole, FieldType,
    InMemoryDataSource, PanelSpec, SemanticField, TimeRange,
)

ROWS = (
    {'id': 1, 'area': 'ETCH', 'chamber': 'A', 'cd': 12.0},
    {'id': 2, 'area': 'ETCH', 'chamber': 'B', 'cd': 14.0},
)


def build_runtime() -> ApplicationRuntime:
    runtime = ApplicationRuntime()
    schema = DataSchema((
        SemanticField('id', type=FieldType.INTEGER, role=FieldRole.IDENTIFIER),
        SemanticField('area', type=FieldType.CATEGORY, role=FieldRole.DIMENSION),
        SemanticField('chamber', type=FieldType.CATEGORY, role=FieldRole.ENTITY),
        SemanticField('cd', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT, unit='nm'),
    ), key='id')
    runtime.data.register_source(InMemoryDataSource('process', ROWS, schema=schema))
    workspace = runtime.open_workspace('analysis')
    workspace.analysis.set_source('process')
    workspace.analysis.add_filter(Comparison('area', ComparisonOperator.EQ, 'ETCH'))
    workspace.analysis.set_time_range(TimeRange('id', 1, 2))
    workspace.workspace.register_panel(PanelSpec('trend', preferred_columns=8, metadata={'title': 'Process trend'}))
    workspace.workspace.register_panel(PanelSpec('records', preferred_columns=4, metadata={'title': 'Records'}))
    return runtime
