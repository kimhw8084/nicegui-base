from __future__ import annotations


def render_layout_studio() -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, Select
    from nicegui_base.integrations.nicegui_layout import SegmentedControl
    from nicegui_base.patterns.registry import PATTERN_REGISTRY, get_pattern
    from .project_state import project_snapshot, save_project_snapshot

    ui.label('Canonical application shells').classes('cui-workbench-section-title')
    ui.label('Choose information hierarchy before individual controls. Every card below is the canonical responsive pattern contract used by Builder and generated starters.').classes('cui-workbench-note')

    inspector = {'pattern':'dashboard', 'device':'desktop'}
    preview_host = ui.element('div').classes('cui-workbench-preview')

    def render_preview() -> None:
        definition = get_pattern(inspector['pattern'])
        widths = {'desktop':'1200px','tablet':'760px','phone':'390px'}
        behavior = {
            'desktop':definition.desktop_behavior,
            'tablet':definition.tablet_behavior,
            'phone':definition.phone_behavior,
        }[inspector['device']]
        preview_host.clear(); preview_host.style(replace=f"max-width:{widths[inspector['device']]};width:100%")
        with preview_host:
            ui.label(f"{definition.pattern.value.replace('_',' ').title()} · {inspector['device'].title()}").classes('cui-workbench-card__title')
            ui.label(behavior).classes('cui-workbench-note')
            with ui.element('div').classes('cui-workbench-grid'):
                for slot in definition.slot_order:
                    if slot.value == 'header':
                        continue
                    required = slot in definition.required_slots
                    with ui.element('article').classes('cui-workbench-quality-card'):
                        ui.label(slot.value.replace('_',' ').title()).classes('cui-workbench-card__title')
                        ui.label('Required' if required else 'Optional').classes('cui-workbench-chip')

    def pattern_changed(event) -> None:
        inspector['pattern'] = str(getattr(event, 'value', 'dashboard')); render_preview()
    def device_changed(event) -> None:
        inspector['device'] = str(getattr(event, 'value', 'desktop')); render_preview()

    with ui.element('div').classes('cui-workbench-toolbar'):
        Select('Pattern', {pattern.value:pattern.value.replace('_',' ').title() for pattern in PATTERN_REGISTRY}, value='dashboard', clearable=False, on_change=pattern_changed)
        SegmentedControl({'desktop':'Desktop','tablet':'Tablet','phone':'Phone'}, value='desktop', on_change=device_changed)
    render_preview()

    def use_pattern(key: str) -> None:
        project = project_snapshot()
        project['pattern_key'] = key
        definition = get_pattern(key)
        allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
        project['placements'] = {slot: values for slot, values in dict(project.get('placements') or {}).items() if slot in allowed}
        save_project_snapshot(project)
        ui.navigate.to('/build')

    for pattern, definition in PATTERN_REGISTRY.items():
        with ui.element('article').classes('cui-workbench-card'):
            ui.label(pattern.value.replace('_',' ').upper()).classes('cui-workbench-card__meta')
            ui.label(pattern.value.replace('_',' ').title()).classes('cui-workbench-card__title')
            ui.label(definition.purpose).classes('cui-workbench-card__body')
            with ui.element('div').classes('cui-workbench-chiprow'):
                for slot in definition.slot_order:
                    if slot.value == 'header':
                        continue
                    required = slot in definition.required_slots
                    ui.label(slot.value.replace('_',' ').title() + (' *' if required else '')).classes('cui-workbench-chip')
            with ui.element('div').classes('cui-workbench-quality-grid'):
                for label, value in (
                    ('Desktop', definition.desktop_behavior),
                    ('Tablet', definition.tablet_behavior),
                    ('Phone', definition.phone_behavior),
                ):
                    with ui.element('div').classes('cui-workbench-quality-card'):
                        ui.label(label).classes('cui-workbench-card__title')
                        ui.label(value).classes('cui-workbench-note')
            ui.label(f'Width: {definition.content_width.value} · Grid: {definition.primary_grid.value if definition.primary_grid else "pattern-specific"}').classes('cui-workbench-note')
            Button('Use in Builder', on_click=lambda key=pattern.value: use_pattern(key))


__all__ = ['render_layout_studio']
