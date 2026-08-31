from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from .catalog import all_entries
from .codegen import CapabilityConfiguration, CodeArtifact, code_artifact, generate_application_zip
from .data_dock import DataDockModel, default_data_dock
from .models import WorkbenchEntry, WorkbenchKind
from .search import score_entry


class BuilderStage(str, Enum):
    GOAL = 'goal'
    DATA = 'data'
    RECOMMENDATION = 'recommendation'
    COMPOSE = 'compose'
    REVIEW = 'review'
    GENERATE = 'generate'


STAGE_ORDER = (
    BuilderStage.GOAL,
    BuilderStage.DATA,
    BuilderStage.RECOMMENDATION,
    BuilderStage.COMPOSE,
    BuilderStage.REVIEW,
    BuilderStage.GENERATE,
)


@dataclass(frozen=True, slots=True)
class BuilderRecommendation:
    entry: WorkbenchEntry
    score: int
    reasons: tuple[str, ...]
    blockers: tuple[str, ...] = ()

    @property
    def selectable(self) -> bool:
        return not self.blockers


@dataclass(slots=True)
class BuilderModel:
    goal: str = ''
    problem_type: str = 'engineering analysis'
    data: DataDockModel = field(default_factory=default_data_dock)
    stage: BuilderStage = BuilderStage.GOAL
    selected_entry_key: str | None = None
    app_name: str = 'My NiceGUI App'
    configuration: CapabilityConfiguration = field(default_factory=CapabilityConfiguration)
    revision: int = 0

    def set_goal(self, goal: str, *, problem_type: str | None = None) -> None:
        self.goal = str(goal).strip()
        if problem_type is not None:
            self.problem_type = str(problem_type).strip() or 'engineering analysis'
        self.selected_entry_key = None
        self.stage = BuilderStage.DATA
        self.revision += 1

    def go(self, stage: BuilderStage | str) -> BuilderStage:
        self.stage = BuilderStage(stage)
        self.revision += 1
        return self.stage

    @property
    def selected_entry(self) -> WorkbenchEntry | None:
        if self.selected_entry_key is None:
            return None
        return next((entry for entry in all_entries() if entry.key == self.selected_entry_key), None)

    def select(self, entry_key: str) -> WorkbenchEntry:
        entry = next((item for item in all_entries() if item.key == entry_key), None)
        if entry is None:
            raise KeyError(entry_key)
        recommendation = next((item for item in self.recommendations(limit=100) if item.entry.key == entry_key), None)
        if recommendation is not None and not recommendation.selectable:
            raise ValueError('selected recommendation has unresolved required-data blockers')
        self.selected_entry_key = entry.key
        self.configuration = CapabilityConfiguration(title=entry.title)
        self.stage = BuilderStage.COMPOSE
        self.revision += 1
        return entry

    def _recipe_evidence(self, entry: WorkbenchEntry) -> tuple[int, list[str], list[str]]:
        if entry.kind is not WorkbenchKind.RECIPE:
            return 0, [], []
        from nicegui_base.semiconductor import resolve_recipe_source
        recipe_key = str(entry.metadata.get('recipe_key'))
        compatibility = resolve_recipe_source(recipe_key, self.data.to_schema(key='workbench:builder'))
        reasons: list[str] = []
        blockers: list[str] = []
        score = 0
        if compatibility.compatible:
            score += 70
            reasons.append('your current schema satisfies the recipe’s required logical fields')
        else:
            score -= 45
            blockers.extend(f'missing required field: {item}' for item in compatibility.missing_required)
            reasons.append('recipe semantics match the goal, but required data mapping is incomplete')
        if compatibility.available_panels:
            score += min(20, len(compatibility.available_panels) * 3)
            reasons.append(f'{len(compatibility.available_panels)} recipe panels are available with the current schema')
        if compatibility.unavailable_panels:
            reasons.append(f'{len(compatibility.unavailable_panels)} panels would degrade safely until optional fields are mapped')
        return score, reasons, blockers

    def recommendations(self, *, limit: int = 8) -> tuple[BuilderRecommendation, ...]:
        query = ' '.join(part for part in (self.problem_type, self.goal) if part).strip()
        candidates: list[BuilderRecommendation] = []
        preferred_kinds = {WorkbenchKind.RECIPE, WorkbenchKind.PATTERN, WorkbenchKind.ANALYTIC}
        for entry in all_entries():
            if entry.kind not in preferred_kinds:
                continue
            match = score_entry(entry, query) if query else None
            score = match.score if match else 0
            reasons: list[str] = []
            blockers: list[str] = []
            if match:
                reasons.append('matches your stated goal: ' + ', '.join(match.matched_terms))
            if self.problem_type.casefold().startswith('generic') and entry.kind is WorkbenchKind.PATTERN:
                score += 80; reasons.append('generic application goals prefer a governed application pattern')
            if 'engineering' in self.problem_type.casefold() and entry.kind is WorkbenchKind.RECIPE:
                score += 65; reasons.append('engineering analysis goals prefer a complete governed semiconductor recipe')
            if 'visual' in self.problem_type.casefold() and entry.kind is WorkbenchKind.ANALYTIC:
                score += 70; reasons.append('visualization goals prefer a directly runnable analytical surface')
            extra, recipe_reasons, recipe_blockers = self._recipe_evidence(entry)
            score += extra; reasons.extend(recipe_reasons); blockers.extend(recipe_blockers)
            if entry.kind is WorkbenchKind.PATTERN:
                score += 15
                reasons.append('the pattern provides a governed responsive page structure and starter output')
            if score <= 0 and not reasons:
                continue
            candidates.append(BuilderRecommendation(entry, score, tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(blockers))))
        candidates.sort(key=lambda item: (-item.selectable, -item.score, item.entry.kind.value, item.entry.title.casefold(), item.entry.key))
        return tuple(candidates[:limit])

    def review(self) -> dict[str, Any]:
        entry = self.selected_entry
        if entry is None:
            raise RuntimeError('select a recommendation before review')
        return {
            'goal': self.goal,
            'problem_type': self.problem_type,
            'data': {
                'rows': self.data.snapshot.quality.rows,
                'columns': self.data.snapshot.column_names,
                'roles': {column.name: column.role for column in self.data.columns},
            },
            'selection': {
                'key': entry.key,
                'title': entry.title,
                'kind': entry.kind.value,
                'authority': entry.source_authority,
            },
            'configuration': self.configuration.normalized(),
        }

    def artifact(self) -> CodeArtifact:
        entry = self.selected_entry
        if entry is None:
            raise RuntimeError('select a recommendation before generation')
        return code_artifact(entry, self.configuration, data_columns=self.data.snapshot.column_names)

    def generate_zip(self) -> bytes:
        entry = self.selected_entry
        if entry is None:
            raise RuntimeError('select a recommendation before generation')
        return generate_application_zip(entry, app_name=self.app_name, config=self.configuration)

    def deterministic_signature(self) -> str:
        review = repr(self.review()).encode('utf-8')
        artifact = self.artifact()
        payload = review + artifact.minimal.encode() + artifact.production.encode() + artifact.fragment.to_json().encode()
        return hashlib.sha256(payload).hexdigest()


def render_builder(model: BuilderModel | None = None) -> BuilderModel:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, Select, TextInput
    from nicegui_base.integrations.nicegui_content import CodeViewer, ProgressSteps
    from nicegui_base.content import StepSpec, StepState
    from .capability_studio import render_data_dock

    model = model or BuilderModel()
    host = ui.element('div').classes('cui-builder')

    def render() -> None:
        host.clear()
        with host:
            ui.label('Goal → Data → Recommendation → Compose → Review → Generate').classes('cui-workbench-note')
            current_index = STAGE_ORDER.index(model.stage)
            steps = tuple(
                StepSpec(
                    stage.value, stage.value.title(),
                    state=StepState.COMPLETE if index < current_index else StepState.ACTIVE if index == current_index else StepState.UPCOMING,
                )
                for index, stage in enumerate(STAGE_ORDER)
            )
            ProgressSteps(steps)
            if model.stage is BuilderStage.GOAL:
                goal = TextInput('What are you trying to build?', value=model.goal, placeholder='e.g. monitor chamber drift and investigate abnormal wafers')
                kind = Select('Problem type', {
                    'engineering analysis':'Engineering analysis',
                    'generic application':'Generic application',
                    'visualization':'Visualization / analytical surface',
                }, value=model.problem_type, clearable=False)
                def continue_goal():
                    model.set_goal(str(getattr(goal.element,'value','')), problem_type=str(getattr(kind.element,'value','engineering analysis')))
                    render()
                Button('Continue to data', on_click=continue_goal)
            elif model.stage is BuilderStage.DATA:
                ui.label('Development data').classes('cui-workbench-section-title')
                render_data_dock(model.data, on_change=lambda _data: None)
                Button('Recommend architecture', on_click=lambda: (model.go(BuilderStage.RECOMMENDATION), render()))
            elif model.stage is BuilderStage.RECOMMENDATION:
                recommendations = model.recommendations()
                if not recommendations:
                    ui.label('Add a clearer goal or development data to get a deterministic recommendation.').classes('cui-workbench-note')
                for item in recommendations:
                    with ui.element('article').classes('cui-workbench-card'):
                        ui.label(item.entry.title).classes('cui-workbench-card__title')
                        ui.label(f'{item.entry.kind.value} · score {item.score}').classes('cui-workbench-note')
                        for reason in item.reasons:
                            ui.label('✓ ' + reason).classes('cui-workbench-note')
                        for blocker in item.blockers:
                            ui.label('⚠ ' + blocker).classes('cui-workbench-note')
                        Button('Compose with this', disabled=not item.selectable, on_click=lambda key=item.entry.key: (model.select(key), render()))
            elif model.stage is BuilderStage.COMPOSE:
                entry = model.selected_entry
                if entry is None:
                    model.go(BuilderStage.RECOMMENDATION); render(); return
                ui.label(entry.title).classes('cui-workbench-title')
                ui.label(entry.description).classes('cui-workbench-subtitle')
                app_name = TextInput('Application name', value=model.app_name)
                title = TextInput('Primary page/surface title', value=model.configuration.title or entry.title)
                density = Select('Density', {'comfortable':'Comfortable','compact':'Compact','dense':'Dense'}, value=model.configuration.density, clearable=False)
                def review_stage():
                    model.app_name = str(getattr(app_name.element,'value',model.app_name) or model.app_name)
                    model.configuration = CapabilityConfiguration(
                        title=str(getattr(title.element,'value',entry.title) or entry.title),
                        density=str(getattr(density.element,'value','compact')),
                        responsive_width=model.configuration.responsive_width,
                        theme=model.configuration.theme,
                        options=model.configuration.options,
                    )
                    model.go(BuilderStage.REVIEW); render()
                Button('Review composition', on_click=review_stage)
            elif model.stage is BuilderStage.REVIEW:
                review = model.review()
                ui.label('Review').classes('cui-workbench-section-title')
                CodeViewer(__import__('json').dumps(review, indent=2, sort_keys=True), language='json')
                ui.label('Why this architecture').classes('cui-workbench-section-title')
                selected = next((x for x in model.recommendations(limit=100) if x.entry.key == model.selected_entry_key), None)
                if selected:
                    for reason in selected.reasons:
                        ui.label('• ' + reason).classes('cui-workbench-note')
                Button('Generate', on_click=lambda: (model.go(BuilderStage.GENERATE), render()))
            elif model.stage is BuilderStage.GENERATE:
                artifact = model.artifact()
                ui.label('Generated starter output').classes('cui-workbench-section-title')
                CodeViewer(artifact.production, language='python')
                def download_zip():
                    data = model.generate_zip()
                    ui.download.content(data, f'{model.app_name.lower().replace(" ", "-")}.zip')
                Button('Download starter ZIP', on_click=download_zip)
                ui.label('Deterministic signature: ' + model.deterministic_signature()).classes('cui-workbench-note')

    render()
    return model


__all__ = ['BuilderModel','BuilderRecommendation','BuilderStage','STAGE_ORDER','render_builder']
