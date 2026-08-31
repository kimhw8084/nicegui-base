from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_VAR_DECL = re.compile(r'(--cui-[\w-]+)\s*:')
_VAR_REF = re.compile(r'var\((--cui-[\w-]+)(?:\s*,[^)]*)?\)')


@dataclass(frozen=True, slots=True)
class VisualAuditIssue:
    code: str
    message: str
    path: str | None = None


REQUIRED_NORMALIZATION_SELECTORS = (
    '.cui-choice.q-checkbox',
    '.cui-choice.q-radio',
    '.cui-slider.q-slider',
    '.cui-tabs-region.q-tabs',
    '.cui-segmented-control.q-btn-toggle',
    '.cui-stepper.q-stepper',
    '.cui-tree.q-tree',
    '.cui-upload.q-uploader',
    '.q-dialog__backdrop',
    '.cui-progress.q-linear-progress',
    '.cui-data-table .ag-root-wrapper',
    '.cui-data-table .ag-header-cell',
    '.cui-data-table .ag-row-selected',
    '@media (forced-colors: active)',
)

FORBIDDEN_INTERNAL_PATTERNS = (
    ('STOCK_NOTIFY', re.compile(r'(?<![\w])(?:ui|_ui\(\))\.notify\s*\(')),
    ('STOCK_MENU_ITEM', re.compile(r'(?<![\w])(?:ui|_ui\(\))\.menu_item\s*\(')),
    ('RAW_MATERIAL_ICON', re.compile(r'(?<![\w])(?:ui|_ui\(\))\.icon\s*\(')),
)


def unresolved_custom_properties(css: str) -> tuple[str, ...]:
    declared = set(_VAR_DECL.findall(css))
    referenced = set(_VAR_REF.findall(css))
    return tuple(sorted(referenced - declared))


def audit_visual_css(css: str) -> tuple[VisualAuditIssue, ...]:
    issues: list[VisualAuditIssue] = []
    for token in unresolved_custom_properties(css):
        issues.append(VisualAuditIssue('UNRESOLVED_TOKEN', f'CSS variable {token} is referenced but never declared.'))
    for selector in REQUIRED_NORMALIZATION_SELECTORS:
        if selector not in css:
            issues.append(VisualAuditIssue('MISSING_NORMALIZER', f'Required visual normalization selector missing: {selector}'))
    if css.count('{') != css.count('}'):
        issues.append(VisualAuditIssue('UNBALANCED_CSS', 'Combined framework CSS braces are not balanced.'))
    return tuple(issues)


def audit_framework_visual_sources(root: str | Path) -> tuple[VisualAuditIssue, ...]:
    root = Path(root)
    integrations = root / 'nicegui_base' / 'integrations'
    issues: list[VisualAuditIssue] = []
    if not integrations.exists():
        return (VisualAuditIssue('SOURCE_ROOT_MISSING', 'nicegui_base/integrations was not found.', str(integrations)),)
    for path in sorted(integrations.rglob('*.py')):
        text = path.read_text(encoding='utf-8')
        for code, pattern in FORBIDDEN_INTERNAL_PATTERNS:
            if pattern.search(text):
                issues.append(VisualAuditIssue(code, f'Forbidden stock NiceGUI visual path detected: {pattern.pattern}', str(path.relative_to(root))))
        if '.tooltip(' in text:
            for line_no, line in enumerate(text.splitlines(), 1):
                if '.tooltip(' in line and "classes('cui-tooltip')" not in line:
                    # two-line assignment is accepted when the next line applies the class
                    lines = text.splitlines()
                    next_line = lines[line_no] if line_no < len(lines) else ''
                    if "classes('cui-tooltip')" not in next_line:
                        issues.append(VisualAuditIssue('UNTHEMED_TOOLTIP', f'Tooltip does not visibly apply cui-tooltip at line {line_no}.', str(path.relative_to(root))))
    return tuple(issues)


__all__ = [
    'VisualAuditIssue', 'REQUIRED_NORMALIZATION_SELECTORS', 'unresolved_custom_properties',
    'audit_visual_css', 'audit_framework_visual_sources',
]
