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
    """Return whether Workbench can truthfully emit this catalog entry.

    Framework-catalog rows are intentionally REFERENCE entries. They become project
    composable only when this generator owns a rendering adapter for the exact
    canonical registry/key. Catalog visibility and generator support remain separate
    contracts so choosing a capability can never silently emit an unrelated widget.
    """
    kind = _entry_kind(entry)
    if kind == 'analytic':
        return True
    metadata = getattr(entry, 'metadata', {}) or {}
    registry = str(metadata.get('registry_name') or '')
    registry_key = str(metadata.get('registry_key') or metadata.get('component_key') or '')
    if kind not in {'component', 'reference'}:
        return False
    allowed = _COMPOSABLE_REFERENCE_KEYS.get(registry)
    if allowed is not None:
        return registry_key in allowed
    return registry_key in _COMPOSABLE_RENDER_KEYS


def _safe_title(value: Any) -> str:
    return str(value or 'Capability').replace('\n', ' ').strip()[:100]


def _render_entry_lines(entry, indent: str) -> list[str]:
    title = _safe_title(entry.title)
    kind = _entry_kind(entry)
    if kind == 'analytic':
        key = str(entry.metadata.get('surface_key') or entry.key.split(':')[-1])
        return [
            f"{indent}with SemiconductorAnalyticalPanel({key!r}, CONTEXT, SELECTIONS, title={title!r}):",
            f"{indent}    MetricCard('Surface', {key!r}.replace('_', ' ').title())",
        ]
    registry = str(entry.metadata.get('registry_name') or '')
    registry_key = str(entry.metadata.get('registry_key') or entry.metadata.get('component_key') or '')
    if registry == 'tables':
        return [f"{indent}DataTable(ROWS, COLUMNS, row_key='id', title={title!r})"]
    if registry == 'visualizations':
        chart = registry_key if registry_key in {'LineChart','AreaChart','BarChart','StackedBarChart'} else 'BoxPlot'
        if chart == 'BoxPlot':
            return [
                f"{indent}BoxPlot({title!r}, (SeriesSpec('distribution','Distribution',((9.4,9.8,10.1,10.5,10.9),(9.7,10.0,10.3,10.6,11.1))),),",
                f"{indent}        x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('Baseline','Current')))",
            ]
        return [
            f"{indent}{chart}({title!r}, (SeriesSpec('value','Value',(10.1,10.4,10.2,10.8,11.0), smooth=True),),",
            f"{indent}          x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('R1','R2','R3','R4','R5')))",
        ]
    if registry_key in {'search_input'}:
        return [f"{indent}SearchInput({title!r}, placeholder='Search…')"]
    if registry_key in {'select'}:
        return [f"{indent}Select({title!r}, {{'all':'All','watch':'Watch','critical':'Critical'}}, value='all')"]
    if registry_key in {'text_input'}:
        return [f"{indent}TextInput({title!r})"]
    if registry_key == 'button':
        return [f"{indent}Button({title!r})"]
    if registry_key == 'action_button':
        return [f"{indent}ActionButton({title!r})"]
    if registry_key in {'status_badge', 'badge'}:
        return [f"{indent}StatusBadge({title!r})"]
    if registry_key == 'alert':
        return [f"{indent}Alert({title!r}, message='Generated application alert')"]
    if registry_key == 'metric_strip':
        return [f"{indent}with MetricStrip():", f"{indent}    MetricCard({title!r}, 'Ready')"]
    return [f"{indent}MetricCard({title!r}, 'Ready')"]


def project_home_code(project: Mapping[str, Any], lookup: Mapping[str, Any]) -> str:
    pattern_key = str(project.get('pattern_key') or 'analysis_workspace')
    page_class = _PATTERN_PAGE.get(pattern_key, 'AnalysisWorkspacePage')
    from nicegui_base.patterns.registry import get_pattern
    definition = get_pattern(pattern_key)
    required = {slot.value for slot in definition.required_slots if slot.value != 'header'}
    allowed = [slot.value for slot in definition.slot_order if slot.value != 'header']
    placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    imports = (
        'ActionButton, Alert, AnalysisContext, AreaChart, AxisSpec, AxisType, BarChart, BoxPlot, Button, DataTable, LayoutSlot, LineChart, '
        'MetricCard, MetricStrip, SearchInput, Select, SelectionBus, SemiconductorAnalyticalPanel, SeriesSpec, StackedBarChart, '
        'StatusBadge, TableColumn, TextInput'
    )
    lines = [
        'from __future__ import annotations',
        f'from nicegui_base import {page_class}, {imports}',
        '',
        "ROWS = (",
        "    {'id':'R-001','tool':'ETCH-01','value':10.2,'status':'Normal'},",
        "    {'id':'R-002','tool':'ETCH-02','value':10.7,'status':'Watch'},",
        ")",
        "COLUMNS = (TableColumn('id','Record'), TableColumn('tool','Tool'), TableColumn('value','Value'), TableColumn('status','Status'))",
        "CONTEXT = AnalysisContext(source_key='application')",
        'SELECTIONS = SelectionBus()',
        '',
        'def build_page() -> None:',
        f"    with {page_class}({_safe_title(project.get('name'))!r}, {_safe_title(project.get('goal') or definition.purpose)!r}) as page:",
    ]
    rendered = 0
    for slot in allowed:
        keys = list(placements.get(slot, ())) if isinstance(placements, Mapping) else []
        entries = [lookup[key] for key in keys if key in lookup and is_composable_entry(lookup[key])]
        if not entries and slot not in required:
            continue
        lines.append(f'        with page.slot(LayoutSlot.{slot.upper()}):')
        if entries:
            for entry in entries:
                lines.extend(_render_entry_lines(entry, '            '))
                rendered += 1
        elif slot == 'data':
            lines.append("            DataTable(ROWS, COLUMNS, row_key='id', title='Records')")
        else:
            lines.append(f"            MetricCard({slot.replace('_',' ').title()!r}, 'Configure in NiceGUI Base Workbench')")
    if rendered == 0 and not required:
        lines.extend([
            '        with page.slot(LayoutSlot.PRIMARY):',
            "            MetricCard('Starter', 'Configure in NiceGUI Base Workbench')",
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

    pattern_key = str(project.get('pattern_key') or 'analysis_workspace')
    template = _PATTERN_TEMPLATE.get(pattern_key, 'analysis-workspace')
    app_name = str(project.get('name') or 'My NiceGUI App')
    manifest = {
        'schema_version': 1,
        'name': app_name,
        'goal': str(project.get('goal') or ''),
        'problem_type': str(project.get('problem_type') or ''),
        'pattern_key': pattern_key,
        'placements': {str(k): list(v) for k, v in dict(project.get('placements') or {}).items()},
        'theme': str(project.get('theme') or 'system'),
        'density': str(project.get('density') or 'compact'),
    }
    with tempfile.TemporaryDirectory(prefix='nicegui-base-workbench-project-') as temp:
        root = Path(temp) / 'app'
        created = create_application(root, name=app_name, template=template)
        (root / 'pages' / 'home.py').write_text(project_home_code(manifest, lookup), encoding='utf-8')
        meta = root / '.nicegui_base'
        meta.mkdir(parents=True, exist_ok=True)
        (meta / 'workbench_project.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        from .browser_contract import build_browser_acceptance_contract
        browser_contract = build_browser_acceptance_contract(manifest)
        (meta / 'browser_acceptance.json').write_text(json.dumps(browser_contract, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        generator_files = _relative_written_paths(root, created.written)
        payload = _zip_directory(root)
    report = smoke_generated_zip(payload, expected_files=(*generator_files, '.nicegui_base/workbench_project.json', '.nicegui_base/browser_acceptance.json'))
    import nicegui_base as public_api
    signature_findings = validate_public_call_signatures(project_home_code(manifest, lookup), public_api)
    if signature_findings:
        report = GeneratedSmokeReport(False, tuple(dict.fromkeys((*report.findings, *signature_findings))), report.python_files, report.files)
    return payload, report


__all__ = ['_relative_written_paths','generate_project_zip', 'is_composable_entry', 'project_home_code']
