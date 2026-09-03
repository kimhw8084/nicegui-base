from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

STATE_KEY = 'nicegui_base_workbench_project_v2_2'
STATE_VERSION = 6
MAX_RECENTS = 16
MAX_FAVORITES = 64
MAX_PERSISTED_ROWS = 200


def _safe_nonnegative_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or default)
    return text if text in allowed else default


def empty_state() -> dict[str, Any]:
    return {
        'version': STATE_VERSION,
        'project': {
            'name': 'My NiceGUI App',
            'goal': '',
            'problem_type': 'engineering analysis',
            'pattern_key': None,
            'blueprint_key': None,
            'placements': {},
            'queued_entry_keys': [],
            'data_rows': [],
            'data_schema': [],
            'data_source_name': '',
            'data_handoff_mode': 'schema_only',
            'production_provider': 'none',
            'theme': 'system',
            'density': 'compact',
            'revision': 0,
        },
        'favorites': [],
        'recents': [],
        'history': [],
        'presets': {},
        'proof_evidence': {},
    }


def normalize_state(value: Mapping[str, Any] | None) -> dict[str, Any]:
    base = empty_state()
    if not isinstance(value, Mapping):
        return base
    project = value.get('project') if isinstance(value.get('project'), Mapping) else {}
    base['project'].update({
        'name': str(project.get('name') or base['project']['name'])[:80],
        'goal': str(project.get('goal') or '')[:1000],
        'problem_type': str(project.get('problem_type') or 'engineering analysis')[:80],
        'pattern_key': str(project['pattern_key']) if project.get('pattern_key') else None,
        'blueprint_key': str(project['blueprint_key'])[:80] if project.get('blueprint_key') else None,
        'theme': _choice(project.get('theme'), {'system','light','dark'}, 'system'),
        'density': _choice(project.get('density'), {'comfortable','compact','dense'}, 'compact'),
        'revision': _safe_nonnegative_int(project.get('revision'), 0),
    })
    placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    base['project']['placements'] = {
        str(slot): list(dict.fromkeys(str(item) for item in entries if item))
        for slot, entries in placements.items() if isinstance(entries, (list, tuple))
    }
    queued = project.get('queued_entry_keys') if isinstance(project.get('queued_entry_keys'), (list, tuple)) else ()
    base['project']['queued_entry_keys'] = list(dict.fromkeys(str(item) for item in queued if item))[:100]
    rows = project.get('data_rows') if isinstance(project.get('data_rows'), (list, tuple)) else ()
    base['project']['data_rows'] = [dict(row) for row in rows[:MAX_PERSISTED_ROWS] if isinstance(row, Mapping)]
    schema = project.get('data_schema') if isinstance(project.get('data_schema'), (list, tuple)) else ()
    allowed_types = {'string','integer','float','boolean','date','datetime','category','json','unknown'}
    allowed_roles = {'dimension','measurement','identifier','timestamp','entity','attribute'}
    normalized_schema: list[dict[str, Any]] = []
    for item in schema[:128]:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get('name') or '').strip()[:160]
        if not name:
            continue
        inferred = str(item.get('inferred_type') or item.get('type') or 'unknown')
        role = str(item.get('role') or 'attribute')
        try:
            confidence = max(0.0, min(1.0, float(item.get('confidence', 1.0))))
        except (TypeError, ValueError, OverflowError):
            confidence = 1.0
        normalized_schema.append({
            'name': name,
            'inferred_type': inferred if inferred in allowed_types else 'unknown',
            'role': role if role in allowed_roles else 'attribute',
            'nullable': bool(item.get('nullable', True)),
            'confidence': confidence,
            'original_name': str(item.get('original_name'))[:160] if item.get('original_name') else None,
        })
    base['project']['data_schema'] = normalized_schema
    base['project']['data_source_name'] = str(project.get('data_source_name') or '')[:160]
    base['project']['data_handoff_mode'] = _choice(
        project.get('data_handoff_mode'), {'schema_only','include_development_rows'}, 'schema_only',
    )
    base['project']['production_provider'] = _choice(
        project.get('production_provider'), {'none','csv','sqlite'}, 'none',
    )
    favorites = value.get('favorites') if isinstance(value.get('favorites'), (list, tuple)) else ()
    recents = value.get('recents') if isinstance(value.get('recents'), (list, tuple)) else ()
    base['favorites'] = list(dict.fromkeys(str(item) for item in favorites if item))[:MAX_FAVORITES]
    base['recents'] = list(dict.fromkeys(str(item) for item in recents if item))[:MAX_RECENTS]
    from .project_history import normalize_history, normalize_presets
    from .portable_project import normalize_proof_evidence
    base['history'] = normalize_history(value.get('history'))
    base['presets'] = normalize_presets(value.get('presets'))
    base['proof_evidence'] = normalize_proof_evidence(value.get('proof_evidence'))
    return base


def _storage_state() -> dict[str, Any]:
    from nicegui import app
    state = normalize_state(app.storage.user.get(STATE_KEY))
    app.storage.user[STATE_KEY] = state
    return state


def _save_storage_state(state: Mapping[str, Any]) -> None:
    from nicegui import app
    app.storage.user[STATE_KEY] = normalize_state(state)


def project_snapshot() -> dict[str, Any]:
    return deepcopy(_storage_state()['project'])


def save_project_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    from .project_history import diff_projects, project_signature, push_history
    state = _storage_state()
    current = state['project']
    project = normalize_state({'project': snapshot})['project']
    if project_signature(current) != project_signature(project):
        state['history'] = push_history(state.get('history', ()), current, label=diff_projects(current, project).summary())
        state['proof_evidence'] = {}
    project['revision'] = max(int(current.get('revision') or 0), int(project.get('revision') or 0)) + 1
    state['project'] = project
    _save_storage_state(state)
    return deepcopy(project)


def clear_project() -> dict[str, Any]:
    from .project_history import push_history
    state = _storage_state()
    state['history'] = push_history(state.get('history', ()), state['project'], label='Before clearing project')
    state['project'] = empty_state()['project']
    state['proof_evidence'] = {}
    _save_storage_state(state)
    return deepcopy(state['project'])


def project_history() -> tuple[dict[str, Any], ...]:
    return tuple(deepcopy(_storage_state().get('history', ())))


def restore_project_revision(revision_id: str) -> dict[str, Any]:
    from .project_history import project_signature, push_history
    state = _storage_state()
    target = next((item for item in state.get('history', ()) if str(item.get('id')) == str(revision_id)), None)
    if target is None or not isinstance(target.get('snapshot'), Mapping):
        raise KeyError(f'unknown project revision: {revision_id!r}')
    current = state['project']
    restored = normalize_state({'project': target['snapshot']})['project']
    if project_signature(current) != project_signature(restored):
        state['history'] = push_history(state.get('history', ()), current, label='Before restoring revision')
    restored['revision'] = max(int(current.get('revision') or 0), int(restored.get('revision') or 0)) + 1
    state['project'] = restored
    state['proof_evidence'] = {}
    _save_storage_state(state)
    return deepcopy(restored)


def project_presets() -> dict[str, dict[str, Any]]:
    return deepcopy(_storage_state().get('presets', {}))


def save_project_preset(name: str, snapshot: Mapping[str, Any] | None = None) -> str:
    from .project_history import MAX_PRESETS, normalize_presets, preset_name
    clean = preset_name(name)
    state = _storage_state()
    presets = dict(state.get('presets', {}))
    if clean not in presets and len(presets) >= MAX_PRESETS:
        raise ValueError(f'At most {MAX_PRESETS} project presets may be saved.')
    source = snapshot if snapshot is not None else state['project']
    presets[clean] = normalize_state({'project': source})['project']
    state['presets'] = normalize_presets(presets)
    _save_storage_state(state)
    return clean


def apply_project_preset(name: str) -> dict[str, Any]:
    presets = _storage_state().get('presets', {})
    if name not in presets:
        raise KeyError(f'unknown project preset: {name!r}')
    return save_project_snapshot(presets[name])


def delete_project_preset(name: str) -> bool:
    state = _storage_state()
    presets = dict(state.get('presets', {}))
    if name not in presets:
        return False
    presets.pop(name, None)
    state['presets'] = presets
    _save_storage_state(state)
    return True


def proof_evidence() -> dict[str, Any]:
    return deepcopy(_storage_state().get('proof_evidence', {}))


def save_proof_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    from .portable_project import normalize_proof_evidence
    from .project_history import project_signature
    state = _storage_state()
    normalized = normalize_proof_evidence(evidence)
    expected = str(normalized.get('project_signature') or '')
    actual = project_signature(state['project'])
    if expected and expected != actual:
        raise ValueError('Proof evidence does not match the current project signature.')
    state['proof_evidence'] = normalized
    _save_storage_state(state)
    return deepcopy(normalized)


def clear_proof_evidence() -> None:
    state = _storage_state()
    state['proof_evidence'] = {}
    _save_storage_state(state)


def export_portable_project_bundle() -> bytes:
    from nicegui_base.version import FRAMEWORK_VERSION
    from .portable_project import build_portable_project_bundle
    state = _storage_state()
    return build_portable_project_bundle(state, framework_version=FRAMEWORK_VERSION, proof_evidence=state.get('proof_evidence'))


def import_portable_project_bundle(payload: bytes):
    from nicegui_base.version import FRAMEWORK_VERSION
    from .portable_project import extract_portable_project_bundle
    from .project_history import project_signature, push_history
    imported, evidence, inspection = extract_portable_project_bundle(payload, expected_framework_version=FRAMEWORK_VERSION)
    current = _storage_state()
    imported['history'] = push_history(imported.get('history', ()), current['project'], label='Before portable project import')
    imported_project = imported['project']
    imported_project['revision'] = max(int(current['project'].get('revision') or 0), int(imported_project.get('revision') or 0)) + 1
    imported['proof_evidence'] = evidence if str(evidence.get('project_signature') or '') in {'', project_signature(imported_project)} else {}
    _save_storage_state(imported)
    return deepcopy(imported_project), inspection


def set_project_pattern(pattern_key: str) -> None:
    from nicegui_base.patterns.registry import get_pattern
    definition = get_pattern(pattern_key)
    state = _storage_state()
    allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
    state['project']['pattern_key'] = definition.pattern.value
    state['project']['placements'] = {
        slot: values for slot, values in state['project'].get('placements', {}).items() if slot in allowed
    }
    state['project']['revision'] += 1
    state['proof_evidence'] = {}
    _save_storage_state(state)


def queue_entry(entry_key: str) -> bool:
    key = str(entry_key).strip()
    if not key:
        return False
    state = _storage_state()
    placed = {item for values in state['project'].get('placements', {}).values() for item in values}
    if key in placed:
        return False
    queued = state['project']['queued_entry_keys']
    changed = key not in queued
    if changed:
        queued.append(key)
        state['project']['revision'] += 1
        state['proof_evidence'] = {}
        _save_storage_state(state)
    return changed


def remove_queued_entry(entry_key: str) -> bool:
    key = str(entry_key)
    state = _storage_state()
    queued = state['project']['queued_entry_keys']
    if key not in queued:
        return False
    state['project']['queued_entry_keys'] = [item for item in queued if item != key]
    state['project']['revision'] += 1
    state['proof_evidence'] = {}
    _save_storage_state(state)
    return True


def mark_recent(entry_key: str) -> None:
    key = str(entry_key).strip()
    if not key:
        return
    state = _storage_state()
    state['recents'] = [key, *[item for item in state['recents'] if item != key]][:MAX_RECENTS]
    _save_storage_state(state)


def toggle_favorite(entry_key: str) -> bool:
    key = str(entry_key).strip()
    state = _storage_state()
    favorites = list(state['favorites'])
    if key in favorites:
        favorites = [item for item in favorites if item != key]
        selected = False
    else:
        favorites = [key, *favorites][:MAX_FAVORITES]
        selected = True
    state['favorites'] = favorites
    _save_storage_state(state)
    return selected


def favorites() -> tuple[str, ...]:
    return tuple(_storage_state()['favorites'])


def recents() -> tuple[str, ...]:
    return tuple(_storage_state()['recents'])


def render_entry_project_actions(entry) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button

    mark_recent(entry.key)
    host = ui.element('div').classes('cui-workbench-toolbar cui-studio-project-actions')

    def render() -> None:
        from .project_codegen import is_composable_entry
        host.clear()
        state = _storage_state()
        queued = entry.key in state['project']['queued_entry_keys']
        placed = any(entry.key in values for values in state['project'].get('placements', {}).values())
        favorite = entry.key in state['favorites']
        kind = getattr(getattr(entry, 'kind', None), 'value', str(getattr(entry, 'kind', '')))
        with host:
            if kind == 'pattern' and entry.metadata.get('pattern_key'):
                Button('Use as app pattern', on_click=lambda: (set_project_pattern(str(entry.metadata['pattern_key'])), ui.navigate.to('/build')))
            elif is_composable_entry(entry):
                Button(
                    'Already in project' if placed else ('Queued for Builder' if queued else 'Add to current project'),
                    disabled=queued or placed,
                    on_click=lambda: (queue_entry(entry.key), render()),
                )
            Button(
                '★ Favorited' if favorite else '☆ Favorite',
                on_click=lambda: (toggle_favorite(entry.key), render()),
            )
            ui.link('Open Builder', '/build').classes('cui-workbench-chip')

    render()


def render_home_project_resume() -> None:
    from nicegui import ui
    from .catalog import all_entries

    lookup = {entry.key: entry for entry in all_entries()}
    state = _storage_state()
    project = state['project']

    with ui.element('section').classes('cui-workbench-section'):
        ui.label('Resume').classes('cui-workbench-section-title')
        with ui.element('div').classes('cui-workbench-grid'):
            with ui.element('article').classes('cui-workbench-card'):
                ui.label('CURRENT PROJECT').classes('cui-workbench-card__meta')
                ui.label(project['name']).classes('cui-workbench-card__title')
                summary = project['goal'] or 'No goal entered yet.'
                ui.label(summary).classes('cui-workbench-card__body')
                details = []
                if project.get('pattern_key'):
                    details.append(str(project['pattern_key']).replace('_', ' ').title())
                placed = sum(len(items) for items in project.get('placements', {}).values())
                queued = len(project.get('queued_entry_keys', ()))
                details.extend((f'{placed} placed', f'{queued} queued'))
                ui.label(' · '.join(details)).classes('cui-workbench-note')
                ui.link('Resume in Builder', '/build').classes('cui-workbench-chip')

    def render_entry_group(title: str, keys: tuple[str, ...]) -> None:
        entries = [lookup[key] for key in keys if key in lookup][:8]
        if not entries:
            return
        with ui.element('section').classes('cui-workbench-section'):
            ui.label(title).classes('cui-workbench-section-title')
            with ui.element('div').classes('cui-workbench-grid'):
                for entry in entries:
                    with ui.element('article').classes('cui-workbench-card'):
                        ui.label(entry.kind.value.upper()).classes('cui-workbench-card__meta')
                        ui.label(entry.title).classes('cui-workbench-card__title')
                        ui.label(entry.description).classes('cui-workbench-card__body')
                        ui.link('Open Studio', entry.route).classes('cui-workbench-chip')

    render_entry_group('Favorites', tuple(state['favorites']))
    render_entry_group('Recent capabilities', tuple(state['recents']))


__all__ = [
    'STATE_KEY','STATE_VERSION','clear_project','empty_state','favorites','mark_recent','normalize_state',
    'project_snapshot','project_history','project_presets','queue_entry','recents','set_project_pattern','remove_queued_entry','render_entry_project_actions',
    'render_home_project_resume','save_project_snapshot','save_project_preset','apply_project_preset','delete_project_preset','restore_project_revision','toggle_favorite',
    'proof_evidence','save_proof_evidence','clear_proof_evidence','export_portable_project_bundle','import_portable_project_bundle',
]
