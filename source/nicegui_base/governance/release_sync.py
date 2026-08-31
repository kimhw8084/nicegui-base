from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .public_api import write_public_api_contract

_PRERELEASE_VERSION_RE = re.compile(r'(?<!\d)\d+\.\d+\.\d+(?:a|b|rc)\d+(?!\d)')

_AUTHORITY_JSONS = (
    'COMPATIBILITY.json',
    'FRAMEWORK_CATALOG.json',
    'AI_CONSTRUCTION_MANIFEST.json',
    'BUILD_ENV_RUNTIME_CONTRACT.json',
    'nicegui_base/runtime/compatibility.json',
    'nicegui_base/ai/framework_catalog.json',
    'nicegui_base/ai/construction_manifest.json',
    'nicegui_base/certification/certification_manifest.json',
)

_CURRENT_EVIDENCE_JSONS = (
    'CERTIFICATION_REPORT.json',
    'CLEAN_INSTALL_CERTIFICATION.json',
    'LIVE_CERTIFICATION_READINESS.json',
    'LIVE_COMPONENT_COVERAGE.json',
)

_CURRENT_DOCS = (
    'README.md',
    '00_READ_ME_FIRST.md',
    'START_HERE.md',
    'docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md',
    'docs/RUNTIME_COMPATIBILITY_GUIDE.md',
    'docs/COMPANY_CERTIFICATION_CHECKLIST.md',
    'docs/V2_PUBLIC_API_POLICY.md',
    'nicegui_base/ai/guides/AGENTS.md',
    'mac_bundle/README.md',
    'mac_bundle/setup_mac.sh',
    'linux_bundle/README.md',
    'linux_bundle/setup_linux.sh',
)

_GUIDE_MIRRORS = (
    ('docs/RUNTIME_COMPATIBILITY_GUIDE.md', 'nicegui_base/ai/guides/RUNTIME_COMPATIBILITY_GUIDE.md'),
    ('docs/COMPANY_CERTIFICATION_CHECKLIST.md', 'nicegui_base/ai/guides/COMPANY_CERTIFICATION_CHECKLIST.md'),
    ('docs/PUBLIC_API_INDEX.md', 'nicegui_base/ai/guides/PUBLIC_API_INDEX.md'),
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _replace_version_values(value: Any, version: str) -> Any:
    if isinstance(value, str):
        # Only replace release-candidate identities. Intentional references to
        # the stable promotion target 2.0.0 must never become an RC string.
        return _PRERELEASE_VERSION_RE.sub(version, value)
    if isinstance(value, list):
        return [_replace_version_values(item, version) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_version_values(item, version) for item in value)
    if isinstance(value, dict):
        return {key: _replace_version_values(item, version) for key, item in value.items()}
    return value


def _stable_default_text(default: dict[str, Any]) -> str | None:
    if not default.get('present'):
        return None
    if 'value' in default:
        return repr(default['value'])
    if 'enum' in default:
        return repr(default['enum'].rsplit('.', 1)[-1])
    if 'set' in default:
        values = ', '.join(_stable_default_text(item) or '?' for item in default['set'])
        return f'frozenset({{{values}}})'
    if 'tuple' in default:
        values = ', '.join(_stable_default_text(item) or '?' for item in default['tuple'])
        if len(default['tuple']) == 1:
            values += ','
        return f'({values})'
    if 'list' in default:
        return '[' + ', '.join(_stable_default_text(item) or '?' for item in default['list']) + ']'
    if 'dict' in default:
        entries = ', '.join(f'{key!r}: {_stable_default_text(item) or "?"}' for key, item in default['dict'].items())
        return '{' + entries + '}'
    return default.get('repr') or default.get('type') or '?'


def _render_signature(symbol: dict[str, Any]) -> str:
    callable_contract = symbol.get('callable')
    if not isinstance(callable_contract, dict):
        return ''
    parts: list[str] = []
    for parameter in callable_contract.get('parameters', []):
        if not isinstance(parameter, dict):
            continue
        name = str(parameter.get('name', ''))
        kind = str(parameter.get('kind', ''))
        annotation = str(parameter.get('annotation', ''))
        if kind == 'VAR_POSITIONAL':
            name = '*' + name
        elif kind == 'VAR_KEYWORD':
            name = '**' + name
        text = name
        if annotation:
            text += f': {annotation!r}'
        default = parameter.get('default')
        if isinstance(default, dict):
            rendered = _stable_default_text(default)
            if rendered is not None:
                text += f' = {rendered}'
        parts.append(text)
    result = '(' + ', '.join(parts) + ')'
    returns = str(callable_contract.get('return', ''))
    if returns and returns != '<unavailable>':
        result += f' -> {returns!r}'
    return result


def render_public_api_index(root: Path, *, version: str, nicegui: str) -> str:
    contract = _load(root / 'PUBLIC_API_CONTRACT.json')
    symbols = contract.get('symbols')
    if not isinstance(symbols, dict):
        raise ValueError('PUBLIC_API_CONTRACT.json symbols must be an object')
    lines = [
        '# NiceGUI Base Public API Index', '',
        f'Framework version: `{version}`  ',
        f'NiceGUI runtime: `{nicegui}`  ',
        f'Frozen root exports: **{len(symbols)}**', '',
        'Generated from `PUBLIC_API_CONTRACT.json`. The JSON contract—not this rendered table—is authoritative for compatibility checks.', '',
        '| Symbol | Kind | Owning module | Signature |',
        '|---|---|---|---|',
    ]
    for name in sorted(symbols):
        symbol = symbols[name]
        if not isinstance(symbol, dict):
            continue
        signature = _render_signature(symbol).replace('|', '\\|')
        module = str(symbol.get('module', '')).replace('|', '\\|')
        kind = str(symbol.get('kind', '')).replace('|', '\\|')
        lines.append(f'| `{name}` | {kind} | `{module}` | `{signature}` |')
    return '\n'.join(lines) + '\n'


def sync_release_authority(root: str | Path = '.') -> tuple[Path, ...]:
    """Synchronize current release-facing copies from release_authority.json.

    Promotion workflow intentionally has one editable identity source: update
    nicegui_base/release_authority.json, then run this command in a fresh Python
    process. Historical PHASE_* evidence is never rewritten.
    """
    root = Path(root).resolve()
    authority = _load(root / 'nicegui_base/release_authority.json')
    version = str(authority['framework_version'])
    nicegui = str(authority['nicegui_version'])
    touched: list[Path] = []

    pyproject = root / 'pyproject.toml'
    text = pyproject.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^version\s*=\s*"[^"]+"', f'version = "{version}"', text, count=1)
    text = re.sub(r'"nicegui==[^"]+"', f'"nicegui=={nicegui}"', text)
    pyproject.write_text(text, encoding='utf-8')
    touched.append(pyproject)

    for rel in _AUTHORITY_JSONS:
        path = root / rel
        if not path.exists():
            continue
        data = _replace_version_values(_load(path), version)
        data['framework_version'] = version
        if 'nicegui_version' in data:
            data['nicegui_version'] = nicegui
        _write_json(path, data)
        touched.append(path)

    # Root/package authority mirrors are exact copies, not independently edited JSON.
    for source, target in (
        ('FRAMEWORK_CATALOG.json', 'nicegui_base/ai/framework_catalog.json'),
        ('AI_CONSTRUCTION_MANIFEST.json', 'nicegui_base/ai/construction_manifest.json'),
        ('COMPATIBILITY.json', 'nicegui_base/runtime/compatibility.json'),
    ):
        shutil.copyfile(root / source, root / target)

    for rel in _CURRENT_EVIDENCE_JSONS:
        path = root / rel
        if not path.exists():
            continue
        data = _replace_version_values(_load(path), version)
        if isinstance(data, dict):
            data['framework_version'] = version
            _write_json(path, data)
            touched.append(path)

    # Regenerate signature-aware API authority after the version source is current.
    write_public_api_contract(root, framework_version=version)
    touched.append(root / 'PUBLIC_API_CONTRACT.json')

    for rel in _CURRENT_DOCS:
        path = root / rel
        if not path.exists():
            continue
        path.write_text(_PRERELEASE_VERSION_RE.sub(version, path.read_text(encoding='utf-8')), encoding='utf-8')
        touched.append(path)

    api_index = root / 'docs/PUBLIC_API_INDEX.md'
    api_index.write_text(render_public_api_index(root, version=version, nicegui=nicegui), encoding='utf-8')
    touched.append(api_index)
    for source, target in _GUIDE_MIRRORS:
        shutil.copyfile(root / source, root / target)
        touched.append(root / target)

    return tuple(dict.fromkeys(touched))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Synchronize NiceGUI Base current-release authorities from release_authority.json.')
    parser.add_argument('--root', default='.')
    args = parser.parse_args(argv)
    touched = sync_release_authority(args.root)
    for path in touched:
        print(path)
    print(f'Synchronized {len(touched)} current-release files from release_authority.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
