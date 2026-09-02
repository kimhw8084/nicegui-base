from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

STATE_KEY = 'nicegui_base_workbench_project_v2_2'
STATE_VERSION = 1
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
            'placements': {},
            'queued_entry_keys': [],
            'data_rows': [],
            'theme': 'system',
            'density': 'compact',
            'revision': 0,
        },
        'favorites': [],
        'recents': [],
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
    favorites = value.get('favorites') if isinstance(value.get('favorites'), (list, tuple)) else ()
    recents = value.get('recents') if isinstance(value.get('recents'), (list, tuple)) else ()
    base['favorites'] = list(dict.fromkeys(str(item) for item in favorites if item))[:MAX_FAVORITES]
    base['recents'] = list(dict.fromkeys(str(item) for item in recents if item))[:MAX_RECENTS]
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
    state = _storage_state()
    project = normalize_state({'project': snapshot})['project']
    project['revision'] = max(int(state['project'].get('revision') or 0), int(project.get('revision') or 0)) + 1
    state['project'] = project
    _save_storage_state(state)
    return deepcopy(project)


def clear_project() -> dict[str, Any]:
    state = _storage_state()
    state['project'] = empty_state()['project']
    _save_storage_state(state)
    return deepcopy(state['project'])


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
    'project_snapshot','queue_entry','recents','set_project_pattern','remove_queued_entry','render_entry_project_actions',
    'render_home_project_resume','save_project_snapshot','toggle_favorite',
]
