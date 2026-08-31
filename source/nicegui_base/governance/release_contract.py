from __future__ import annotations

import json
import re
from pathlib import Path

from .models import GovernanceFinding
from .release_identity import load_release_identity


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return payload


def scan_release_contract(root: Path) -> tuple[GovernanceFinding, ...]:
    findings: list[GovernanceFinding] = []
    authority_path = root / 'nicegui_base/release_authority.json'
    authority = _load(authority_path)
    identity = load_release_identity(root)
    version = identity.framework_version
    nicegui = identity.nicegui_version

    pyproject = (root / 'pyproject.toml').read_text(encoding='utf-8')
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    if not version_match or version_match.group(1) != version:
        findings.append(GovernanceFinding('release.version', 'pyproject.toml', 'project version does not match release_authority.json'))
    if f'nicegui=={nicegui}' not in pyproject:
        findings.append(GovernanceFinding('release.nicegui-pin', 'pyproject.toml', f'nicegui must be pinned to {nicegui}'))

    cert_manifest_path = root / 'nicegui_base/certification/certification_manifest.json'
    if cert_manifest_path.exists():
        cert_manifest = _load(cert_manifest_path)
        if int(cert_manifest.get('phase', -1)) != identity.current_phase:
            findings.append(GovernanceFinding('release.phase-drift', str(cert_manifest_path.relative_to(root)), f'phase={cert_manifest.get("phase")!r}; expected current_phase={identity.current_phase} from release_authority.json'))
    else:
        findings.append(GovernanceFinding('release.missing-certification-manifest', 'nicegui_base/certification/certification_manifest.json', 'packaged certification manifest is missing'))

    json_targets = (
        'COMPATIBILITY.json',
        'FRAMEWORK_CATALOG.json',
        'AI_CONSTRUCTION_MANIFEST.json',
        'BUILD_ENV_RUNTIME_CONTRACT.json',
        'nicegui_base/runtime/compatibility.json',
        'nicegui_base/ai/framework_catalog.json',
        'nicegui_base/ai/construction_manifest.json',
        'nicegui_base/certification/certification_manifest.json',
    )
    for rel in json_targets:
        path = root / rel
        if not path.exists():
            findings.append(GovernanceFinding('release.missing-authority-copy', rel, 'required generated authority copy is missing'))
            continue
        data = _load(path)
        actual = data.get('framework_version')
        if actual != version:
            findings.append(GovernanceFinding('release.version-drift', rel, f'framework_version={actual!r}; expected {version!r}'))
        actual_nicegui = data.get('nicegui_version')
        if actual_nicegui is not None and actual_nicegui != nicegui:
            findings.append(GovernanceFinding('release.nicegui-drift', rel, f'nicegui_version={actual_nicegui!r}; expected {nicegui!r}'))

    current_text_targets = (
        'docs/RUNTIME_COMPATIBILITY_GUIDE.md',
        'docs/COMPANY_CERTIFICATION_CHECKLIST.md',
        'docs/V2_PUBLIC_API_POLICY.md',
        'docs/PUBLIC_API_INDEX.md',
        'README.md', '00_READ_ME_FIRST.md', 'START_HERE.md',
        'docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md',
        'nicegui_base/ai/guides/AGENTS.md',
        'nicegui_base/ai/guides/RUNTIME_COMPATIBILITY_GUIDE.md',
        'nicegui_base/ai/guides/COMPANY_CERTIFICATION_CHECKLIST.md',
        'nicegui_base/ai/guides/PUBLIC_API_INDEX.md',
        'mac_bundle/README.md', 'mac_bundle/setup_mac.sh',
        'linux_bundle/README.md', 'linux_bundle/setup_linux.sh',
    )
    for rel in current_text_targets:
        path = root / rel
        if not path.exists():
            findings.append(GovernanceFinding('release.missing-current-text', rel, 'current release-facing text is missing'))
            continue
        text = path.read_text(encoding='utf-8')
        if version not in text:
            findings.append(GovernanceFinding('release.current-text-drift', rel, f'current release-facing text does not identify {version}'))
        if rel in {'README.md', '00_READ_ME_FIRST.md', 'START_HERE.md', 'docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md'} and f'Wave {identity.current_wave}' not in text:
            findings.append(GovernanceFinding('release.current-wave-text-drift', rel, f'current release-facing text does not identify Wave {identity.current_wave}'))

    pairs = (
        ('FRAMEWORK_CATALOG.json', 'nicegui_base/ai/framework_catalog.json'),
        ('AI_CONSTRUCTION_MANIFEST.json', 'nicegui_base/ai/construction_manifest.json'),
        ('COMPATIBILITY.json', 'nicegui_base/runtime/compatibility.json'),
    )
    for left, right in pairs:
        if (root / left).exists() and (root / right).exists() and _load(root / left) != _load(root / right):
            findings.append(GovernanceFinding('release.copy-drift', f'{left} <> {right}', 'root/package authority copies differ'))

    return tuple(findings)
