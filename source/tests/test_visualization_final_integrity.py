"""Final semantic/reference integrity gates for the governed analytics surface."""
from __future__ import annotations

import ast
from pathlib import Path

from nicegui_base.semiconductor import spc, yield_doe
from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY
from nicegui_base.workbench.analytic_specimens import (
    ANALYTIC_SEMANTIC_CONTRACTS,
    CANONICAL_ANALYTIC_FIXTURES,
    canonical_fixture_for_surface,
)
from nicegui_base.workbench.catalog import analytics_entries
from nicegui_base.workbench.public_examples import production_example_code


ROOT = Path(__file__).resolve().parents[1]


def test_all_promoted_surfaces_have_registry_contract_fixture_and_catalog_entry():
    keys = set(SEMICONDUCTOR_SURFACE_REGISTRY)
    assert len(keys) == 58
    assert keys == set(ANALYTIC_SEMANTIC_CONTRACTS)
    assert keys == set(CANONICAL_ANALYTIC_FIXTURES)
    entries = analytics_entries()
    assert len(entries) == 58
    assert {str(entry.metadata['surface_key']) for entry in entries} == keys
    assert all(entry.reference_contract.live_example for entry in entries)


def test_analytics_code_examples_are_specific_public_api_compositions():
    for entry in analytics_entries():
        code = production_example_code(entry)
        ast.parse(code)
        assert 'from nicegui_base import' in code or 'from nicegui_base.integrations.nicegui_visualization import' in code, entry.key
        assert 'Generated from the current ReferenceContract' not in code, entry.key
        assert 'use the registered API' not in code, entry.key
        assert 'ui.echart' not in code, entry.key


def test_workbench_reference_does_not_bypass_the_governed_chart_boundary():
    workbench = ROOT / 'nicegui_base' / 'workbench'
    offenders = []
    for path in workbench.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        if 'ui.echart(' in text or 'ui.plotly(' in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_control_chart_families_keep_their_distinct_semantic_statistics():
    # Use explicit deterministic subgroup data so the paired result fields are
    # tested independently from the Workbench specimen.
    groups = tuple(
        tuple(40.0 + subgroup * 0.1 + observation * 0.04 for observation in range(4))
        for subgroup in range(4)
    )
    xbar_r = spc.xbar_r(groups)
    xbar_s = spc.xbar_s(groups)
    assert xbar_r.family is spc.ControlChartFamily.XBAR_R
    assert xbar_s.family is spc.ControlChartFamily.XBAR_S
    assert len(xbar_r.secondary_values) == len(xbar_s.secondary_values)
    assert xbar_r.secondary_values != xbar_s.secondary_values
    p = spc.p_chart((4, 8, 2, 12), (200, 400, 200, 600))
    u = spc.u_chart((4, 8, 2, 12), (200, 400, 200, 600))
    assert len(set(round(value, 8) for value in p.ucl)) > 1
    assert len(set(round(value, 8) for value in u.ucl)) > 1
    assert p.family is not u.family


def test_distribution_and_doe_contracts_are_not_generic_aliases():
    ecdf = spc.ecdf((1.0, 2.0, 2.0, 3.0))
    assert ecdf == ((1.0, 0.25), (2.0, 0.5), (2.0, 0.75), (3.0, 1.0))
    interactions = yield_doe.doe_interactions(
        canonical_fixture_for_surface('doe_interactions'),
        'factor_a', 'factor_b', 'response',
    )
    assert interactions
    low = tuple(interactions[level]['Pressure low'] for level in ('RF low', 'RF center', 'RF high'))
    high = tuple(interactions[level]['Pressure high'] for level in ('RF low', 'RF center', 'RF high'))
    assert (low[0] - high[0]) * (low[-1] - high[-1]) < 0
    assert {'lsl', 'target', 'usl'} <= set(canonical_fixture_for_surface('capability_histogram')[0])


def test_weibull_fixture_retains_failure_and_censoring_semantics():
    rows = canonical_fixture_for_surface('weibull_reliability')
    flags = tuple(bool(row['failed']) for row in rows)
    result = yield_doe.weibull_analysis(tuple(float(row['time']) for row in rows), failures=flags)
    assert result.failures > 0
    assert result.censored > 0
    assert result.eta > 0
