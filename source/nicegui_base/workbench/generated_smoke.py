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
                except Exception as exc:
                    findings.append(f'manifest:{type(exc).__name__}')
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
            if 'app.py' in names:
                app_source = archive.read('app.py').decode('utf-8', errors='replace')
                if 'def runtime(' not in app_source:
                    findings.append('app:missing_runtime')
                if 'def main(' not in app_source:
                    findings.append('app:missing_main')
    except zipfile.BadZipFile:
        findings.append('bad_zip')
    findings = list(dict.fromkeys(findings))
    return GeneratedSmokeReport(not findings, tuple(findings), python_files, files)


__all__ = ['DEFAULT_REQUIRED_PROJECT_FILES', 'GeneratedSmokeReport', 'smoke_generated_zip', 'validate_public_call_signatures']
