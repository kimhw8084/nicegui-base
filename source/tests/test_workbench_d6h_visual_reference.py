from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_d6h_identity_and_reference_explorer_copy_are_current():
    from nicegui_base.workbench.app import WORKBENCH_SUBTITLE, WORKBENCH_TITLE
    from nicegui_base.workbench.update_identity import BUILD_ID

    assert BUILD_ID == 'NGB-20260906-D6H.3'
    assert WORKBENCH_TITLE == 'NiceGUI Base Reference Explorer'
    assert 'Workbench' not in WORKBENCH_TITLE
    assert 'Reference Explorer' in WORKBENCH_SUBTITLE


def test_components_and_patterns_render_only_their_authoritative_entries():
    from nicegui_base.workbench.app import reference_entries_for_section
    from nicegui_base.workbench.models import WorkbenchKind

    components = reference_entries_for_section('components')
    patterns = reference_entries_for_section('patterns')
    assert components and all(entry.kind is WorkbenchKind.COMPONENT for entry in components)
    assert patterns and all(entry.kind is WorkbenchKind.PATTERN for entry in patterns)
    assert not set(entry.key for entry in components) & set(entry.key for entry in patterns)


def test_every_data_driven_visual_reference_has_a_compatible_golden_fixture():
    from nicegui_base.workbench.analytic_specimens import (
        CANONICAL_ANALYTIC_FIXTURES,
        CANONICAL_MEASUREMENT_FIELDS,
        DATA_SURFACES,
    )
    from nicegui_base.workbench.catalog import analytics_entries
    from nicegui_base.workbench.preview_data import numeric_data

    for entry in analytics_entries():
        key = str(entry.metadata['surface_key'])
        assert key in CANONICAL_ANALYTIC_FIXTURES
        if key in DATA_SURFACES:
            field = CANONICAL_MEASUREMENT_FIELDS[key]
            assert numeric_data(CANONICAL_ANALYTIC_FIXTURES[key], field=field) == (
                field,
                tuple(row.get(field) for row in CANONICAL_ANALYTIC_FIXTURES[key]),
            )


def test_visual_reference_uses_semantic_distribution_and_wafer_legends():
    app_source = (ROOT / 'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    integration_source = (ROOT / 'source/nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    assert "ViolinPlot(title" in app_source
    assert "RidgePlot(title" in app_source
    assert 'data-visual-semantic="violin"' in integration_source
    assert 'data-visual-semantic="ridge"' in integration_source
    assert "legend_title='Category'" in app_source
    assert "legend_title='Defect state'" in app_source


def test_recipe_reference_is_immediately_useful_and_full_apps_are_domain_distinct():
    app_source = (ROOT / 'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    assert "_mount_recipe_panel(panel, host)" in app_source
    assert 'Preview mounts on demand.' not in app_source
    assert 'Load sample preview' not in app_source

    from nicegui_base.workbench.full_applications import FULL_APPLICATION_REGISTRY

    assert len({item.primary_surface_key for item in FULL_APPLICATION_REGISTRY.values()}) == len(FULL_APPLICATION_REGISTRY)
    assert len({item.fixture_signature for item in FULL_APPLICATION_REGISTRY.values()}) == len(FULL_APPLICATION_REGISTRY)


def test_diagnostics_does_not_promote_unreviewed_gaps_as_golden_readiness():
    source = (ROOT / 'source/nicegui_base/workbench/coverage_matrix.py').read_text(encoding='utf-8')
    assert 'Human visual review' not in source
    assert 'entries still have at least one source/developer-readiness gap' not in source
