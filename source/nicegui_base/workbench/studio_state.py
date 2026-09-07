"""Versioned Studio drafts and explicit Studio -> Builder handoff.

Call with the current user's storage mapping, never shared/general storage.
No UI or disk dependencies; mutations replace one bounded value atomically.
"""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
import hashlib
import json
from typing import Any

from .data_dock import DataDockModel
from .preview_data import _json_value

DRAFT_STORAGE_KEY = 'nicegui_base_studio_drafts_d1'  # Preserve existing D1 drafts.
MAX_DRAFTS = 8


class DraftConflict(ValueError):
    pass


def token(value: Any) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def normalize_configuration(value: Mapping[str, Any] | None, *, title: str = 'Capability') -> dict[str, Any]:
    if value is not None and not isinstance(value, Mapping):
        raise ValueError('Configuration must be an object.')
    source = dict(value or {})
    label = str(source.get('title') or title)
    if len(label) > 160:
        raise ValueError('Use at most 160 characters for the title.')
    cfg = {'title': label}
    choices = {'density': ('compact', 'comfortable', 'dense'),
               'responsive_width': ('desktop', 'compact', 'tablet', 'phone'),
               'theme': ('system', 'light', 'dark')}
    for key, allowed in choices.items():
        raw = source.get(key, allowed[0])
        if raw not in allowed:
            raise ValueError(f'Unsupported {key}: {raw!r}.')
        cfg[key] = raw
    options = source.get('options', {})
    if not isinstance(options, Mapping):
        raise ValueError('Configuration options must be an object.')
    options = _json_value(options)
    if len(json.dumps(options).encode()) > 16384:
        raise ValueError('Configuration options exceed 16 KiB.')
    if 'disabled' in options and not isinstance(options['disabled'], bool):
        raise ValueError('Disabled must be true or false.')
    if 'selection' in options and options['selection'] not in {'none','single','multiple'}:
        raise ValueError('Unsupported selection setting.')
    if 'measurement' in options and not isinstance(options['measurement'], str):
        raise ValueError('Measurement field must be a string.')
    cfg['options'] = options
    return cfg


def normalize_capability_configurations(value: Any) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > 100:
        raise ValueError('A project supports at most 100 capability configurations.')
    result = {}
    for key, config in value.items():
        if not isinstance(key, str) or not key or len(key) > 200:
            raise ValueError('Invalid capability configuration key.')
        result[key] = normalize_configuration(config)
    return result


def draft_payload(model: DataDockModel, configuration: Mapping[str, Any], *, revision: int = 0,
                  export_mode: str = 'schema_only') -> dict[str, Any]:
    if export_mode not in {'schema_only', 'include_development_rows'}:
        raise ValueError('Unsupported export data mode.')
    data = model.to_payload()
    # A D1 source rollback can still read current rows/title. D2 owns the full
    # data+schema representation; D1 does not understand schema/policy metadata.
    return {'schema_version': 2, 'revision': revision, 'data': data, 'rows': data['rows'],
            'configuration': normalize_configuration(configuration), 'export_mode': export_mode}


def restore_draft(value: Mapping[str, Any], *, title: str) -> tuple[DataDockModel, dict[str, Any], str]:
    if not isinstance(value, Mapping):
        raise ValueError('Saved draft is not an object.')
    version = value.get('schema_version', 1)
    if version not in (1, 2):
        raise ValueError('This draft uses a newer, unsupported schema. Its saved value was not changed.')
    if version == 1:
        data = DataDockModel(value.get('rows', []), sample_name='Restored D1 draft')
    else:
        if not isinstance(value.get('data'), Mapping):
            raise ValueError('Saved draft has no valid dataset.')
        data = DataDockModel.from_payload(value['data'])
    cfg = normalize_configuration(value.get('configuration'), title=title)
    mode = value.get('export_mode', 'schema_only')
    if mode not in {'schema_only', 'include_development_rows'}:
        raise ValueError('Saved export policy is invalid.')
    return data, cfg, mode


def save_draft(storage: MutableMapping, entry_key: str, payload: Mapping[str, Any], *, expected: str | None) -> str:
    existing = storage.get(DRAFT_STORAGE_KEY, {})
    if not isinstance(existing, Mapping):
        raise ValueError('Saved draft collection is damaged; it was not overwritten.')
    drafts = dict(existing)
    current = drafts.get(entry_key)
    if token(current) != expected:
        raise DraftConflict('This draft changed in another tab. Reload before saving; neither version was overwritten.')
    if current is None and len(drafts) >= MAX_DRAFTS:
        raise ValueError(f'All {MAX_DRAFTS} draft slots are occupied. Remove a saved draft first; none was silently deleted.')
    model, cfg, mode = restore_draft(payload, title=entry_key)
    revision = int(current.get('revision', 0)) + 1 if isinstance(current, Mapping) else 1
    next_value = draft_payload(model, cfg, revision=revision, export_mode=mode)
    drafts[entry_key] = next_value
    storage[DRAFT_STORAGE_KEY] = drafts
    return token(next_value)


def remove_draft(storage: MutableMapping, entry_key: str, *, expected: str | None) -> None:
    existing = storage.get(DRAFT_STORAGE_KEY, {})
    if not isinstance(existing, Mapping):
        raise ValueError('Saved draft collection is invalid.')
    drafts = dict(existing)
    if token(drafts.get(entry_key)) != expected:
        raise DraftConflict('This draft changed in another tab. Reload before removing it.')
    drafts.pop(entry_key, None)
    storage[DRAFT_STORAGE_KEY] = drafts


def project_handoff(project: Mapping[str, Any], entry_key: str, data: DataDockModel,
                    configuration: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(project))
    result.update(data_rows=data.to_payload()['rows'], data_schema=list(data.schema_metadata()),
                  data_source_name=data.snapshot.source_name, data_source_format=data.snapshot.source_format.value)
    configs = normalize_capability_configurations(result.get('capability_configurations'))
    configs[entry_key] = normalize_configuration(configuration)
    result['capability_configurations'] = normalize_capability_configurations(configs)
    result['queued_entry_keys'] = list(dict.fromkeys([*result.get('queued_entry_keys', []), entry_key]))
    # Passing data to Builder does not grant permission to include it in an export.
    result['data_handoff_mode'] = 'schema_only'
    return result
