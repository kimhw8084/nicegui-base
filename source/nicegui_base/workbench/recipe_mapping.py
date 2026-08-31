from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .data_dock import DataDockModel


@dataclass(frozen=True, slots=True)
class RecipeMappingSummary:
    recipe_key: str
    bindings: Mapping[str, str]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    available_panels: tuple[str, ...]
    unavailable_panels: tuple[str, ...]
    available_filters: tuple[str, ...]
    unavailable_filters: tuple[str, ...]

    @property
    def compatible(self) -> bool:
        return not self.missing_required


@dataclass(slots=True)
class RecipeMappingModel:
    """Workbench adapter over canonical recipe/source compatibility semantics."""

    recipe_key: str
    data: DataDockModel
    overrides: dict[str, str] = field(default_factory=dict)
    confirmed: bool = False
    revision: int = 0

    @property
    def recipe(self):
        from nicegui_base.semiconductor import get_semiconductor_recipe
        return get_semiconductor_recipe(self.recipe_key)

    def evaluate(self) -> RecipeMappingSummary:
        from nicegui_base.semiconductor import resolve_recipe_source
        compatibility = resolve_recipe_source(
            self.recipe,
            self.data.to_schema(key=f'workbench:{self.recipe_key}'),
            field_overrides=self.overrides,
        )
        return RecipeMappingSummary(
            compatibility.recipe_key,
            dict(compatibility.bindings),
            tuple(compatibility.missing_required),
            tuple(compatibility.missing_optional),
            tuple(compatibility.available_panels),
            tuple(compatibility.unavailable_panels),
            tuple(compatibility.available_filters),
            tuple(compatibility.unavailable_filters),
        )

    def set_override(self, logical_field: str, source_field: str | None) -> RecipeMappingSummary:
        keys = {item.key for item in self.recipe.field_requirements}
        if logical_field not in keys:
            raise KeyError(f'unknown recipe logical field: {logical_field}')
        if not source_field:
            self.overrides.pop(logical_field, None)
        else:
            if source_field not in self.data.snapshot.column_names:
                raise KeyError(f'unknown source column: {source_field}')
            self.overrides[logical_field] = source_field
        self.confirmed = False
        self.revision += 1
        return self.evaluate()

    def auto_map(self) -> RecipeMappingSummary:
        """Accept canonical candidate/role matching; do not invent Workbench heuristics."""
        self.overrides.clear()
        self.confirmed = False
        self.revision += 1
        return self.evaluate()

    def confirm(self) -> RecipeMappingSummary:
        result = self.evaluate()
        if not result.compatible:
            raise ValueError('required recipe fields must be mapped before confirmation')
        self.confirmed = True
        self.revision += 1
        return result

    def to_data_source(self):
        if not self.confirmed:
            raise RuntimeError('confirm recipe mapping before creating a source')
        return self.data.to_data_source(key=f'workbench:{self.recipe_key}')


def mapping_requirements(recipe_key: str) -> tuple[dict[str, Any], ...]:
    from nicegui_base.semiconductor import get_semiconductor_recipe
    recipe = get_semiconductor_recipe(recipe_key)
    return tuple({
        'key': item.key,
        'required': item.required,
        'candidates': tuple(item.candidates),
        'roles': tuple(role.value for role in item.roles),
        'description': item.description,
    } for item in recipe.field_requirements)


def render_recipe_mapping(
    model: RecipeMappingModel,
    *,
    on_confirm=None,
    preview_panel=None,
) -> None:
    """Render the canonical recipe mapping flow around an existing Data Dock model."""
    from nicegui import ui
    from nicegui_base.feedback import FeedbackIntent
    from nicegui_base.integrations.nicegui_components import Button, Select
    from nicegui_base.integrations.nicegui_interactions import Alert

    host = ui.element('div').classes('cui-recipe-mapping')

    def render() -> None:
        result = model.evaluate()
        host.clear()
        with host:
            with ui.element('div').classes('cui-data-dock-summary'):
                for value, label in (
                    (len(result.bindings), 'mapped logical fields'),
                    (len(result.missing_required), 'required missing'),
                    (len(result.missing_optional), 'optional missing'),
                    (len(result.available_panels), 'available panels'),
                ):
                    with ui.element('div').classes('cui-workbench-kpi'):
                        ui.label(str(value)).classes('text-h6')
                        ui.label(label)
            if result.missing_required:
                Alert(
                    'Required mapping incomplete',
                    message='Map: ' + ', '.join(result.missing_required),
                    intent=FeedbackIntent.DANGER,
                )
            elif result.missing_optional:
                Alert(
                    'Optional data unavailable',
                    message='The recipe remains runnable; dependent optional panels will be unavailable: ' + ', '.join(result.missing_optional),
                    intent=FeedbackIntent.WARNING,
                )
            ui.label('Logical field mapping').classes('cui-workbench-section-title')
            columns = model.data.snapshot.column_names
            options = {'': 'Auto / unmapped', **{name:name for name in columns}}
            requirements = mapping_requirements(model.recipe_key)
            for requirement in requirements:
                key = requirement['key']
                automatic = result.bindings.get(key, '')
                selected = model.overrides.get(key, automatic)
                with ui.element('div').classes('cui-recipe-mapping__row'):
                    ui.label(key + (' *' if requirement['required'] else '')).classes('cui-field-label')
                    detail = []
                    if requirement['candidates']:
                        detail.append('candidates: ' + ', '.join(requirement['candidates']))
                    if requirement['roles']:
                        detail.append('roles: ' + ', '.join(requirement['roles']))
                    if detail:
                        ui.label(' · '.join(detail)).classes('cui-workbench-note')
                    def mapping_changed(event, logical=key):
                        value = str(getattr(event, 'value', '') or '')
                        model.set_override(logical, value or None)
                        render()
                    Select('Source column', options, value=selected or '', clearable=False, on_change=mapping_changed)
            ui.label('Panel availability').classes('cui-workbench-section-title')
            recipe = model.recipe
            for panel in recipe.panels:
                available = panel.panel_id in result.available_panels
                with ui.element('article').classes('cui-recipe-panel-status ' + ('is-available' if available else 'is-unavailable')):
                    ui.label(panel.title).classes('cui-workbench-card__title')
                    ui.label('Available' if available else 'Unavailable with current mapping').classes('cui-workbench-note')
                    if panel.field_requirements:
                        ui.label('Needs: ' + ', '.join(panel.field_requirements)).classes('cui-workbench-note')
                    if available and preview_panel is not None:
                        Button('Preview panel', on_click=lambda panel=panel: preview_panel(panel))
            if result.unavailable_filters:
                ui.label('Unavailable filters: ' + ', '.join(result.unavailable_filters)).classes('cui-workbench-note')

            async def confirm():
                confirmed = model.confirm()
                if on_confirm is not None:
                    value = on_confirm(model, confirmed)
                    if hasattr(value, '__await__'):
                        await value
                render()

            Button('Confirm mapping', disabled=not result.compatible, on_click=confirm)
            if model.confirmed:
                Alert('Mapping confirmed', message='The recipe preview can now use this governed source mapping.', intent=FeedbackIntent.SUCCESS)

    render()


__all__ = ['RecipeMappingModel','RecipeMappingSummary','mapping_requirements','render_recipe_mapping']
