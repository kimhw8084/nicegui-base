from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_d6h3_identity_is_distinct_from_preserved_candidates():
    from nicegui_base.workbench.update_identity import BUILD_ID

    assert BUILD_ID == 'NGB-20260907-G2.6'


def test_all_patterns_declare_and_render_their_defining_anatomy():
    from nicegui_base.patterns.registry import PATTERN_REGISTRY
    from nicegui_base.workbench.pattern_specimens import PATTERN_SEMANTIC_ANATOMY

    assert set(PATTERN_SEMANTIC_ANATOMY) == {item.value for item in PATTERN_REGISTRY}
    expected = {
        'dashboard': {'kpis', 'trend', 'exceptions'},
        'data_explorer': {'filters', 'primary_table', 'selected_detail'},
        'master_detail': {'master', 'selected_detail'},
        'crud': {'create', 'read', 'update', 'delete', 'validation'},
        'monitoring': {'status_kpis', 'health_trend', 'alerts', 'supporting_data'},
        'search': {'query', 'facets', 'results', 'selected_context', 'empty_state'},
        'settings': {'section_navigation', 'settings_form', 'dirty_state', 'save', 'reset', 'validation'},
        'wizard': {'progress', 'back', 'next', 'validation', 'review'},
        'comparison': {'populations', 'delta', 'comparison_visual', 'aligned_evidence'},
        'analysis_workspace': {'analysis_filters', 'primary_visual', 'supporting_table', 'selected_inspector'},
    }
    assert {key: set(value) for key, value in PATTERN_SEMANTIC_ANATOMY.items()} == expected
    source = (ROOT / 'nicegui_base/workbench/pattern_specimens.py').read_text(encoding='utf-8')
    assert 'data-pattern-region' in source
    assert 'DangerConfirmDialog' in source
    assert 'SearchResults' in source
    assert 'ProgressSteps' in source
    assert 'DifferenceTable' in source


def test_all_promoted_analytics_have_complete_semantic_contracts_and_fixtures():
    from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY
    from nicegui_base.workbench.analytic_specimens import (
        ANALYTIC_SEMANTIC_CONTRACTS,
        CANONICAL_ANALYTIC_FIXTURES,
    )

    expected = set(SEMICONDUCTOR_SURFACE_REGISTRY)
    assert set(ANALYTIC_SEMANTIC_CONTRACTS) == expected
    assert set(CANONICAL_ANALYTIC_FIXTURES) == expected
    for key, contract in ANALYTIC_SEMANTIC_CONTRACTS.items():
        assert contract.key == key
        assert contract.geometry and contract.x_axis and contract.y_axis and contract.meaning
        assert contract.required_fields
        rows = CANONICAL_ANALYTIC_FIXTURES[key]
        assert len(rows) >= 3
        assert all(set(contract.required_fields) <= set(row) for row in rows)
        numeric = [value for row in rows for value in row.values() if isinstance(value, (int, float)) and not isinstance(value, bool)]
        assert len(set(numeric)) > 1, key


def test_required_analytic_contracts_encode_geometry_not_mount_status():
    from nicegui_base.workbench.analytic_specimens import ANALYTIC_SEMANTIC_CONTRACTS as contracts

    assert contracts['spc_i_mr'].panels == ('individuals', 'moving_range')
    assert contracts['spc_xbar_r'].panels == ('xbar', 'range')
    assert contracts['spc_xbar_s'].panels == ('xbar', 'standard_deviation')
    assert 'step' in contracts['ecdf'].options
    assert 'spec_limits' in contracts['capability_histogram'].options
    assert contracts['rca_sankey'].geometry == 'sankey'
    assert contracts['rca_fault_tree'].geometry == 'fault_tree'
    assert contracts['rca_genealogy_graph'].geometry == 'relationship_graph'
    assert 'non_parallel' in contracts['doe_interactions'].options
    assert all('control_limits' in contracts[key].options for key in ('spc_p', 'spc_np', 'spc_c', 'spc_u'))
    assert 'event_marker' in contracts['fdc_alarm_overlay'].options
    assert 'contour_isolines' in contracts['wafer_contour'].options
    assert all('cumulative_bridge' in contracts[key].options for key in ('rca_contribution_waterfall', 'yield_waterfall'))


def test_ecdf_and_network_renderers_expose_real_option_contracts():
    from nicegui_base.integrations.nicegui_visualization import _EmpiricalCDFChart, _FaultTreeDiagram, _RelationshipGraph, _SankeyDiagram, _WaterfallDiagram

    ecdf = _EmpiricalCDFChart.build_options('ECDF', ((1.0, .25), (2.0, .5), (3.0, .75), (4.0, 1.0)))
    assert ecdf['series'][0]['step'] == 'end'

    sankey = _SankeyDiagram.build_options(
        ('Affected', 'ETCH-021', 'CH-3', 'Review'),
        (('Affected', 'ETCH-021', 84), ('ETCH-021', 'CH-3', 61), ('CH-3', 'Review', 43)),
    )
    assert sankey['series'][0]['type'] == 'sankey'
    assert all(link['value'] > 0 for link in sankey['series'][0]['links'])

    graph = _RelationshipGraph.build_options(
        (('lot', 'LOT-2471', 0, 1), ('w8', 'W08', 1, 0), ('w9', 'W09', 1, 2), ('ch3', 'CH-3', 2, 1)),
        (('lot', 'w8'), ('lot', 'w9'), ('w8', 'ch3'), ('w9', 'ch3')),
    )
    assert graph['series'][0]['type'] == 'graph'
    assert len(graph['series'][0]['links']) == 4

    tree = _FaultTreeDiagram.build_options(
        {'name': 'OOS event', 'children': ({'name': 'OR', 'gate': 'OR', 'children': ({'name': 'Pressure unstable'}, {'name': 'RF mismatch'})},)},
    )
    assert tree['series'][0]['type'] == 'tree'
    assert 'OR' in str(tree)

    waterfall = _WaterfallDiagram.build_options(('A', 'B', 'C'), (2.0, -0.5, 1.0))
    assert [series['stack'] for series in waterfall['series']] == ['bridge', 'bridge', 'bridge']
    assert [series['type'] for series in waterfall['series']] == ['custom', 'custom', 'custom']
    bars = {item['name']: item for series in waterfall['series'] for item in series['data']}
    assert bars['A']['value'][1:3] == [0.0, 2.0]
    assert bars['B']['value'][1:3] == [2.0, 1.5]
    assert bars['B']['deltaLabel'] == '-0.5'
    assert bars['Net']['value'][1:3] == [0.0, 2.5]


def test_layout_and_agent_references_expose_each_governed_visual_contract():
    layout = (ROOT / 'nicegui_base/workbench/layout_studio.py').read_text(encoding='utf-8')
    app = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')

    assert 'render_catalog_miniature(definition, device)' in layout
    assert "for device in ('desktop', 'tablet', 'phone')" in layout
    assert 'data-live-layout-pattern' in layout and 'data-scaffold-command' in layout
    assert '5 · Business/domain logic' in app


def test_doe_and_subgroup_fixtures_are_non_degenerate():
    from nicegui_base.workbench.analytic_specimens import CANONICAL_ANALYTIC_FIXTURES as fixtures

    interaction = fixtures['doe_interactions']
    grouped = {}
    for row in interaction:
        grouped.setdefault(row['factor_b'], []).append(float(row['response']))
    slopes = {level: values[-1] - values[0] for level, values in grouped.items()}
    assert min(slopes.values()) < 0 < max(slopes.values())
    for key in ('spc_xbar_r', 'spc_xbar_s'):
        rows = fixtures[key]
        assert len({row['subgroup'] for row in rows}) >= 8
        assert all(sum(1 for row in rows if row['subgroup'] == group) >= 4 for group in {row['subgroup'] for row in rows})


def test_full_app_primary_analytics_are_registered_governed_contracts():
    from nicegui_base.workbench.analytic_specimens import ANALYTIC_SEMANTIC_CONTRACTS
    from nicegui_base.workbench.full_applications import FULL_APPLICATION_REGISTRY

    assert all(app.primary_surface_key in ANALYTIC_SEMANTIC_CONTRACTS for app in FULL_APPLICATION_REGISTRY.values())
    source = (ROOT / 'nicegui_base/workbench/full_applications.py').read_text(encoding='utf-8')
    assert 'data-governed-analytic' in source


def test_component_evidence_uses_production_renderer_and_public_code():
    from nicegui_base.workbench.component_specimens import COMPONENT_SPECIMEN_KEYS
    from nicegui_base.workbench.registry_adapters import build_registry_entries

    entries = tuple(entry for entry in build_registry_entries() if entry.metadata.get('component_key') in COMPONENT_SPECIMEN_KEYS)
    assert len(entries) == len(COMPONENT_SPECIMEN_KEYS) == 34
    for entry in entries:
        assert 'nicegui_base' in entry.reference_contract.recommended_code
        assert entry.reference_contract.states
        assert entry.reference_contract.variants
