from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from nicegui_base.ai.models import ValidationIssue, ValidationReport, ValidationSeverity

_ALLOW = 'nicegui-base: allow-'
_HEX = re.compile(r'(?<![A-Za-z0-9])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![A-Za-z0-9])')
_CSS_VALUE = re.compile(r'\b(?:margin|padding|gap|border-radius|font-size|width|height|box-shadow|background|color)\s*:')
_PIXEL = re.compile(r'(?<![\w.])-?\d+(?:\.\d+)?px\b')
_EMOJI = re.compile('[\U0001F300-\U0001FAFF\u2600-\u27BF]')
_SQL = re.compile(r'\b(?:SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|MERGE\s+INTO)\b', re.I)
_HTTP = re.compile(r'https?://', re.I)
_UI_MODULE_CALLS = {'button','input','select','switch','toggle','checkbox','radio','aggrid','echart','row','column','grid','dialog','drawer','tabs','tab_panels','card','label','image','notify'}
_VISUAL_CALLS = {'image','add_head_html','add_css','html'}
_LAYOUT_CALLS = {'row','column','grid','splitter','drawer'}


@dataclass(frozen=True, slots=True)
class ValidatorConfig:
    exclude_dirs: tuple[str, ...] = ('.git', '.venv', 'venv', '__pycache__', 'build', 'dist', 'nicegui_base')
    page_dirs: tuple[str, ...] = ('pages', 'views', 'screens')
    warnings_as_errors: bool = False


def _call_name(node: ast.Call) -> str:
    fn = node.func
    parts: list[str] = []
    while isinstance(fn, ast.Attribute):
        parts.append(fn.attr)
        fn = fn.value
    if isinstance(fn, ast.Name):
        parts.append(fn.id)
    return '.'.join(reversed(parts))


def _literal_text(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _line_allowed(lines: list[str], line: int, rule: str) -> bool:
    indexes = [line - 1, line - 2]
    marker = f'{_ALLOW}{rule.lower()}'
    return any(0 <= i < len(lines) and marker in lines[i].lower() for i in indexes)


class _PythonValidator(ast.NodeVisitor):
    def __init__(self, path: Path, root: Path, source: str, config: ValidatorConfig) -> None:
        self.path = path
        self.root = root
        self.source = source
        self.lines = source.splitlines()
        self.config = config
        self.issues: list[ValidationIssue] = []
        self.nicegui_aliases: set[str] = set()
        self.ui_names: set[str] = set()

    def issue(self, code: str, severity: ValidationSeverity, node: ast.AST, message: str, suggestion: str | None = None) -> None:
        if _line_allowed(self.lines, getattr(node, 'lineno', 1), code):
            return
        rel = str(self.path.relative_to(self.root))
        self.issues.append(ValidationIssue(code, severity, message, rel, getattr(node,'lineno',1), getattr(node,'col_offset',0), suggestion))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == 'nicegui' or alias.name.startswith('nicegui.'):
                self.nicegui_aliases.add(alias.asname or alias.name.split('.')[0])
                self.issue('AI001', ValidationSeverity.ERROR, node,
                           'Application code imports NiceGUI directly.',
                           'Use nicegui_base public APIs; raw NiceGUI is an explicit escape hatch only.')
            if alias.name.startswith('nicegui_base.integrations.nicegui_'):
                self.issue('AI017', ValidationSeverity.WARNING, node,
                           'Application code imports a NiceGUI integration implementation module directly.',
                           'Import the governed public symbol from nicegui_base instead of coupling app code to renderer internals.')
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and (node.module == 'nicegui' or node.module.startswith('nicegui.')):
            for alias in node.names:
                if alias.name == 'ui':
                    self.ui_names.add(alias.asname or alias.name)
            self.issue('AI001', ValidationSeverity.ERROR, node,
                       'Application code imports NiceGUI directly.',
                       'Use nicegui_base public APIs; raw NiceGUI is an explicit escape hatch only.')
        if node.module and node.module.startswith('nicegui_base.integrations.nicegui_'):
            self.issue('AI017', ValidationSeverity.WARNING, node,
                       'Application code imports a NiceGUI integration implementation module directly.',
                       'Import the governed public symbol from nicegui_base instead of coupling app code to renderer internals.')
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        parts = name.split('.')
        last = parts[-1] if parts else ''
        if len(parts) >= 2 and parts[-2] in self.ui_names | {'ui'} and last in _UI_MODULE_CALLS:
            code = 'AI002' if last == 'aggrid' else 'AI003' if last == 'echart' else 'AI004' if last in _LAYOUT_CALLS else 'AI005'
            msg = {
                'AI002':'Raw AG Grid construction detected.',
                'AI003':'Raw ECharts construction detected.',
                'AI004':'Raw NiceGUI layout construction detected.',
                'AI005':'Raw NiceGUI control construction detected.',
            }[code]
            fix = {
                'AI002':'Use DataTable/ServerDataTable and TABLE_REGISTRY.',
                'AI003':'Use ChartPanel and nicegui_base.visualization wrappers.',
                'AI004':'Use Page/Section/Grid/Stack/SplitPane or a page pattern.',
                'AI005':'Use the corresponding nicegui_base component.',
            }[code]
            self.issue(code, ValidationSeverity.ERROR, node, msg, fix)

        if last == 'style' and node.args:
            text = _literal_text(node.args[0])
            if text:
                self.issue('AI006', ValidationSeverity.ERROR, node,
                           'Inline visual CSS detected through .style().',
                           'Use semantic framework parameters/tokens; extend the framework if a visual primitive is missing.')
        if last == 'classes' and node.args:
            text = _literal_text(node.args[0])
            if text and not all(token.startswith('cui-') for token in text.split() if token):
                self.issue('AI007', ValidationSeverity.WARNING, node,
                           'Raw utility/component classes detected.',
                           'Prefer semantic nicegui_base APIs; app-level visual classes require a documented escape hatch.')

        for kw in node.keywords:
            if kw.arg == 'icon':
                value = _literal_text(kw.value)
                if value is not None:
                    self.issue('AI008', ValidationSeverity.WARNING, kw.value,
                               f'Arbitrary icon string {value!r} detected.',
                               'Use Icons.* so icon names are registry-backed and validated.')
            if kw.arg in {'style','classes'}:
                text = _literal_text(kw.value)
                if text:
                    self.issue('AI006' if kw.arg=='style' else 'AI007',
                               ValidationSeverity.ERROR if kw.arg=='style' else ValidationSeverity.WARNING,
                               kw.value, f'Raw {kw.arg} value detected.', 'Use semantic nicegui_base APIs.')

        if last in _VISUAL_CALLS:
            for arg in node.args:
                text = _literal_text(arg)
                if text and _HTTP.search(text):
                    self.issue('AI009', ValidationSeverity.ERROR, arg,
                               'Remote visual/runtime resource URL detected.',
                               'Package the resource locally through the Visual Asset System.')

        if 'app.storage.' in name or name.startswith('app.storage'):
            self.issue('AI010', ValidationSeverity.ERROR, node,
                       'Direct NiceGUI storage access detected.',
                       'Use PreferenceService, UserPreferences, SessionState, TabState or NiceGUIStateServices.')
        if name in {'asyncio.create_task', 'asyncio.ensure_future'} or name.endswith('.create_task') and parts and parts[0] == 'asyncio':
            self.issue('AI015', ValidationSeverity.WARNING, node,
                       'Raw asyncio task creation detected.',
                       'Use WorkspaceRuntime.create_task, AsyncAction, CancelableTask, or a durable job boundary so lifecycle ownership is explicit.')
        if last == 'props' and node.args and _literal_text(node.args[0]):
            self.issue('AI016', ValidationSeverity.WARNING, node,
                       'Raw renderer/Quasar props detected in application code.',
                       'Prefer typed NiceGUI Base parameters; use a narrow documented escape hatch only when the public API cannot express the requirement.')
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, str):
            return
        text = node.value
        if (_HEX.search(text) or _CSS_VALUE.search(text) or _PIXEL.search(text)) and ('style' in text.lower() or '{' in text or ';' in text):
            self.issue('AI011', ValidationSeverity.WARNING, node,
                       'Hard-coded visual value detected in a string.',
                       'Move colors/spacing/sizes into framework semantic tokens.')
        if _EMOJI.search(text):
            # Avoid noisy warnings for prose/docs: only flag short UI-like literals.
            if len(text) <= 80:
                self.issue('AI012', ValidationSeverity.WARNING, node,
                           'Emoji-like symbol detected in a short UI string.',
                           'Use Icons.* for interface iconography; emoji may remain in user-authored content.')
        self.generic_visit(node)

    def validate_ui_sql(self) -> None:
        parts = {p.lower() for p in self.path.parts}
        if parts.intersection(self.config.page_dirs) and _SQL.search(self.source):
            fake = ast.parse('x').body[0]
            fake.lineno = next((i for i,l in enumerate(self.lines,1) if _SQL.search(l)), 1)
            fake.col_offset = 0
            self.issue('AI013', ValidationSeverity.WARNING, fake,
                       'SQL text appears inside a UI/page module.',
                       'Move database access into a repository/service layer and call it from the page.')


def validate_python_file(path: str | Path, *, root: str | Path | None = None, config: ValidatorConfig | None = None) -> tuple[ValidationIssue, ...]:
    file = Path(path)
    root_path = Path(root) if root else file.parent
    cfg = config or ValidatorConfig()
    try:
        source = file.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(file))
    except SyntaxError as exc:
        return (ValidationIssue('AI000', ValidationSeverity.ERROR, f'Python syntax error: {exc.msg}', str(file), exc.lineno or 1, exc.offset or 0, 'Fix syntax before framework validation.'),)
    visitor = _PythonValidator(file, root_path, source, cfg)
    visitor.visit(tree)
    visitor.validate_ui_sql()
    return tuple(visitor.issues)


def _validate_text_asset(path: Path, root: Path) -> tuple[ValidationIssue, ...]:
    text = path.read_text(encoding='utf-8', errors='replace')
    rel = str(path.relative_to(root))
    issues: list[ValidationIssue] = []
    suffix = path.suffix.lower()
    if suffix == '.css':
        issues.append(ValidationIssue('AI014', ValidationSeverity.WARNING,
            'Application-level CSS file detected.', rel, 1, 0,
            'Prefer NiceGUI Base semantic APIs; keep custom CSS only for a documented framework gap.'))
        for i, line in enumerate(text.splitlines(), 1):
            if _HTTP.search(line):
                issues.append(ValidationIssue('AI009', ValidationSeverity.ERROR,
                    'Remote runtime resource URL detected in CSS.', rel, i, 0,
                    'Package visual resources locally.'))
            if _HEX.search(line) or _PIXEL.search(line):
                issues.append(ValidationIssue('AI011', ValidationSeverity.WARNING,
                    'Hard-coded visual value detected in application CSS.', rel, i, 0,
                    'Use framework semantic tokens/variables.'))
    elif suffix in {'.html', '.htm'}:
        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if _HTTP.search(line) and any(token in low for token in ('src=', 'href=', 'url(')):
                issues.append(ValidationIssue('AI009', ValidationSeverity.ERROR,
                    'Remote visual/runtime resource detected in HTML.', rel, i, 0,
                    'Use locally packaged framework resources.'))
    return tuple(issues)


def _iter_python(root: Path, config: ValidatorConfig) -> Iterable[Path]:
    excludes = set(config.exclude_dirs)
    for path in root.rglob('*.py'):
        if any(part in excludes for part in path.relative_to(root).parts[:-1]):
            continue
        yield path


def validate_app(root: str | Path, *, config: ValidatorConfig | None = None) -> ValidationReport:
    target = Path(root).resolve()
    cfg = config or ValidatorConfig()
    # A single file is a valid CLI target. Older releases silently scanned zero
    # files because Path.rglob on a file yields nothing; fail-safe validation
    # must inspect the supplied file instead of returning a false green result.
    if target.is_file():
        if target.suffix.lower() == '.py':
            issues = validate_python_file(target, root=target.parent, config=cfg)
        elif target.suffix.lower() in {'.css', '.html', '.htm'}:
            issues = _validate_text_asset(target, target.parent)
        else:
            issues = ()
        return ValidationReport(root=target, issues=tuple(issues), scanned_files=1)
    root_path = target
    issues: list[ValidationIssue] = []
    count = 0
    for path in _iter_python(root_path, cfg):
        count += 1
        issues.extend(validate_python_file(path, root=root_path, config=cfg))
    issues.sort(key=lambda i: (i.path, i.line, i.column, i.code))
    excludes = set(cfg.exclude_dirs)
    for pattern in ('*.css', '*.html', '*.htm'):
        for path in root_path.rglob(pattern):
            if any(part in excludes for part in path.relative_to(root_path).parts[:-1]):
                continue
            count += 1
            issues.extend(_validate_text_asset(path, root_path))
    issues.sort(key=lambda i: (i.path, i.line, i.column, i.code))
    return ValidationReport(root=root_path, issues=tuple(issues), scanned_files=count)
