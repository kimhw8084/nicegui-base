from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .generated_smoke import GeneratedSmokeReport, smoke_generated_zip, validate_public_call_signatures

_PATTERN_PAGE = {
    'dashboard': 'DashboardPage',
    'data_explorer': 'DataExplorerPage',
    'master_detail': 'MasterDetailPage',
    'crud': 'CrudPage',
    'monitoring': 'MonitoringPage',
    'search': 'SearchPage',
    'settings': 'SettingsPage',
    'wizard': 'WizardPage',
    'comparison': 'ComparisonPage',
    'analysis_workspace': 'AnalysisWorkspacePage',
}

_PATTERN_TEMPLATE = {
    'dashboard': 'dashboard',
    'data_explorer': 'data-explorer',
    'crud': 'crud',
    'monitoring': 'dashboard',
    'master_detail': 'analysis-workspace',
    'search': 'data-explorer',
    'settings': 'analysis-workspace',
    'wizard': 'analysis-workspace',
    'comparison': 'analysis-workspace',
    'analysis_workspace': 'analysis-workspace',
}


def _entry_kind(entry) -> str:
    return getattr(getattr(entry, 'kind', None), 'value', str(getattr(entry, 'kind', '')))


_COMPOSABLE_REFERENCE_KEYS = {
    'tables': frozenset({'data_table'}),
    'visualizations': frozenset({'LineChart', 'AreaChart', 'BarChart', 'StackedBarChart', 'BoxPlot'}),
}
_COMPOSABLE_RENDER_KEYS = frozenset({
    'metric_card', 'metric_strip', 'status_badge', 'badge',
    'alert', 'search_input', 'select', 'text_input', 'button', 'action_button',
})


def is_composable_entry(entry) -> bool:
    from .catalog_runtime import describe_entry
    info = describe_entry(entry)
    return info['runnable'] and info['mode'] not in {'pattern'}


def _safe_title(value: Any) -> str:
    return str(value or 'Capability').replace('\n', ' ').strip()[:100]


def _render_entry_lines(entry, indent: str, configuration=None, *, density: str = 'compact') -> list[str]:
    from .studio_state import normalize_configuration
    cfg = normalize_configuration(configuration, title=entry.title)
    options = {'density': cfg['density'] if configuration else density, **cfg['options']}
    # Preserve the same renderer, options and data source through composition.
    # Tables still use a bounded provider query; other page-owned data slots retain
    # the existing paged DataSourceTable adapter.
    encoded = json.dumps(options, ensure_ascii=False, allow_nan=False)
    return [
        f"{indent}render_provider_capability({entry.key!r}, SOURCE, CONTEXT, title={cfg['title']!r}, "
        f"options=json.loads({encoded!r}), schema=DATA_SCHEMA, measurement_field=MEASUREMENT_FIELD, "
        f"category_field=CATEGORY_FIELD, filter_state=FILTER_STATE)"
    ]


def project_home_code(project: Mapping[str, Any], lookup: Mapping[str, Any]) -> str:
    pattern_key = str(project.get('pattern_key') or 'analysis_workspace')
    page_class = _PATTERN_PAGE.get(pattern_key, 'AnalysisWorkspacePage')
    from nicegui_base.patterns.registry import get_pattern
    definition = get_pattern(pattern_key)
    required = {slot.value for slot in definition.required_slots if slot.value != 'header'}
    allowed = [slot.value for slot in definition.slot_order if slot.value != 'header']
    placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    navigation = project.get('navigation') if isinstance(project.get('navigation'), (list, tuple)) else ()
    from .interaction_contract import action_specs_for_pattern
    workflow_actions = action_specs_for_pattern(pattern_key)
    workflow_slot = next((slot for slot in ('actions','toolbar','filters','controls','primary','data') if slot in allowed), allowed[0] if allowed else None)
    workflow_route = str(project.get('active_route') or '/')
    imports = (
        'ActionButton, Alert, AnalysisContext, AppShell, AreaChart, AxisSpec, AxisType, BarChart, BoxPlot, Button, DataSourceTable, LayoutSlot, LineChart, '
        'MetricCard, MetricStrip, NavigationModel, NavItem, NavSection, SearchInput, Select, SelectionBus, SemiconductorAnalyticalPanel, SeriesSpec, StackedBarChart, '
        'StatusBadge, TableColumn, TextInput'
    )
    lines = [
        'from __future__ import annotations',
        'import json',
        f'from nicegui_base import {page_class}, {imports}',
        '',
        'from services.app_data import DATA_SCHEMA, DATA_TABLE_SPEC, ROW_KEY, SOURCE, MEASUREMENT_FIELD, CATEGORY_FIELD, series_labels, series_values',
        'from nicegui_base.workbench.provider_preview import render_provider_capability',
        'from services.app_workflow import create_page_workflow',
        '',

    ]
    if navigation:
        lines.extend(['', 'NAVIGATION = NavigationModel((', "    NavSection('application', None, ("])
        seen_ids: set[str] = set()
        for item in navigation:
            if not isinstance(item, Mapping):
                continue
            item_id = str(item.get('id') or '').strip()
            label = _safe_title(item.get('label'))
            route = str(item.get('route') or '').strip()
            if not item_id or item_id in seen_ids or not route.startswith('/'):
                continue
            seen_ids.add(item_id)
            lines.append(f'        NavItem({item_id!r}, {label!r}, route={route!r}),')
        lines.extend(['    )),', '))', f"ACTIVE_ROUTE = {str(project.get('active_route') or '/')!r}"])
    lines.extend([
        '', 'def build_page() -> None:', "    CONTEXT = AnalysisContext(source_key='application')",
        '    SELECTIONS = SelectionBus()', '    FILTER_STATE = {}',
        f"    workflow = create_page_workflow(CONTEXT, SELECTIONS, route={workflow_route!r}, pattern_key={pattern_key!r})",
    ])
    page_indent = '    '
    if navigation:
        lines.append(f"    with AppShell({_safe_title(project.get('name'))!r}, NAVIGATION, active_route=ACTIVE_ROUTE):")
        page_indent = '        '
    title = _safe_title(project.get('page_title') or project.get('name'))
    purpose = _safe_title(project.get('goal') or definition.purpose)
    lines.append(f"{page_indent}with {page_class}({title!r}, {purpose!r}) as page:")
    slot_indent = page_indent + '    '
    content_indent = slot_indent + '    '
    rendered = 0
    for slot in allowed:
        keys = list(placements.get(slot, ())) if isinstance(placements, Mapping) else []
        entries = [lookup[key] for key in keys if key in lookup and is_composable_entry(lookup[key])]
        if not entries and slot not in required and slot != workflow_slot:
            continue
        lines.append(f'{slot_indent}with page.slot(LayoutSlot.{slot.upper()}):')
        if slot == workflow_slot:
            for action in workflow_actions:
                lines.append(f"{content_indent}Button({action.label!r}, on_click=lambda e=None, action_id={action.key!r}: workflow.execute(action_id, e))")
                rendered += 1
        if entries:
            for entry in entries:
                lines.extend(_render_entry_lines(entry, content_indent, project.get('capability_configurations', {}).get(entry.key), density=str(project.get('density') or 'compact')))
                rendered += 1
        elif slot == 'data':
            lines.append(f"{content_indent}DataSourceTable(SOURCE, schema=DATA_SCHEMA, context=CONTEXT, selections=SELECTIONS, spec=DATA_TABLE_SPEC)")
        else:
            lines.append(f"{content_indent}MetricCard({slot.replace('_',' ').title()!r}, 'Configure in NiceGUI Base Workbench')")
    if rendered == 0 and not required:
        lines.extend([
            f'{slot_indent}with page.slot(LayoutSlot.PRIMARY):',
            f"{content_indent}MetricCard('Starter', 'Configure in NiceGUI Base Workbench')",
        ])
    return '\n'.join(lines) + '\n'

def _relative_written_paths(root: Path, written) -> tuple[str, ...]:
    """Return generator-owned paths relative to *root* after canonical path resolution.

    macOS exposes temporary directories through both /var/... and /private/var/... .
    ``Path.relative_to`` is lexical, so resolving both sides is required before
    containment checks. This also handles ordinary symlink aliases on Linux.
    """
    canonical_root = root.resolve()
    result: list[str] = []
    for raw in written:
        canonical_path = Path(raw).resolve()
        try:
            relative = canonical_path.relative_to(canonical_root)
        except ValueError as exc:
            raise RuntimeError(
                f'generated file escaped application root: {canonical_path} not under {canonical_root}'
            ) from exc
        result.append(relative.as_posix())
    return tuple(dict.fromkeys(result))


def generate_project_zip(project: Mapping[str, Any], lookup: Mapping[str, Any]) -> tuple[bytes, GeneratedSmokeReport]:
    from nicegui_base.ai.project import create_application
    from .codegen import _zip_directory
    from .studio_state import normalize_capability_configurations

    pattern_key = str(project.get('pattern_key') or 'analysis_workspace')
    template = _PATTERN_TEMPLATE.get(pattern_key, 'analysis-workspace')
    app_name = str(project.get('name') or 'My NiceGUI App')
    blueprint_key = str(project.get('blueprint_key') or '').strip() or None
    manifest = {
        'schema_version': 1,
        'name': app_name,
        'goal': str(project.get('goal') or ''),
        'problem_type': str(project.get('problem_type') or ''),
        'pattern_key': pattern_key,
        'blueprint_key': blueprint_key,
        'placements': {str(k): list(v) for k, v in dict(project.get('placements') or {}).items()},
        'theme': str(project.get('theme') or 'system'),
        'density': str(project.get('density') or 'compact'),
        'capability_configurations': normalize_capability_configurations(project.get('capability_configurations')),
    }
    with tempfile.TemporaryDirectory(prefix='nicegui-base-workbench-project-') as temp:
        root = Path(temp) / 'app'
        created = create_application(root, name=app_name, template=template)
        meta = root / '.nicegui_base'
        meta.mkdir(parents=True, exist_ok=True)
        from .data_handoff import materialize_data_handoff
        data_contract, data_written, data_sources = materialize_data_handoff(root, project)
        manifest['data_handoff_mode'] = str(project.get('data_handoff_mode') or 'schema_only')
        manifest['data_contract'] = data_contract
        page_sources: dict[str, str] = dict(data_sources)
        extra_written: list[Path] = list(data_written)
        if blueprint_key:
            from .app_blueprint_codegen import materialize_app_blueprint
            blueprint_manifest, blueprint_written, blueprint_sources = materialize_app_blueprint(root, manifest, lookup)
            extra_written.extend(blueprint_written)
            page_sources.update(blueprint_sources)
            manifest['blueprint'] = blueprint_manifest
            manifest['routes'] = list(blueprint_manifest['routes'])
            manifest['pages'] = list(blueprint_manifest['pages'])
        else:
            home_source = project_home_code(manifest, lookup)
            (root / 'pages' / 'home.py').write_text(home_source, encoding='utf-8')
            page_sources['pages/home.py'] = home_source
            manifest['routes'] = ['/']
        from .interaction_contract import materialize_interaction_contract
        interaction_contract, interaction_written, interaction_sources = materialize_interaction_contract(root, manifest)
        manifest['interaction_contract'] = interaction_contract
        extra_written.extend(interaction_written)
        page_sources.update(interaction_sources)
        # Production integration is materialized after blueprint/runtime assembly so
        # it extends the canonical generated app.py instead of being overwritten.
        from .production_integration import materialize_production_integration
        provider_contract, provider_written, provider_sources = materialize_production_integration(root, project)
        manifest['provider_contract'] = provider_contract
        manifest['production_provider'] = str(provider_contract['selected_provider'])
        extra_written.extend(provider_written)
        page_sources.update({path: source for path, source in provider_sources.items() if path.endswith('.py')})
        # Access policy is materialized last because it wraps the final provider-aware
        # runtime and guards every generated page at the HTTP boundary.
        from .access_policy import materialize_access_policy
        access_contract, access_written, access_sources = materialize_access_policy(root, manifest)
        manifest['access_contract'] = access_contract
        extra_written.extend(access_written)
        page_sources.update({path: source for path, source in access_sources.items() if path.endswith('.py')})
        (meta / 'workbench_project.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        from .browser_contract import build_browser_acceptance_contract
        from .browser_acceptance_runner import generated_browser_runner_source
        browser_contract = build_browser_acceptance_contract(manifest)
        (meta / 'browser_acceptance.json').write_text(json.dumps(browser_contract, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        tools = root / 'tools'
        tools.mkdir(parents=True, exist_ok=True)
        (tools / 'browser_acceptance.py').write_text(generated_browser_runner_source(), encoding='utf-8')
        generator_files = _relative_written_paths(root, created.written)
        extra_files = _relative_written_paths(root, extra_written) if extra_written else ()
        from .runtime_bundle import materialize_runtime_bundle
        bundle = materialize_runtime_bundle(root)
        manifest['runtime_bundle'] = {'build_id': bundle['build_id'], 'wheel_sha256': bundle['wheel_sha256']}
        (meta / 'workbench_project.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        payload = _zip_directory(root)
    expected = [*generator_files, *extra_files, '.nicegui_base/workbench_project.json', '.nicegui_base/browser_acceptance.json', 'tools/browser_acceptance.py']
    if blueprint_key:
        expected.append('.nicegui_base/app_blueprint.json')
    report = smoke_generated_zip(payload, expected_files=tuple(dict.fromkeys(expected)))
    import nicegui_base as public_api
    signature_findings: list[str] = []
    for source in page_sources.values():
        signature_findings.extend(validate_public_call_signatures(source, public_api))
    if signature_findings:
        report = GeneratedSmokeReport(False, tuple(dict.fromkeys((*report.findings, *signature_findings))), report.python_files, report.files)
    return payload, report

__all__ = ['_relative_written_paths','generate_project_zip', 'is_composable_entry', 'project_home_code']
