from __future__ import annotations


def test_department_app_needs_have_one_canonical_composition_path():
    from nicegui_base.patterns.composition import APPLICATION_PATTERN_COVERAGE, get_application_pattern

    required = {
        'dashboard', 'monitoring', 'analysis_workspace', 'investigation', 'comparison',
        'master_detail', 'crud', 'settings', 'upload_review', 'report', 'drill_down',
        'full_screen_operations',
    }
    assert required <= {item.key for item in APPLICATION_PATTERN_COVERAGE}
    assert all(get_application_pattern(key).page_pattern for key in required)
    assert all(item.composition_apis for item in APPLICATION_PATTERN_COVERAGE)


def test_composition_facade_uses_existing_governed_authorities():
    from nicegui_base.patterns.composition import COMPOSITION_API_AUTHORITIES

    assert COMPOSITION_API_AUTHORITIES == {
        'shell': 'nicegui_base.integrations.nicegui_layout.AppShell',
        'page_section': 'nicegui_base.patterns.pages.PatternPage.slot',
        'filter_bar': 'nicegui_base.integrations.nicegui_interactions.FilterBar',
        'kpi_strip': 'nicegui_base.integrations.nicegui_content.MetricStrip',
        'chart_table_detail': 'nicegui_base.layouts.Section + registered chart/table',
        'inspector': 'nicegui_base.integrations.nicegui_interactions.InspectorDrawer',
        'state_panel': 'nicegui_base.integrations.nicegui_interactions.StateView',
    }


def test_recipe_workflow_matrix_covers_required_semiconductor_questions():
    from nicegui_base.semiconductor.recipes import recipe_workflow_coverage

    required = {
        'spc_monitoring', 'i_mr', 'ewma_cusum', 'capability_distribution_comparison',
        'chamber_tool_health', 'lot_history', 'yield_defect_review', 'recipe_tool_comparison',
        'fdc_signal_explorer', 'excursion_investigation', 'correlation_parameter_exploration',
        'golden_tool_before_after', 'alarm_event_timeline', 'pm_effectiveness',
    }
    rows = recipe_workflow_coverage()
    assert required <= {item.key for item in rows}
    assert all(item.recipe_key and item.engineering_question and item.required_data for item in rows)
    assert all(item.visualizations and item.patterns and item.alternatives and item.caveats for item in rows)
    assert all(item.runnable_example and item.scaffold_command for item in rows)


def test_recipe_catalog_exposes_questions_contracts_and_scaffold_commands():
    from nicegui_base.semiconductor.recipes import recipe_catalog_entries

    entries = recipe_catalog_entries()
    assert len(entries) >= 8
    assert all(item['engineering_questions'] for item in entries)
    assert all(item['required_data'] for item in entries)
    assert all(item['scaffold_command'].startswith('nicegui-base create ') for item in entries)
    assert all(item['runnable_example'] for item in entries)


def test_full_application_gallery_has_real_pattern_recipe_compositions():
    from nicegui_base.patterns.registry import get_pattern
    from nicegui_base.semiconductor.recipes import get_semiconductor_recipe
    from nicegui_base.workbench.full_applications import FULL_APPLICATION_REGISTRY

    assert len(FULL_APPLICATION_REGISTRY) >= 3
    assert len({item.route for item in FULL_APPLICATION_REGISTRY.values()}) == len(FULL_APPLICATION_REGISTRY)
    for item in FULL_APPLICATION_REGISTRY.values():
        assert get_pattern(item.pattern_key).purpose
        assert get_semiconductor_recipe(item.recipe_key).panels
        assert item.fixture and item.question and item.caveats
        assert item.composition_apis == ('shell', 'page_section', 'filter_bar', 'kpi_strip', 'chart_table_detail', 'inspector', 'state_panel')


def test_full_application_routes_are_registered_without_replacing_recipe_routes():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "ui.page('/applications')(applications_page)" in source
    assert "ui.page('/applications/{application_key}')(full_application_detail_page)" in source
    assert "ui.page('/recipes/{recipe_key}')(recipe_detail_page)" in source
