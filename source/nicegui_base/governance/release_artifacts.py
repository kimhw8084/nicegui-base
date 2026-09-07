from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

_TRANSIENT_DIRS = {
    '.git', '.hg', '.svn', '.mypy_cache', '.pytest_cache', '.ruff_cache',
    '__pycache__', 'build', '.tox', '.nox',
}
_TRANSIENT_SUFFIXES = ('.pyc', '.pyo')
_HASH_LINE = re.compile(r'^([0-9a-f]{64})  (.+)$')


@dataclass(frozen=True, slots=True)
class ManifestVerification:
    path: Path
    expected: int
    verified: int
    missing: tuple[str, ...] = ()
    mismatches: tuple[str, ...] = ()
    extras: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.missing and not self.mismatches and not self.extras and self.expected == self.verified

    def to_dict(self) -> dict[str, object]:
        return {
            'path': str(self.path), 'expected': self.expected, 'verified': self.verified,
            'missing': list(self.missing), 'mismatches': list(self.mismatches),
            'extras': list(self.extras), 'status': 'PASS' if self.passed else 'FAIL',
        }


@dataclass(frozen=True, slots=True)
class WheelVerification:
    path: Path
    sha256: str
    size_bytes: int
    record_rows: int
    record_hashes_verified: int
    record_mismatches: int
    metadata_name: str
    metadata_version: str
    requires_dist: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.record_mismatches == 0

    def to_dict(self) -> dict[str, object]:
        return {
            'path': str(self.path), 'sha256': self.sha256, 'size_bytes': self.size_bytes,
            'record_rows': self.record_rows, 'record_hashes_verified': self.record_hashes_verified,
            'record_mismatches': self.record_mismatches, 'metadata_name': self.metadata_name,
            'metadata_version': self.metadata_version, 'requires_dist': list(self.requires_dist),
            'status': 'PASS' if self.passed else 'FAIL',
        }


@dataclass(frozen=True, slots=True)
class WheelSourceVerification:
    root: Path
    wheel: Path
    compared_files: int
    mismatches: tuple[str, ...] = ()
    missing_from_source: tuple[str, ...] = ()
    missing_from_wheel: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.mismatches and not self.missing_from_source and not self.missing_from_wheel

    def to_dict(self) -> dict[str, object]:
        return {
            'root': str(self.root), 'wheel': str(self.wheel), 'compared_files': self.compared_files,
            'mismatches': list(self.mismatches), 'missing_from_source': list(self.missing_from_source),
            'missing_from_wheel': list(self.missing_from_wheel), 'status': 'PASS' if self.passed else 'FAIL',
        }


@dataclass(frozen=True, slots=True)
class ArchiveVerification:
    path: Path
    sha256: str
    size_bytes: int
    file_count: int
    duplicate_entries: tuple[str, ...]
    unsafe_entries: tuple[str, ...]
    manifest: ManifestVerification | None = None
    source_manifest: ManifestVerification | None = None
    executable_entries: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return (
            not self.duplicate_entries and not self.unsafe_entries
            and (self.manifest is None or self.manifest.passed)
            and (self.source_manifest is None or self.source_manifest.passed)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            'path': str(self.path), 'sha256': self.sha256, 'size_bytes': self.size_bytes,
            'file_count': self.file_count, 'duplicate_entries': list(self.duplicate_entries),
            'unsafe_entries': list(self.unsafe_entries), 'executable_entries': list(self.executable_entries),
            'manifest': self.manifest.to_dict() if self.manifest else None,
            'source_manifest': self.source_manifest.to_dict() if self.source_manifest else None,
            'status': 'PASS' if self.passed else 'FAIL',
        }


def sha256_file(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _is_transient(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in _TRANSIENT_DIRS or part.endswith('.egg-info') for part in rel.parts[:-1]):
        return True
    return path.suffix in _TRANSIENT_SUFFIXES


def iter_release_files(root: str | Path, *, exclude: Iterable[str] = ()) -> tuple[Path, ...]:
    root = Path(root).resolve()
    excluded = {PurePosixPath(item).as_posix().rstrip('/') for item in exclude}
    files: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file() or _is_transient(path, root):
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item + '/') for item in excluded):
            continue
        files.append(path)
    return tuple(sorted(files, key=lambda item: item.relative_to(root).as_posix()))


def write_sha256_manifest(root: str | Path, manifest: str | Path = 'SHA256SUMS.txt', *, exclude: Iterable[str] = ()) -> Path:
    root = Path(root).resolve()
    target = root / manifest
    rel_target = target.relative_to(root).as_posix()
    excluded = set(exclude)
    excluded.add(rel_target)
    lines = [f'{sha256_file(path)}  {path.relative_to(root).as_posix()}' for path in iter_release_files(root, exclude=excluded)]
    target.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
    return target


def _parse_manifest_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text.splitlines():
        if not raw.strip():
            continue
        match = _HASH_LINE.match(raw)
        if not match:
            raise ValueError(f'invalid SHA256 manifest line: {raw!r}')
        digest, rel = match.groups()
        posix = PurePosixPath(rel)
        if posix.is_absolute() or '..' in posix.parts:
            raise ValueError(f'unsafe SHA256 manifest path: {rel!r}')
        if rel in result:
            raise ValueError(f'duplicate SHA256 manifest path: {rel!r}')
        result[rel] = digest
    return result


def verify_sha256_manifest(root: str | Path, manifest: str | Path = 'SHA256SUMS.txt', *, require_exact_coverage: bool = True, exclude: Iterable[str] = ()) -> ManifestVerification:
    root = Path(root).resolve()
    target = root / manifest
    entries = _parse_manifest_text(target.read_text(encoding='utf-8'))
    missing: list[str] = []
    mismatches: list[str] = []
    verified = 0
    for rel, digest in entries.items():
        path = root / rel
        if not path.is_file():
            missing.append(rel); continue
        if sha256_file(path) != digest:
            mismatches.append(rel); continue
        verified += 1
    extras: list[str] = []
    if require_exact_coverage:
        rel_target = target.relative_to(root).as_posix()
        excluded = set(exclude); excluded.add(rel_target)
        actual = {path.relative_to(root).as_posix() for path in iter_release_files(root, exclude=excluded)}
        extras = sorted(actual - set(entries))
    return ManifestVerification(target, len(entries), verified, tuple(sorted(missing)), tuple(sorted(mismatches)), tuple(extras))


def verify_wheel(path: str | Path) -> WheelVerification:
    path = Path(path).resolve()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        record_name = next((name for name in names if name.endswith('.dist-info/RECORD')), None)
        metadata_name = next((name for name in names if name.endswith('.dist-info/METADATA')), None)
        if record_name is None or metadata_name is None:
            raise ValueError('wheel is missing RECORD or METADATA')
        record_text = archive.read(record_name).decode('utf-8')
        rows = list(csv.reader(io.StringIO(record_text)))
        verified = 0; mismatches = 0
        for row in rows:
            if len(row) < 3 or not row[1]:
                continue
            name, encoded_hash, size_text = row[:3]
            algorithm, encoded = encoded_hash.split('=', 1)
            if algorithm != 'sha256':
                mismatches += 1; continue
            data = archive.read(name)
            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode('ascii').rstrip('=')
            if actual != encoded or (size_text and int(size_text) != len(data)):
                mismatches += 1
            else:
                verified += 1
        metadata = archive.read(metadata_name).decode('utf-8', 'replace')
    fields: dict[str, list[str]] = {}
    for line in metadata.splitlines():
        if ': ' in line:
            key, value = line.split(': ', 1); fields.setdefault(key, []).append(value)
    return WheelVerification(
        path=path, sha256=sha256_file(path), size_bytes=path.stat().st_size,
        record_rows=len(rows), record_hashes_verified=verified, record_mismatches=mismatches,
        metadata_name=(fields.get('Name') or [''])[0], metadata_version=(fields.get('Version') or [''])[0],
        requires_dist=tuple(fields.get('Requires-Dist', ())),
    )


def verify_wheel_source_representation(root: str | Path, wheel_path: str | Path) -> WheelSourceVerification:
    root = Path(root).resolve(); wheel_path = Path(wheel_path).resolve()
    mismatches: list[str] = []; missing_source: list[str] = []; compared = 0
    with zipfile.ZipFile(wheel_path) as archive:
        names = {name for name in archive.namelist() if name.startswith('nicegui_base/') and not name.endswith('/')}
        for name in sorted(names):
            source = root / name
            if not source.is_file():
                missing_source.append(name); continue
            compared += 1
            if archive.read(name) != source.read_bytes():
                mismatches.append(name)
        expected: set[str] = set()
        expected.update(path.relative_to(root).as_posix() for path in (root / 'nicegui_base').rglob('*.py') if path.is_file() and '__pycache__' not in path.parts)
        for pattern in (
            'nicegui_base/ai/guides/*.md', 'nicegui_base/ai/*.json', 'nicegui_base/ai/templates/golden/*',
            'nicegui_base/runtime/*.json', 'nicegui_base/certification/certification_manifest.json',
            'nicegui_base/release_authority.json', 'nicegui_base/visual/**/*.svg', 'nicegui_base/visual/**/*.json',
        ):
            expected.update(path.relative_to(root).as_posix() for path in root.glob(pattern) if path.is_file())
        missing_wheel = sorted(expected - names)
    return WheelSourceVerification(root, wheel_path, compared, tuple(mismatches), tuple(sorted(missing_source)), tuple(missing_wheel))


def _safe_archive_name(name: str) -> bool:
    posix = PurePosixPath(name)
    return bool(name) and not posix.is_absolute() and '..' not in posix.parts and '\\' not in name


def build_deterministic_zip(staging_root: str | Path, target: str | Path, *, exclude: Iterable[str] = ()) -> Path:
    root = Path(staging_root).resolve(); target = Path(target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_release_files(root, exclude=exclude):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return target


def _verify_manifest_from_archive(archive: zipfile.ZipFile, manifest_name: str, prefix: str = '') -> ManifestVerification:
    entries = _parse_manifest_text(archive.read(manifest_name).decode('utf-8'))
    missing: list[str] = []; mismatches: list[str] = []; verified = 0
    names = set(archive.namelist())
    for rel, digest in entries.items():
        name = f'{prefix}{rel}' if prefix else rel
        if name not in names:
            missing.append(rel); continue
        if hashlib.sha256(archive.read(name)).hexdigest() != digest:
            mismatches.append(rel); continue
        verified += 1
    if prefix:
        actual = {name[len(prefix):] for name in names if name.startswith(prefix) and name != manifest_name and not name.endswith('/')}
    else:
        actual = {name for name in names if name != manifest_name and not name.endswith('/')}
    extras = tuple(sorted(actual - set(entries)))
    return ManifestVerification(Path(manifest_name), len(entries), verified, tuple(sorted(missing)), tuple(sorted(mismatches)), extras)


def verify_release_archive(path: str | Path, *, manifest_name: str = 'SHA256SUMS.txt', source_manifest_name: str = 'source/SHA256SUMS.txt') -> ArchiveVerification:
    path = Path(path).resolve()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        counts: dict[str, int] = {}
        for name in names: counts[name] = counts.get(name, 0) + 1
        duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))
        unsafe = tuple(sorted(name for name in names if not _safe_archive_name(name)))
        manifest = _verify_manifest_from_archive(archive, manifest_name) if manifest_name in counts else None
        source_manifest = _verify_manifest_from_archive(archive, source_manifest_name, prefix='source/') if source_manifest_name in counts else None
        executable = []
        for info in archive.infolist():
            mode = (info.external_attr >> 16) & 0o7777
            if mode & 0o111:
                executable.append(info.filename)
    return ArchiveVerification(
        path=path, sha256=sha256_file(path), size_bytes=path.stat().st_size,
        file_count=len(names), duplicate_entries=duplicates, unsafe_entries=unsafe,
        manifest=manifest, source_manifest=source_manifest, executable_entries=tuple(sorted(executable)),
    )


__all__ = [
    'ManifestVerification', 'WheelVerification', 'WheelSourceVerification', 'ArchiveVerification', 'sha256_file',
    'iter_release_files', 'write_sha256_manifest', 'verify_sha256_manifest', 'verify_wheel', 'verify_wheel_source_representation',
    'build_deterministic_zip', 'verify_release_archive',
]
