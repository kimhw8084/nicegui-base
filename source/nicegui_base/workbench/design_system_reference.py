"""Live Design System reference rendered from the public token authority."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Mapping

from nicegui_base.design import CANONICAL_VIEWPORTS, ThemePalette, build_design_system
from nicegui_base.components import ButtonIntent, StatusIntent
from nicegui_base.integrations.nicegui_components import ActionButton, Button, StatusBadge


_FAMILY_GUIDANCE = {
    'spacing': 'Use for recurring distances; prefer semantic gaps for composition.',
    'semantic_gaps': 'Use for page, section, content, stack, cluster, and control relationships.',
    'radii': 'Use control, surface, and overlay families; use pill only for true pills.',
    'typography': 'Use a named hierarchy role instead of a local font size or weight.',
    'surfaces_colors': 'Use palette roles for surfaces, content, borders, status, and focus.',
    'borders': 'Use subtle for structural boundaries and strong for deliberate emphasis.',
    'elevation': 'Use flat, raised, or overlay roles; shadows vary with the active theme.',
    'density': 'Select one page density; table rows remain 44/38/34px for comfort/compact/dense.',
    'breakpoints': 'Use the responsive tiers and framework layout primitives, not local widths.',
    'motion': 'Use named durations and easing; honor reduced-motion preferences.',
    'z_index': 'Use the canonical overlay ordering; never invent local z-index values.',
    'interactive_states': 'Use state tokens for focus, disabled, pressed, selected, and hover behavior.',
}


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return ', '.join(f'{key}={item}' for key, item in value.items())
    return str(value)


def _copy_api(api: str) -> None:
    """Keep the reference copy action on a governed component boundary."""
    from nicegui import ui

    with ui.element('div').classes('cui-d6c-api-row'):
        ui.label(api).classes('cui-d6c-api cui-tabular')
        button = Button('Copy semantic API', intent=ButtonIntent.SECONDARY)
        button.element.props('aria-label="Copy semantic API"')
        button.element.on('click', lambda _event=None: ui.run_javascript(
            f'navigator.clipboard && navigator.clipboard.writeText({api!r})'
        ))


def _live_specimen(key: str) -> None:
    """Show the token in use beside its contract, using only semantic classes."""
    from nicegui import ui

    api = {
        'spacing': 'classes("cui-stack cui-gap-content")',
        'semantic-gaps': 'page_section(..., gap="section")',
        'radii': 'classes("cui-surface-token")',
        'typography': 'classes("cui-type-body")',
        'borders': 'classes("cui-border-subtle")',
        'elevation': 'classes("cui-elevation-raised")',
        'density': 'density="compact"',
        'breakpoints': 'responsive="desktop | tablet | phone"',
        'motion': 'motion="normal"  # honors reduced motion',
        'z-index': 'OverlayLayer.order("popover")',
        'interactive-states': 'state="selected"  # semantic state token',
    }.get(key, 'nicegui_base.design.build_design_system()')
    with ui.element('div').classes('cui-d6c-live-specimen').props(f'data-token-specimen="{key}"'):
        ui.label('Live use').classes('cui-d6c-live-specimen__title')
        if key == 'spacing':
            with ui.element('div').classes('cui-d6c-spacing-demo cui-stack cui-gap-content'):
                for label in ('Page section', 'Content group', 'Control cluster'):
                    with ui.element('div').classes('cui-d6c-spacing-block'):
                        ui.label(label)
        elif key == 'semantic-gaps':
            with ui.element('div').classes('cui-d6c-gap-demo'):
                for label in ('Page', 'Section', 'Content', 'Control'):
                    with ui.element('div').classes('cui-d6c-gap-node'):
                        ui.label(label)
        elif key == 'radii':
            with ui.element('div').classes('cui-d6c-radius-demo'):
                for label, css_class in (('Control', 'cui-radius-control'), ('Surface', 'cui-radius-surface'), ('Overlay', 'cui-radius-overlay'), ('Pill', 'cui-radius-pill')):
                    with ui.element('div').classes(f'cui-d6c-radius-sample {css_class}'):
                        ui.label(label)
        elif key == 'typography':
            with ui.element('div').classes('cui-d6c-type-demo'):
                ui.label('Reference heading').classes('cui-d6c-type-display')
                ui.label('Section title and supporting copy').classes('cui-d6c-type-heading')
                ui.label('Body text uses a readable hierarchy with stable line length.').classes('cui-d6c-type-body')
                ui.label('Metadata · 08:42 · Ready').classes('cui-d6c-type-meta')
        elif key == 'borders':
            with ui.element('div').classes('cui-d6c-border-demo'):
                ui.label('Subtle structural boundary').classes('cui-d6c-border-subtle')
                ui.label('Strong deliberate emphasis').classes('cui-d6c-border-strong')
        elif key == 'elevation':
            with ui.element('div').classes('cui-d6c-elevation-demo'):
                ui.label('Flat surface').classes('cui-d6c-elevation-flat')
                ui.label('Raised surface').classes('cui-d6c-elevation-raised')
                ui.label('Overlay surface').classes('cui-d6c-elevation-overlay')
        elif key == 'density':
            with ui.element('div').classes('cui-d6c-density-demo'):
                for label in ('Comfortable', 'Compact', 'Dense'):
                    with ui.element('div').classes('cui-d6c-density-row'):
                        ui.label(label)
                        ui.label('Row · 44 / 38 / 34 px').classes('cui-tabular')
        elif key == 'breakpoints':
            with ui.element('div').classes('cui-d6c-responsive-canvas'):
                for label, css_class in (('Desktop', 'cui-d6c-canvas--desktop'), ('Tablet', 'cui-d6c-canvas--tablet'), ('Phone', 'cui-d6c-canvas--phone')):
                    with ui.element('div').classes(f'cui-d6c-mini-canvas {css_class}'):
                        ui.label(label).classes('cui-d6c-mini-canvas__label')
                        with ui.element('div').classes('cui-d6c-mini-canvas__content'):
                            ui.label('Main').classes('cui-d6c-mini-slot')
                            ui.label('Aside').classes('cui-d6c-mini-slot')
        elif key == 'motion':
            with ui.element('div').classes('cui-d6c-motion-demo'):
                ui.label('Hover or focus this surface').classes('cui-d6c-motion-sample')
                ui.label('Reduced motion removes movement, not feedback.').classes('cui-workbench-note')
        elif key == 'z-index':
            with ui.element('div').classes('cui-d6c-z-demo'):
                for label, css_class in (('Page', 'cui-d6c-z-page'), ('Popover', 'cui-d6c-z-popover'), ('Modal', 'cui-d6c-z-modal'), ('Toast', 'cui-d6c-z-toast')):
                    ui.label(label).classes(f'cui-d6c-z-layer {css_class}')
        elif key == 'interactive-states':
            with ui.element('div').classes('cui-d6c-state-demo'):
                ui.label('Default').classes('cui-d6c-state-sample')
                ui.label('Hover').classes('cui-d6c-state-sample is-hover')
                ui.label('Selected').classes('cui-d6c-state-sample is-selected')
                ui.label('Disabled').classes('cui-d6c-state-sample is-disabled')
        else:
            ui.label('The active theme maps the semantic role consistently across consumers.').classes('cui-workbench-note')
        _copy_api(api)
        with ui.element('div').classes('cui-d6c-guidance-row'):
            ui.label('Recommended use').classes('cui-d6c-guidance-label')
            ui.label(_FAMILY_GUIDANCE.get(key.replace('-', '_'), 'Use the semantic authority.')).classes('cui-workbench-note')
            ui.label("Don't: invent a local value when a token exists.").classes('cui-d6c-dont')


def _family(title: str, key: str, values: Mapping[str, Any], guidance: str) -> None:
    from nicegui import ui

    with ui.element('section').classes('cui-d6c-token-family cui-surface-token').props(
        f'data-design-token-family="{key}"'
    ):
        with ui.element('div').classes('cui-d6c-token-family__head'):
            ui.label(title).classes('cui-workbench-section-title')
            ui.label(guidance).classes('cui-workbench-note')
        with ui.element('div').classes('cui-d6c-token-family__body'):
            with ui.element('div').classes('cui-d6c-token-contract'):
                with ui.element('div').classes('cui-d6c-token-list'):
                    for name, value in values.items():
                        with ui.element('div').classes('cui-d6c-token-row'):
                            ui.label(name.replace('_', ' ')).classes('cui-d6c-token-name')
                            ui.label(_text(value)).classes('cui-d6c-token-value cui-tabular')
            _live_specimen(key)


def _palette() -> None:
    from nicegui import ui

    system = build_design_system()
    roles = tuple(field.name for field in fields(ThemePalette))
    with ui.element('section').classes('cui-d6c-token-family cui-surface-token').props(
        'data-design-token-family="surfaces-colors"'
    ):
        with ui.element('div').classes('cui-d6c-token-family__head'):
            ui.label('Surfaces & colors').classes('cui-workbench-section-title')
            ui.label(_FAMILY_GUIDANCE['surfaces_colors']).classes('cui-workbench-note')
        with ui.element('div').classes('cui-d6c-theme-grid'):
            for mode, palette in (('light', system.light), ('dark', system.dark)):
                with ui.element('article').classes('cui-d6c-theme-card').props(f'data-theme-preview="{mode}"'):
                    ui.label(f'{mode.title()} mapping').classes('cui-d6c-token-name')
                    for role in roles:
                        value = getattr(palette, role)
                        with ui.element('div').classes('cui-d6c-color-row'):
                            # This is a token-driven specimen swatch, not an app CSS escape hatch.
                            ui.element('span').classes('cui-d6c-swatch').style(f'background-color:{value}')
                            ui.label(f'{role.replace("_", " ")} · {value}').classes('cui-d6c-token-value')
        with ui.element('div').classes('cui-d6c-palette-specimen'):
            ui.label('Live semantic surface pairing').classes('cui-d6c-live-specimen__title')
            with ui.element('div').classes('cui-d6c-palette-cards'):
                for label, css_class, copy in (
                    ('Page', 'cui-d6c-palette-page', 'Canvas and reading area'),
                    ('Surface', 'cui-d6c-palette-surface', 'Card and section surface'),
                    ('Status', 'cui-d6c-palette-status', 'State communicates meaning'),
                ):
                    with ui.element('article').classes(f'cui-d6c-palette-card {css_class}'):
                        ui.label(label).classes('cui-d6c-token-name')
                        ui.label(copy).classes('cui-workbench-note')
            _copy_api('classes("cui-surface-token cui-border-subtle")')


def _responsive() -> None:
    from nicegui import ui

    with ui.element('section').classes('cui-d6c-token-family cui-surface-token').props(
        'data-design-token-family="responsive-preview"'
    ):
        ui.label('Responsive reference').classes('cui-workbench-section-title')
        ui.label('The same semantic surface is checked at the governed desktop, tablet, and phone profiles.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-d6c-viewport-grid'):
            for key in ('desktop-wide', 'tablet-wide', 'phone-compact'):
                viewport = CANONICAL_VIEWPORTS[key]
                with ui.element('article').classes('cui-d6c-viewport-card').props(
                    f'data-design-viewport="{viewport.tier}" data-viewport-width="{viewport.width}"'
                ):
                    ui.label(viewport.tier.title()).classes('cui-d6c-viewport-card__title')
                    ui.label(f'{viewport.width} × {viewport.height}').classes('cui-d6c-token-value cui-tabular')
                    with ui.element('div').classes(f'cui-d6c-mini-canvas cui-d6c-canvas--{key.split("-")[0]}'):
                        ui.label('Main').classes('cui-d6c-mini-slot')
                        ui.label('Inspector').classes('cui-d6c-mini-slot')
                    ui.label('Full-width canvas; inner content reflows through framework slots.').classes('cui-workbench-note')


def _density_and_states() -> None:
    from nicegui import ui

    system = build_design_system()
    with ui.element('section').classes('cui-d6c-token-family cui-surface-token').props(
        'data-design-token-family="density-states"'
    ):
        ui.label('Density & component states').classes('cui-workbench-section-title')
        ui.label('Density changes rhythm and table ergonomics; state styling remains accessible and semantic.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-d6c-density-grid'):
            for name, values in system.densities.items():
                with ui.element('article').classes('cui-d6c-density-card').props(f'data-density="{name}"'):
                    ui.label(name.title()).classes('cui-d6c-token-name')
                    ui.label(f'control {values["control_height"]}px · row {values["table_row_height"]}px').classes('cui-d6c-token-value cui-tabular')
                    with ui.element('div').classes('cui-layout-cluster'):
                        Button('Secondary', intent=ButtonIntent.SECONDARY)
                        ActionButton('Primary')
        with ui.element('div').classes('cui-d6c-state-row').props('aria-label="Component state examples"'):
            StatusBadge('Ready', intent=StatusIntent.SUCCESS)
            StatusBadge('Review', intent=StatusIntent.WARNING)
            StatusBadge('Blocked', intent=StatusIntent.DANGER)
            StatusBadge('Info', intent=StatusIntent.INFO)
            Button('Disabled', disabled=True)
        ui.label('Recommended: use semantic status and interaction states so meaning survives light/dark and touch input.').classes('cui-workbench-note')


def render_design_system_reference() -> None:
    """Render the complete token contract and live component examples."""
    from nicegui import ui

    system = build_design_system()
    with ui.element('section').classes('cui-d6c-reference-hero cui-surface-token').props('data-design-reference'):
        ui.label('Design System Authority').classes('cui-workbench-section-title')
        ui.label('See the token in use first; the compact contract beside each specimen is the source for Python consumers, components, CSS, and generated applications.').classes('cui-workbench-note')
        ui.label('Import from nicegui_base.design; choose semantic roles before extending the framework.').classes('cui-workbench-chip')

    with ui.element('div').classes('cui-d6c-reference-grid'):
        _family('Spacing scale', 'spacing', system.spacing, _FAMILY_GUIDANCE['spacing'])
        _family('Semantic gaps', 'semantic-gaps', system.semantic_gaps, _FAMILY_GUIDANCE['semantic_gaps'])
        _family('Radius', 'radii', system.radii, _FAMILY_GUIDANCE['radii'])
        _family('Typography hierarchy', 'typography', system.typography, _FAMILY_GUIDANCE['typography'])
        _palette()
        _family('Borders', 'borders', system.border_widths, _FAMILY_GUIDANCE['borders'])
        _family('Elevation', 'elevation', system.elevation, _FAMILY_GUIDANCE['elevation'])
        _family('Density', 'density', system.densities, _FAMILY_GUIDANCE['density'])
        _family('Breakpoints', 'breakpoints', system.breakpoints, _FAMILY_GUIDANCE['breakpoints'])
        _family('Motion', 'motion', system.motion, _FAMILY_GUIDANCE['motion'])
        _family('Z-index', 'z-index', system.z_index, _FAMILY_GUIDANCE['z_index'])
        _family('Interactive states', 'interactive-states', system.interactive_states, _FAMILY_GUIDANCE['interactive_states'])

    _responsive()
    _density_and_states()


__all__ = ['render_design_system_reference']
