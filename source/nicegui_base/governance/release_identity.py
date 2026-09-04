from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ReleaseIdentity:
    framework_name: str
    framework_version: str
    nicegui_version: str
    current_wave: int
    current_phase: int
    release_status: str
    promotion_target: str
    release_kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'framework_name': self.framework_name,
            'framework_version': self.framework_version,
            'nicegui_version': self.nicegui_version,
            'current_wave': self.current_wave,
            'current_phase': self.current_phase,
            'release_status': self.release_status,
            'promotion_target': self.promotion_target,
            'release_kind': self.release_kind,
        }


def load_release_identity(root: str | Path | None = None) -> ReleaseIdentity:
    if root is None:
        authority_text = files('nicegui_base').joinpath('release_authority.json').read_text(encoding='utf-8')
    else:
        path = Path(root).resolve() / 'nicegui_base' / 'release_authority.json'
        authority_text = path.read_text(encoding='utf-8')
    payload = json.loads(authority_text)
    if not isinstance(payload, dict):
        raise ValueError('nicegui_base/release_authority.json must contain a JSON object')
    current_wave = int(payload.get('current_wave', payload.get('current_phase', 0)))
    current_phase = int(payload.get('current_phase', current_wave))
    if current_wave <= 0 or current_phase <= 0:
        raise ValueError('release authority must define positive current_wave/current_phase')
    if current_wave != current_phase:
        raise ValueError('current_wave and current_phase must match for the Wave release line')
    return ReleaseIdentity(
        framework_name=str(payload.get('framework_name', 'nicegui-base')),
        framework_version=str(payload['framework_version']),
        nicegui_version=str(payload['nicegui_version']),
        current_wave=current_wave,
        current_phase=current_phase,
        release_status=str(payload.get('release_status', 'UNKNOWN')),
        promotion_target=str(payload.get('promotion_target', '')),
        release_kind=str(payload.get('release_kind', f'wave{current_wave}')),
    )


__all__ = ['ReleaseIdentity', 'load_release_identity']
