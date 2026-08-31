from __future__ import annotations

import re
from pathlib import Path

from .models import GovernanceFinding

_RADIUS_RE = re.compile(r'border-radius\s*:\s*([^;}\n]+)', re.IGNORECASE)
_RADIUS_LITERAL_RE = re.compile(r'(?<![-\w])(?:\d+(?:\.\d+)?px|\d+(?:\.\d+)?%)(?![-\w])', re.IGNORECASE)
_Z_INDEX_RE = re.compile(r'z-index\s*:\s*([^;}\n]+)', re.IGNORECASE)
_Z_INDEX_INTEGER_RE = re.compile(r'^\s*(\d+)\s*(?:!important)?\s*$')
_ALLOWED_LITERAL_VALUES = {'0', '0px'}

_PROTECTED_CORE_TOKENS = (
    'shell-header-height',
    'shell-sidebar-width',
    'shell-sidebar-compact-width',
    'page-gutter',
    'surface-padding',
    'control-height',
    'control-small',
    'control-medium',
    'control-large',
    'control-padding-x',
    'icon-button-size',
    'control-content-gap',
    'table-row-height',
    'table-header-height',
    'stack-gap',
    'cluster-gap',
    'content-gap',
    'section-gap',
    'nav-item-height',
    'nav-icon-box',
    'overlay-edge-gap',
)
_CORE_TOKEN_DECL_RE = re.compile(
    r'--cui-(' + '|'.join(re.escape(name) for name in _PROTECTED_CORE_TOKENS) + r')\s*:',
    re.IGNORECASE,
)
_CORE_TOKEN_AUTHORITY = {
    Path('nicegui_base/design/css.py'),
    Path('nicegui_base/design/tokens.py'),
}
_EXCLUDED = {
    Path('nicegui_base/design/tokens.py'),
    Path('nicegui_base/visualization/options.py'),  # canvas/ECharts serialized CSS cannot consume DOM custom properties
}


def scan_geometry_contract(root: Path) -> tuple[GovernanceFinding, ...]:
    """Reject raw border-radius geometry outside the token authority.

    v2 does not force every rectangle to the same radius. Instead every radius must
    resolve through a named Company token (micro/inner/control/surface/overlay/pill/circle),
    making intentional geometry reviewable and preventing screenshot hotfix drift.
    """
    findings: list[GovernanceFinding] = []
    package_root = root / 'nicegui_base'
    for path in sorted(package_root.rglob('*.py')):
        rel = path.relative_to(root)
        if rel in _EXCLUDED:
            continue
        text = path.read_text(encoding='utf-8')
        for match in _RADIUS_RE.finditer(text):
            value = match.group(1).strip().replace('!important', '').strip()
            if value in _ALLOWED_LITERAL_VALUES:
                continue
            if 'var(--cui-radius-' in value or 'calc(var(--cui-radius-' in value:
                continue
            literal = _RADIUS_LITERAL_RE.search(value)
            if literal:
                line = text.count('\n', 0, match.start()) + 1
                findings.append(GovernanceFinding(
                    rule='geometry.radius-token',
                    path=str(rel),
                    line=line,
                    detail=f'border-radius must use a --cui-radius-* token; found {match.group(1).strip()!r}',
                ))
    # Values below 100 are allowed for strictly local stacking contexts (markers,
    # table headers, focused range thumbs). Global/application layers must use
    # the named layer authority so modules cannot recreate the old 9999 race.
    for path in sorted(package_root.rglob('*.py')):
        rel = path.relative_to(root)
        if rel in _EXCLUDED:
            continue
        text = path.read_text(encoding='utf-8')
        for match in _Z_INDEX_RE.finditer(text):
            value = match.group(1).strip()
            integer = _Z_INDEX_INTEGER_RE.match(value)
            if integer and int(integer.group(1)) >= 100:
                line = text.count('\n', 0, match.start()) + 1
                findings.append(GovernanceFinding(
                    rule='geometry.layer-token',
                    path=str(rel),
                    line=line,
                    detail=f'global z-index must use a named --cui-*-z/--cui-layer-* token; found {value!r}',
                ))
    # Core layout/density custom properties have exactly one source authority:
    # design.tokens -> design.css. Downstream CSS may consume them but must never
    # redeclare them, otherwise load-order silently becomes a second constitution.
    for path in sorted(package_root.rglob('*.py')):
        rel = path.relative_to(root)
        if rel in _CORE_TOKEN_AUTHORITY:
            continue
        text = path.read_text(encoding='utf-8')
        for match in _CORE_TOKEN_DECL_RE.finditer(text):
            line = text.count('\n', 0, match.start()) + 1
            findings.append(GovernanceFinding(
                rule='geometry.single-token-authority',
                path=str(rel),
                line=line,
                detail=(
                    f'--cui-{match.group(1)} is generated only by design.tokens/design.css; '
                    'downstream CSS must consume rather than redeclare it'
                ),
            ))
    return tuple(findings)
