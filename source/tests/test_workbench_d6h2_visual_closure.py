"""D6H.2 semantic reference closure regressions."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
REPO = ROOT.parent


def test_d6h2_identity_and_visual_acceptance_authority_are_current():
    from nicegui_base.workbench.update_identity import BUILD_ID

    assert BUILD_ID == 'NGB-20260907-G2.6'
    browser = (REPO / 'tools' / 'verify_development_D6H3_browser.py').read_text(encoding='utf-8')
    for marker in ('58', '34', '10', 'data-chart-semantics'):
        assert marker in browser


def test_all_promoted_analytics_have_varied_machine_readable_fixtures():
    from nicegui_base.workbench.analytic_specimens import ANALYTIC_SEMANTIC_CONTRACTS, CANONICAL_ANALYTIC_FIXTURES
    from nicegui_base.workbench.catalog import analytics_entries

    assert len(analytics_entries()) == 58
    assert set(CANONICAL_ANALYTIC_FIXTURES) == {str(entry.metadata['surface_key']) for entry in analytics_entries()}
    for key, rows in CANONICAL_ANALYTIC_FIXTURES.items():
        assert len(rows) >= 3
        assert all(set(ANALYTIC_SEMANTIC_CONTRACTS[key].required_fields) <= set(row) for row in rows)
        values = [value for row in rows for value in row.values() if isinstance(value, (int, float)) and not isinstance(value, bool)]
        assert len(set(values)) > 1


def test_key_analytics_prove_geometry_and_semantics_from_their_fixtures():
    from nicegui_base.semiconductor import spc
    from nicegui_base.workbench.analytic_specimens import canonical_fixture_for_surface
    from nicegui_base.workbench.app import _render_surface_preview

    values = tuple(float(row['measurement']) for row in canonical_fixture_for_surface('spc_i_mr'))
    i_mr = spc.i_mr(values)
    assert len(i_mr.values) == 20
    assert all(value > 0 for value in i_mr.secondary_values)
    assert len(set(i_mr.values)) > 1
    ewma = spc.ewma(tuple(float(row['measurement']) for row in canonical_fixture_for_surface('spc_ewma')))
    assert len(set(round(value, 6) for value in ewma.values)) > 3
    cusum = spc.cusum(tuple(float(row['measurement']) for row in canonical_fixture_for_surface('spc_cusum')), k=.15, h=1.5)
    assert any(value > 0 for value in cusum.values) and any(value < 0 for value in cusum.values)

    app = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    for marker in (
        'Individuals — SPC I-MR', 'Moving Range — SPC I-MR',
        'data-chart-semantics="center-ucl-lcl"',
        'positive-negative-decision-limits', 'observed-vs-expected',
        'monotone-cdf', 'quartiles-median-whiskers',
    ):
        assert marker in app
    assert callable(_render_surface_preview)


def test_golden_readiness_denominator_excludes_only_framework_component_contracts():
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.coverage_matrix import golden_readiness_entries, readiness_rows
    from nicegui_base.workbench.models import WorkbenchKind

    entries = all_entries()
    promoted = golden_readiness_entries(entries)
    assert len(promoted) == 76
    assert all(entry.kind in {WorkbenchKind.ANALYTIC, WorkbenchKind.PATTERN, WorkbenchKind.RECIPE} for entry in promoted)
    assert sum(row.complete for row in readiness_rows(promoted)) == 76


def test_layout_and_ai_guide_show_live_authority_workflow():
    layout = (ROOT / 'nicegui_base/workbench/layout_studio.py').read_text(encoding='utf-8')
    app = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    assert 'cui-layout-live-composition' in layout
    assert 'data-layout-slot' in layout
    for marker in ('requirement', 'recommendation', 'business_logic', 'extension_rule', 'validation', 'Expected result'):
        assert marker in app


def test_excursion_reference_fixture_has_visible_grouped_distribution_geometry():
    from nicegui_base.workbench.full_applications import FULL_APPLICATION_REGISTRY

    rows = FULL_APPLICATION_REGISTRY['excursion-investigation'].fixture
    groups = {
        population: [float(row['value']) for row in rows if row['population'] == population]
        for population in ('Affected', 'Control')
    }
    assert all(len(values) >= 4 and max(values) > min(values) for values in groups.values())
    assert max(groups['Affected']) - min(groups['Control']) > 1.0
