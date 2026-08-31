from __future__ import annotations

import re
from pathlib import Path

from nicegui_base.design.tokens import TYPOGRAPHY

from .models import GovernanceFinding

_FONT_SIZE_RE = re.compile(r'font-size\s*:\s*([^;}\n]+)', re.IGNORECASE)
_LINE_HEIGHT_RE = re.compile(r'line-height\s*:\s*([^;}\n]+)', re.IGNORECASE)
_FONT_WEIGHT_RE = re.compile(r'font-weight\s*:\s*([^;}\n]+)', re.IGNORECASE)
_FONT_SHORTHAND_RE = re.compile(r'(?<![-\w])font\s*:\s*([^;}\n]+)', re.IGNORECASE)
_MOTION_RE = re.compile(r'(?:transition|transition-duration|animation|animation-duration)\s*:\s*([^;}\n]+)', re.IGNORECASE)
_RAW_LENGTH_RE = re.compile(r'(?<![-\w])(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|pt)(?![-\w])', re.IGNORECASE)
_RAW_WEIGHT_RE = re.compile(r'(?<![-\w])(?:[1-9]\d{2})(?![-\w])')
_RAW_DURATION_RE = re.compile(r'(?<![-\w])(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)(?![-\w])', re.IGNORECASE)
_RAW_EASING_RE = re.compile(r'(?<![-\w])(?:linear|ease|ease-in|ease-out|ease-in-out|cubic-bezier\([^)]*\))(?![-\w])', re.IGNORECASE)
_ECHART_FONT_RE = re.compile(r"['\"]font(?:Size|Weight)['\"]\s*:\s*(\d+(?:\.\d+)?)")
_ECHART_DURATION_RE = re.compile(r"['\"]animationDuration(?:Update)?['\"]\s*:\s*(\d+(?:\.\d+)?)")

_EXCLUDED = {Path('nicegui_base/design/tokens.py')}


def _line(text: str, offset: int) -> int:
    return text.count('\n', 0, offset) + 1


def _raw_typography_value(value: str, *, weight: bool = False) -> bool:
    value = value.strip().replace('!important', '').strip()
    if value in {'0', 'normal', 'inherit', 'initial', 'unset'}:
        return False
    if 'var(--cui-' in value:
        # A composite shorthand can contain both governed vars and a raw value;
        # callers still inspect the full shorthand separately.
        if not (_RAW_LENGTH_RE.search(value) or (weight and _RAW_WEIGHT_RE.search(value))):
            return False
    return bool(_RAW_WEIGHT_RE.search(value) if weight else _RAW_LENGTH_RE.search(value))


def scan_typography_motion_contract(root: Path) -> tuple[GovernanceFinding, ...]:
    """Enforce v2 typography/motion token ownership across rendered sources.

    Raw values were historically introduced by screenshot hotfixes. v2 preserves
    approved visuals but requires every absolute type dimension, numeric weight,
    duration and easing to resolve through the Company token authority.
    """
    findings: list[GovernanceFinding] = []
    package_root = root / 'nicegui_base'
    for path in sorted(package_root.rglob('*.py')):
        rel = path.relative_to(root)
        if rel in _EXCLUDED:
            continue
        text = path.read_text(encoding='utf-8')
        for match in _FONT_SIZE_RE.finditer(text):
            if _raw_typography_value(match.group(1)):
                findings.append(GovernanceFinding('type.font-size-token', str(rel), f'font-size must use a --cui-* token; found {match.group(1).strip()!r}', _line(text, match.start())))
        for match in _LINE_HEIGHT_RE.finditer(text):
            value = match.group(1).strip().replace('!important', '').strip()
            if value not in {'0', 'normal', 'inherit', 'initial', 'unset'} and (re.search(r'(?<![-\w])(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|pt)?(?![-\w])', value) and 'var(--cui-' not in value):
                findings.append(GovernanceFinding('type.line-height-token', str(rel), f'line-height must use a --cui-* token; found {match.group(1).strip()!r}', _line(text, match.start())))
        for match in _FONT_WEIGHT_RE.finditer(text):
            if _raw_typography_value(match.group(1), weight=True):
                findings.append(GovernanceFinding('type.font-weight-token', str(rel), f'font-weight must use a --cui-* token; found {match.group(1).strip()!r}', _line(text, match.start())))
        for match in _FONT_SHORTHAND_RE.finditer(text):
            value = match.group(1).strip()
            if value.lower() == 'inherit':
                continue
            if _RAW_LENGTH_RE.search(value) or _RAW_WEIGHT_RE.search(value):
                findings.append(GovernanceFinding('type.font-shorthand-token', str(rel), f'font shorthand must use governed tokens; found {value!r}', _line(text, match.start())))
        for match in _MOTION_RE.finditer(text):
            value = match.group(1).strip()
            if value.lower() == 'none':
                continue
            if _RAW_DURATION_RE.search(value):
                findings.append(GovernanceFinding('motion.duration-token', str(rel), f'motion duration must use a --cui-* token; found {value!r}', _line(text, match.start())))
            if _RAW_EASING_RE.search(value):
                findings.append(GovernanceFinding('motion.easing-token', str(rel), f'motion easing must use a --cui-* token; found {value!r}', _line(text, match.start())))
        # Canvas/ECharts cannot consume DOM custom properties. It still uses the
        # same Python token authority instead of local numeric literals.
        for match in _ECHART_FONT_RE.finditer(text):
            findings.append(GovernanceFinding('type.chart-token', str(rel), f'chart typography must use nicegui_base.design.tokens; found literal {match.group(1)}', _line(text, match.start())))
        for match in _ECHART_DURATION_RE.finditer(text):
            findings.append(GovernanceFinding('motion.chart-token', str(rel), f'chart animation duration must use nicegui_base.design.tokens; found literal {match.group(1)}', _line(text, match.start())))

    # Semantic hierarchy: this is product behavior, not merely a token-presence check.
    order = ('display', 'page_title', 'heading', 'subheading', 'body', 'label', 'caption')
    sizes = [float(TYPOGRAPHY[name]['size']) for name in order]
    if any(left < right for left, right in zip(sizes, sizes[1:])):
        findings.append(GovernanceFinding('type.semantic-hierarchy', 'nicegui_base/design/tokens.py', f'typography role sizes must descend across {order}; got {sizes}'))
    app = TYPOGRAPHY.get('app_identity', {})
    if float(app.get('size', 0)) < 16 or int(app.get('weight', 0)) < 700:
        findings.append(GovernanceFinding('type.app-identity', 'nicegui_base/design/tokens.py', 'application identity must remain >=16px and >=700 weight'))
    profile_hint = TYPOGRAPHY.get('profile_hint', {})
    profile_name = TYPOGRAPHY.get('profile_name', {})
    if float(profile_name.get('size', 0)) < float(profile_hint.get('size', 0)) or int(profile_name.get('weight', 0)) <= int(profile_hint.get('weight', 0)):
        findings.append(GovernanceFinding('type.profile-hierarchy', 'nicegui_base/design/tokens.py', 'profile name must remain visually stronger than greeting/helper text'))
    return tuple(findings)
