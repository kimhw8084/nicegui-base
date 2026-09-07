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
    from nicegui_base.integrations.nicegui_components import Select
    from nicegui_base.patterns.registry import PATTERN_REGISTRY, get_pattern

    ui.label('Canonical application shells').classes('cui-workbench-section-title')
    ui.label('Choose information hierarchy before individual controls. Responsive behavior is shown simultaneously so desktop decisions cannot silently break tablet or phone composition.').classes('cui-workbench-note')

    inspector = {'pattern':'dashboard'}
    preview_host = ui.element('div').classes('cui-workbench-preview')

    def render_device(definition, device: str, behavior: str) -> None:
        with ui.element('article').classes('cui-workbench-quality-card').props(f'data-device-proof="{device}"'):
            ui.label(device.upper()).classes('cui-workbench-card__meta')
            ui.label(behavior).classes('cui-workbench-note')
            with ui.element(f'div').classes(f'cui-layout-mini-frame cui-layout-mini-frame--{device}').props(
                f'data-layout-pattern="{definition.pattern.value}" data-layout-device="{device}"'
            ):
                with ui.element('div').classes('cui-layout-mini-frame__header'):
                    ui.label('App shell').classes('cui-layout-mini-frame__title')
                    ui.label('Header / navigation').classes('cui-layout-mini-frame__meta')
                with ui.element('div').classes('cui-layout-mini-frame__slots'):
                    for slot in definition.slot_order:
                        if slot.value == 'header':
                            continue
                        required = slot in definition.required_slots
                        with ui.element('div').classes('cui-layout-mini-slot').props(
                            f'data-layout-slot="{slot.value}" aria-label="{slot.value.replace("_", " ").title()} slot"'
                        ):
                            ui.label(slot.value.replace('_',' ').title()).classes('cui-layout-mini-slot__label')
                            if required:
                                ui.label('required').classes('cui-layout-mini-slot__meta')
            with ui.element('div').classes('cui-workbench-chiprow'):
                for slot in definition.slot_order:
                    if slot.value == 'header':
                        continue
                    required = slot in definition.required_slots
                    ui.label(slot.value.replace('_',' ').title() + (' *' if required else '')).classes('cui-workbench-chip')

    def render_catalog_miniature(definition, device: str) -> None:
        """Render the registered slot geometry, not a textual slot inventory."""
        with ui.element('div').classes(f'cui-layout-mini-frame cui-layout-mini-frame--{device}').props(
            f'data-layout-pattern="{definition.pattern.value}" data-layout-device="{device}"'
        ):
            with ui.element('div').classes('cui-layout-mini-frame__header'):
                ui.label(device.title()).classes('cui-layout-mini-frame__title')
            with ui.element('div').classes('cui-layout-mini-frame__slots'):
                for slot in definition.slot_order:
                    if slot.value == 'header':
                        continue
                    with ui.element('div').classes('cui-layout-mini-slot').props(
                        f'data-layout-slot="{slot.value}" aria-label="{slot.value.replace("_", " ").title()} slot"'
                    ):
                        ui.label(slot.value.replace('_', ' ').title()).classes('cui-layout-mini-slot__label')

    def render_preview() -> None:
        definition = get_pattern(inspector['pattern'])
        preview_host.clear()
        with preview_host:
            ui.label(definition.pattern.value.replace('_',' ').title()).classes('cui-workbench-title')
            ui.label(definition.purpose).classes('cui-workbench-subtitle')
            ui.label(f'Content width: {definition.content_width.value} · Primary grid: {definition.primary_grid.value if definition.primary_grid else "pattern-specific"}').classes('cui-workbench-note')
            with ui.element('section').classes('cui-layout-live-composition').props(
                f'data-live-layout-pattern="{definition.pattern.value}" data-scaffold-command="nicegui-base create-pattern ./my-app --name \'My App\' --pattern {definition.pattern.value}\"'
            ):
                ui.label('Live governed composition').classes('cui-workbench-section-title')
                ui.label('This example is the registered page implementation used by generated applications; the frames below explain its responsive slot contract.').classes('cui-workbench-note')
                from .pattern_specimens import render_pattern
                render_pattern(
                    definition.pattern.value,
                    title=f'{definition.pattern.value.replace("_", " ").title()} reference composition',
                    rows=({'id': 'REF-001', 'status': 'Nominal', 'value': 40.2}, {'id': 'REF-002', 'status': 'Watch', 'value': 40.8}),
                )
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

    ui.label('All governed patterns').classes('cui-workbench-section-title')
    with ui.element('div').classes('cui-workbench-grid'):
        for pattern, definition in PATTERN_REGISTRY.items():
            with ui.element('article').classes('cui-workbench-card').props(
                f'data-live-layout-pattern="{pattern.value}" data-scaffold-command="nicegui-base create-pattern ./my-app --name My-App --pattern {pattern.value}"'
            ):
                ui.label(pattern.value.replace('_',' ').upper()).classes('cui-workbench-card__meta')
                ui.label(pattern.value.replace('_',' ').title()).classes('cui-workbench-card__title')
                ui.label(definition.purpose).classes('cui-workbench-card__body')
                with ui.element('div').classes('cui-layout-catalog-miniatures'):
                    for device in ('desktop', 'tablet', 'phone'):
                        render_catalog_miniature(definition, device)
                with ui.element('div').classes('cui-workbench-chiprow'):
                    for slot in definition.slot_order:
                        if slot.value == 'header':
                            continue
                        required = slot in definition.required_slots
                        ui.label(slot.value.replace('_',' ').title() + (' *' if required else '')).classes('cui-workbench-chip')
                checks = _pattern_checks(definition)
                ui.label(f'{sum(passed for passed, _ in checks)} / {len(checks)} responsive contract checks').classes('cui-workbench-note')
                ui.link('Open live reference', f'/studio/pattern%3A{pattern.value}').classes('cui-workbench-chip')
                ui.label(f'nicegui-base create-pattern ./my-app --name "My App" --pattern {pattern.value}').classes('cui-workbench-note')
                from nicegui_base.integrations.nicegui_components import Button
                Button('Inspect', on_click=lambda _e=None, key=pattern.value: (inspector.__setitem__('pattern', key), render_preview()))


__all__ = ['_pattern_checks','render_layout_studio']
