"""Final semantic/reference integrity gates for the governed analytics surface."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
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
        assert 'from nicegui_base import' in code, entry.key
        assert 'nicegui_base.integrations.nicegui_visualization' not in code, entry.key
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


def test_all_promoted_examples_execute_against_real_public_constructors():
    tool = ROOT.parent / 'tools' / 'execute_visualization_examples.py'
    completed = subprocess.run(
        [sys.executable, str(tool)], cwd=ROOT.parent, env={**__import__('os').environ, 'PYTHONPATH': 'source'},
        capture_output=True, text=True, check=False,
    )
    payload=json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert payload['count'] == payload['passed'] == 58
    assert payload['failed'] == []


def test_cusum_keeps_independent_positive_and_negative_paths():
    result=spc.cusum((39.0, 39.2, 40.8, 41.0, 39.1, 39.0), target=40.0)
    assert result.c_plus and result.c_minus
    assert all(value >= 0 for value in result.c_plus)
    assert all(value <= 0 for value in result.c_minus)
    assert result.c_plus != result.c_minus
    assert result.metadata['c_plus'] == result.c_plus
    assert result.metadata['c_minus'] == result.c_minus


def test_qq_capability_and_weibull_use_truthful_mixed_geometry():
    from nicegui_base.integrations.nicegui_visualization import _QQProbabilityPlot
    from nicegui_base.semiconductor.visualization import capability_histogram_visual

    qq=_QQProbabilityPlot.build_options('Q-Q', ((-1.0, 39.5), (0.0, 40.0), (1.0, 40.5)))
    assert [item['type'] for item in qq['series']] == ['scatter', 'line']
    assert qq['series'][1]['data'][0][1] != qq['series'][1]['data'][0][0]

    plan=capability_histogram_visual((39.2,39.8,40.1,40.6), bins=3, lsl=38.5, target=40.0, usl=41.5)
    options=__import__('nicegui_base', fromlist=['build_echarts_options']).build_echarts_options(plan.spec, plan.series, spec_limits=plan.spec_limits)
    assert plan.spec.x_axis.kind.value == 'value'
    assert {item['xAxis'] for item in options['series'][0]['markLine']['data']} == {38.5,40.0,41.5}

    from nicegui_base import WeibullPlot
    import sys as _sys
    _sys.path.insert(0, str(ROOT.parent / 'tools'))
    import execute_visualization_examples as support
    with support._fake_nicegui():
        weibull=WeibullPlot('Reliability', ((1.0,.2),(2.0,.4)), ((3.0,.4),), ((1.0,.1),(3.0,.6)))
    assert [item.kind.value for item in weibull.series] == ['scatter','scatter','line']


def test_spatial_scale_modes_and_data_derived_contours():
    import sys as _sys
    _sys.path.insert(0, str(ROOT.parent / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import ScaleMode, WaferContourPlot, WaferMap, WaferPoint
    with support._fake_nicegui():
        categorical=WaferMap('Categories', (WaferPoint(0,0,1,status='Nominal'), WaferPoint(1,0,1,status='Watch')), scale_mode=ScaleMode.CATEGORICAL, category_key='status', legend_labels=('Nominal','Watch'))
        delta=WaferMap('Delta', (WaferPoint(0,0,-2), WaferPoint(1,0,3)), scale_mode=ScaleMode.DIVERGING)
        first=WaferContourPlot('Contour', (WaferPoint(-1,-1,1),WaferPoint(0,-1,2),WaferPoint(1,-1,3),WaferPoint(-1,0,2),WaferPoint(0,0,4),WaferPoint(1,0,3)))
        second=WaferContourPlot('Contour', (WaferPoint(-1,-1,4),WaferPoint(0,-1,3),WaferPoint(1,-1,2),WaferPoint(-1,0,3),WaferPoint(0,0,1),WaferPoint(1,0,2)))
    assert categorical.scale_mode is ScaleMode.CATEGORICAL
    assert delta.scale_bounds == (-3.0, 3.0)
    assert categorical.legend_mapping['Nominal'] != categorical.legend_mapping['Watch']
    assert first.svg != second.svg


def test_chart_data_view_exports_semantic_xy_columns():
    import sys as _sys
    _sys.path.insert(0, str(ROOT.parent / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import AxisSpec, AxisType, ChartPanel, ChartPanelSpec, ChartKind, SeriesSpec
    with support._fake_nicegui():
        panel=ChartPanel(
            (SeriesSpec('trace','Trace',({'time': 1, 'value': 40.1},),kind=ChartKind.LINE,x_key='time',y_key='value'),),
            spec=ChartPanelSpec('Trace',x_axis=AxisSpec(kind=AxisType.VALUE),y_axis=AxisSpec(kind=AxisType.VALUE)),
        )
        rows=panel.data_view.rows(); csv_text=panel.export.csv_text(); panel.dispose()
    assert rows[0]['x'] == 1 and rows[0]['y'] == 40.1
    assert csv_text.splitlines()[0] == 'series,index,x,y,value'
    assert 'Trace,0,1,40.1' in csv_text
