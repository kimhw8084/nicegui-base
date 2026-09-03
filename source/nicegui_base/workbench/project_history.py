from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

MAX_HISTORY = 24
MAX_PRESETS = 16
MAX_SNAPSHOT_ROWS = 200


def _stable_project(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(snapshot or {})
    source.pop('revision', None)
    placements = source.get('placements') if isinstance(source.get('placements'), Mapping) else {}
    source['placements'] = {
        str(slot): list(dict.fromkeys(str(key) for key in keys if key))
        for slot, keys in placements.items() if isinstance(keys, (list, tuple))
    }
    queued = source.get('queued_entry_keys') if isinstance(source.get('queued_entry_keys'), (list, tuple)) else ()
    source['queued_entry_keys'] = list(dict.fromkeys(str(key) for key in queued if key))
    rows = source.get('data_rows') if isinstance(source.get('data_rows'), (list, tuple)) else ()
    source['data_rows'] = [dict(row) for row in rows[:MAX_SNAPSHOT_ROWS] if isinstance(row, Mapping)]
    return source


def project_signature(snapshot: Mapping[str, Any] | None) -> str:
    payload = json.dumps(_stable_project(snapshot), sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectDiff:
    fields: tuple[str, ...]
    added: tuple[tuple[str, str], ...]
    removed: tuple[tuple[str, str], ...]
    moved: tuple[tuple[str, str, str], ...]
    data_rows_before: int
    data_rows_after: int

    @property
    def changed(self) -> bool:
        return bool(self.fields or self.added or self.removed or self.moved or self.data_rows_before != self.data_rows_after)

    def summary(self) -> str:
        parts: list[str] = []
        if self.fields:
            parts.append('Changed ' + ', '.join(self.fields[:4]))
        if self.added:
            parts.append(f'{len(self.added)} added')
        if self.removed:
            parts.append(f'{len(self.removed)} removed')
        if self.moved:
            parts.append(f'{len(self.moved)} moved')
        if self.data_rows_before != self.data_rows_after:
            parts.append(f'data {self.data_rows_before}→{self.data_rows_after} rows')
        return ' · '.join(parts) or 'Project checkpoint'

    def to_dict(self) -> dict[str, object]:
        return {
            'fields': list(self.fields),
            'added': [list(item) for item in self.added],
            'removed': [list(item) for item in self.removed],
            'moved': [list(item) for item in self.moved],
            'data_rows_before': self.data_rows_before,
            'data_rows_after': self.data_rows_after,
        }


def diff_projects(before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> ProjectDiff:
    left = _stable_project(before)
    right = _stable_project(after)
    tracked = ('name', 'goal', 'problem_type', 'pattern_key', 'blueprint_key', 'data_handoff_mode', 'production_provider', 'data_source_name', 'data_schema', 'theme', 'density', 'queued_entry_keys')
    fields = tuple(key for key in tracked if left.get(key) != right.get(key))
    left_loc = {str(key): str(slot) for slot, keys in left.get('placements', {}).items() for key in keys}
    right_loc = {str(key): str(slot) for slot, keys in right.get('placements', {}).items() for key in keys}
    added = tuple(sorted((slot, key) for key, slot in right_loc.items() if key not in left_loc))
    removed = tuple(sorted((slot, key) for key, slot in left_loc.items() if key not in right_loc))
    moved = tuple(sorted((key, left_loc[key], right_loc[key]) for key in left_loc.keys() & right_loc.keys() if left_loc[key] != right_loc[key]))
    return ProjectDiff(
        fields,
        added,
        removed,
        moved,
        len(left.get('data_rows') or ()),
        len(right.get('data_rows') or ()),
    )


def _revision(snapshot: Mapping[str, Any], label: str | None = None) -> dict[str, Any]:
    stable = _stable_project(snapshot)
    try:
        revision = max(0, int(snapshot.get('revision') or 0))
    except (TypeError, ValueError, OverflowError):
        revision = 0
    stable['revision'] = revision
    signature = project_signature(stable)
    return {
        'id': signature[:16],
        'signature': signature,
        'label': str(label or 'Project checkpoint')[:120],
        'snapshot': deepcopy(stable),
    }


def normalize_history(value: Any, *, limit: int = MAX_HISTORY) -> list[dict[str, Any]]:
    source = value if isinstance(value, (list, tuple)) else ()
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, Mapping) or not isinstance(item.get('snapshot'), Mapping):
            continue
        revision = _revision(item['snapshot'], str(item.get('label') or 'Project checkpoint'))
        if revision['signature'] in seen:
            continue
        seen.add(str(revision['signature']))
        result.append(revision)
        if len(result) >= max(1, int(limit)):
            break
    return result


def push_history(history: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any], *, label: str | None = None, limit: int = MAX_HISTORY) -> list[dict[str, Any]]:
    if not snapshot or not any(snapshot.get(key) for key in ('goal', 'pattern_key', 'placements', 'queued_entry_keys', 'data_rows')):
        return normalize_history(history, limit=limit)
    revision = _revision(snapshot, label)
    existing = normalize_history(history, limit=limit)
    return [revision, *[item for item in existing if item['signature'] != revision['signature']]][:limit]


def normalize_presets(value: Any, *, limit: int = MAX_PRESETS) -> dict[str, dict[str, Any]]:
    source = value if isinstance(value, Mapping) else {}
    result: dict[str, dict[str, Any]] = {}
    for raw_name, snapshot in source.items():
        name = str(raw_name).strip()[:64]
        if not name or not isinstance(snapshot, Mapping):
            continue
        result[name] = deepcopy(_stable_project(snapshot))
        if 'revision' in snapshot:
            result[name]['revision'] = max(0, int(snapshot.get('revision') or 0)) if str(snapshot.get('revision') or '0').lstrip('-').isdigit() else 0
        if len(result) >= max(1, int(limit)):
            break
    return result


def preset_name(value: Any) -> str:
    name = ' '.join(str(value or '').strip().split())[:64]
    if not name:
        raise ValueError('Preset name must not be empty.')
    if any(ord(char) < 32 for char in name):
        raise ValueError('Preset name contains unsupported control characters.')
    return name


__all__ = [
    'MAX_HISTORY', 'MAX_PRESETS', 'MAX_SNAPSHOT_ROWS', 'ProjectDiff', 'diff_projects', 'normalize_history', 'normalize_presets',
    'preset_name', 'project_signature', 'push_history',
]
