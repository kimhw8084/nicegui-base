from __future__ import annotations

import enum
import hashlib
import inspect
import json
import re
from pathlib import Path
from typing import Any

from .models import GovernanceFinding

CONTRACT_FILE = Path('PUBLIC_API_CONTRACT.json')
_ADDRESS_RE = re.compile(r' at 0x[0-9a-fA-F]+')


def export_names() -> tuple[str, ...]:
    import nicegui_base
    return tuple(sorted(set(nicegui_base.__all__)))


def _annotation(value: Any) -> str:
    if value is inspect.Signature.empty:
        return ''
    try:
        return inspect.formatannotation(value)
    except Exception:
        return str(value)


def _stable_default(value: Any) -> Any:
    if value is inspect.Signature.empty:
        return {'present': False}
    if value is None or isinstance(value, (str, int, float, bool)):
        return {'present': True, 'value': value}
    if isinstance(value, enum.Enum):
        return {'present': True, 'enum': f'{type(value).__module__}.{type(value).__qualname__}.{value.name}'}
    if isinstance(value, (set, frozenset)):
        return {'present': True, 'set': sorted((_stable_default(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))}
    if isinstance(value, tuple):
        return {'present': True, 'tuple': [_stable_default(item) for item in value]}
    if isinstance(value, list):
        return {'present': True, 'list': [_stable_default(item) for item in value]}
    if isinstance(value, dict):
        return {'present': True, 'dict': {str(key): _stable_default(value[key]) for key in sorted(value, key=lambda item: str(item))}}
    text = _ADDRESS_RE.sub('', repr(value))
    return {'present': True, 'type': f'{type(value).__module__}.{type(value).__qualname__}', 'repr': text}


def _callable_contract(value: Any) -> dict[str, Any]:
    try:
        signature = inspect.signature(value)
    except (TypeError, ValueError):
        return {'parameters': [], 'return': '<unavailable>'}
    parameters = []
    for parameter in signature.parameters.values():
        parameters.append({
            'name': parameter.name,
            'kind': parameter.kind.name,
            'annotation': _annotation(parameter.annotation),
            'default': _stable_default(parameter.default),
        })
    return {'parameters': parameters, 'return': _annotation(signature.return_annotation)}


def _symbol_contract(name: str) -> dict[str, Any]:
    import nicegui_base
    value = getattr(nicegui_base, name, None)
    if inspect.isclass(value):
        kind = 'class'
    elif inspect.isfunction(value):
        kind = 'function'
    elif inspect.ismodule(value):
        kind = 'module'
    else:
        kind = 'constant'
    module = getattr(value, '__module__', type(value).__module__ if value is not None else '')
    contract: dict[str, Any] = {'kind': kind, 'module': module}
    if kind in {'class', 'function'}:
        contract['callable'] = _callable_contract(value)
    return contract


def public_api_snapshot() -> dict[str, dict[str, Any]]:
    return {name: _symbol_contract(name) for name in export_names()}


def export_digest(snapshot: dict[str, dict[str, Any]] | None = None) -> str:
    current = snapshot or public_api_snapshot()
    encoded = json.dumps(current, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def write_public_api_contract(root: Path, *, framework_version: str) -> Path:
    symbols = public_api_snapshot()
    payload = {
        'schema_version': 3,
        'framework_version': framework_version,
        'stability': 'frozen-for-2.0',
        'policy': 'Removal or incompatible signature change requires a major-version decision; additions require explicit contract regeneration.',
        'export_count': len(symbols),
        'sha256': export_digest(symbols),
        'symbols': symbols,
    }
    target = root / CONTRACT_FILE
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return target


def scan_public_api_contract(root: Path) -> tuple[GovernanceFinding, ...]:
    target = root / CONTRACT_FILE
    if not target.exists():
        return (GovernanceFinding('api.missing-contract', str(CONTRACT_FILE), 'public API contract is missing'),)
    data = json.loads(target.read_text(encoding='utf-8'))
    expected = data.get('symbols')
    if not isinstance(expected, dict) or data.get('schema_version') != 3:
        return (GovernanceFinding('api.contract-schema', str(CONTRACT_FILE), 'public API contract schema is invalid or pre-v2'),)
    current = public_api_snapshot()
    findings: list[GovernanceFinding] = []
    if current != expected:
        expected_names = set(expected); current_names = set(current)
        removed = sorted(expected_names - current_names)
        added = sorted(current_names - expected_names)
        changed = sorted(name for name in expected_names & current_names if expected[name] != current[name])
        findings.append(GovernanceFinding('api.surface-drift', str(CONTRACT_FILE), f'public API changed; removed={removed[:8]} added={added[:8]} signature/module changes={changed[:8]}'))
    if data.get('sha256') != export_digest(expected):
        findings.append(GovernanceFinding('api.contract-integrity', str(CONTRACT_FILE), 'stored API digest does not match stored symbol contract'))
    return tuple(findings)
