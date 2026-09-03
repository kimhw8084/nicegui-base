from __future__ import annotations

import ast
import io
import inspect
import json
import tomllib
import zipfile
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeneratedSmokeReport:
    ok: bool
    findings: tuple[str, ...]
    python_files: int
    files: int

    def to_dict(self) -> dict[str, object]:
        return {'ok': self.ok, 'findings': list(self.findings), 'python_files': self.python_files, 'files': self.files}


DEFAULT_REQUIRED_PROJECT_FILES = frozenset({
    'app.py',
    'pages/home.py',
    'requirements.txt',
    'nicegui_base.toml',
    'tests/test_project_contract.py',
    '.nicegui_base/workbench_project.json',
})


def validate_public_call_signatures(source: str, public_api) -> tuple[str, ...]:
    """Bind generated direct public-API calls against their real Python signatures.

    This catches runtime call-contract defects which ``ast.parse``/``py_compile``
    cannot detect. Only direct names imported from ``nicegui_base`` are checked;
    method calls and dynamic callbacks remain outside this static contract.
    """
    findings: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return (f'signature_source_syntax:{exc.lineno}:{exc.msg}',)
    imported: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'nicegui_base':
            for alias in node.names:
                imported[alias.asname or alias.name] = alias.name
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        local_name = node.func.id
        public_name = imported.get(local_name)
        if not public_name:
            continue
        target = getattr(public_api, public_name, None)
        if target is None:
            findings.append(f'public_api_missing:{public_name}')
            continue
        try:
            signature = inspect.signature(target)
        except (TypeError, ValueError):
            findings.append(f'signature_unavailable:{public_name}')
            continue
        if any(isinstance(arg, ast.Starred) for arg in node.args) or any(keyword.arg is None for keyword in node.keywords):
            findings.append(f'signature_dynamic_call:{public_name}:line{getattr(node, "lineno", 0)}')
            continue
        args = [object() for _ in node.args]
        kwargs = {str(keyword.arg): object() for keyword in node.keywords}
        try:
            signature.bind(*args, **kwargs)
        except TypeError as exc:
            findings.append(f'signature:{public_name}:line{getattr(node, "lineno", 0)}:{exc}')
    return tuple(dict.fromkeys(findings))



def smoke_generated_zip(payload: bytes, *, expected_files=()) -> GeneratedSmokeReport:
    findings: list[str] = []
    python_files = 0
    files = 0
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            files = len(archive.namelist())
            bad = archive.testzip()
            if bad:
                findings.append(f'crc:{bad}')
            names = set(archive.namelist())
            required = set(DEFAULT_REQUIRED_PROJECT_FILES)
            required.update(str(path).replace('\\', '/').lstrip('/') for path in expected_files if str(path).strip())
            for path in sorted(required - names):
                findings.append(f'missing:{path}')
            if '.nicegui_base/workbench_project.json' in names:
                try:
                    manifest = json.loads(archive.read('.nicegui_base/workbench_project.json'))
                    if not isinstance(manifest, dict) or not manifest.get('pattern_key'):
                        findings.append('manifest:missing_pattern_key')
                    if not isinstance(manifest.get('placements', {}), dict):
                        findings.append('manifest:invalid_placements')
                    if manifest.get('blueprint_key') and '.nicegui_base/app_blueprint.json' not in names:
                        findings.append('manifest:missing_app_blueprint')
                except Exception as exc:
                    findings.append(f'manifest:{type(exc).__name__}')
            if '.nicegui_base/app_blueprint.json' in names:
                try:
                    from .app_blueprints import validate_app_blueprint_manifest
                    blueprint = json.loads(archive.read('.nicegui_base/app_blueprint.json'))
                    findings.extend(validate_app_blueprint_manifest(blueprint))
                    for page in blueprint.get('pages', ()) if isinstance(blueprint, dict) else ():
                        if not isinstance(page, dict):
                            continue
                        module = str(page.get('module') or '')
                        expected_page = f'pages/{module}.py'
                        if module and expected_page not in names:
                            findings.append(f'blueprint:missing_page:{expected_page}')
                except Exception as exc:
                    findings.append(f'blueprint:{type(exc).__name__}')
            if '.nicegui_base/data_contract.json' in names:
                try:
                    from .data_handoff import validate_data_contract_manifest
                    data_contract = json.loads(archive.read('.nicegui_base/data_contract.json'))
                    findings.extend(validate_data_contract_manifest(data_contract))
                    for required_data_file in ('services/data_contract.py','services/development_fixture.py','services/app_data.py'):
                        if required_data_file not in names:
                            findings.append(f'data_contract:missing:{required_data_file}')
                    if '.nicegui_base/workbench_project.json' in names:
                        project_manifest = json.loads(archive.read('.nicegui_base/workbench_project.json'))
                        project_contract = project_manifest.get('data_contract') if isinstance(project_manifest, dict) else None
                        if not isinstance(project_contract, dict):
                            findings.append('data_contract:missing_workbench_contract')
                        else:
                            if project_contract.get('contract_signature') != data_contract.get('contract_signature'):
                                findings.append('data_contract:workbench_signature_drift')
                            if project_manifest.get('data_handoff_mode') != data_contract.get('mode'):
                                findings.append('data_contract:workbench_mode_drift')
                except Exception as exc:
                    findings.append(f'data_contract:{type(exc).__name__}')
            if '.nicegui_base/provider_contract.json' in names:
                try:
                    from .production_integration import validate_provider_contract
                    provider_contract = json.loads(archive.read('.nicegui_base/provider_contract.json'))
                    findings.extend(validate_provider_contract(provider_contract))
                    for required_provider_file in ('services/provider_config.py','services/app_data.py','.env.example'):
                        if required_provider_file not in names:
                            findings.append(f'provider_contract:missing:{required_provider_file}')
                    if '.nicegui_base/workbench_project.json' in names:
                        project_manifest = json.loads(archive.read('.nicegui_base/workbench_project.json'))
                        project_contract = project_manifest.get('provider_contract') if isinstance(project_manifest, dict) else None
                        if not isinstance(project_contract, dict):
                            findings.append('provider_contract:missing_workbench_contract')
                        elif project_contract.get('contract_signature') != provider_contract.get('contract_signature'):
                            findings.append('provider_contract:workbench_signature_drift')
                        if isinstance(project_manifest, dict) and project_manifest.get('production_provider') != provider_contract.get('selected_provider'):
                            findings.append('provider_contract:workbench_provider_drift')
                    if 'services/app_data.py' in names:
                        data_source = archive.read('services/app_data.py').decode('utf-8', errors='replace')
                        for marker in ('def build_source(', 'def provider_diagnostics(', 'def register_source_health('):
                            if marker not in data_source:
                                findings.append(f'provider_contract:unwired_data_service:{marker}')
                    if 'app.py' in names:
                        app_source = archive.read('app.py').decode('utf-8', errors='replace')
                        if 'register_source_health' not in app_source:
                            findings.append('provider_contract:unwired_runtime_health')
                    if '.env.example' in names:
                        example = archive.read('.env.example').decode('utf-8', errors='replace')
                        sensitive = ('PASSWORD','TOKEN','API_KEY','SECRET','AUTHORIZATION','COOKIE','CONNECTION_STRING','PRIVATE_KEY')
                        for line in example.splitlines():
                            stripped = line.strip()
                            if not stripped or stripped.startswith('#') or '=' not in stripped:
                                continue
                            key, _value = stripped.split('=', 1)
                            upper = key.upper()
                            if any(term in upper for term in sensitive):
                                findings.append(f'provider_contract:sensitive_env_example:{key}')
                except Exception as exc:
                    findings.append(f'provider_contract:{type(exc).__name__}')
            if '.nicegui_base/interaction_contract.json' in names:
                try:
                    from .interaction_contract import validate_interaction_contract
                    interaction = json.loads(archive.read('.nicegui_base/interaction_contract.json'))
                    findings.extend(validate_interaction_contract(interaction))
                    if 'services/app_workflow.py' not in names:
                        findings.append('interaction_contract:missing:services/app_workflow.py')
                    if '.nicegui_base/workbench_project.json' in names:
                        project_manifest = json.loads(archive.read('.nicegui_base/workbench_project.json'))
                        project_contract = project_manifest.get('interaction_contract') if isinstance(project_manifest, dict) else None
                        if not isinstance(project_contract, dict):
                            findings.append('interaction_contract:missing_workbench_contract')
                        elif project_contract.get('contract_signature') != interaction.get('contract_signature'):
                            findings.append('interaction_contract:workbench_signature_drift')
                    interaction_routes = [str(page.get('route') or '') for page in interaction.get('pages', ()) if isinstance(page, dict)]
                    if '.nicegui_base/app_blueprint.json' in names:
                        blueprint = json.loads(archive.read('.nicegui_base/app_blueprint.json'))
                        if interaction_routes != [str(route) for route in blueprint.get('routes', ())]:
                            findings.append('interaction_contract:blueprint_route_drift')
                    elif interaction_routes != ['/']:
                        findings.append('interaction_contract:single_page_route_drift')
                    for page in interaction.get('pages', ()) if isinstance(interaction, dict) else ():
                        if not isinstance(page, dict):
                            continue
                        module = str(page.get('module') or '')
                        source_path = f'pages/{module}.py'
                        if source_path not in names:
                            findings.append(f'interaction_contract:missing_page:{source_path}')
                            continue
                        page_source = archive.read(source_path).decode('utf-8', errors='replace')
                        if 'create_page_workflow' not in page_source or 'workflow.execute(' not in page_source:
                            findings.append(f'interaction_contract:unwired_page:{source_path}')
                except Exception as exc:
                    findings.append(f'interaction_contract:{type(exc).__name__}')
            if '.nicegui_base/browser_acceptance.json' in names:
                try:
                    from .browser_contract import validate_browser_acceptance_contract
                    browser_contract = json.loads(archive.read('.nicegui_base/browser_acceptance.json'))
                    findings.extend(validate_browser_acceptance_contract(browser_contract))
                    if browser_contract.get('schema_version') == 2:
                        if 'tools/browser_acceptance.py' not in names:
                            findings.append('browser_contract:missing_runner')
                        else:
                            runner_source = archive.read('tools/browser_acceptance.py').decode('utf-8', errors='replace')
                            if 'run_browser_acceptance_file' not in runner_source:
                                findings.append('browser_contract:invalid_runner')
                except Exception as exc:
                    findings.append(f'browser_contract:{type(exc).__name__}')
            if 'requirements.txt' in names:
                requirements = archive.read('requirements.txt').decode('utf-8', errors='replace')
                if not any(line.strip().startswith('nicegui-base==') for line in requirements.splitlines()):
                    findings.append('requirements:missing_exact_nicegui_base_pin')
            if 'nicegui_base.toml' in names:
                try:
                    project_meta = tomllib.loads(archive.read('nicegui_base.toml').decode('utf-8'))
                    section = project_meta.get('nicegui_base', {})
                    if not section.get('framework_version'):
                        findings.append('project_meta:missing_framework_version')
                    if section.get('build_page') != 'pages.home:build_page':
                        findings.append('project_meta:invalid_build_page')
                except Exception as exc:
                    findings.append(f'project_meta:{type(exc).__name__}')
            for name in sorted(names):
                if not name.endswith('.py'):
                    continue
                python_files += 1
                try:
                    text = archive.read(name).decode('utf-8')
                except UnicodeDecodeError:
                    findings.append(f'encoding:{name}')
                    continue
                try:
                    tree = ast.parse(text, filename=name)
                except SyntaxError as exc:
                    findings.append(f'syntax:{name}:{exc.lineno}:{exc.msg}')
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and (node.module == 'company_ui' or node.module.startswith('company_ui.')):
                        findings.append(f'deprecated_import:{name}')
                    if isinstance(node, ast.Import):
                        if any(alias.name == 'company_ui' or alias.name.startswith('company_ui.') for alias in node.names):
                            findings.append(f'deprecated_import:{name}')
            if 'pages/home.py' in names:
                home = archive.read('pages/home.py').decode('utf-8', errors='replace')
                if 'def build_page(' not in home:
                    findings.append('home:missing_build_page')
                if 'LayoutSlot.' not in home:
                    findings.append('home:missing_layout_slots')
                if '.nicegui_base/data_contract.json' in names:
                    if 'from services.app_data import' not in home:
                        findings.append('home:missing_data_service_binding')
                    if 'ROWS = (' in home:
                        findings.append('home:inline_fixed_rows')
                if '.nicegui_base/interaction_contract.json' in names:
                    if 'create_page_workflow' not in home or 'workflow.execute(' not in home:
                        findings.append('home:missing_interaction_binding')
            if 'app.py' in names:
                app_source = archive.read('app.py').decode('utf-8', errors='replace')
                if 'def runtime(' not in app_source:
                    findings.append('app:missing_runtime')
                if 'def main(' not in app_source:
                    findings.append('app:missing_main')
                if '.nicegui_base/app_blueprint.json' in names and 'pages=ROUTES' not in app_source:
                    findings.append('app:missing_blueprint_routes')
    except zipfile.BadZipFile:
        findings.append('bad_zip')
    findings = list(dict.fromkeys(findings))
    return GeneratedSmokeReport(not findings, tuple(findings), python_files, files)


__all__ = ['DEFAULT_REQUIRED_PROJECT_FILES', 'GeneratedSmokeReport', 'smoke_generated_zip', 'validate_public_call_signatures']
