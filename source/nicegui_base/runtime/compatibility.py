from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

COMPATIBILITY_PATH = Path(__file__).with_name('compatibility.json')


@dataclass(frozen=True, slots=True)
class CompatibilityManifest:
    framework_name: str = 'nicegui-base'
    framework_version: str = FRAMEWORK_VERSION
    python_min: str = '3.11'
    python_max_exclusive: str = '3.14'
    nicegui_version: str = NICEGUI_VERSION
    primary_browsers: tuple[str, ...] = ('Microsoft Edge', 'Google Chrome')
    external_cdn_required: bool = False
    max_nicegui_workers_per_process: int = 1
    reverse_proxy_supported: bool = True
    root_path_supported: bool = True
    redis_recommended_for_multi_instance: bool = True
    session_affinity_required_multi_instance: bool = True
    notes: tuple[str, ...] = (
        'NiceGUI user/browser storage requires a storage_secret.',
        'Production session cookies should be HTTPS-only.',
        'Multiple application instances require shared persistence for cross-instance user/general/tab state.',
        'Multiple NiceGUI instances require load-balancer session affinity for page/WebSocket continuity.',
    )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in tuple(data.items()):
            if isinstance(value, tuple):
                data[key] = list(value)
        return data

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(self.to_json() + '\n', encoding='utf-8')
        return target


def installed_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def runtime_fingerprint() -> dict[str, str | None]:
    return {
        'python': platform.python_version(),
        'platform': platform.platform(),
        'implementation': platform.python_implementation(),
        'nicegui': installed_version('nicegui'),
        'nicegui_base': installed_version('nicegui-base'),
        'executable': sys.executable,
    }


def load_compatibility_manifest(path: str | Path | None = None) -> dict[str, Any]:
    """Load the packaged compatibility manifest as a validated mapping.

    The packaged JSON is the deployable machine-readable contract. Falling back
    to the live dataclass keeps source checkouts usable before metadata sync.
    """
    target = Path(path) if path is not None else COMPATIBILITY_PATH
    if not target.exists():
        return CompatibilityManifest().to_dict()
    payload = json.loads(target.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'compatibility manifest must contain a JSON object: {target}')
    return payload


__all__ = [
    'COMPATIBILITY_PATH', 'CompatibilityManifest', 'installed_version',
    'runtime_fingerprint', 'load_compatibility_manifest',
]
