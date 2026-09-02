from __future__ import annotations


def _pattern_checks(definition) -> tuple[tuple[bool, str], ...]:
    required = set(definition.required_slots)
    optional = set(definition.optional_slots)
    ordered = tuple(definition.slot_order)
    return (
        (not bool(required & optional), 'Required and optional slots do not overlap'),
        (set(ordered) == required | optional, 'Slot order covers every declared slot exactly once'),
        (all((definition.desktop_behavior, definition.tablet_behavior, definition.phone_behavior)), 'Desktop/tablet/phone behavior is explicitly declared'),
        (bool(definition.content_width), 'Content-width authority is declared'),
    )


def render_layout_studio() -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, Select
    from nicegui_base.patterns.registry import PATTERN_REGISTRY, get_pattern
    from .project_state import project_snapshot, save_project_snapshot

    ui.label('Canonical application shells').classes('cui-workbench-section-title')
    ui.label('Choose information hierarchy before individual controls. Responsive behavior is shown simultaneously so desktop decisions cannot silently break tablet or phone composition.').classes('cui-workbench-note')

    inspector = {'pattern':'dashboard'}
    preview_host = ui.element('div').classes('cui-workbench-preview')

    def render_device(definition, device: str, behavior: str) -> None:
        with ui.element('article').classes('cui-workbench-quality-card').props(f'data-device-proof="{device}"'):
            ui.label(device.upper()).classes('cui-workbench-card__meta')
            ui.label(behavior).classes('cui-workbench-note')
            with ui.element('div').classes('cui-workbench-chiprow'):
                for slot in definition.slot_order:
                    if slot.value == 'header':
                        continue
                    required = slot in definition.required_slots
                    ui.label(slot.value.replace('_',' ').title() + (' *' if required else '')).classes('cui-workbench-chip')

    def render_preview() -> None:
        definition = get_pattern(inspector['pattern'])
        preview_host.clear()
        with preview_host:
            ui.label(definition.pattern.value.replace('_',' ').title()).classes('cui-workbench-title')
            ui.label(definition.purpose).classes('cui-workbench-subtitle')
            ui.label(f'Content width: {definition.content_width.value} · Primary grid: {definition.primary_grid.value if definition.primary_grid else "pattern-specific"}').classes('cui-workbench-note')
            with ui.element('div').classes('cui-workbench-quality-grid cui-layout-device-proof-grid'):
                render_device(definition, 'desktop', definition.desktop_behavior)
                render_device(definition, 'tablet', definition.tablet_behavior)
                render_device(definition, 'phone', definition.phone_behavior)
            ui.label('Contract checks').classes('cui-workbench-section-title')
            for passed, text in _pattern_checks(definition):
                ui.label(f"{'✓' if passed else '✕'} {text}").classes('cui-workbench-note')
            ui.label('* required slot').classes('cui-workbench-note')

    def pattern_changed(event) -> None:
        inspector['pattern'] = str(getattr(event, 'value', 'dashboard'))
        render_preview()

    with ui.element('div').classes('cui-workbench-toolbar'):
        Select('Inspect pattern', {pattern.value:pattern.value.replace('_',' ').title() for pattern in PATTERN_REGISTRY}, value='dashboard', clearable=False, on_change=pattern_changed)
    render_preview()

    def use_pattern(key: str) -> None:
        project = project_snapshot()
        project['pattern_key'] = key
        definition = get_pattern(key)
        allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
        project['placements'] = {slot: values for slot, values in dict(project.get('placements') or {}).items() if slot in allowed}
        save_project_snapshot(project)
        ui.navigate.to('/build')

    ui.label('All governed patterns').classes('cui-workbench-section-title')
    with ui.element('div').classes('cui-workbench-grid'):
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
                checks = _pattern_checks(definition)
                ui.label(f'{sum(passed for passed, _ in checks)} / {len(checks)} responsive contract checks').classes('cui-workbench-note')
                Button('Inspect', on_click=lambda _e=None, key=pattern.value: (inspector.__setitem__('pattern', key), render_preview()))
                Button('Use in Builder', on_click=lambda _e=None, key=pattern.value: use_pattern(key))


__all__ = ['_pattern_checks','render_layout_studio']
