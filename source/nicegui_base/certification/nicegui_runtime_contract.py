from __future__ import annotations

import argparse
import ast
import importlib.metadata as metadata
import inspect
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from nicegui_base.version import NICEGUI_VERSION



APPROVED_NICEGUI_315_FACTORIES = frozenset({
    'add_body_html','add_css','add_head_html','aggrid','badge','button','checkbox','code','colors','column',
    'context_menu','dark_mode','dialog','download','echart','element','expansion','header','html','image','input',
    'item','item_label','item_section','json_editor','keyboard','label','left_drawer','linear_progress','link','log',
    'markdown','menu','number','page','plotly','query','radio','range','row','run','run_javascript','select','separator',
    'slider','spinner','step','stepper','switch','tab','tab_panel','tab_panels','tabs','textarea','timer','toggle','tree','upload',
})

@dataclass(frozen=True, slots=True)
class RuntimeContractIssue:
    code: str
    detail: str
    path: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class RuntimeContractReport:
    nicegui_version: str | None
    source_issues: tuple[RuntimeContractIssue, ...]
    runtime_issues: tuple[RuntimeContractIssue, ...]
    factories_checked: int
    calls_checked: int

    @property
    def ok(self) -> bool:
        return not self.source_issues and not self.runtime_issues and self.nicegui_version == NICEGUI_VERSION


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _source_files(root: Path | None = None) -> tuple[Path, ...]:
    root = root or _package_root()
    if (root / 'nicegui_base' / 'integrations').exists():
        root = root / 'nicegui_base'
    paths = list((root / 'integrations').glob('nicegui_*.py'))
    for name in ('certification/mac_lab.py', 'certification/live_lab.py'):
        p = root / name
        if p.exists():
            paths.append(p)
    return tuple(sorted(set(paths)))


def _is_ui_receiver(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id == 'ui':
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_ui':
        return True
    return False


def iter_ui_factory_calls(root: Path | None = None) -> Iterable[tuple[Path, ast.Call, str, tuple[str, ...]]]:
    for path in _source_files(root):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if not _is_ui_receiver(node.func.value):
                continue
            keywords = tuple(k.arg for k in node.keywords if k.arg is not None)
            yield path, node, node.func.attr, keywords


def scan_source_contract(root: Path | None = None) -> tuple[RuntimeContractIssue, ...]:
    root = root or _package_root()
    if (root / 'nicegui_base' / 'integrations').exists():
        root = root / 'nicegui_base'
    issues: list[RuntimeContractIssue] = []
    for path in _source_files(root):
        try:
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except Exception as exc:
            issues.append(RuntimeContractIssue('SOURCE_PARSE', str(exc), str(path)))
            continue

        for node in ast.walk(tree):
            # NiceGUI 3.15 EChart.options is read-only; mutate the returned dict instead.
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets: list[ast.AST] = []
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                else:
                    targets = [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr == 'options':
                        issues.append(RuntimeContractIssue(
                            'ECHART_OPTIONS_ASSIGNMENT',
                            'Direct assignment to .options is forbidden for NiceGUI 3.15 EChart; mutate options dict then update().',
                            str(path.relative_to(root)), getattr(node, 'lineno', None),
                        ))
            # NiceGUI 3.15 Fullscreen.enter/exit/toggle are synchronous setters.
            if isinstance(node, ast.Await) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                func = node.value.func
                receiver = func.value
                native_fullscreen = (
                    isinstance(receiver, ast.Attribute)
                    and receiver.attr == 'fullscreen'
                    and _is_ui_receiver(receiver.value)
                )
                if func.attr in {'enter', 'exit', 'toggle'} and native_fullscreen:
                    issues.append(RuntimeContractIssue(
                        'AWAIT_NATIVE_FULLSCREEN',
                        f'NiceGUI 3.15 fullscreen.{func.attr}() is synchronous and must not be awaited.',
                        str(path.relative_to(root)), getattr(node, 'lineno', None),
                    ))

        # Drawer contract: Company wrapper may expose open/close, but raw LeftDrawer must use show/hide/toggle.
        if path.name == 'nicegui_layout.py':
            class_node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MobileNavigationDrawer'), None)
            if class_node is not None:
                class_source = ast.get_source_segment(source, class_node) or ''
                if 'self.element.open' in class_source or 'self.element.close' in class_source:
                    issues.append(RuntimeContractIssue(
                        'LEFT_DRAWER_OPEN_CLOSE',
                        'MobileNavigationDrawer must call LeftDrawer.show()/hide()/toggle(), not open()/close().',
                        str(path.relative_to(root)), class_node.lineno,
                    ))
    for path, node, factory_name, _ in iter_ui_factory_calls(root):
        if factory_name not in APPROVED_NICEGUI_315_FACTORIES:
            issues.append(RuntimeContractIssue(
                'UNREVIEWED_FACTORY',
                f'nicegui.ui.{factory_name} is not in the reviewed NiceGUI 3.15 NiceGUI Base factory allowlist.',
                str(path.relative_to(root)), node.lineno,
            ))
    return tuple(issues)


def _signature_accepts(callable_obj: Any, keyword: str) -> bool:
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return True  # non-introspectable NiceGUI utility; dedicated class checks still cover critical APIs
    parameters = signature.parameters
    if keyword in parameters:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())


def _check_methods(cls: type, required: tuple[str, ...], *, label: str) -> list[RuntimeContractIssue]:
    issues: list[RuntimeContractIssue] = []
    for name in required:
        if not callable(getattr(cls, name, None)):
            issues.append(RuntimeContractIssue('MISSING_METHOD', f'{label}.{name} is required by NiceGUI Base'))
    return issues


def run_installed_runtime_contract(root: Path | None = None) -> RuntimeContractReport:
    source_issues = scan_source_contract(root)
    runtime_issues: list[RuntimeContractIssue] = []
    try:
        version = metadata.version('nicegui')
    except metadata.PackageNotFoundError:
        return RuntimeContractReport(None, source_issues, (RuntimeContractIssue('NICEGUI_MISSING', f'NiceGUI {NICEGUI_VERSION} is not installed'),), 0, 0)
    if version != NICEGUI_VERSION:
        runtime_issues.append(RuntimeContractIssue('NICEGUI_VERSION', f'Expected NiceGUI {NICEGUI_VERSION}, found {version}'))

    try:
        from nicegui import ui
        from nicegui.element import Element
        from nicegui.elements.context_menu import ContextMenu
        from nicegui.elements.dialog import Dialog
        from nicegui.elements.drawer import LeftDrawer
        from nicegui.elements.echart.echart import EChart
        from nicegui.elements.fullscreen import Fullscreen
        from nicegui.elements.menu import Menu
    except Exception as exc:
        runtime_issues.append(RuntimeContractIssue('NICEGUI_IMPORT', f'NiceGUI API import failed: {type(exc).__name__}: {exc}'))
        return RuntimeContractReport(version, source_issues, tuple(runtime_issues), 0, 0)

    # High-risk contracts confirmed against NiceGUI 3.15.0 tagged source.
    runtime_issues.extend(_check_methods(LeftDrawer, ('show', 'hide', 'toggle'), label='LeftDrawer'))
    runtime_issues.extend(_check_methods(Dialog, ('open', 'close', 'toggle'), label='Dialog'))
    runtime_issues.extend(_check_methods(Menu, ('open', 'close', 'toggle'), label='Menu'))
    runtime_issues.extend(_check_methods(ContextMenu, ('open', 'close'), label='ContextMenu'))
    runtime_issues.extend(_check_methods(EChart, ('update', 'run_chart_method'), label='EChart'))
    runtime_issues.extend(_check_methods(Fullscreen, ('enter', 'exit', 'toggle'), label='Fullscreen'))
    runtime_issues.extend(_check_methods(Element, ('on', 'update', 'delete', 'set_visibility', 'tooltip'), label='Element'))

    options_descriptor = inspect.getattr_static(EChart, 'options', None)
    if not isinstance(options_descriptor, property) or options_descriptor.fset is not None:
        runtime_issues.append(RuntimeContractIssue('ECHART_OPTIONS_DESCRIPTOR', 'EChart.options contract differs from pinned NiceGUI 3.15 read-only property expectation'))
    for method in ('enter', 'exit', 'toggle'):
        if inspect.iscoroutinefunction(getattr(Fullscreen, method)):
            runtime_issues.append(RuntimeContractIssue('FULLSCREEN_COROUTINE', f'Fullscreen.{method} unexpectedly became async'))
    for prop in ('classes', 'style', 'props'):
        if not isinstance(inspect.getattr_static(Element, prop, None), property):
            runtime_issues.append(RuntimeContractIssue('ELEMENT_HELPER_DESCRIPTOR', f'Element.{prop} must remain a property helper'))

    calls = tuple(iter_ui_factory_calls(root))
    factories: set[str] = set()
    for path, node, factory_name, keywords in calls:
        factories.add(factory_name)
        factory = getattr(ui, factory_name, None)
        if factory is None:
            runtime_issues.append(RuntimeContractIssue('MISSING_FACTORY', f'nicegui.ui.{factory_name} does not exist', str(path), node.lineno))
            continue
        if not callable(factory) and factory_name not in {'download'}:
            runtime_issues.append(RuntimeContractIssue('NONCALLABLE_FACTORY', f'nicegui.ui.{factory_name} is not callable', str(path), node.lineno))
            continue
        if callable(factory):
            for keyword in keywords:
                if not _signature_accepts(factory, keyword):
                    runtime_issues.append(RuntimeContractIssue(
                        'FACTORY_KEYWORD',
                        f'nicegui.ui.{factory_name} does not accept keyword {keyword!r} in installed {version}',
                        str(path), node.lineno,
                    ))

    return RuntimeContractReport(version, source_issues, tuple(runtime_issues), len(factories), len(calls))


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify NiceGUI Base against the exact installed NiceGUI runtime API contract')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    report = run_installed_runtime_contract()
    if args.format == 'json':
        print(json.dumps({
            'ok': report.ok,
            'required_nicegui_version': NICEGUI_VERSION,
            'installed_nicegui_version': report.nicegui_version,
            'factories_checked': report.factories_checked,
            'calls_checked': report.calls_checked,
            'source_issues': [asdict(i) for i in report.source_issues],
            'runtime_issues': [asdict(i) for i in report.runtime_issues],
        }, indent=2))
    else:
        print(f'NiceGUI required: {NICEGUI_VERSION}; installed: {report.nicegui_version or "missing"}')
        print(f'Factory contract: {report.factories_checked} factories / {report.calls_checked} direct calls checked')
        for issue in (*report.source_issues, *report.runtime_issues):
            where = f' · {issue.path}:{issue.line}' if issue.path else ''
            print(f'[FAIL] {issue.code}: {issue.detail}{where}')
        print(f'\nRuntime contract: {"PASS" if report.ok else "FAIL"}')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())


__all__ = [
    'RuntimeContractIssue', 'RuntimeContractReport', 'APPROVED_NICEGUI_315_FACTORIES', 'iter_ui_factory_calls', 'scan_source_contract',
    'run_installed_runtime_contract',
]
