from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .catalog import all_entries
from .data_dock import DataDockModel, default_data_dock
from .models import WorkbenchEntry, WorkbenchKind
from .project_codegen import generate_project_zip, is_composable_entry
from .search import score_entry


class BuilderStage(str, Enum):
    GOAL = 'goal'
    DATA = 'data'
    PATTERN = 'pattern'
    COMPOSE = 'compose'
    REVIEW = 'review'
    GENERATE = 'generate'


STAGE_ORDER = (
    BuilderStage.GOAL,
    BuilderStage.DATA,
    BuilderStage.PATTERN,
    BuilderStage.COMPOSE,
    BuilderStage.REVIEW,
    BuilderStage.GENERATE,
)


@dataclass(frozen=True, slots=True)
class PatternRecommendation:
    entry: WorkbenchEntry
    reasons: tuple[str, ...]
    rank_score: int


@dataclass(slots=True)
class BuilderModel:
    goal: str = ''
    problem_type: str = 'engineering analysis'
    data: DataDockModel = field(default_factory=default_data_dock)
    stage: BuilderStage = BuilderStage.GOAL
    pattern_key: str | None = None
    app_name: str = 'My NiceGUI App'
    theme: str = 'system'
    density: str = 'compact'
    placements: dict[str, list[str]] = field(default_factory=dict)
    queued_entry_keys: list[str] = field(default_factory=list)
    revision: int = 0

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> 'BuilderModel':
        rows = snapshot.get('data_rows') if isinstance(snapshot.get('data_rows'), list) else []
        data = DataDockModel(rows, sample_name='Resumed project data') if rows else default_data_dock()
        return cls(
            goal=str(snapshot.get('goal') or ''),
            problem_type=str(snapshot.get('problem_type') or 'engineering analysis'),
            data=data,
            pattern_key=str(snapshot['pattern_key']) if snapshot.get('pattern_key') else None,
            app_name=str(snapshot.get('name') or 'My NiceGUI App'),
            theme=str(snapshot.get('theme') or 'system'),
            density=str(snapshot.get('density') or 'compact'),
            placements={str(k): list(v) for k, v in dict(snapshot.get('placements') or {}).items()},
            queued_entry_keys=list(snapshot.get('queued_entry_keys') or ()),
            revision=int(snapshot.get('revision') or 0),
            stage=BuilderStage.COMPOSE if snapshot.get('pattern_key') else BuilderStage.GOAL,
        )

    def load_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        restored = type(self).from_snapshot(snapshot)
        self.goal = restored.goal
        self.problem_type = restored.problem_type
        self.data = restored.data
        self.stage = restored.stage
        self.pattern_key = restored.pattern_key
        self.app_name = restored.app_name
        self.theme = restored.theme
        self.density = restored.density
        self.placements = restored.placements
        self.queued_entry_keys = restored.queued_entry_keys
        self.revision = restored.revision

    def snapshot(self) -> dict[str, Any]:
        return {
            'name': self.app_name,
            'goal': self.goal,
            'problem_type': self.problem_type,
            'pattern_key': self.pattern_key,
            'placements': {slot: list(keys) for slot, keys in self.placements.items()},
            'queued_entry_keys': list(dict.fromkeys(self.queued_entry_keys)),
            'data_rows': list(self.data.serializable_rows())[:200],
            'theme': self.theme,
            'density': self.density,
            'revision': self.revision,
        }

    def _changed(self) -> None:
        self.revision += 1

    def set_goal(self, goal: str, *, problem_type: str | None = None) -> None:
        self.goal = str(goal).strip()
        if problem_type is not None:
            self.problem_type = str(problem_type).strip() or 'engineering analysis'
        self.stage = BuilderStage.DATA
        self._changed()

    def apply_golden_starter(self, starter_key: str):
        from .starter_kits import get_golden_starter, resolve_starter
        spec = get_golden_starter(starter_key)
        resolution = resolve_starter(spec, all_entries(), data_model=self.data)
        self.goal = spec.goal
        self.problem_type = spec.problem_type
        self.pattern_key = resolution.pattern_key
        self.app_name = spec.title.replace('/', '-').replace('\\', '-').strip()
        self.placements = {slot: list(keys) for slot, keys in resolution.placements.items()}
        self.queued_entry_keys = [key for key in self.queued_entry_keys if key not in resolution.selected_keys]
        self.stage = BuilderStage.COMPOSE
        self._changed()
        return resolution

    def recommended_composition(self):
        if not self.pattern_key:
            raise ValueError('Choose an application pattern before auto-composition.')
        from .starter_kits import recommend_composition
        return recommend_composition(self.pattern_key, all_entries(), goal=self.goal, data_model=self.data)

    def auto_compose(self, *, replace: bool = False):
        resolution = self.recommended_composition()
        if replace or not self.placements:
            self.placements = {slot: list(keys) for slot, keys in resolution.placements.items()}
        else:
            placed = {key for keys in self.placements.values() for key in keys}
            for slot, keys in resolution.placements.items():
                if self.placements.get(slot):
                    continue
                fresh = [key for key in keys if key not in placed]
                if fresh:
                    self.placements[slot] = list(fresh)
                    placed.update(fresh)
        selected = {key for keys in self.placements.values() for key in keys}
        self.queued_entry_keys = [key for key in self.queued_entry_keys if key not in selected]
        self.stage = BuilderStage.COMPOSE
        self._changed()
        return resolution

    def composition_diff(self):
        from .starter_kits import composition_diff
        recommended = self.recommended_composition()
        return composition_diff(self.placements, recommended.placements), recommended

    def audit(self):
        from .project_audit import audit_project
        return audit_project(self.review(), all_entries(), data_model=self.data)

    def go(self, stage: BuilderStage | str) -> BuilderStage:
        self.stage = BuilderStage(stage)
        self._changed()
        return self.stage

    @property
    def pattern_entry(self) -> WorkbenchEntry | None:
        if not self.pattern_key:
            return None
        return next((entry for entry in all_entries() if entry.kind is WorkbenchKind.PATTERN and entry.metadata.get('pattern_key') == self.pattern_key), None)

    def pattern_recommendations(self) -> tuple[PatternRecommendation, ...]:
        query = ' '.join(part for part in (self.problem_type, self.goal) if part).strip()
        items: list[PatternRecommendation] = []
        for entry in all_entries():
            if entry.kind is not WorkbenchKind.PATTERN:
                continue
            match = score_entry(entry, query) if query else None
            score = match.score if match else 0
            reasons: list[str] = []
            if match and match.matched_terms:
                reasons.append('Matches: ' + ', '.join(match.matched_terms[:5]))
            key = str(entry.metadata.get('pattern_key') or '')
            goal = self.goal.casefold()
            problem = self.problem_type.casefold()
            boosts = {
                'monitoring': ('monitor', 'alert', 'health', 'refresh', 'status'),
                'data_explorer': ('explore', 'filter', 'table', 'data', 'records'),
                'master_detail': ('detail', 'entity', 'inspect', 'selected'),
                'crud': ('crud', 'manage', 'edit', 'create', 'record'),
                'search': ('search', 'find', 'lookup'),
                'settings': ('setting', 'configuration', 'preference'),
                'wizard': ('wizard', 'guided', 'step', 'workflow'),
                'comparison': ('compare', 'comparison', 'baseline', 'control', 'affected'),
                'analysis_workspace': ('analysis', 'investigate', 'rca', 'workspace'),
                'dashboard': ('dashboard', 'overview', 'kpi', 'executive'),
            }
            hits = [token for token in boosts.get(key, ()) if token in goal]
            if hits:
                score += 60 + 8 * len(hits)
                reasons.append('Goal explicitly fits this application shape: ' + ', '.join(hits))
            if 'generic' in problem and key in {'dashboard','data_explorer','crud','search','settings','wizard'}:
                score += 20
            if 'engineering' in problem and key in {'analysis_workspace','monitoring','comparison','data_explorer'}:
                score += 25
            if not reasons:
                reasons.append(entry.description)
            items.append(PatternRecommendation(entry, tuple(dict.fromkeys(reasons)), score))
        items.sort(key=lambda item: (-item.rank_score, item.entry.title.casefold()))
        return tuple(items)

    def select_pattern(self, pattern_key: str) -> None:
        from nicegui_base.patterns.registry import get_pattern
        definition = get_pattern(pattern_key)
        self.pattern_key = definition.pattern.value
        allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
        self.placements = {slot: list(keys) for slot, keys in self.placements.items() if slot in allowed}
        self.stage = BuilderStage.COMPOSE
        self._changed()

    def allowed_slots(self) -> tuple[str, ...]:
        if not self.pattern_key:
            return ()
        from nicegui_base.patterns.registry import get_pattern
        return tuple(slot.value for slot in get_pattern(self.pattern_key).slot_order if slot.value != 'header')

    def required_slots(self) -> tuple[str, ...]:
        if not self.pattern_key:
            return ()
        from nicegui_base.patterns.registry import get_pattern
        return tuple(slot.value for slot in get_pattern(self.pattern_key).required_slots if slot.value != 'header')

    def place(self, entry_key: str, slot: str) -> None:
        if slot not in self.allowed_slots():
            raise ValueError(f'{slot!r} is not allowed by {self.pattern_key}')
        lookup = {entry.key: entry for entry in all_entries()}
        entry = lookup.get(entry_key)
        if entry is None or not is_composable_entry(entry):
            raise ValueError(f'{entry_key!r} is not composable')
        for keys in self.placements.values():
            while entry_key in keys:
                keys.remove(entry_key)
        self.placements.setdefault(slot, []).append(entry_key)
        self.queued_entry_keys = [key for key in self.queued_entry_keys if key != entry_key]
        self._changed()

    def remove(self, entry_key: str) -> None:
        removed = False
        for keys in self.placements.values():
            while entry_key in keys:
                keys.remove(entry_key); removed = True
        if removed and entry_key not in self.queued_entry_keys:
            self.queued_entry_keys.append(entry_key)
        if removed:
            self._changed()

    def candidates(self, *, limit: int = 28) -> tuple[WorkbenchEntry, ...]:
        entries = [entry for entry in all_entries() if is_composable_entry(entry)]
        query = ' '.join(part for part in (self.problem_type, self.goal) if part).strip()
        scores: dict[str, int] = {}
        for entry in entries:
            match = score_entry(entry, query) if query else None
            scores[entry.key] = match.score if match else 0
        queued_order = {key: index for index, key in enumerate(self.queued_entry_keys)}
        entries.sort(key=lambda entry: (
            0 if entry.key in queued_order else 1,
            queued_order.get(entry.key, 999),
            -scores.get(entry.key, 0),
            entry.title.casefold(),
        ))
        return tuple(entries[:limit])

    def review(self) -> dict[str, Any]:
        return {
            **self.snapshot(),
            'allowed_slots': list(self.allowed_slots()),
            'required_slots': list(self.required_slots()),
            'empty_required_slots': [slot for slot in self.required_slots() if not self.placements.get(slot)],
            'placed_capabilities': sum(len(keys) for keys in self.placements.values()),
            'data': {
                'rows': self.data.snapshot.quality.rows,
                'columns': list(self.data.snapshot.column_names),
                'roles': {column.name: column.role for column in self.data.columns},
            },
        }

    def generation_issues(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9 _.-]{1,79}', self.app_name.strip()):
            issues.append('Application name must start with a letter and contain 2–80 letters, numbers, spaces, dot, underscore, or dash characters.')
        if not self.pattern_key:
            issues.append('Choose an application pattern before generation.')
        else:
            audit = self.audit()
            issues.extend(item.message for item in audit.blocking)
        return tuple(dict.fromkeys(issues))

    def deterministic_signature(self) -> str:
        return hashlib.sha256(json.dumps(self.review(), sort_keys=True, default=str).encode('utf-8')).hexdigest()

    def generate(self):
        issues = self.generation_issues()
        if issues:
            raise ValueError('; '.join(issues))
        lookup = {entry.key: entry for entry in all_entries()}
        return generate_project_zip(self.review(), lookup)


def render_builder(model: BuilderModel | None = None) -> BuilderModel:
    from nicegui import ui
    from nicegui_base.content import StepSpec, StepState
    from nicegui_base.integrations.nicegui_components import Button, Select, TextInput
    from nicegui_base.integrations.nicegui_content import CodeViewer, ProgressSteps
    from .capability_studio import render_data_dock
    from .project_state import (
        apply_project_preset, clear_project, delete_project_preset, project_history, project_presets,
        project_snapshot, restore_project_revision, save_project_preset, save_project_snapshot,
    )

    if model is None:
        snapshot = project_snapshot()
        meaningful = bool(snapshot.get('goal') or snapshot.get('pattern_key') or snapshot.get('queued_entry_keys'))
        model = BuilderModel.from_snapshot(snapshot) if meaningful else BuilderModel()

    host = ui.element('div').classes('cui-builder')

    def save() -> None:
        save_project_snapshot(model.snapshot())

    def change(action) -> None:
        action(); save(); render()

    def render() -> None:
        host.clear()
        with host:
            ui.label('Goal → Data → App Pattern → Page Composition → Review → Generate').classes('cui-workbench-note')
            current_index = STAGE_ORDER.index(model.stage)
            steps = tuple(
                StepSpec(stage.value, {'pattern':'App Pattern','compose':'Page Composition'}.get(stage.value, stage.value.title()),
                         state=StepState.COMPLETE if index < current_index else StepState.ACTIVE if index == current_index else StepState.UPCOMING)
                for index, stage in enumerate(STAGE_ORDER)
            )
            ProgressSteps(steps)
            with ui.element('div').classes('cui-workbench-toolbar'):
                if model.stage is not BuilderStage.GOAL:
                    Button('Edit goal', on_click=lambda: change(lambda: model.go(BuilderStage.GOAL)))
                if current_index >= STAGE_ORDER.index(BuilderStage.PATTERN):
                    Button('Edit data', on_click=lambda: change(lambda: model.go(BuilderStage.DATA)))
                if model.pattern_key:
                    Button('Change pattern', on_click=lambda: change(lambda: model.go(BuilderStage.PATTERN)))
                Button('Clear project', on_click=lambda: (clear_project(), host.clear(), ui.navigate.to('/build')))

            with ui.element('details').classes('cui-workbench-section cui-project-memory'):
                with ui.element('summary').props('tabindex="0"'):
                    ui.label('Project presets & history').classes('cui-workbench-section-title')
                ui.label('Named presets are reusable project snapshots. History is bounded and automatically records structural changes so you can diff or restore without creating another project model.').classes('cui-workbench-note')
                preset_field = TextInput('Preset name', placeholder='e.g. Chamber drift investigation')
                def save_named_preset():
                    name = str(getattr(preset_field.element, 'value', '') or '')
                    try:
                        save_project_preset(name, model.snapshot())
                    except ValueError as exc:
                        ui.notify(str(exc), type='warning')
                        return
                    render()
                Button('Save current as preset', on_click=save_named_preset)
                presets_now = project_presets()
                if presets_now:
                    ui.label('Saved presets').classes('cui-workbench-card__meta')
                    for preset_name in tuple(presets_now)[:8]:
                        with ui.element('div').classes('cui-workbench-toolbar'):
                            ui.label(preset_name).classes('cui-workbench-chip')
                            def apply_named(name=preset_name):
                                model.load_snapshot(apply_project_preset(name)); render()
                            def delete_named(name=preset_name):
                                delete_project_preset(name); render()
                            Button('Apply', on_click=apply_named)
                            Button('Delete', on_click=delete_named)
                history_now = project_history()
                if history_now:
                    ui.label('Recent revisions').classes('cui-workbench-card__meta')
                    current = model.snapshot()
                    from .project_history import diff_projects
                    for revision in history_now[:8]:
                        snapshot = revision.get('snapshot', {})
                        diff = diff_projects(snapshot, current)
                        with ui.element('article').classes('cui-workbench-card'):
                            ui.label(str(revision.get('label') or 'Project checkpoint')).classes('cui-workbench-card__title')
                            ui.label(diff.summary()).classes('cui-workbench-note')
                            Button('Restore revision', on_click=lambda rid=revision.get('id'): (model.load_snapshot(restore_project_revision(str(rid))), render()))

            if model.stage is BuilderStage.GOAL:
                from .starter_kits import GOLDEN_STARTERS
                ui.label('Fastest path · Golden Starters').classes('cui-workbench-section-title')
                ui.label('Choose a proven application intent and NiceGUI Base will select the canonical pattern, page slots and best reusable capabilities from the current registries. You can still edit every decision afterward.').classes('cui-workbench-note')
                quick_build_host = ui.element('div').classes('cui-workbench-section')
                async def quick_build(starter_key: str):
                    from .release_pipeline import build_runtime_proven_starter
                    rows = tuple(model.data.serializable_rows())
                    quick_build_host.clear()
                    with quick_build_host:
                        ui.label('Building and proving starter…').classes('cui-workbench-note')
                    try:
                        result = await asyncio.to_thread(build_runtime_proven_starter, starter_key, rows=rows)
                    except Exception as exc:
                        quick_build_host.clear()
                        with quick_build_host:
                            ui.label(f'Build failed: {type(exc).__name__}: {exc}').classes('cui-workbench-note')
                        return
                    quick_build_host.clear()
                    with quick_build_host:
                        ui.label(str(result.project.get('name') or starter_key)).classes('cui-workbench-section-title')
                        with ui.element('div').classes('cui-workbench-quality-grid'):
                            for label, value in (
                                ('Project audit', result.audit.status),
                                ('Source / ZIP', 'PASS' if result.source_ok else 'FAIL'),
                                ('Live startup', 'PASS' if result.live and result.live.ok else 'FAIL'),
                            ):
                                with ui.element('article').classes('cui-workbench-quality-card'):
                                    ui.label(label).classes('cui-workbench-card__title'); ui.label(value).classes('cui-workbench-chip')
                        if result.ok:
                            filename = str(result.project.get('name') or starter_key).lower().replace(' ', '-').replace('/', '-') + '.zip'
                            Button('Download runtime-proven ZIP', on_click=lambda data=result.payload, name=filename: ui.download.content(data, name))
                        else:
                            for finding in result.source_findings:
                                ui.label('✕ ' + finding).classes('cui-workbench-note')
                            if result.live and result.live.findings:
                                for finding in result.live.findings:
                                    ui.label('✕ ' + finding).classes('cui-workbench-note')
                for category in ('Engineering', 'Generic'):
                    ui.label(category).classes('cui-workbench-card__meta')
                    with ui.element('div').classes('cui-workbench-grid cui-golden-starter-grid'):
                        for starter in (item for item in GOLDEN_STARTERS if item.category == category):
                            with ui.element('article').classes('cui-workbench-card cui-golden-starter-card'):
                                ui.label(starter.pattern_key.replace('_', ' ').title()).classes('cui-workbench-card__meta')
                                ui.label(starter.title).classes('cui-workbench-card__title')
                                ui.label(starter.description).classes('cui-workbench-card__body')
                                ui.label(' · '.join(starter.tags)).classes('cui-workbench-note')
                                with ui.element('div').classes('cui-workbench-toolbar'):
                                    Button('Use Golden Starter', on_click=lambda key=starter.key: change(lambda: model.apply_golden_starter(key)))
                                    Button('Build & prove ZIP', on_click=lambda key=starter.key: quick_build(key))
                ui.label('Or describe a custom application').classes('cui-workbench-section-title')
                goal = TextInput('What are you trying to build?', value=model.goal, placeholder='e.g. monitor chamber drift and investigate abnormal wafers')
                kind = Select('Problem type', {
                    'engineering analysis':'Engineering analysis',
                    'generic application':'Generic application',
                    'visualization':'Visualization / analytical workspace',
                }, value=model.problem_type, clearable=False)
                def continue_goal():
                    model.set_goal(str(getattr(goal.element,'value','')), problem_type=str(getattr(kind.element,'value','engineering analysis')))
                    save(); render()
                Button('Continue to data', on_click=continue_goal)

            elif model.stage is BuilderStage.DATA:
                ui.label('Development data').classes('cui-workbench-section-title')
                ui.label('Paste/upload/edit once. The schema is carried into composition recommendations; project resume stores at most 200 development rows and never becomes a production data store.').classes('cui-workbench-note')
                render_data_dock(model.data, on_change=lambda _data: save())
                Button('Choose application pattern', on_click=lambda: change(lambda: model.go(BuilderStage.PATTERN)))

            elif model.stage is BuilderStage.PATTERN:
                ui.label('Choose the application shell first').classes('cui-workbench-section-title')
                ui.label('Patterns own responsive information hierarchy. Components fill slots; they do not invent layout ad hoc.').classes('cui-workbench-note')
                for item in model.pattern_recommendations():
                    key = str(item.entry.metadata.get('pattern_key'))
                    from nicegui_base.patterns.registry import get_pattern
                    definition = get_pattern(key)
                    with ui.element('article').classes('cui-workbench-card'):
                        ui.label(item.entry.title).classes('cui-workbench-card__title')
                        ui.label(definition.purpose).classes('cui-workbench-card__body')
                        for reason in item.reasons[:2]:
                            ui.label('✓ ' + reason).classes('cui-workbench-note')
                        ui.label('Slots: ' + ', '.join(slot.value for slot in definition.slot_order if slot.value != 'header')).classes('cui-workbench-note')
                        Button('Use this pattern', on_click=lambda key=key: change(lambda: model.select_pattern(key)))

            elif model.stage is BuilderStage.COMPOSE:
                if not model.pattern_key:
                    model.go(BuilderStage.PATTERN); save(); render(); return
                from nicegui_base.patterns.registry import get_pattern
                definition = get_pattern(model.pattern_key)
                ui.label(definition.pattern.value.replace('_',' ').title()).classes('cui-workbench-title')
                ui.label(definition.purpose).classes('cui-workbench-subtitle')
                recommended = model.recommended_composition()
                with ui.element('section').classes('cui-workbench-section cui-auto-compose'):
                    ui.label('Auto-compose').classes('cui-workbench-section-title')
                    ui.label('Schema-aware deterministic assembly uses your goal, semantic roles, canonical pattern slots and the existing registries. No opaque AI ranking or duplicate component catalog is introduced.').classes('cui-workbench-note')
                    ui.label(f'Recommended capabilities: {len(recommended.selected_keys)}' + (f" · unresolved required intents: {len(recommended.unresolved)}" if recommended.unresolved else '')).classes('cui-workbench-note')
                    with ui.element('div').classes('cui-workbench-toolbar'):
                        Button('Fill empty slots automatically', on_click=lambda: change(lambda: model.auto_compose(replace=False)))
                        Button('Replace with recommended composition', on_click=lambda: change(lambda: model.auto_compose(replace=True)))
                with ui.element('div').classes('cui-workbench-quality-grid'):
                    for label, value in (('Desktop',definition.desktop_behavior),('Tablet',definition.tablet_behavior),('Phone',definition.phone_behavior)):
                        with ui.element('article').classes('cui-workbench-quality-card'):
                            ui.label(label).classes('cui-workbench-card__title'); ui.label(value).classes('cui-workbench-note')
                app_name = TextInput('Application name', value=model.app_name)
                theme = Select('Theme', {'system':'System','light':'Light','dark':'Dark'}, value=model.theme, clearable=False)
                density = Select('Density', {'comfortable':'Comfortable','compact':'Compact','dense':'Dense'}, value=model.density, clearable=False)
                def apply_config():
                    model.app_name = str(getattr(app_name.element,'value',model.app_name) or model.app_name)
                    model.theme = str(getattr(theme.element,'value','system'))
                    model.density = str(getattr(density.element,'value','compact'))
                    model._changed(); save(); render()
                Button('Apply project settings', on_click=apply_config)

                ui.label('Page slots').classes('cui-workbench-section-title')
                lookup = {entry.key:entry for entry in all_entries()}
                for slot in model.allowed_slots():
                    required = slot in model.required_slots()
                    with ui.element('article').classes('cui-workbench-card'):
                        ui.label(slot.replace('_',' ').title() + (' · required' if required else '')).classes('cui-workbench-card__title')
                        keys = model.placements.get(slot, [])
                        if not keys:
                            ui.label('Empty — generator will insert a safe starter for required slots.' if required else 'Optional slot is empty.').classes('cui-workbench-note')
                        for key in keys:
                            entry = lookup.get(key)
                            if not entry: continue
                            with ui.element('div').classes('cui-workbench-toolbar'):
                                ui.label(entry.title).classes('cui-workbench-chip')
                                Button('Remove', on_click=lambda key=key: change(lambda: model.remove(key)))

                slot_select = Select('Target slot', {slot:slot.replace('_',' ').title() for slot in model.allowed_slots()}, value=(model.allowed_slots()[0] if model.allowed_slots() else None), clearable=False)
                queued = set(model.queued_entry_keys)
                ui.label('Add reusable capability').classes('cui-workbench-section-title')
                ui.label('Studio-queued items appear first, followed by goal-ranked analytics, tables, charts and common controls.').classes('cui-workbench-note')
                for entry in model.candidates():
                    with ui.element('article').classes('cui-workbench-card'):
                        meta = entry.kind.value + (' · queued from Studio' if entry.key in queued else '')
                        ui.label(meta).classes('cui-workbench-card__meta')
                        ui.label(entry.title).classes('cui-workbench-card__title')
                        ui.label(entry.description).classes('cui-workbench-card__body')
                        def add(entry_key=entry.key):
                            slot = str(getattr(slot_select.element,'value','') or '')
                            model.place(entry_key, slot); save(); render()
                        Button('Add to selected slot', on_click=add)
                Button('Review composed app', on_click=lambda: change(lambda: model.go(BuilderStage.REVIEW)))

            elif model.stage is BuilderStage.REVIEW:
                review = model.review()
                ui.label('Review composed application').classes('cui-workbench-section-title')
                empty = review['empty_required_slots']
                if empty:
                    ui.label('Required slots without an explicit capability: ' + ', '.join(empty) + '. Safe generated starters will fill them.').classes('cui-workbench-note')
                audit = model.audit()
                with ui.element('section').classes('cui-workbench-section cui-project-audit'):
                    ui.label('Project audit').classes('cui-workbench-section-title')
                    with ui.element('div').classes('cui-workbench-quality-grid'):
                        for label, value in (
                            ('Assembly status', audit.status),
                            ('Placed capabilities', audit.placed_capabilities),
                            ('Explicit required slots', f'{len(audit.explicit_required_slots)} / {len(audit.required_slots)}'),
                            ('Warnings', len(audit.warnings)),
                            ('Blocking', len(audit.blocking)),
                        ):
                            with ui.element('article').classes('cui-workbench-quality-card'):
                                ui.label(label).classes('cui-workbench-card__title')
                                ui.label(str(value)).classes('cui-workbench-chip')
                    for finding in audit.findings:
                        mark = '✕' if finding.severity.value == 'blocking' else '⚠' if finding.severity.value == 'warning' else '•'
                        ui.label(f'{mark} {finding.message}').classes('cui-workbench-note')
                diff, recommended = model.composition_diff()
                with ui.element('section').classes('cui-workbench-section cui-composition-diff'):
                    ui.label('Current vs recommended').classes('cui-workbench-section-title')
                    if not diff.changed:
                        ui.label('Current composition already matches the deterministic recommendation for this goal, pattern and schema.').classes('cui-workbench-note')
                    else:
                        ui.label(f'{len(diff.added)} add · {len(diff.removed)} remove · {len(diff.moved)} move').classes('cui-workbench-note')
                        for slot, key in diff.added[:6]:
                            ui.label(f'+ {slot} · {key}').classes('cui-workbench-note')
                        for slot, key in diff.removed[:6]:
                            ui.label(f'− {slot} · {key}').classes('cui-workbench-note')
                        for key, before, after in diff.moved[:6]:
                            ui.label(f'↔ {key} · {before} → {after}').classes('cui-workbench-note')
                        Button('Apply recommended composition', on_click=lambda: change(lambda: model.auto_compose(replace=True)))
                CodeViewer(json.dumps(review, indent=2, sort_keys=True, default=str), language='json')
                generation_issues = model.generation_issues()
                for issue in generation_issues:
                    ui.label('⚠ ' + issue).classes('cui-workbench-note')
                Button('Generate and smoke-test', disabled=bool(generation_issues), on_click=lambda: change(lambda: model.go(BuilderStage.GENERATE)))

            elif model.stage is BuilderStage.GENERATE:
                generation_issues = model.generation_issues()
                if generation_issues:
                    for issue in generation_issues:
                        ui.label('✕ ' + issue).classes('cui-workbench-note')
                    Button('Back to composition', on_click=lambda: change(lambda: model.go(BuilderStage.COMPOSE)))
                    return
                payload, report = model.generate()
                ui.label('Generated starter').classes('cui-workbench-section-title')
                with ui.element('div').classes('cui-workbench-quality-grid'):
                    for label, value in (('Source / ZIP smoke', 'PASS' if report.ok else 'FAIL'),('Python files',report.python_files),('ZIP files',report.files)):
                        with ui.element('article').classes('cui-workbench-quality-card'):
                            ui.label(label).classes('cui-workbench-card__title'); ui.label(str(value)).classes('cui-workbench-chip')
                proof_state = {'report': None}
                proof_host = ui.element('div').classes('cui-workbench-section')
                download_host = ui.element('div').classes('cui-workbench-toolbar')

                async def run_live_proof():
                    from .runtime_proof import run_generated_live_smoke
                    proof_state['report'] = await asyncio.to_thread(run_generated_live_smoke, payload)
                    render_live_proof()

                def render_live_proof() -> None:
                    proof_host.clear(); download_host.clear()
                    with proof_host:
                        ui.label('Runtime startup proof').classes('cui-workbench-section-title')
                        if report.findings:
                            for finding in report.findings:
                                ui.label('✕ ' + finding).classes('cui-workbench-note')
                            ui.label('Live startup is blocked until source/ZIP smoke passes.').classes('cui-workbench-note')
                            return
                        live = proof_state['report']
                        if live is None:
                            ui.label('Source and generated-code contracts passed. Execute the generated app in a fresh subprocess and request its root route before download.').classes('cui-workbench-note')
                            Button('Run live startup proof', on_click=run_live_proof)
                            return
                        with ui.element('div').classes('cui-workbench-quality-grid'):
                            for label, value in (
                                ('Live startup', 'PASS' if live.ok else 'FAIL'),
                                ('Elapsed', f'{live.elapsed_ms} ms'),
                                ('Routes', f'{sum(item.ok for item in live.routes)} / {len(live.routes)}'),
                            ):
                                with ui.element('article').classes('cui-workbench-quality-card'):
                                    ui.label(label).classes('cui-workbench-card__title'); ui.label(str(value)).classes('cui-workbench-chip')
                        for route in live.routes:
                            ui.label(f"{'✓' if route.ok else '✕'} {route.route} · {route.status if route.status is not None else 'unreachable'} · {route.elapsed_ms} ms" + (f' · {route.detail}' if route.detail else '')).classes('cui-workbench-note')
                        if live.findings:
                            for finding in live.findings:
                                ui.label('✕ ' + finding).classes('cui-workbench-note')
                            if live.stderr_tail:
                                ui.label('Server stderr').classes('cui-workbench-section-title')
                                CodeViewer(live.stderr_tail, language='text')
                            Button('Run live startup proof again', on_click=run_live_proof)
                        else:
                            ui.label('The generated app started in a fresh Python process and rendered its root route successfully.').classes('cui-workbench-note')
                    live = proof_state['report']
                    if live is not None and live.ok:
                        with download_host:
                            def download_zip():
                                ui.download.content(payload, f"{model.app_name.lower().replace(' ','-')}.zip")
                            Button('Download runtime-proven starter ZIP', on_click=download_zip)

                render_live_proof()
                ui.label('Deterministic project signature: ' + model.deterministic_signature()).classes('cui-workbench-note')

    render()
    return model


__all__ = ['BuilderModel','BuilderStage','PatternRecommendation','STAGE_ORDER','render_builder']
