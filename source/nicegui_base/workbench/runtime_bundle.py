"""Deterministic, installable framework snapshot for generated app downloads.

This is a local development bundle, not publication of a new stable release.
Only package code and declared asset formats are copied; no repository, user
storage, runtime logs, .env, caches, or external dependency bytes are included.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import threading
import zipfile

from nicegui_base.version import FRAMEWORK_VERSION
from .update_identity import BUILD_ID

_ALLOWED = {'.py', '.json', '.svg', '.md', '.css', '.js', '.html', '.txt'}
_CACHE: dict[str, tuple[bytes, dict]] = {}
_LOCK = threading.Lock()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items(), key=lambda item: ('.dist-info/' in item[0], item[0])):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return output.getvalue()


def framework_snapshot() -> tuple[bytes, dict]:
    import nicegui_base
    root = Path(nicegui_base.__file__).resolve().parent
    entries: dict[str, bytes] = {}
    for package in (root, root.parent / 'company_ui'):
        if not package.is_dir():
            continue
        for path in sorted(package.rglob('*')):
            relative = path.relative_to(package)
            if any(part.startswith('.') or part == '__pycache__' for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f'Cannot bundle a symlinked package path: {relative}')
            if path.is_file() and path.suffix in _ALLOWED:
                entries[f'{package.name}/{relative.as_posix()}'] = path.read_bytes()
    # A snapshot must not mix changed on-disk files with the running build identity.
    identity = entries['nicegui_base/workbench/update_identity.py'].decode()
    if repr(BUILD_ID) not in identity and json.dumps(BUILD_ID) not in identity:
        raise RuntimeError('Source changed since the server started. Restart before exporting.')
    source_hashes = {key: _sha(value) for key, value in sorted(entries.items())}
    fingerprint = _sha(json.dumps(source_hashes, sort_keys=True).encode())
    with _LOCK:
        if fingerprint in _CACHE:
            data, manifest = _CACHE[fingerprint]
            return data, json.loads(json.dumps(manifest))
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?', FRAMEWORK_VERSION):
            raise ValueError('Unsupported framework version for development wheel.')
        dist = f'nicegui_base-{FRAMEWORK_VERSION}.dist-info'
        entries[dist + '/METADATA'] = (
            'Metadata-Version: 2.1\nName: nicegui-base\n'
            f'Version: {FRAMEWORK_VERSION}\n'
            'Summary: NiceGUI Base generated-application runtime snapshot\n'
            'Requires-Python: >=3.11,<3.14\nRequires-Dist: nicegui==3.15.0\n\n'
            f'Local development snapshot {BUILD_ID}. Not a stable release qualification.\n'
        ).encode()
        entries[dist + '/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: nicegui-base-runtime-bundle-D3\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
        entries[dist + '/entry_points.txt'] = b'[console_scripts]\nnicegui-base = nicegui_base.cli:main\nnicegui-base-validate = nicegui_base.validate:main\n'
        record = io.StringIO(newline='')
        writer = csv.writer(record, lineterminator='\n')
        for name, value in sorted(entries.items()):
            encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip('=')
            writer.writerow((name, 'sha256=' + encoded, len(value)))
        writer.writerow((dist + '/RECORD', '', ''))
        entries[dist + '/RECORD'] = record.getvalue().encode()
        wheel = _zip(entries)
        manifest = {'schema_version': 1, 'build_id': BUILD_ID, 'framework_version': FRAMEWORK_VERSION,
                    'nicegui_version': '3.15.0', 'source_fingerprint': fingerprint,
                    'source_sha256': source_hashes, 'wheel_sha256': _sha(wheel),
                    'wheel': f'vendor/nicegui_base-{FRAMEWORK_VERSION}-py3-none-any.whl',
                    'qualification': 'development snapshot; installed/browser acceptance is a separate result'}
        _CACHE.clear()  # Bound memory to the current source snapshot.
        _CACHE[fingerprint] = (wheel, manifest)
        return wheel, json.loads(json.dumps(manifest))


def materialize_runtime_bundle(root: Path) -> dict:
    wheel, lock = framework_snapshot()
    vendor = root / 'vendor'
    vendor.mkdir(exist_ok=True)
    (root / lock['wheel']).write_bytes(wheel)
    meta = root / '.nicegui_base'
    meta.mkdir(exist_ok=True)
    (meta / 'runtime_bundle.json').write_text(json.dumps(lock, indent=2, sort_keys=True) + '\n')
    from . import export_bootstrap
    (root / 'bootstrap.py').write_bytes(Path(export_bootstrap.__file__).read_bytes())
    # Preserve the generator's app.py implementation while refusing the older same-version wheel.
    app_file = root / 'app.py'
    source = app_file.read_text()
    import ast
    tree = ast.parse(source)
    after = 0
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.ImportFrom) and node.module == '__future__':
            after = max(after, node.end_lineno)
        elif index == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            after = max(after, node.end_lineno)
    lines = source.splitlines(keepends=True)
    guard = ("\n# Require the framework build included with this generated application.\n"
             "from nicegui_base.workbench.update_identity import BUILD_ID as _NGB_BUILD_ID\n"
             f"if _NGB_BUILD_ID != {BUILD_ID!r}:\n"
             "    raise RuntimeError('Wrong NiceGUI Base build. Run bootstrap.py --setup --run.')\n\n")
    app_file.write_text(''.join(lines[:after]) + guard + ''.join(lines[after:]))
    (root / 'RUN_GENERATED_APP.md').write_text(
        f'# Run this generated app independently\n\nRequired build: `{BUILD_ID}`.\n\n'
        'From this extracted directory, using Python 3.11–3.13:\n\n'
        '```sh\npython3.13 bootstrap.py --setup --run\n```\n\n'
        'Open http://127.0.0.1:8092. Later starts: `python3.13 bootstrap.py --run`.\n'
        'Use `--port` for another unused port. The setup uses your configured pip index for NiceGUI; '
        'the updated framework wheel is included under `vendor/`. No development repository is needed.\n\n'
        'The app-local environment is isolated. Startup verifies the framework build and every '
        'bundled source/asset hash. `--check --output proof.json` writes that result without running a server. '
        'Runtime verification does not establish browser behavior or production-provider readiness.\n\n'
        'Do not share `.venv`, `.nicegui_base/local-storage-secret`, local state, or credentials. '
        'The included wheel is a development snapshot, not a published stable release. '
        'Review the explicit data export policy in `.nicegui_base/` before sharing the ZIP.\n'
    )
    gitignore = root / '.gitignore'
    previous = gitignore.read_text() if gitignore.exists() else ''
    gitignore.write_text(previous + '\n.venv/\n.nicegui_base/local-storage-secret\n.nicegui/\n')
    return lock
