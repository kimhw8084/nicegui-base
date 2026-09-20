"""CHG-148 regressions for RCA recipe graph resize lifecycle."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_relationship_graph_has_a_transient_resize_geometry_guard():
    source = (ROOT / 'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    constructor = source.split('class _RelationshipGraph', 1)[1].split('class _FaultTreeDiagram', 1)[0]

    assert "self.element.classes('cui-chart-canvas--resize-safe')" in constructor
    css = (ROOT / 'nicegui_base' / 'visualization' / 'css.py').read_text(encoding='utf-8')
    assert '.cui-chart-canvas--resize-safe { min-width:1px; }' in css
    assert 'transient zero-width canvas' in constructor


def test_rca_recipe_composition_and_relationship_graph_contract_remain_complete():
    from nicegui_base import RelationshipGraph
    from nicegui_base.semiconductor.recipes import get_semiconductor_recipe

    expected = {
        'excursion-defense-line': (
            'rca_affected_control', 'wafer_delta', 'rca_commonality_ranking',
            'rca_commonality_matrix', 'rca_genealogy_graph', 'rca_evidence_matrix',
        ),
        'rca-cockpit': (
            'rca_affected_control', 'rca_commonality_ranking', 'rca_commonality_matrix',
            'rca_contribution_waterfall', 'rca_evidence_matrix', 'rca_genealogy_graph',
            'rca_fault_tree', 'rca_sankey',
        ),
    }
    for recipe_key, surfaces in expected.items():
        recipe = get_semiconductor_recipe(recipe_key)
        assert tuple(panel.surface_key for panel in recipe.panels if panel.surface_key) == surfaces

    assert callable(RelationshipGraph)
