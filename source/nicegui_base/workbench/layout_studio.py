from __future__ import annotations


_LAYOUT_GUIDANCE = {
    'dashboard': ('KPI + trends + exceptions', 'Avoid when the user must inspect one record at a time.'),
    'data_explorer': ('Filter → inspect → compare records', 'Avoid when recurring health monitoring is the primary job.'),
    'master_detail': ('Browse a list with persistent selected detail', 'Avoid when users need simultaneous population comparison.'),
    'crud': ('Managed records with create/edit/delete', 'Avoid when the surface is read-only analysis.'),
    'monitoring': ('Operational health with recurring refresh', 'Avoid when the workflow is a one-time investigation.'),
    'search': ('Query and contextual result selection', 'Avoid when filters are more important than text search.'),
    'settings': ('Configuration sections and durable save state', 'Avoid for high-frequency operational work.'),
    'wizard': ('Validated multi-step completion', 'Avoid when users need free navigation across records.'),
    'comparison': ('Aligned populations, deltas and evidence', 'Avoid when there is only one population.'),
    'analysis_workspace': ('Filters + governed visual + inspector', 'Avoid when a simple dashboard answers the question.'),
}


_SLOT_LABELS = {
    'filters': 'Filters', 'metrics': 'KPI strip', 'primary': 'Primary view', 'data': 'Supporting records',
    'details': 'Selected detail', 'inspector': 'Inspector', 'actions': 'Actions', 'navigation': 'Sections',
    'header': 'Header', 'steps': 'Progress steps', 'form': 'Validated form', 'comparison': 'Aligned comparison',
}

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

    ui.label('Canonical application shells').classes('cui-workbench-section-title')
    ui.label(
        'Scan every desktop/tablet/phone anatomy first. Inspect a full governed composition only after '
        'you have identified the closest information hierarchy.'
    ).classes('cui-workbench-note')

    inspector = {'pattern': 'dashboard'}
    preview_host = None

    def render_catalog_miniature(definition, device: str) -> None:
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
                        ui.label(_SLOT_LABELS.get(slot.value, slot.value.replace('_', ' ').title())).classes('cui-layout-mini-slot__label')

    def render_device(definition, device: str, behavior: str) -> None:
        with ui.element('article').classes('cui-workbench-quality-card').props(f'data-device-proof="{device}"'):
            ui.label(device.upper()).classes('cui-workbench-card__meta')
            ui.label(behavior).classes('cui-workbench-note')
            render_catalog_miniature(definition, device)

    def render_preview() -> None:
        definition = get_pattern(inspector['pattern'])
        if preview_host is None:
            return
        preview_host.clear()
        with preview_host:
            with ui.element('section').classes('cui-layout-live-composition').props(
                f'data-live-layout-pattern="{definition.pattern.value}" '
                f'data-scaffold-command="nicegui-base create-pattern ./my-app --name My-App --pattern {definition.pattern.value}"'
            ):
                ui.label(definition.pattern.value.replace('_', ' ').title()).classes('cui-workbench-title')
                ui.label(definition.purpose).classes('cui-workbench-subtitle')
                ui.label(
                    f'Content width: {definition.content_width.value} · '
                    f'Primary grid: {definition.primary_grid.value if definition.primary_grid else "pattern-specific"}'
                ).classes('cui-workbench-note')
                from .pattern_specimens import render_pattern
                render_pattern(
                    definition.pattern.value,
                    title=f'{definition.pattern.value.replace("_", " ").title()} reference composition',
                    rows=(
                        {'id': 'REF-001', 'status': 'Nominal', 'value': 40.2},
                        {'id': 'REF-002', 'status': 'Watch', 'value': 40.8},
                    ),
                )
            with ui.element('div').classes('cui-workbench-quality-grid cui-layout-device-proof-grid'):
                render_device(definition, 'desktop', definition.desktop_behavior)
                render_device(definition, 'tablet', definition.tablet_behavior)
                render_device(definition, 'phone', definition.phone_behavior)
            with ui.element('div').classes('cui-workbench-chiprow'):
                for passed, text in _pattern_checks(definition):
                    ui.label(('✓ ' if passed else '✕ ') + text).classes('cui-workbench-chip')

    def inspect(key: str) -> None:
        inspector['pattern'] = key
        render_preview()

    ui.label('All governed layouts').classes('cui-workbench-section-title')
    with ui.element('div').classes('cui-layout-gallery-grid').props('data-layout-gallery'):
        for pattern, definition in PATTERN_REGISTRY.items():
            key = pattern.value
            with ui.element('article').classes('cui-explorer-card cui-layout-gallery-card').props(
                f'data-layout-card="{key}"'
            ):
                ui.label(key.replace('_', ' ').upper()).classes('cui-workbench-card__meta')
                ui.label(key.replace('_', ' ').title()).classes('cui-workbench-card__title')
                ui.label(definition.purpose).classes('cui-workbench-card__body')
                best_for, avoid_when = _LAYOUT_GUIDANCE.get(key, (definition.purpose, 'Choose another registered layout when the anatomy differs.'))
                ui.label('Best for · ' + best_for).classes('cui-workbench-note')
                ui.label('Avoid when · ' + avoid_when).classes('cui-workbench-note')
                with ui.element('div').classes('cui-layout-catalog-miniatures'):
                    for device in ('desktop', 'tablet', 'phone'):
                        render_catalog_miniature(definition, device)
                with ui.element('div').classes('cui-explorer-card__actions'):
                    Button('Open live example', icon='arrow-right', on_click=lambda _e=None, value=key: inspect(value))
                    Button(
                        'Copy scaffold command', icon='code',
                        on_click=lambda _e=None, value=key: ui.run_javascript(
                            f'navigator.clipboard && navigator.clipboard.writeText({("nicegui-base create-pattern ./" + value)!r})'
                        ),
                    )

    ui.label('Inspect a layout').classes('cui-workbench-section-title')
    ui.label(
        'The complete live composition stays below the scan-first gallery so it never blocks discovery.'
    ).classes('cui-workbench-note')
    with ui.element('div').classes('cui-workbench-toolbar'):
        Select(
            'Inspect pattern',
            {pattern.value: pattern.value.replace('_', ' ').title() for pattern in PATTERN_REGISTRY},
            value='dashboard',
            clearable=False,
            on_change=lambda event: inspect(str(getattr(event, 'value', 'dashboard'))),
        )

    # DOM ownership is intentionally created here, after the scan-first gallery.
    # The inspector can be populated by the default selection or any card action
    # without moving ahead of the gallery in document order.
    preview_host = ui.element('div').classes('cui-layout-inspector-host')
    render_preview()


__all__ = ['_pattern_checks','render_layout_studio']
