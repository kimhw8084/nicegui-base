from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tomllib
import types
import inspect
from dataclasses import dataclass
from pathlib import Path

from nicegui_base.ai.preflight import run_agent_preflight
from nicegui_base.version import FRAMEWORK_VERSION


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {'name': self.name, 'status': self.status, 'detail': self.detail}


@dataclass(frozen=True, slots=True)
class ApplicationGateReport:
    root: Path
    framework_version: str
    release_mode: bool
    checks: tuple[GateCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.status == 'PASS' for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            'root': str(self.root),
            'framework_version': self.framework_version,
            'release_mode': self.release_mode,
            'passed': self.passed,
            'checks': [check.to_dict() for check in self.checks],
        }


def _manifest(root: Path) -> dict:
    path = root / 'nicegui_base.toml'
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open('rb') as handle:
        value = tomllib.load(handle)
    company = value.get('nicegui_base')
    if not isinstance(company, dict):
        raise ValueError('nicegui_base.toml must define [nicegui_base]')
    return company


def _compile_python(root: Path) -> tuple[int, list[str]]:
    failures: list[str] = []
    count = 0
    excludes = {'.venv', 'venv', '.git', '__pycache__', 'build', 'dist'}
    for path in root.rglob('*.py'):
        if any(part in excludes for part in path.relative_to(root).parts):
            continue
        count += 1
        try:
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append(f'{path.relative_to(root)}: {exc}')
    return count, failures


def _import_symbol(root: Path, spec: str) -> object:
    module_name, separator, symbol = spec.partition(':')
    if not separator or not module_name or not symbol:
        raise ValueError(f'invalid entrypoint {spec!r}; expected module:symbol')
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        importlib.invalidate_caches()
        # Generated starters use stable module names (app/pages/services). Purge
        # those app-local modules so repeated dogfood gates cannot reuse a module
        # imported from a different workspace.
        for loaded in tuple(sys.modules):
            if loaded == module_name or loaded == 'recipe_config' or loaded == 'pages' or loaded.startswith('pages.') or loaded == 'services' or loaded.startswith('services.') or loaded == 'data' or loaded.startswith('data.') or loaded == 'domain' or loaded.startswith('domain.'):
                sys.modules.pop(loaded, None)
        module = importlib.import_module(module_name)
        value = getattr(module, symbol)
        if not callable(value):
            raise TypeError(f'{spec} is not callable')
        return value
    finally:
        sys.path[:] = old_path


class _ConstructionElement:
    _next_id = 1
    def __init__(self, *args, **kwargs):
        self.id=_ConstructionElement._next_id; _ConstructionElement._next_id += 1
        self.options=dict(args[0]) if args and isinstance(args[0], dict) else {}
        self.value=kwargs.get('value'); self.visible=True; self.enabled=True
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def __getattr__(self, name):
        if name in {'run_grid_method','run_chart_method'}:
            async def async_method(*args, **kwargs): return None
            return async_method
        def method(*args, **kwargs): return self
        return method
    def descendants(self, **kwargs): return ()


class _ConstructionClient:
    def on_delete(self, callback): return callback


class _ConstructionUI:
    def __init__(self):
        self.context=types.SimpleNamespace(client=_ConstructionClient())
        self.navigate=types.SimpleNamespace(to=lambda *args, **kwargs: None)
    def __getattr__(self, name):
        if name in {'add_head_html','add_body_html'}:
            return lambda *args, **kwargs: None
        if name == 'run_javascript':
            return lambda *args, **kwargs: None
        if name == 'query':
            return lambda *args, **kwargs: _ConstructionElement()
        if name == 'timer':
            return lambda *args, **kwargs: _ConstructionElement()
        return lambda *args, **kwargs: _ConstructionElement(*args, **kwargs)


def _execute_build_page(root: Path, spec: str) -> None:
    """Execute generated page composition with a deterministic UI construction fake.

    This catches Python/API/lifecycle composition failures even in source-only CI
    where NiceGUI/browser packages are intentionally absent. The release live gate
    remains responsible for the real framework/browser runtime.
    """
    existing=sys.modules.get('nicegui')
    fake=types.ModuleType('nicegui'); fake.ui=_ConstructionUI()
    sys.modules['nicegui']=fake
    try:
        build_page=_import_symbol(root, spec)
        result=build_page()
        if inspect.isawaitable(result):
            import asyncio
            asyncio.run(result)
    finally:
        if existing is None: sys.modules.pop('nicegui', None)
        else: sys.modules['nicegui']=existing


def _exact_requirement(root: Path) -> bool:
    path = root / 'requirements.txt'
    if not path.exists():
        return False
    normalized = {line.strip().lower().replace('_','-') for line in path.read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')}
    return f'nicegui-base=={FRAMEWORK_VERSION}'.lower() in normalized


def _run_tests(root: Path) -> tuple[bool, str]:
    tests = root / 'tests'
    if not tests.exists():
        return False, 'tests/ is missing'
    env = dict(os.environ)
    package_root = str(Path(__file__).resolve().parents[2])
    env['PYTHONPATH'] = package_root + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    completed = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(tests)], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, env=env)
    tail = '\n'.join(completed.stdout.splitlines()[-12:])
    return completed.returncode == 0, tail or f'pytest exit={completed.returncode}'


def _run_live_release_gate(root: Path) -> tuple[bool, str]:
    # Delegate the target-only browser/runtime work to the application live gate.
    # Keeping this in a subprocess prevents the gate from contaminating the caller's
    # NiceGUI event loop or module state.
    completed = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.ai.live_gate', '--root', str(root), '--format', 'json'],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        env=dict(os.environ),
    )
    if completed.returncode == 0:
        try:
            payload = json.loads(completed.stdout)
            return True, f"{payload.get('passed_checks', 0)}/{payload.get('total_checks', 0)} live checks"
        except json.JSONDecodeError:
            return True, 'live application runtime check passed'
    return False, '\n'.join(completed.stdout.splitlines()[-12:]) or f'live gate exit={completed.returncode}'


def run_application_gate(root: str | Path='.', *, release: bool=False) -> ApplicationGateReport:
    root = Path(root).resolve()
    checks: list[GateCheck] = []
    try:
        manifest = _manifest(root)
        version = str(manifest.get('framework_version') or '')
        checks.append(GateCheck('manifest', 'PASS' if version == FRAMEWORK_VERSION else 'FAIL', f'framework={version or "missing"}; installed={FRAMEWORK_VERSION}'))
    except Exception as exc:
        manifest = {}
        checks.append(GateCheck('manifest', 'FAIL', str(exc)))

    preflight = run_agent_preflight(root)
    checks.append(GateCheck('agent-preflight', 'PASS' if preflight.passed else 'FAIL', f'{preflight.validation_errors} errors / {preflight.validation_warnings} warnings; scaffold={preflight.scaffold_version or "missing"}'))

    checks.append(GateCheck('dependency-pin', 'PASS' if _exact_requirement(root) else 'FAIL', f'requirements.txt must contain nicegui-base=={FRAMEWORK_VERSION}'))

    count, failures = _compile_python(root)
    checks.append(GateCheck('python-compile', 'PASS' if not failures else 'FAIL', f'{count} files' if not failures else '; '.join(failures[:4])))

    entrypoint = str(manifest.get('entrypoint') or '')
    try:
        _import_symbol(root, entrypoint)
        checks.append(GateCheck('entrypoint', 'PASS', entrypoint))
    except Exception as exc:
        checks.append(GateCheck('entrypoint', 'FAIL', f'{entrypoint or "missing"}: {exc}'))

    build_page = str(manifest.get('build_page') or '')
    try:
        _execute_build_page(root, build_page)
        checks.append(GateCheck('build-page', 'PASS', build_page))
    except Exception as exc:
        checks.append(GateCheck('build-page', 'FAIL', f'{build_page or "missing"}: {type(exc).__name__}: {exc}'))

    try:
        tests_ok, tests_detail = _run_tests(root)
    except Exception as exc:
        tests_ok, tests_detail = False, str(exc)
    checks.append(GateCheck('tests', 'PASS' if tests_ok else 'FAIL', tests_detail))

    if release:
        try:
            live_ok, live_detail = _run_live_release_gate(root)
        except Exception as exc:
            live_ok, live_detail = False, str(exc)
        checks.append(GateCheck('live-uiux', 'PASS' if live_ok else 'FAIL', live_detail))

    return ApplicationGateReport(root=root, framework_version=FRAMEWORK_VERSION, release_mode=release, checks=tuple(checks))


__all__ = ['ApplicationGateReport', 'GateCheck', 'run_application_gate']
