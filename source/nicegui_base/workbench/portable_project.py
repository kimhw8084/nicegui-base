from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

PORTABLE_SCHEMA_VERSION = 1
PORTABLE_FORMAT = 'nicegui-base-portable-project'
MAX_PORTABLE_BYTES = 5 * 1024 * 1024
_ALLOWED_FILES = frozenset({'manifest.json', 'workbench_state.json', 'proof_evidence.json', 'README.txt'})
_SENSITIVE_KEYS = frozenset({
    'password', 'passwd', 'secret', 'token', 'access_token', 'refresh_token', 'authorization',
    'cookie', 'cookies', 'api_key', 'apikey', 'private_key', 'connection_string', 'client_secret',
})


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, default=str) + '\n').encode('utf-8')


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(name: str) -> bool:
    path = PurePosixPath(str(name).replace('\\', '/'))
    return bool(name) and not path.is_absolute() and '..' not in path.parts and '\x00' not in name


def _sensitive_paths(value: Any, path: tuple[str, ...] = ()) -> tuple[str, ...]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.casefold().replace('-', '_').strip()
            current = (*path, key)
            if normalized in _SENSITIVE_KEYS:
                findings.append('.'.join(current))
            findings.extend(_sensitive_paths(item, current))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(_sensitive_paths(item, (*path, str(index))))
    return tuple(dict.fromkeys(findings))


def normalize_proof_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    allowed = {
        'project_signature', 'handoff_status', 'source_ok', 'source_findings', 'runtime', 'browser',
        'framework_version', 'environment', 'portable_integrity',
    }
    result = {str(key): deepcopy(item) for key, item in value.items() if str(key) in allowed}
    sensitive = _sensitive_paths(result)
    if sensitive:
        return {}
    # Bound persisted evidence so browser/runtime logs cannot turn user storage into a log sink.
    encoded = _json_bytes(result)
    return result if len(encoded) <= 512 * 1024 else {}


@dataclass(frozen=True, slots=True)
class PortableProjectInspection:
    ok: bool
    findings: tuple[str, ...]
    framework_version: str
    state_version: int
    project_signature: str
    file_count: int
    proof_present: bool

    def to_dict(self) -> dict[str, object]:
        return {
            'ok': self.ok,
            'findings': list(self.findings),
            'framework_version': self.framework_version,
            'state_version': self.state_version,
            'project_signature': self.project_signature,
            'file_count': self.file_count,
            'proof_present': self.proof_present,
        }


def build_portable_project_bundle(state: Mapping[str, Any], *, framework_version: str, proof_evidence: Mapping[str, Any] | None = None) -> bytes:
    from .project_history import project_signature
    from .project_state import normalize_state

    normalized = normalize_state(state)
    proof = normalize_proof_evidence(proof_evidence if proof_evidence is not None else normalized.get('proof_evidence'))
    normalized = deepcopy(normalized)
    normalized.pop('proof_evidence', None)

    sensitive = _sensitive_paths({'state': normalized, 'proof': proof})
    if sensitive:
        raise ValueError('Portable project contains sensitive-key fields: ' + ', '.join(sensitive[:8]))

    readme = (
        'NiceGUI Base Portable Golden Project\n'
        'This bundle contains bounded Workbench development state, presets/history, and optional proof evidence.\n'
        'It intentionally excludes browser storage, credentials, cookies, authorization headers, and production secrets.\n'
    ).encode('utf-8')
    files: dict[str, bytes] = {
        'workbench_state.json': _json_bytes(normalized),
        'README.txt': readme,
    }
    if proof:
        files['proof_evidence.json'] = _json_bytes(proof)

    manifest = {
        'format': PORTABLE_FORMAT,
        'schema_version': PORTABLE_SCHEMA_VERSION,
        'framework_version': str(framework_version),
        'state_version': int(normalized.get('version') or 0),
        'project_signature': project_signature(normalized.get('project') or {}),
        'proof_present': bool(proof),
        'files': {name: _sha256(content) for name, content in sorted(files.items())},
    }
    files['manifest.json'] = _json_bytes(manifest)

    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name])
    payload = output.getvalue()
    if len(payload) > MAX_PORTABLE_BYTES:
        raise ValueError(f'Portable project exceeds {MAX_PORTABLE_BYTES // (1024 * 1024)} MiB limit.')
    inspection = inspect_portable_project_bundle(payload, expected_framework_version=str(framework_version))
    if not inspection.ok:
        raise ValueError('Portable project self-check failed: ' + '; '.join(inspection.findings))
    return payload


def inspect_portable_project_bundle(payload: bytes, *, expected_framework_version: str | None = None) -> PortableProjectInspection:
    findings: list[str] = []
    framework_version = ''
    state_version = 0
    project_sig = ''
    proof_present = False
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        return PortableProjectInspection(False, ('bundle:not_bytes',), '', 0, '', 0, False)
    raw = bytes(payload)
    if not raw or len(raw) > MAX_PORTABLE_BYTES:
        return PortableProjectInspection(False, ('bundle:size',), '', 0, '', 0, False)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                findings.append('bundle:duplicate_paths')
            for name in names:
                if not _safe_name(name):
                    findings.append(f'bundle:unsafe_path:{name}')
                if name not in _ALLOWED_FILES:
                    findings.append(f'bundle:unexpected_file:{name}')
            bad = archive.testzip()
            if bad:
                findings.append(f'bundle:crc:{bad}')
            if 'manifest.json' not in names or 'workbench_state.json' not in names:
                findings.append('bundle:required_files')
                raise ValueError('required files unavailable')
            manifest = json.loads(archive.read('manifest.json'))
            state = json.loads(archive.read('workbench_state.json'))
            if not isinstance(manifest, Mapping) or manifest.get('format') != PORTABLE_FORMAT:
                findings.append('manifest:format')
            if manifest.get('schema_version') != PORTABLE_SCHEMA_VERSION:
                findings.append('manifest:schema_version')
            framework_version = str(manifest.get('framework_version') or '')
            if expected_framework_version is not None and framework_version != str(expected_framework_version):
                findings.append(f'manifest:framework_version:{framework_version}')
            try:
                state_version = int(manifest.get('state_version') or 0)
            except (TypeError, ValueError):
                findings.append('manifest:state_version')
                state_version = 0
            project_sig = str(manifest.get('project_signature') or '')
            file_hashes = manifest.get('files') if isinstance(manifest.get('files'), Mapping) else {}
            for name, expected in file_hashes.items():
                if name not in names:
                    findings.append(f'manifest:missing:{name}')
                    continue
                actual = _sha256(archive.read(name))
                if actual != str(expected):
                    findings.append(f'manifest:sha256:{name}')
            from .project_history import project_signature
            from .project_state import normalize_state
            normalized = normalize_state(state)
            actual_sig = project_signature(normalized.get('project') or {})
            if actual_sig != project_sig:
                findings.append('manifest:project_signature')
            sensitive = _sensitive_paths(normalized)
            if sensitive:
                findings.append('bundle:sensitive_keys:' + ','.join(sensitive[:4]))
            proof_present = 'proof_evidence.json' in names
            if proof_present:
                evidence = json.loads(archive.read('proof_evidence.json'))
                normalized_proof = normalize_proof_evidence(evidence)
                if evidence and not normalized_proof:
                    findings.append('proof:invalid_or_sensitive')
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError) as exc:
        if not findings:
            findings.append(f'bundle:{type(exc).__name__}')
    findings = list(dict.fromkeys(findings))
    return PortableProjectInspection(not findings, tuple(findings), framework_version, state_version, project_sig, len(names) if 'names' in locals() else 0, proof_present)


def extract_portable_project_bundle(payload: bytes, *, expected_framework_version: str) -> tuple[dict[str, Any], dict[str, Any], PortableProjectInspection]:
    inspection = inspect_portable_project_bundle(payload, expected_framework_version=expected_framework_version)
    if not inspection.ok:
        raise ValueError('Portable project rejected: ' + '; '.join(inspection.findings))
    with zipfile.ZipFile(io.BytesIO(bytes(payload))) as archive:
        state = json.loads(archive.read('workbench_state.json'))
        proof = json.loads(archive.read('proof_evidence.json')) if 'proof_evidence.json' in archive.namelist() else {}
    from .project_state import normalize_state
    normalized = normalize_state(state)
    normalized['proof_evidence'] = normalize_proof_evidence(proof)
    return normalized, normalized['proof_evidence'], inspection


__all__ = [
    'MAX_PORTABLE_BYTES', 'PORTABLE_FORMAT', 'PORTABLE_SCHEMA_VERSION', 'PortableProjectInspection',
    'build_portable_project_bundle', 'extract_portable_project_bundle', 'inspect_portable_project_bundle',
    'normalize_proof_evidence',
]
