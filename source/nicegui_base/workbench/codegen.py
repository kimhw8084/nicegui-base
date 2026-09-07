from __future__ import annotations

import ast
import io
import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import WorkbenchEntry, WorkbenchKind


@dataclass(frozen=True, slots=True)
class CapabilityConfiguration:
    title: str | None = None
    density: str = 'compact'
    responsive_width: str = 'desktop'
    theme: str = 'system'
    options: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> dict[str, Any]:
        return {
            'title': self.title,
            'density': self.density,
            'responsive_width': self.responsive_width,
            'theme': self.theme,
            'options': {str(key): self.options[key] for key in sorted(self.options)},
        }


@dataclass(frozen=True, slots=True)
class StarterFragment:
    entry_key: str
    entry_kind: str
    route: str
    configuration: Mapping[str, Any]
    data_columns: tuple[str, ...] = ()
    recipe_key: str | None = None
    pattern_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'entry_key': self.entry_key,
            'entry_kind': self.entry_kind,
            'route': self.route,
            'configuration': dict(self.configuration),
            'data_columns': list(self.data_columns),
            'recipe_key': self.recipe_key,
            'pattern_key': self.pattern_key,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + '\n'


@dataclass(frozen=True, slots=True)
class CodeArtifact:
    minimal: str
    production: str
    fragment: StarterFragment
    cli_equivalent: str | None = None


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

_PATTERN_BASE_TEMPLATE = {
    'dashboard': 'dashboard',
    'data_explorer': 'data-explorer',
    'master_detail': 'analysis-workspace',
    'crud': 'crud',
    'monitoring': 'dashboard',
    'search': 'data-explorer',
    'settings': 'analysis-workspace',
    'wizard': 'analysis-workspace',
    'comparison': 'analysis-workspace',
    'analysis_workspace': 'analysis-workspace',
}


def _safe_identifier(text: str, fallback: str = 'GeneratedApp') -> str:
    words = re.findall(r'[A-Za-z0-9]+', text)
    name = ''.join(word[:1].upper() + word[1:] for word in words)
    if not name or not name[0].isalpha():
        name = fallback
    return name


def _entry_symbol(entry: WorkbenchEntry) -> str | None:
    payload = entry.metadata.get('catalog_item') if isinstance(entry.metadata, Mapping) else None
    if isinstance(payload, Mapping):
        for field in ('public_name', 'name'):
            value = payload.get(field)
            if isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
                return value
    key = str(entry.metadata.get('component_key') or '')
    if key:
        return ''.join(piece[:1].upper() + piece[1:] for piece in key.split('_'))
    return None


def _pattern_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('pattern_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def _recipe_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('recipe_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def _surface_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('surface_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def starter_fragment(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None, *, data_columns: Sequence[str] = ()) -> StarterFragment:
    config = config or CapabilityConfiguration()
    return StarterFragment(
        entry.key,
        entry.kind.value,
        entry.route,
        config.normalized(),
        tuple(str(column) for column in data_columns),
        recipe_key=_recipe_key(entry),
        pattern_key=_pattern_key(entry),
    )


def minimal_code(
    entry: WorkbenchEntry,
    config: CapabilityConfiguration | None = None,
    *,
    rows=None,
    data_schema=None,
    measurement_field: str | None = None,
    category_field: str | None = None,
) -> str:
    from .catalog_runtime import describe_entry, example_rows
    from .preview_data import checked_rows
    config = config or CapabilityConfiguration()
    info = describe_entry(entry)
    if not info['runnable']:
        return (
            "# Integration reference: this entry is not an independent GUI component.\n"
            "from nicegui_base.workbench.catalog_runtime import entries_by_key\n\n"
            f"CAPABILITY_KEY = {entry.key!r}\n"
            "entry = entries_by_key()[CAPABILITY_KEY]\n"
            "print(entry.title)\nprint(entry.description)\nprint(entry.source_authority)\n"
        )
    data = checked_rows(example_rows(entry) if rows is None else rows)
    options = dict(config.options)
    options['density'] = config.density
    if measurement_field and not options.get('measurement'):
        options['measurement'] = measurement_field
    if category_field and not options.get('label_field'):
        options['label_field'] = category_field
    contract_import = ''
    contract_kwargs = ''
    if data_schema is not None or measurement_field is not None or category_field is not None:
        contract_import = 'from services.app_data import CATEGORY_FIELD, DATA_SCHEMA, MEASUREMENT_FIELD\n'
        contract_kwargs = ', schema=DATA_SCHEMA, measurement_field=MEASUREMENT_FIELD, category_field=CATEGORY_FIELD'
    return (
        "# Runnable development example. Replace sample data through your governed provider.\n"
        "import json\n"
        "from nicegui_base.workbench.catalog_runtime import render_catalog_example\n"
        "from nicegui_base import PageHeader\n"
        + contract_import
        + "from nicegui_base.workbench.update_identity import BUILD_ID\n\n"
        f"CAPABILITY_KEY = {entry.key!r}\n"
        f"ROWS = json.loads({json.dumps(data, ensure_ascii=False, allow_nan=False)!r})\n"
        f"OPTIONS = json.loads({json.dumps(options, ensure_ascii=False, allow_nan=False)!r})\n\n"
        "def build_page() -> None:\n"
        f"    PageHeader({str(config.title or entry.title)!r})\n"
        + f"    render_catalog_example(CAPABILITY_KEY, title={str(config.title or entry.title)!r}, rows=ROWS, options=OPTIONS, on_event=print{contract_kwargs})\n"
    )


def production_code(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None, *, rows=None) -> str:
    """Legacy API name retained; the Studio labels this a runnable example, not production certification."""
    from .catalog_runtime import describe_entry
    config = config or CapabilityConfiguration()
    body = minimal_code(entry, config, rows=rows)
    if not describe_entry(entry)['runnable']:
        return body
    return body + (
        "\nfrom nicegui_base import NiceGUIRuntimeAdapter, RuntimeConfig\n\n"
        "def main() -> None:\n"
        f"    runtime = NiceGUIRuntimeAdapter(RuntimeConfig({_safe_identifier(config.title or entry.title)!r}, app_version='0.1.0', require_storage_secret=False, show_browser=False))\n"
        "    runtime.run(root=build_page)\n\n"
        "if __name__ == '__main__':\n    main()\n"
    )


def cli_equivalent(entry: WorkbenchEntry, *, app_name: str = 'My NiceGUI App') -> str | None:
    recipe = _recipe_key(entry)
    if recipe:
        return f'nicegui-base create ./my-app --name {json.dumps(app_name)} --template analysis-workspace --recipe {recipe}'
    pattern = _pattern_key(entry)
    if pattern:
        template = _PATTERN_BASE_TEMPLATE.get(pattern, 'analysis-workspace')
        return f'nicegui-base create ./my-app --name {json.dumps(app_name)} --template {template}'
    return None


def code_artifact(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None, *, data_columns: Sequence[str] = (), rows=None) -> CodeArtifact:
    config = config or CapabilityConfiguration()
    return CodeArtifact(
        minimal_code(entry, config, rows=rows),
        production_code(entry, config, rows=rows),
        starter_fragment(entry, config, data_columns=data_columns),
        cli_equivalent(entry, app_name=config.title or 'My NiceGUI App'),
    )


def validate_generated_code(code: str) -> tuple[str, ...]:
    """Return deterministic source-contract findings for generated Python."""
    findings: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return (f'syntax:{exc.lineno}:{exc.msg}',)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    if not any(name == 'nicegui_base' or name.startswith('nicegui_base.') for name in imports):
        findings.append('missing_nicegui_base_import')
    if any(name == 'company_ui' or name.startswith('company_ui.') for name in imports):
        findings.append('deprecated_company_ui_import')
    if 'ui.' in code and 'nicegui import ui' in code:
        findings.append('raw_nicegui_primary_api')
    return tuple(findings)


def _zip_directory(root: Path) -> bytes:
    """Return byte-deterministic ZIP bytes for the same generated tree."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.stat().st_mode & 0o111 else 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def generate_application_zip(
    entry: WorkbenchEntry,
    *,
    app_name: str,
    config: CapabilityConfiguration | None = None,
    rows=None,
    data_schema=None,
    data_mode: str = 'schema_only',
) -> bytes:
    """Generate a governed starter by delegating project ownership to create_application.

    The Workbench replaces ``pages/home.py`` for non-recipe runnable examples using
    the same renderer as Studio. The surrounding runtime, project gates and agent materials are always
    emitted by NiceGUI Base's existing project generator.
    """
    from nicegui_base.ai.project import create_application
    from .catalog_runtime import describe_entry
    if not describe_entry(entry)['runnable']:
        raise ValueError('This catalog entry is an integration reference. Use its dedicated recipe or application generator instead.')

    config = config or CapabilityConfiguration(title=app_name)
    from .catalog_runtime import example_rows
    from .data_dock import DataDockModel
    from .data_handoff import build_data_handoff_plan
    model = DataDockModel(example_rows(entry) if rows is None else rows)
    if data_schema is not None:
        model.restore_schema_metadata(data_schema)
    handoff_project = {
        'data_rows': model.serializable_rows(),
        'data_schema': model.schema_metadata(),
        'data_handoff_mode': data_mode,
        'data_source_name': model.snapshot.source_name,
        'capability_configurations': {entry.key: config.normalized()},
    }
    handoff = build_data_handoff_plan(handoff_project, require_measurement=False)
    exported_rows = handoff.fixture_rows if describe_entry(entry)['uses_rows'] else ()
    recipe = _recipe_key(entry)
    pattern = _pattern_key(entry)
    template = 'analysis-workspace' if recipe else _PATTERN_BASE_TEMPLATE.get(pattern or '', 'analysis-workspace')
    with tempfile.TemporaryDirectory(prefix='nicegui-base-workbench-') as temp:
        root = Path(temp) / 'app'
        create_application(root, name=app_name, template=template, recipe=recipe)
        from .data_handoff import materialize_data_handoff
        materialize_data_handoff(root, handoff_project, require_measurement=False)
        if not recipe:
            from .catalog_runtime import describe_entry
            if not describe_entry(entry)['runnable']:
                raise ValueError('This capability is an integration reference, not a standalone GUI application.')
            (root / 'pages' / 'home.py').write_text(
                minimal_code(
                    entry,
                    config,
                    rows=exported_rows,
                    data_schema=model.schema_metadata(),
                    measurement_field=handoff.measurement_field,
                    category_field=handoff.category_field,
                ),
                encoding='utf-8',
            )
        # Studio exports are standalone applications too. Keep their generated
        # app_data provider boundary complete and bind the same bounded health
        # integration used by Builder project exports.
        from .production_integration import materialize_production_integration
        materialize_production_integration(root, handoff_project)
        from .update_identity import BUILD_ID
        (root / '.nicegui_base' / 'required_development_build.json').write_text(json.dumps({'build_id': BUILD_ID}), encoding='utf-8')
        (root / '.nicegui_base' / 'workbench_fragment.json').write_text(starter_fragment(entry, config).to_json(), encoding='utf-8')
        (root / '.nicegui_base' / 'example_snapshot.json').write_text(json.dumps({'schema_version': 1, 'entry_key': entry.key, 'configuration': config.normalized(), 'data_mode': data_mode, 'source_rows': len(model.rows), 'exported_rows': len(exported_rows), 'schema': list(model.schema_metadata()), 'data_sha256': hashlib.sha256(json.dumps(list(exported_rows), sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()}, indent=2) + '\n', encoding='utf-8')
        from .runtime_bundle import materialize_runtime_bundle
        materialize_runtime_bundle(root)
        return _zip_directory(root)


__all__ = [
    'CapabilityConfiguration','CodeArtifact','StarterFragment','cli_equivalent','code_artifact','generate_application_zip',
    'minimal_code','production_code','starter_fragment','validate_generated_code',
]
