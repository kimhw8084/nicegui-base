from __future__ import annotations

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
        return tuple(issues)

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
    from .project_state import clear_project, project_snapshot, save_project_snapshot

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

            if model.stage is BuilderStage.GOAL:
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
                    for label, value in (('Smoke', 'PASS' if report.ok else 'FAIL'),('Python files',report.python_files),('ZIP files',report.files)):
                        with ui.element('article').classes('cui-workbench-quality-card'):
                            ui.label(label).classes('cui-workbench-card__title'); ui.label(str(value)).classes('cui-workbench-chip')
                if report.findings:
                    for finding in report.findings:
                        ui.label('✕ ' + finding).classes('cui-workbench-note')
                    ui.label('Download is blocked until generated-app smoke passes.').classes('cui-workbench-note')
                else:
                    def download_zip():
                        ui.download.content(payload, f"{model.app_name.lower().replace(' ','-')}.zip")
                    Button('Download smoke-tested starter ZIP', on_click=download_zip)
                ui.label('Deterministic project signature: ' + model.deterministic_signature()).classes('cui-workbench-note')

    render()
    return model


__all__ = ['BuilderModel','BuilderStage','PatternRecommendation','STAGE_ORDER','render_builder']
