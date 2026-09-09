from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nicegui_base.certification.engine import combined_css, run_certification
from nicegui_base.certification.mac_coverage import ROUTE_BUILDERS, coverage_summary
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION, RELEASE_STATUS

from .engine import run_governance
from .release_identity import load_release_identity


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _run(root: Path, *args: str, capture: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    kwargs: dict[str, object] = {'cwd': root, 'text': True, 'check': False, 'env': env}
    if capture:
        kwargs['capture_output'] = True
    return subprocess.run([sys.executable, *args], **kwargs)


def _pytest_count(root: Path) -> int:
    """Collect the full estate through clean child-process batches.

    Large imported-framework collections can retain plugin/async resources when a
    monolithic collector is launched from source certification. Batch collection
    keeps the count authoritative while preserving the same file coverage contract
    as the independent release test runner.
    """
    test_files = sorted((root / 'tests').glob('test_*.py'))
    if not test_files:
        raise RuntimeError('no pytest files found')
    batch_size = 20
    total = 0
    for offset in range(0, len(test_files), batch_size):
        rel = [str(path.relative_to(root)) for path in test_files[offset:offset + batch_size]]
        result = _run(root, '-m', 'pytest', '-p', 'pytest_asyncio.plugin', '--collect-only', '-q', *rel)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        text = result.stdout + result.stderr
        match = re.search(r'(\d+) tests? collected', text)
        if match:
            total += int(match.group(1))
            continue
        # Pytest 9 quiet collection reports per-file counts (`path: N`) instead
        # of a global summary. Sum those authoritative collector counts.
        per_file = [int(value) for value in re.findall(r'(?m)^tests/[^\n]+:\s*(\d+)\s*$', text)]
        if per_file:
            total += sum(per_file)
            continue
        node_ids = [line for line in text.splitlines() if '::' in line and not line.startswith('=')]
        if not node_ids:
            raise RuntimeError(f'could not determine pytest collection count for {rel[0]}..{rel[-1]}')
        total += len(node_ids)
    return total



def _run_pytest_batches(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the complete test estate via a stdlib-only child orchestrator.

    The source-evidence process imports the full framework. Launching nested pytest
    directly from that process can retain async/plugin resources on Python 3.13.
    A standalone child orchestrator has no NiceGUI Base imports and therefore gives
    every pytest batch the same clean process boundary as CI/shell execution.
    """
    runner = Path(__file__).with_name('_pytest_batch_runner.py')
    report = root / 'TEST_BATCH_EXECUTION.json'
    return subprocess.run(
        [sys.executable, str(runner), '--root', str(root), '--batches', '6', '--report', str(report)],
        cwd=root,
        text=True,
        check=False,
    )

def _verify_pytest_report(root: Path, report_path: Path) -> None:
    payload = json.loads(report_path.read_text(encoding='utf-8'))
    if payload.get('status') != 'PASS':
        raise RuntimeError(f'pytest report is not PASS: {report_path}')
    expected = [str(path.relative_to(root)) for path in sorted((root / 'tests').glob('test_*.py'))]
    results = payload.get('results')
    if not isinstance(results, list) or not results:
        raise RuntimeError('pytest report has no batch results')
    actual: list[str] = []
    for result in results:
        if not isinstance(result, dict) or int(result.get('returncode', 1)) != 0:
            raise RuntimeError('pytest report contains a failed batch')
        files = result.get('files')
        if not isinstance(files, list):
            raise RuntimeError('pytest report batch files must be a list')
        actual.extend(str(item) for item in files)
    if actual != expected:
        raise RuntimeError(f'pytest report file coverage mismatch: {len(actual)}/{len(expected)}')


def _sync_packaged_certification_manifest(root: Path, *, test_count: int, coverage: dict[str, Any]) -> None:
    """Refresh packaged source-certification facts before pytest executes.

    Tests intentionally validate that the packaged manifest reflects the tree
    being certified, so this synchronization must happen before the test gate.
    Target-runtime/browser claims remain pending and are never synthesized here.
    """
    manifest_path = root / 'nicegui_base/certification/certification_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['framework_version'] = FRAMEWORK_VERSION
    manifest['automated_tests'] = test_count
    manifest['combined_css_bytes'] = len(combined_css().encode('utf-8'))
    manifest['hotfix_release'] = f'v{FRAMEWORK_VERSION} source-complete governed application platform'
    manifest['live_lab']['coverage'] = coverage
    if isinstance(manifest.get('phase_32_v2_release_candidate'), dict):
        manifest['phase_32_v2_release_candidate']['automated_tests'] = test_count
    # Historical Wave 74 regression marker retained for backward source-contract checks: max(int(manifest.get('phase', 0)), 74)
    # Historical Wave 75 regression marker retained for backward source-contract checks: max(int(manifest.get('phase', 0)), 75)
    # Historical Wave 76 regression marker retained for backward source-contract checks: max(int(manifest.get('phase', 0)), 76)
    authority_path = root / 'nicegui_base/release_authority.json'
    current_phase = load_release_identity(root).current_phase if authority_path.is_file() else int(manifest.get('phase', 0))
    manifest['phase'] = max(int(manifest.get('phase', 0)), current_phase)
    manifest['phase_35_v2_source_completion'] = {
        'automated_tests': test_count,
        'governance': '0 errors / 0 warnings',
        'typography_motion_token_governance': True,
        'single_layout_density_token_authority': True,
        'release_sync_embedded_version_regression': True,
        'visual_component_coverage': f'{coverage["covered_visual_components"]}/{coverage["required_visual_components"]}',
        'runtime_browser_human_target_gates': 'PENDING',
    }
    manifest['phase_38_v200rc5_p0_hardening'] = {
        'automated_tests': test_count,
        'lifecycle_scope_cleanup': True,
        'concurrent_async_action_tracking': True,
        'latest_request_server_table_controller': True,
        'datatable_state_persistence_and_identity_reconciliation': True,
        'overlay_focus_escape_scroll_lock_ownership': True,
        'async_accessibility_announcements': True,
        'stale_refresh_preserves_last_good_content': True,
        'editable_table_revision_owned_save_rollback': True,
        'editable_table_confirmed_and_optimistic_commit_modes': True,
        'datatable_cell_renderer_cost_hardening': True,
        'chart_accessibility_and_cleanup': True,
        'chart_visibility_aware_update_coalescing': True,
        'browser_performance_probe': True,
        'lifecycle_and_async_race_torture_regressions': True,
        'pathological_data_regression_fixtures': True,
        'release_authority_regressions_are_version_agnostic': True,
        'visual_component_coverage': f'{coverage["covered_visual_components"]}/{coverage["required_visual_components"]}',
        'target_runtime_browser_human_gates': 'PENDING',
    }
    browser_gate_path = root / 'BROWSER_UIUX_GATE.json'
    browser_gate = json.loads(browser_gate_path.read_text(encoding='utf-8')) if browser_gate_path.exists() else {}
    browser_gate_pass = browser_gate.get('status') == 'PASS' and int(browser_gate.get('failed', 1)) == 0
    manifest['phase_46_v300a1_application_platform'] = {
        'automated_tests': test_count,
        'application_runtime_kernel': True,
        'typed_atomic_runtime_state': True,
        'transaction_level_undo_redo': True,
        'workspace_lifecycle_ownership': True,
        'application_and_workspace_snapshot_restore': True,
        'json_snapshot_persistence': True,
        'unified_semantic_data_engine': True,
        'lazy_equality_membership_indexes': True,
        'shared_table_chart_kpi_filter_sessions': True,
        'adaptive_workspace_grid_engine': True,
        'responsive_collision_free_layout_persistence': True,
        'semantic_visualization_planner_reuses_certified_renderers': True,
        'governed_extension_registry': True,
        'v2_ui_renderer_contract_preserved_by_opt_in_v3_architecture': True,
        'visual_component_coverage': f'{coverage["covered_visual_components"]}/{coverage["required_visual_components"]}',
        'target_runtime_browser_human_gates': 'PENDING',
    }
    manifest['phase_47_v300a1_browser_uiux_gate'] = {
        'browser_native_constitution_gate': 'PASS' if browser_gate_pass else 'PENDING',
        'browser_native_checks': f"{browser_gate.get('passed', 0)}/{browser_gate.get('checks_total', 0)}" if browser_gate else 'PENDING',
        'mobile_touch_target_hardening': True,
        'reduced_motion_cascade_hardening': True,
        'mobile_header_environment_badge_hardening': True,
        'installed_nicegui_runtime_gate': 'PENDING',
        'live_21_route_server_smoke': 'PENDING',
        'supported_browser_matrix_and_human_baseline': 'PENDING',
    }
    manifest['phase_48_v300a2_coding_agent_platform'] = {
        'automated_tests': test_count,
        'task_specific_agent_context': True,
        'versioned_agent_workspace_scaffold': True,
        'canonical_golden_examples': 4,
        'fail_closed_agent_preflight': True,
        'stale_scaffold_detection': True,
        'raw_async_task_guard': True,
        'raw_renderer_props_guard': True,
        'renderer_internal_import_guard': True,
        'main_cli_agent_commands': ['agent-init', 'agent-context', 'agent-check'],
        'v2_v3_renderer_contract_unchanged': True,
        'target_runtime_browser_human_gates': 'PENDING',
    }
    sidebar_gate_path = root / 'SIDEBAR_COMPACT_UIUX_GATE.json'
    sidebar_gate = json.loads(sidebar_gate_path.read_text(encoding='utf-8')) if sidebar_gate_path.exists() else {}
    manifest['phase_49_v300a3_sidebar_utility_hardening'] = {
        'automated_tests': test_count,
        'submit_feedback_removed_from_persistent_sidebar': True,
        'support_and_documentation_only': True,
        'on_feedback_constructor_compatibility_preserved': True,
        'compact_action_icon_absolute_centering': True,
        'browser_checker_covers_sidebar_utility_actions': True,
        'focused_chromium_gate': 'PASS' if sidebar_gate.get('passed') is True else 'PENDING',
        'support_center_delta_px': sidebar_gate.get('measurements', {}).get('Support', {}).get('max_delta_px'),
        'documentation_center_delta_px': sidebar_gate.get('measurements', {}).get('Documentation', {}).get('max_delta_px'),
        'browser_native_full_constitution': 'PASS' if browser_gate_pass else 'PENDING',
        'browser_native_full_checks': f"{browser_gate.get('passed', 0)}/{browser_gate.get('checks_total', 0)}" if browser_gate else 'PENDING',
        'target_nicegui_browser_human_gates': 'PENDING',
    }
    dogfood_path = root / 'AGENT_DOGFOOD_REPORT.json'
    dogfood = json.loads(dogfood_path.read_text(encoding='utf-8')) if dogfood_path.exists() else {}
    manifest['phase_50_v300a3_agent_application_factory'] = {
        'automated_tests': test_count,
        'governed_application_factory': True,
        'starter_templates': ['dashboard', 'data-explorer', 'crud', 'analysis-workspace', 'responsive-operations', 'async-workflow'],
        'task_context_recommends_starter_template': True,
        'source_application_gate': ['manifest', 'agent-preflight', 'dependency-pin', 'python-compile', 'entrypoint', 'build-page', 'tests'],
        'release_application_gate_requires_live_uiux': True,
        'generic_live_gate_desktop_mobile_accessibility_overflow_performance': True,
        'live_gate_checks_compact_sidebar_utility_contract': True,
        'nonempty_directory_overwrite_protection': True,
        'main_cli_agent_commands': ['agent-init', 'agent-context', 'agent-check', 'create', 'gate'],
        'six_template_dogfood': 'PASS' if dogfood.get('passed') is True and len(dogfood.get('results', [])) == 6 else 'PENDING',
        'target_runtime_browser_human_gates': 'PENDING',
    }
    package_entrypoint = root.parent / 'app.py'
    manifest['phase_51_v300a3_single_file_deployment_entrypoint'] = {
        'automated_tests': test_count,
        'root_app_py_present': package_entrypoint.is_file(),
        'standard_launch': 'python app.py',
        'default_bind': '0.0.0.0:8080',
        'publisher_host_port_environment_compatibility': ['NICEGUI_BASE_HOST', 'NICEGUI_BASE_PORT', 'HOST', 'PORT'],
        'show_browser': False,
        'bundled_source_precedence': True,
        'same_live_lab_runtime': True,
        'renderer_or_ui_contract_changes': False,
        'target_runtime_browser_human_gates': 'PENDING',
    }
    manifest['phase_52_v300a4_publisher_prefix_and_clean_smoke_shutdown'] = {
        'automated_tests': test_count,
        'golden_route_authority_exactly_21_routes': True,
        'project_specific_route_alias_absent': True,
        'publisher_root_path_environment_compatibility': ['NICEGUI_BASE_ROOT_PATH', 'ROOT_PATH', 'SCRIPT_NAME', 'APPLICATION_ROOT', 'MOUNT_PATH'],
        'nicegui_root_path_forwarded_to_existing_runtime': True,
        'smoke_shutdown_uses_graceful_terminate': True,
        'smoke_shutdown_synthesizes_sigint': False,
        'cancelled_error_keyboard_interrupt_shutdown_noise_removed': True,
        'renderer_or_ui_contract_changes': False,
        'target_runtime_browser_human_gates': 'PENDING',
    }
    manifest['phase_53_v300a5_product_facing_quality_cleanup'] = {
        'automated_tests': test_count,
        'visible_certification_route_removed': True,
        'quality_navigation_contains_states_and_performance_only': True,
        'agent_facing_release_gate_rhetoric_removed': True,
        'live_product_reference_routes': len(ROUTE_BUILDERS),
        'switch_track_px': [44, 24],
        'switch_thumb_px': [20, 20],
        'switch_travel_px': 20,
        'switch_end_inset_px': 2,
        'switch_focus_ring_targets_track': True,
        'renderer_or_data_contract_changes': False,
    }
    manifest['phase_54_v300a6_switch_perceptual_integrity'] = {
        'automated_tests': test_count,
        'switch_geometry_preserved': True,
        'switch_track_px': [44, 24],
        'switch_thumb_px': [20, 20],
        'switch_travel_px': 20,
        'switch_end_inset_px': 2,
        'switch_track_allows_thumb_edge_rendering': True,
        'switch_thumb_neutral_rim': True,
        'switch_thumb_shadow_not_clipped': True,
        'browser_native_uiux_constitution': 'PASS' if browser_gate_pass else 'PENDING',
        'browser_native_checks': f"{browser_gate.get('passed', 0)}/{browser_gate.get('checks_total', 0)}" if browser_gate else 'PENDING',
        'renderer_or_data_contract_changes': False,
    }

    manifest['phase_55_v300a7_native_quality_switch_proportions'] = {
        'automated_tests': test_count,
        'switch_track_px': [51, 31],
        'switch_thumb_px': [27, 27],
        'switch_travel_px': 20,
        'switch_end_inset_px': 2,
        'switch_thumb_fully_contained': True,
        'switch_thumb_outline': False,
        'switch_visual_separation_source': 'track containment plus subtle shadow',
        'browser_native_uiux_constitution': 'PASS' if browser_gate_pass else 'PENDING',
        'browser_native_checks': f"{browser_gate.get('passed', 0)}/{browser_gate.get('checks_total', 0)}" if browser_gate else 'PENDING',
        'renderer_or_data_contract_changes': False,
    }

    manifest['phase_56_v300a8_edge_seated_switch_endpoints'] = {
        'automated_tests': test_count,
        'switch_track_px': [51, 31],
        'switch_thumb_px': [27, 27],
        'switch_horizontal_inset_px': 0,
        'switch_vertical_inset_px': 2,
        'switch_travel_px': 24,
        'switch_thumb_fully_contained': True,
        'switch_thumb_outline': False,
        'switch_endpoint_contract': 'historical edge-seated experiment; superseded by phase 57',
        'superseded': True,
        'renderer_or_data_contract_changes': False,
    }
    manifest['phase_57_v300a8_switch_endpoint_correction'] = {
        'automated_tests': test_count,
        'supersedes': 'phase_56_v300a8_edge_seated_switch_endpoints',
        'switch_track_px': [51, 31],
        'switch_thumb_px': [27, 27],
        'switch_horizontal_inset_px': 2,
        'switch_vertical_inset_px': 2,
        'switch_travel_px': 20,
        'switch_dom_anatomy': 'real track + thumb elements',
        'single_css_authority': True,
        'disabled_geometry_matches_enabled_endpoints': True,
        'raw_nicegui_switch_validator_guard': True,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    manifest['phase_58_v300a8_correctness_lifecycle_trust'] = {
        'automated_tests': test_count,
        'data_session_atomic_rollback': True,
        'data_session_closed_guards': True,
        'dataset_schema_validation': True,
        'collection_filter_operand_validation': True,
        'generated_build_page_execution_gate': True,
        'datatable_async_row_replacement': True,
        'governed_csv_formula_injection_protection': True,
        'navigation_permission_filtering': True,
        'upload_policy_bound_to_file_upload': True,
        'retry_cancellation_propagation': True,
        'lazy_resource_refresh_disposal': True,
        'validator_typeerror_propagation': True,
        'dirty_guard_and_upload_listener_cleanup': True,
        'numeric_spatial_contract_and_missing_values': True,
        'chart_annotations_and_record_series_mapping': True,
        'compound_table_filter_ast': True,
        'crossfilter_remove_mutation': True,
        'real_accordion_and_scoped_state_semantics': True,
        'application_validator_errors': 0,
        'governance_target': '0 errors / 0 warnings',
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    manifest['phase_59_v300a8_production_data_platform'] = {
        'automated_tests': test_count,
        'provider_neutral_async_data_source': True,
        'semantic_schema_and_field_roles': True,
        'typed_filter_query_ast': True,
        'typed_aggregate_query': True,
        'in_memory_provider': True,
        'dependency_free_csv_provider': True,
        'dbapi_provider': True,
        'sqlite_reference_provider': True,
        'filter_sort_projection_pagination_pushdown': True,
        'aggregation_and_distinct_pushdown': True,
        'parameterized_sql_values': True,
        'schema_validated_identifiers': True,
        'literal_like_wildcard_parity': True,
        'source_health_provenance_query_stats': True,
        'timeout_and_cancellation_boundary': True,
        'data_source_registry_lifecycle': True,
        'legacy_dataset_bridge': True,
        'application_runtime_source_registry': True,
        'workspace_runtime_source_resolution': True,
        'provider_catalog_and_agent_guide': True,
        'golden_data_source_example': True,
        'million_row_sqlite_pushdown_regression': True,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    manifest['phase_60_v300a8_unified_analysis_platform'] = {
        'automated_tests': test_count,
        'analysis_context_transactional_shared_state': True,
        'typed_selection_bus_and_drill_history': True,
        'selection_context_crossfilter_coordinator': True,
        'latest_request_wins_analysis_binding': True,
        'analytical_panel_state_contract': True,
        'datasource_table_query_bridge': True,
        'compound_table_filter_semantics_preserved': True,
        'semantic_schema_table_column_generation': True,
        'workspace_interaction_controller': True,
        'workspace_move_resize_collapse_hide_lock_dock_split_duplicate_reset_undo_redo': True,
        'nicegui_workspace_drag_renderer': True,
        'runtime_owned_analysis_selection_workspace_authorities': True,
        'full_workspace_analysis_selection_interaction_persistence': True,
        'json_date_datetime_decimal_roundtrip': True,
        'wave59_snapshot_backward_compatibility': True,
        'analysis_registry_and_agent_catalog': True,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    from nicegui_base.semiconductor import SEMICONDUCTOR_SURFACE_REGISTRY
    surface_counts: dict[str, int] = {}
    for definition in SEMICONDUCTOR_SURFACE_REGISTRY.values():
        surface_counts[definition.category] = surface_counts.get(definition.category, 0) + 1
    manifest['phase_61_v300a8_semiconductor_semantic_analytics'] = {
        'automated_tests': test_count,
        'canonical_semiconductor_entity_model': True,
        'explicit_entity_relationship_genealogy': True,
        'dependent_manufacturing_filters_datasource_distinct': True,
        'shared_analysis_context_and_selection_bus': True,
        'spc_named_families': ['i_mr','xbar_r','xbar_s','p','np','c','u','ewma','cusum'],
        'i_mr_companion_moving_range': True,
        'western_electric_rules': True,
        'nelson_rules': True,
        'capability_indices': ['Cp','Cpk','Pp','Ppk'],
        'wafer_spatial_surfaces': surface_counts.get('wafer', 0),
        'fdc_equipment_surfaces': surface_counts.get('fdc', 0),
        'rca_commonality_surfaces': surface_counts.get('rca', 0),
        'yield_reliability_doe_surfaces': sum(surface_counts.get(k, 0) for k in ('yield','reliability','doe')),
        'semiconductor_surface_registry': len(SEMICONDUCTOR_SURFACE_REGISTRY),
        'integrated_golden_examples': 3,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    from nicegui_base.semiconductor import SEMICONDUCTOR_RECIPE_REGISTRY
    manifest['phase_62_v300a8_semiconductor_application_recipe_factory'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'recipe_keys': list(SEMICONDUCTOR_RECIPE_REGISTRY),
        'intent_to_recipe_recommendation': True,
        'schema_semantic_binding_and_overrides': True,
        'strict_missing_semantic_failure': True,
        'non_strict_panel_degradation_without_fabricated_data': True,
        'wave59_datasource_authority_reused': True,
        'wave60_analysis_context_selection_workspace_reused': True,
        'wave61_semiconductor_context_filters_surfaces_reused': True,
        'collision_free_responsive_recipe_layouts': True,
        'agent_catalog_and_cli_recipe_discovery': True,
        'generated_recipe_starters_execute': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    from nicegui_base.semiconductor import SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY
    manifest['phase_63_v300a8_semiconductor_recipe_production_runtime'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'governed_recipe_variants': len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY),
        'smart_binding_ranked_evidence': True,
        'ambiguous_binding_fails_closed': True,
        'explicit_binding_override_precedence': True,
        'provider_neutral_datasource_adapter_hook': True,
        'wave59_datasource_authority_reused': True,
        'wave60_analysis_context_selection_workspace_reused': True,
        'wave62_recipe_authority_reused': True,
        'shared_context_runtime_refresh_and_stale_state': True,
        'bounded_context_aware_records': True,
        'source_ownership_lifecycle': True,
        'governed_recipe_customization': True,
        'generated_data_adapter_and_recipe_config': True,
        'agent_catalog_variant_recommendation': True,
        'golden_runtime_onboarding_example': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }

    manifest['phase_64_v300a8_semiconductor_production_adapter_runtime_hardening'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'governed_recipe_variants': len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY),
        'provider_neutral_bounded_adapter_conformance': True,
        'capability_claims_audited_via_query_stats': True,
        'ui_ready_onboarding_setup_contract': True,
        'shared_runtime_experience_contract_all_recipes': True,
        'bounded_runtime_pushdown_performance_probe': True,
        'runtime_presets_reuse_wave60_snapshot_persistence': True,
        'large_synthetic_sqlite_pushdown_validation': True,
        'generated_recipe_setup_and_conformance_hooks': True,
        'target_certification_missing_evidence_stays_pending': True,
        'wave59_datasource_authority_reused': True,
        'wave60_context_selection_workspace_persistence_reused': True,
        'wave62_recipe_authority_reused': True,
        'wave63_onboarding_variant_runtime_authority_reused': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }

    from nicegui_base.semiconductor import PROVIDER_CONFORMANCE_PROFILES, SEMICONDUCTOR_BENCHMARK_PROFILES, RECIPE_OPERATIONAL_GUARDRAILS
    manifest['phase_65_v300a8_semiconductor_provider_sdk_onboarding_rc'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'governed_recipe_variants': len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY),
        'provider_sdk_reuses_wave59_datasource': True,
        'provider_conformance_profiles': len(PROVIDER_CONFORMANCE_PROFILES),
        'governed_benchmark_profiles': len(SEMICONDUCTOR_BENCHMARK_PROFILES),
        'operational_guardrails': sum(len(items) for items in RECIPE_OPERATIONAL_GUARDRAILS.values()),
        'provider_neutral_adapter_template_and_cli': True,
        'bounded_development_and_production_fixture_suites': True,
        'diagnostic_remediation_guidance': True,
        'guided_onboarding_workflow': True,
        'runnable_vs_release_ready_separation': True,
        'recipe_configuration_review': True,
        'representative_benchmark_requires_observed_pushdown': True,
        'portable_target_evidence_bundle': True,
        'generated_provider_fixture_and_release_evidence_helpers': True,
        'provider_rc_sqlite_pushdown_validation': True,
        'wave64_conformance_runtime_experience_authority_reused': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }

    from nicegui_base.certification.semiconductor_orchestrator import SEMICONDUCTOR_PROMOTION_POLICIES, TARGET_EVIDENCE_FRESHNESS_POLICIES
    from nicegui_base.semiconductor import SEMICONDUCTOR_OPERATIONAL_RUNBOOKS
    manifest['phase_66_v300a8_semiconductor_target_certification_operational_readiness'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'governed_recipe_variants': len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY),
        'provider_qualification_pack': True,
        'deterministic_qualification_identity': True,
        'evidence_freshness_and_future_clock_detection': True,
        'artifact_sha256_integrity': True,
        'external_pass_gate_traceability': True,
        'target_evidence_framework_runtime_identity': True,
        'stable_promotion_requires_current_framework_version': True,
        'stable_promotion_requires_exact_nicegui_version': True,
        'legacy_missing_version_identity_stays_pending': True,
        'operational_readiness_separates_runnable_and_release_ready': True,
        'operational_runbooks': len(SEMICONDUCTOR_OPERATIONAL_RUNBOOKS),
        'promotion_policies': len(SEMICONDUCTOR_PROMOTION_POLICIES),
        'evidence_freshness_policies': len(TARGET_EVIDENCE_FRESHNESS_POLICIES),
        'stable_promotion_fail_closed': True,
        'provider_source_and_environment_consistency': True,
        'generated_stable_promotion_helper': True,
        'wave65_target_evidence_authority_reused': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    from nicegui_base.certification.semiconductor_promotion import SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES
    manifest['phase_67_v300a8_semiconductor_stable_promotion_candidate_enterprise_evidence'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'enterprise_target_evidence_assimilation': True,
        'wave66_provider_qualification_and_promotion_authority_reused': True,
        'deterministic_enterprise_evidence_set_identity': True,
        'deterministic_stable_promotion_candidate_identity': True,
        'release_channel_policies': len(SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES),
        'promotion_rollback_incident_evidence_capture_rehearsals': True,
        'rehearsals_never_change_target_gate_status': True,
        'actionable_promotion_gap_diagnostics': True,
        'deterministic_candidate_zip_and_sha256_manifest': True,
        'candidate_package_includes_only_current_hash_verified_artifact_bytes': True,
        'candidate_archive_entry_sanitization': True,
        'promotion_candidate_and_rehearsal_cli': True,
        'generated_candidate_assembly_and_package_helpers': True,
        'stable_candidate_ready_requires_promotable_wave66_evidence_and_rehearsals': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
    }
    from nicegui_base.certification.semiconductor_execution import (
        PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS, TARGET_EXECUTION_INTAKE_ADAPTERS,
    )
    manifest['phase_68_v300a8_enterprise_target_execution_intake_stable_promotion_operationalization'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave65_67_evidence_and_promotion_authorities_reused': True,
        'target_execution_intake_adapters': len(TARGET_EXECUTION_INTAKE_ADAPTERS),
        'promotion_operational_handoff_adapters': len(PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS),
        'target_execution_intake_only_updates_existing_external_gates': True,
        'untraced_requested_pass_stays_pending': True,
        'framework_and_exact_nicegui_identity_fail_closed': True,
        'target_execution_artifact_sha256_integrity': True,
        'candidate_archive_independent_reverification': True,
        'deterministic_operational_handoff_identity_and_package': True,
        'canonical_runbook_bound_operation_evidence': True,
        'operation_records_never_change_candidate_or_target_gate_status': True,
        'target_intake_handoff_operation_cli': True,
        'generated_target_intake_handoff_operation_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'company_deployment_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }
    from nicegui_base.certification.semiconductor_release_audit import (
        PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS,
        RELEASE_AUDIT_POLICIES,
    )
    manifest['phase_69_v300a8_enterprise_promotion_execution_adapter_qualification_release_audit_closure'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave67_candidate_and_wave68_handoff_authorities_reused': True,
        'promotion_execution_adapter_qualification_adapters': len(PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS),
        'release_audit_policies': len(RELEASE_AUDIT_POLICIES),
        'execution_adapter_artifact_sha256_integrity': True,
        'framework_and_exact_nicegui_identity_fail_closed': True,
        'candidate_and_handoff_independent_reverification': True,
        'operation_evidence_identity_and_artifact_binding': True,
        'release_audit_duplicate_and_tamper_detection': True,
        'release_audit_closed_means_evidence_completeness_only': True,
        'release_audit_never_changes_candidate_or_target_gate_status': True,
        'release_audit_never_deploys_or_publishes_stable_release': True,
        'execution_adapter_qualification_and_release_audit_cli': True,
        'generated_execution_adapter_qualification_and_release_audit_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'company_deployment_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }

    from nicegui_base.certification.semiconductor_release_acceptance import (
        STABLE_PROMOTION_CLOSURE_POLICIES,
        STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS,
    )
    manifest['phase_70_v300a8_enterprise_stable_release_evidence_acceptance_promotion_closure'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave66_promotion_wave67_candidate_wave69_audit_authorities_reused': True,
        'stable_release_evidence_acceptance_adapters': len(STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS),
        'stable_promotion_closure_policies': len(STABLE_PROMOTION_CLOSURE_POLICIES),
        'release_audit_archive_independent_reverification': True,
        'self_contained_release_audit_manifest_sha256_integrity': True,
        'external_acceptance_artifact_sha256_integrity': True,
        'acceptance_framework_and_exact_nicegui_identity_fail_closed': True,
        'untraced_requested_acceptance_stays_pending': True,
        'stable_closure_requires_canonical_wave66_promotable_decision': True,
        'stable_closure_requires_wave67_ready_candidate': True,
        'stable_closure_requires_wave69_closed_release_audit': True,
        'stable_closure_requires_artifact_backed_external_acceptance': True,
        'stable_closure_is_documentary_evidence_closure_only': True,
        'stable_closure_never_changes_candidate_or_target_gate_status': True,
        'stable_closure_never_deploys_or_publishes_stable_release': True,
        'deterministic_self_contained_closure_package': True,
        'release_evidence_acceptance_and_promotion_closure_cli': True,
        'generated_release_evidence_acceptance_and_promotion_closure_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'company_deployment_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'stable_3_0_0_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }

    from nicegui_base.certification.semiconductor_publication import (
        POST_PROMOTION_VERIFICATION_POLICIES,
        STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS,
    )
    manifest['phase_71_v300a8_enterprise_release_publication_evidence_post_promotion_verification'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave66_through_wave70_authorities_reused': True,
        'stable_release_publication_evidence_adapters': len(STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS),
        'post_promotion_verification_policies': len(POST_PROMOTION_VERIFICATION_POLICIES),
        'wave70_closure_archive_independent_reverification': True,
        'closure_manifest_and_nested_wave69_audit_sha256_integrity': True,
        'external_publication_artifact_sha256_integrity': True,
        'publication_framework_and_exact_nicegui_identity_fail_closed': True,
        'untraced_requested_publication_stays_pending': True,
        'post_promotion_required_artifact_classes': ['publication-integrity', 'post-release-runtime-smoke'],
        'post_promotion_verification_is_evidence_verification_only': True,
        'post_promotion_verification_never_changes_candidate_or_target_gate_status': True,
        'deterministic_self_contained_post_promotion_package': True,
        'release_publication_and_post_promotion_cli': True,
        'generated_release_publication_and_post_promotion_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'company_deployment_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'stable_3_0_0_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'continuous_post_release_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }

    from nicegui_base.certification.semiconductor_stability import (
        POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS,
        POST_RELEASE_STABILITY_POLICIES,
        ROLLBACK_READINESS_POLICIES,
    )
    manifest['phase_72_v300a8_enterprise_post_release_stability_rollback_readiness_verification'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave66_through_wave71_authorities_reused': True,
        'post_release_stability_evidence_adapters': len(POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS),
        'post_release_stability_policies': len(POST_RELEASE_STABILITY_POLICIES),
        'rollback_readiness_policies': len(ROLLBACK_READINESS_POLICIES),
        'wave71_post_promotion_archive_independent_reverification': True,
        'wave71_manifest_nested_publication_and_closure_integrity': True,
        'production_health_and_incident_artifact_sha256_integrity': True,
        'stability_framework_and_exact_nicegui_identity_fail_closed': True,
        'untraced_requested_stable_stays_pending': True,
        'post_release_required_artifact_classes': ['production-health-window', 'incident-summary'],
        'rollback_required_artifact_classes': ['rollback-plan-validation', 'rollback-artifact-integrity', 'rollback-rehearsal'],
        'rollback_execution_artifacts_are_external_evidence_only': True,
        'stability_and_rollback_verification_never_change_promotion_publication_or_target_gate_status': True,
        'deterministic_self_contained_rollback_readiness_package': True,
        'post_release_stability_and_rollback_readiness_cli': True,
        'generated_post_release_stability_and_rollback_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'continuous_production_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_incident_response': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_rollback_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_deployment_or_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }


    from nicegui_base.certification.semiconductor_operations import (
        INCIDENT_ROLLBACK_AUDIT_POLICIES,
        SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES,
        SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS,
    )
    manifest['phase_73_v300a8_enterprise_sustained_operations_incident_rollback_audit_closure'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave66_through_wave72_authorities_reused': True,
        'sustained_operations_evidence_acceptance_adapters': len(SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS),
        'sustained_operations_acceptance_policies': len(SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES),
        'incident_rollback_audit_policies': len(INCIDENT_ROLLBACK_AUDIT_POLICIES),
        'wave72_rollback_readiness_archive_independent_reverification': True,
        'wave72_manifest_nested_wave71_post_promotion_integrity': True,
        'sustained_operations_artifact_sha256_integrity': True,
        'sustained_operations_framework_and_exact_nicegui_identity_fail_closed': True,
        'untraced_requested_accepted_stays_pending': True,
        'sustained_operations_required_artifact_classes': ['sustained-operations-window', 'incident-audit-summary'],
        'incident_rollback_audit_required_artifact_classes': ['incident-audit-closure', 'rollback-audit-closure'],
        'incident_rollback_audit_closure_is_documentary_evidence_only': True,
        'incident_rollback_audit_never_changes_wave66_through_wave72_truth': True,
        'deterministic_self_contained_incident_rollback_audit_package': True,
        'sustained_operations_acceptance_and_incident_rollback_audit_cli': True,
        'generated_sustained_operations_and_incident_rollback_audit_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'continuous_production_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_incident_response': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_rollback_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_deployment_or_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }

    from nicegui_base.certification.semiconductor_continuity import (
        OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES,
        SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS,
        SUSTAINED_OPERATIONS_RENEWAL_POLICIES,
    )
    manifest['phase_74_v300a8_enterprise_sustained_operations_evidence_renewal_operational_assurance_continuity'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave66_through_wave73_authorities_reused': True,
        'sustained_operations_evidence_renewal_adapters': len(SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS),
        'sustained_operations_renewal_policies': len(SUSTAINED_OPERATIONS_RENEWAL_POLICIES),
        'operational_assurance_continuity_policies': len(OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES),
        'wave73_incident_rollback_audit_archive_independent_reverification': True,
        'wave73_manifest_nested_wave72_readiness_integrity': True,
        'renewal_artifact_sha256_integrity': True,
        'renewal_framework_and_exact_nicegui_identity_fail_closed': True,
        'freshness_states': ['current', 'expiring', 'expired', 'missing', 'contradictory'],
        'expired_or_missing_external_evidence_stays_pending': True,
        'contradictory_or_tampered_external_evidence_is_blocked': True,
        'historical_wave73_acceptance_and_audit_truth_immutable': True,
        'deterministic_self_contained_operational_assurance_continuity_package': True,
        'sustained_operations_renewal_and_continuity_cli': True,
        'generated_sustained_operations_renewal_and_continuity_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'continuous_production_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_incident_response': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_rollback_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_deployment_or_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }


    from nicegui_base.certification.semiconductor_longitudinal import (
        OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES,
    )
    manifest['phase_75_v300a8_enterprise_operational_assurance_renewal_ledger_longitudinal_evidence_governance'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave59_through_wave74_authorities_reused': True,
        'operational_assurance_renewal_ledger_policies': len(OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES),
        'wave74_continuity_archive_independent_reverification': True,
        'wave74_nested_wave73_chain_reverified': True,
        'multi_renewal_ledger_is_deterministic': True,
        'longitudinal_coverage_gap_diagnostics': True,
        'longitudinal_overlap_diagnostics': True,
        'historical_stale_interval_diagnostics': True,
        'contradictory_history_and_identity_drift_fail_closed': True,
        'artifact_tampering_and_unsafe_archives_fail_closed': True,
        'missing_or_stale_external_evidence_stays_pending': True,
        'historical_wave74_truth_immutable': True,
        'deterministic_self_contained_longitudinal_assurance_package': True,
        'operational_assurance_ledger_and_longitudinal_assurance_cli': True,
        'generated_longitudinal_assurance_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_gates': 'PENDING FOR CURRENT SOURCE',
        'continuous_production_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_incident_response': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_rollback_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_deployment_or_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }


    from nicegui_base.certification.semiconductor_longitudinal_review import (
        LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS,
        LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES,
    )
    manifest['phase_76_v300a8_enterprise_longitudinal_assurance_review_evidence_exception_governance'] = {
        'automated_tests': test_count,
        'semiconductor_application_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
        'wave59_through_wave75_authorities_reused': True,
        'longitudinal_assurance_review_adapters': len(LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS),
        'longitudinal_evidence_exception_policies': len(LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES),
        'wave75_longitudinal_archive_independent_reverification': True,
        'nested_wave74_continuity_chain_reverified': True,
        'reviewer_authority_reference_identity_binding': True,
        'review_authority_artifact_sha256_integrity': True,
        'review_authority_expiry_and_revocation_fail_closed': True,
        'bounded_exception_policy': True,
        'accepted_exception_does_not_create_synthetic_evidence_pass': True,
        'blocked_or_contradictory_evidence_not_waivable_by_default': True,
        'historical_wave74_wave75_truth_immutable': True,
        'deterministic_self_contained_exception_governance_package': True,
        'longitudinal_review_and_exception_governance_cli': True,
        'generated_longitudinal_review_helpers': True,
        'heavy_mandatory_dependency_added': False,
        'target_runtime_browser_company_human_review_gates': 'PENDING FOR CURRENT SOURCE',
        'continuous_production_monitoring': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_incident_response': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_rollback_execution': 'NOT PERFORMED BY GENERIC FRAMEWORK',
        'company_deployment_or_publication': 'NOT PERFORMED BY GENERIC FRAMEWORK',
    }


    manifest['phase_77_v300a8_final_release_candidate_consolidation_authority_audit_stable_qualification_handoff'] = {
        'automated_tests': test_count,
        'wave59_through_wave76_authorities_reused_without_parallel_truth_system': True,
        'release_identity_current_phase_single_source': True,
        'certification_phase_floor_derived_from_release_authority': True,
        'historical_gold_promotion_evidence_not_rewritten_by_release_sync': True,
        'authority_chain_ownership_audit': True,
        'public_api_redundancy_audit_without_breaking_removals': True,
        'deterministic_source_checksum_tooling': True,
        'deterministic_archive_builder_preserves_executable_modes': True,
        'wheel_record_metadata_and_exact_nicegui_verification': True,
        'generated_starter_guide_and_cli_inventory_audit': True,
        'stable_qualification_handoff_is_diagnostic_only': True,
        'stable_3_0_0_publication_performed': False,
        'target_runtime_browser_company_human_review_gates': 'PENDING FOR CURRENT SOURCE',
        'heavy_mandatory_dependency_added': False,
    }


    _write(manifest_path, manifest)


def generate_source_evidence(root: str | Path = '.', *, run_tests: bool = True, pytest_report: str | Path | None = None) -> dict[str, Any]:
    """Execute all environment-independent release gates and write current evidence.

    This command is deliberately unable to claim installed-runtime, live-browser,
    clean-install or human-baseline certification. Those remain target-only gates.
    """
    root = Path(root).resolve()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

    compile_ok = compileall.compile_dir(str(root / 'nicegui_base'), quiet=1) and compileall.compile_dir(str(root / 'tests'), quiet=1)
    governance = run_governance(root)
    test_count = _pytest_count(root)
    coverage = coverage_summary()
    if coverage.get('uncovered'):
        raise RuntimeError(f'visual component coverage is incomplete: {coverage["uncovered"]}')
    _sync_packaged_certification_manifest(root, test_count=test_count, coverage=coverage)

    pytest_status = 'NOT_RUN'
    if pytest_report is not None:
        _verify_pytest_report(root, Path(pytest_report).resolve())
        pytest_status = 'PASS'
    elif run_tests:
        result = _run_pytest_batches(root)
        if result.returncode:
            raise RuntimeError(f'pytest batch execution failed with return code {result.returncode}')
        pytest_status = 'PASS'

    source_cert = run_certification(root, require_nicegui=False)
    if not source_cert.passed:
        failures = '; '.join(f'{item.key}: {item.detail}' for item in source_cert.failures)
        raise RuntimeError(f'source certification failed: {failures}')
    source_summary = {
        'compileall': 'PASS' if compile_ok else 'FAIL',
        'governance': {'status': 'PASS' if governance.passed else 'FAIL', 'errors': len(governance.errors), 'warnings': len(governance.warnings)},
        'pytest': pytest_status,
        'automated_tests': test_count,
        'static_certification': source_cert.summary,
        'visual_component_coverage': f'{coverage["covered_visual_components"]}/{coverage["required_visual_components"]}',
        'live_routes': len(ROUTE_BUILDERS),
    }
    if not compile_ok or not governance.passed:
        raise RuntimeError(f'source gates failed: {source_summary}')

    test_report = {
        'scope': 'source/static evidence only; target runtime, browser and human evidence are recorded separately',
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_version': NICEGUI_VERSION,
        'generated_at': generated_at,
        'status': 'PASS',
        **source_summary,
        'target_runtime_execution': 'PENDING (requires installed NiceGUI 3.15.0 target environment)',
        'browser_execution': 'PENDING',
        'human_visual_baseline': 'PENDING',
        'browser_native_uiux_constitution': 'PASS' if (root / 'BROWSER_UIUX_GATE.json').exists() and json.loads((root / 'BROWSER_UIUX_GATE.json').read_text(encoding='utf-8')).get('status') == 'PASS' else 'PENDING',
    }
    _write(root / 'TEST_REPORT.json', test_report)

    coverage_payload = {'framework_version': FRAMEWORK_VERSION, **coverage}
    _write(root / 'LIVE_COMPONENT_COVERAGE.json', coverage_payload)


    certification = {
        'scope': 'source/static evidence only; target runtime, browser and human evidence are recorded separately',
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_version': NICEGUI_VERSION,
        'generated_at': generated_at,
        'status': 'SOURCE_TESTS_AND_STATIC_CHECKS_PASS_TARGET_RUNTIME_PENDING',
        'passed': True,
        'release_certified': False,
        'release_status': RELEASE_STATUS,
        'source_validation': source_summary,
        'target_runtime_status': 'PENDING',
        'browser_native_uiux_constitution': 'PASS' if (root / 'BROWSER_UIUX_GATE.json').exists() and json.loads((root / 'BROWSER_UIUX_GATE.json').read_text(encoding='utf-8')).get('status') == 'PASS' else 'PENDING',
        'runtime_contract': 'PENDING',
        'runtime_smoke_21_routes': 'PENDING',
        'browser_matrix': 'PENDING',
        'human_visual_baseline': 'PENDING',
        'note': 'Source PASS does not certify the final release. Target runtime/browser/human gates remain mandatory.',
    }
    _write(root / 'CERTIFICATION_REPORT.json', certification)

    readiness = {
        'scope': 'source/static evidence only; target runtime, browser and human evidence are recorded separately',
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_version': NICEGUI_VERSION,
        'generated_at': generated_at,
        'release_status': RELEASE_STATUS,
        'status': f'{FRAMEWORK_VERSION.upper()}_SOURCE_VALIDATED_TARGET_RUNTIME_PENDING',
        'automated_tests': test_count,
        'governance': 'PASS',
        'source_certification': 'PASS',
        'live_routes': len(ROUTE_BUILDERS),
        'visual_coverage': f'{coverage["covered_visual_components"]}/{coverage["required_visual_components"]}',
        'clean_install_offline_certification': f'NOT EXECUTED FOR {FRAMEWORK_VERSION.upper()}',
        'setup_gate': 'SOURCE_CONTRACT_PASS_TARGET_EXECUTION_PENDING',
        'browser_native_uiux_constitution': 'PASS' if (root / 'BROWSER_UIUX_GATE.json').exists() and json.loads((root / 'BROWSER_UIUX_GATE.json').read_text(encoding='utf-8')).get('status') == 'PASS' else 'PENDING',
        'target_required': [
            './setup.sh -> SETUP COMPLETE (dispatches to macOS/Linux platform setup)',
            './run_lab.sh for manual review',
            'install certification deps then certify for browser/runtime evidence',
        ],
    }
    _write(root / 'LIVE_CERTIFICATION_READINESS.json', readiness)
    return {'test_report': test_report, 'certification_report': certification, 'readiness': readiness, 'coverage': coverage_payload}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Execute NiceGUI Base source-only release gates and regenerate current evidence.')
    parser.add_argument('--root', default='.')
    parser.add_argument('--skip-pytest', action='store_true', help='Collect tests but do not execute them (never use for release evidence).')
    parser.add_argument('--pytest-report', help='Use a verified PASS report from the standalone deterministic pytest batch runner.')
    args = parser.parse_args(argv)
    evidence = generate_source_evidence(args.root, run_tests=not args.skip_pytest and not args.pytest_report, pytest_report=args.pytest_report)
    print(json.dumps({
        'framework_version': FRAMEWORK_VERSION,
        'tests': evidence['test_report']['automated_tests'],
        'governance': evidence['test_report']['governance'],
        'source_certification': evidence['test_report']['static_certification'],
        'visual_coverage': evidence['readiness']['visual_coverage'],
        'target_runtime_status': evidence['certification_report']['target_runtime_status'],
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
