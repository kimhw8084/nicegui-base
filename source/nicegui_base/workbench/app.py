from __future__ import annotations

import json
import os
import secrets
from .update_identity import BUILD_ID
import math
from typing import Any, Callable

from .catalog import CATALOG_INTENT_FILTERS, EXPECTED_FRAMEWORK_CATALOG_RECORDS, REQUIRED_CATALOG_FAMILIES, all_entries, analytics_entries, catalog_contract_audit, catalog_family, catalog_family_coverage, catalog_filter_options, coverage, framework_catalog_audit, recipe_entries, search
from .models import WorkbenchEntry, WorkbenchKind
from .workbench_css import install_workbench_css
from .identity import ExplorerIdentity, resolve_explorer_identity

WORKBENCH_TITLE = 'NiceGUI Base Reference Explorer'
WORKBENCH_SUBTITLE = 'Reference Explorer for the department standard: find the right authority, understand it, and open a governed live example.'


def _imports():
    from nicegui import ui
    from nicegui_base.integrations.nicegui_layout import AppShell, PageHeader
    from nicegui_base.navigation import NavigationModel, NavItem, NavSection
    from nicegui_base.visual import Icons
    return ui, AppShell, PageHeader, NavigationModel, NavItem, NavSection, Icons


def _standard_button(label: str, *, on_click=None, primary: bool = False, disabled: bool = False, classes: str = ''):
    from nicegui_base.integrations.nicegui_components import ActionButton, Button
    control = (ActionButton if primary else Button)(label, disabled=disabled, on_click=on_click)
    if classes:
        control.element.classes(add=classes)
    return control.element


def _standard_search(label: str, *, placeholder: str, on_change=None, autofocus: bool = False):
    from nicegui_base.integrations.nicegui_components import SearchInput
    control = SearchInput(label, placeholder=placeholder, debounce_ms=120, on_change=on_change)
    control.element.classes(add='cui-workbench-search w-full')
    if autofocus:
        control.element.props('autofocus')
    return control.element


def _standard_select(label: str, options: dict[str, str], *, value: str, on_change=None):
    from nicegui_base.integrations.nicegui_components import Select
    control = Select(label, options, value=value, clearable=False, on_change=on_change)
    return control.element



def _display_control_bar(*, inline: bool = False) -> Any:
    """Workbench-owned theme/density/motion controls using governed primitives.

    Preference keys intentionally match the legacy reference lab so engineers can move
    between Workbench and deep reference routes without surprising visual resets. The
    Workbench no longer imports the certification lab's private ``_control_bar``.
    """
    from nicegui import app, ui
    from nicegui_base.integrations.nicegui_data_table import apply_all_table_density
    from nicegui_base.integrations.nicegui_layout import SegmentedControl
    from nicegui_base.integrations.nicegui_visualization import apply_all_chart_themes

    theme = str(app.storage.user.get('cui_lab_theme', 'system'))
    density = str(app.storage.user.get('cui_lab_density', 'compact'))
    motion = str(app.storage.user.get('cui_lab_motion', 'normal'))
    if theme not in {'system', 'light', 'dark'}:
        theme = 'system'
    if density not in {'comfortable', 'compact', 'dense'}:
        density = 'compact'
    if motion not in {'normal', 'reduced'}:
        motion = 'normal'

    dark = ui.dark_mode()

    def sync_theme(value: str) -> None:
        dark_value = {'light': False, 'dark': True, 'system': None}[value]
        if hasattr(dark, 'set_value'):
            dark.set_value(dark_value)
        elif dark_value is True:
            dark.enable()
        elif dark_value is False:
            dark.disable()
        else:
            dark.auto()
        ui.run_javascript(f"""(() => {{
          const root=document.documentElement;
          const requested={value!r};
          const media=window.matchMedia?.('(prefers-color-scheme: dark)');
          const apply=()=>{{
            const resolved=requested==='system' ? (media?.matches ? 'dark' : 'light') : requested;
            root.dataset.theme=resolved;
            document.body?.classList.toggle('q-dark', resolved==='dark');
            document.body?.classList.toggle('body--dark', resolved==='dark');
          }};
          apply();
          if(requested==='system' && media && !root.__niceguiBaseThemeListener){{
            root.__niceguiBaseThemeListener=()=>apply();
            media.addEventListener?.('change',root.__niceguiBaseThemeListener);
          }}
          try{{localStorage.setItem('nicegui_base_theme',requested);localStorage.setItem('cui_lab_theme',requested);}}catch(_){{}}
        }})()""")
        if value in {'light', 'dark'}:
            apply_all_chart_themes(value)

    # WAVE35_THEME_RECONCILIATION_V8
    # Explicit server light/dark is authoritative. If server storage is still
    # neutral 'system', preserve the browser-restored appearance until the
    # connected client can reconcile that display-only preference.
    sync_theme(theme)
    ui.run_javascript(
        f"document.documentElement.dataset.density={density!r}; "
        f"document.documentElement.dataset.motion={motion!r}; "
        f"document.documentElement.classList.toggle('cui-force-reduced-motion',{str(motion == 'reduced').lower()});"
    )

    def theme_changed(e) -> None:
        value = str(getattr(e, 'value', 'system'))
        if value not in {'system', 'light', 'dark'}:
            return
        app.storage.user['cui_lab_theme'] = value
        sync_theme(value)

    async def density_changed(e) -> None:
        value = str(getattr(e, 'value', 'compact'))
        if value not in {'comfortable', 'compact', 'dense'}:
            return
        app.storage.user['cui_lab_density'] = value
        ui.run_javascript(f"document.documentElement.dataset.density={value!r};try{{localStorage.setItem(\'nicegui_base_density\',{value!r});localStorage.setItem(\'cui_lab_density\',{value!r});}}catch(_){{}}")
        await apply_all_table_density(value)

    def motion_changed(e) -> None:
        value = str(getattr(e, 'value', 'normal'))
        if value not in {'normal', 'reduced'}:
            return
        app.storage.user['cui_lab_motion'] = value
        ui.run_javascript(
            f"document.documentElement.dataset.motion={value!r}; "
            f"document.documentElement.classList.toggle('cui-force-reduced-motion',{str(value == 'reduced').lower()});"
            f"try{{localStorage.setItem('nicegui_base_motion',{value!r});localStorage.setItem('cui_lab_motion',{value!r});}}catch(_){{}}"
        )

    def render_controls() -> None:
        with ui.element('div').classes('cui-workbench-display-controls').props(
            'role="group" aria-label="Reference Explorer display preferences"'
        ):
            ui.label('Theme').classes('cui-workbench-display-controls__label')
            SegmentedControl({'system': 'System', 'light': 'Light', 'dark': 'Dark'}, value=theme, on_change=theme_changed)
            ui.label('Density').classes('cui-workbench-display-controls__label')
            SegmentedControl({'comfortable': 'Comfort', 'compact': 'Compact', 'dense': 'Dense'}, value=density, on_change=density_changed)
            ui.label('Motion').classes('cui-workbench-display-controls__label')
            SegmentedControl({'normal': 'Normal', 'reduced': 'Reduced'}, value=motion, on_change=motion_changed)

    if inline:
        render_controls()
        return None
    from nicegui_base.integrations.nicegui_components import Button
    theme_state = {'value': theme}
    quick_theme = Button(
        f'Theme · {theme.title()}',
        icon='appearance',
        on_click=lambda _event=None: toggle_quick_theme(),
    )
    quick_theme.element.classes(add='cui-workbench-theme-quick')
    quick_theme.element.props(f'aria-label="Appearance theme: {theme.title()}" title="Appearance theme: {theme.title()}"')

    def toggle_quick_theme() -> None:
        next_value = {'light': 'dark', 'dark': 'light', 'system': 'dark'}[theme_state['value']]
        theme_state['value'] = next_value
        app.storage.user['cui_lab_theme'] = next_value
        sync_theme(next_value)
        if quick_theme.label_element is not None:
            quick_theme.label_element.set_text(f'Theme · {next_value.title()}')
        quick_theme.element.props(f'aria-label="Appearance theme: {next_value.title()}" title="Appearance theme: {next_value.title()}"')

    trigger = _standard_button('Appearance', classes='cui-workbench-preferences-trigger')
    trigger.props('aria-label="Open appearance preferences"')
    with trigger:
        with ui.menu().props('anchor="bottom left" self="top left"'):
            render_controls()

    # WAVE35_DISPLAY_PREFERENCES_REACHABILITY_V13
    # Keep browser/server display-preference reconciliation reachable.
    return trigger


def workbench_navigation():
    _, _, _, NavigationModel, NavItem, NavSection, Icons = _imports()
    return NavigationModel((
        NavSection('discover', 'DISCOVER', (
            NavItem('reference_start', 'Start Here', '/', Icons.HOME),
        )),
        NavSection('foundations', 'FOUNDATIONS', (
            NavItem('reference_design', 'Design System', '/design', Icons.GRID),
            NavItem('reference_components', 'Components', '/components', Icons.GRID),
            NavItem('reference_data', 'Data & Tables', '/workbench/data', Icons.TABLE),
            NavItem('reference_visualizations', 'Visualizations', '/analytics', Icons.GRID),
        )),
        NavSection('compose', 'COMPOSE', (
            NavItem('reference_patterns', 'Application Patterns', '/patterns', Icons.GRID),
        )),
        NavSection('semiconductor', 'SEMICONDUCTOR', (
            NavItem('reference_recipes', 'Semiconductor Recipes', '/recipes', Icons.FILE),
        )),
        NavSection('develop', 'DEVELOP', (
            NavItem('reference_ai', 'AI Development Guide', '/ai-guide', Icons.FILE),
        )),
        NavSection('system', 'SYSTEM', (
            NavItem('reference_settings', 'Settings', '/settings', Icons.SETTINGS),
        )),
    ))


def reference_entries_for_section(section: str) -> tuple[WorkbenchEntry, ...]:
    """Return only the canonical authority owned by a primary Explorer section."""
    kind_by_section = {
        'components': WorkbenchKind.COMPONENT,
        'patterns': WorkbenchKind.PATTERN,
        'visualizations': WorkbenchKind.ANALYTIC,
        'recipes': WorkbenchKind.RECIPE,
    }
    try:
        kind = kind_by_section[str(section).strip().casefold()]
    except KeyError as exc:
        raise ValueError(f'unknown Reference Explorer section: {section!r}') from exc
    return tuple(entry for entry in all_entries() if entry.kind is kind)


def _command_keywords(entry: WorkbenchEntry) -> tuple[str, ...]:
    """Use the same semantic evidence in ⌘K that the inline Workbench search exposes."""
    values = (
        entry.key, entry.category, entry.description, entry.source_authority, entry.maturity,
        *entry.aliases, *entry.tags, *entry.use_when, *entry.avoid_when, *entry.related_keys,
    )
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _install_command_palette(ui):
    """Install the framework-owned global command palette for this Workbench page."""
    from nicegui_base.integrations.nicegui_content import CommandPalette
    from nicegui_base.services import Command, CommandRegistry

    registry = CommandRegistry(recent_limit=8)
    top_level = (
        ('reference:start','Start Here','/','Reference Explorer','start here framework standard'),
        ('reference:design','Design System','/design','Reference Explorer','design tokens theme assets'),
        ('reference:components','Components','/components','Reference Explorer','components controls content'),
        ('reference:data','Data & Tables','/workbench/data','Reference Explorer','data tables schema playground'),
        ('reference:visualizations','Visualizations','/analytics','Reference Explorer','charts analytics semiconductor'),
        ('reference:patterns','Application Patterns','/patterns','Reference Explorer','patterns application composition'),
        ('reference:recipes','Semiconductor Recipes','/recipes','Reference Explorer','recipes semiconductor'),
        ('reference:ai','AI Development Guide','/ai-guide','Reference Explorer','agents scaffolding developer guidance'),
        ('reference:settings','Settings','/settings','Reference Explorer','appearance account explorer preferences'),
    )
    for key, label, route, group, words in top_level:
        registry.register(Command(key, label, lambda route=route: ui.navigate.to(route), keywords=tuple(words.split()), group=group))
    for entry in all_entries():
        registry.register(Command(
            f'entry:{entry.key}', entry.title, lambda route=entry.route: ui.navigate.to(route),
            keywords=_command_keywords(entry),
            group=entry.kind.value.title(), description=entry.description,
        ))
    palette = CommandPalette(registry, placeholder='Search NiceGUI Base…', limit=24)
    trigger = _standard_button('Search', on_click=palette.open, classes='cui-workbench-command-trigger')
    trigger.props('aria-label="Open global search"')
    with trigger:
        ui.label('⌘K / Ctrl+K').classes('cui-workbench-command-shortcut')
    trigger_id = int(trigger.id)
    ui.run_javascript(f"""(() => {{
      window.__niceguiBaseWorkbenchCommandTarget={trigger_id};
      const params=new URLSearchParams(window.location.search);
      if(params.get('palette')==='1'){{
        params.delete('palette');
        const remaining=params.toString();
        history.replaceState(null,'',window.location.pathname+(remaining?'?'+remaining:'')+window.location.hash);
        requestAnimationFrame(()=>getHtmlElement(window.__niceguiBaseWorkbenchCommandTarget)?.click());
      }}
    }})()""")
    return palette


def _shell(route: str, title: str, description: str):
    ui, AppShell, PageHeader, *_ = _imports()
    identity = resolve_explorer_identity()
    shell = AppShell(
        'NiceGUI Base', workbench_navigation(), active_route=route,
        environment='REFERENCE', subtitle='Department standard · Reference Explorer',
        greeting=identity.role, user_name=identity.access_key, user_initials=identity.initials,
        user_role=identity.role, department=identity.department,
        on_settings=lambda: ui.navigate.to('/settings'), on_about=None,
        owner='NiceGUI Base', on_support=lambda: ui.navigate.to('/catalog'),
        on_feedback=lambda: ui.navigate.to('/quality'), on_docs=lambda: ui.navigate.to('/catalog'),
        debugger=True,
    )
    shell.__enter__()
    # AppShell already owns the document's single main landmark. Keep the Workbench
    # page as content inside that landmark rather than nesting a second <main>.
    page = ui.element('div').classes('cui-page cui-page--wide cui-workbench-page')
    page.__enter__()
    PageHeader(title, description)
    with ui.element('div').classes('cui-workbench-toolbar cui-workbench-global-tools').props(
        'role="toolbar" aria-label="Reference Explorer global tools"'
    ):
        _install_command_palette(ui)
        _display_control_bar()
    shell._workbench_page = page
    return shell


def _end_shell(shell) -> None:
    page = getattr(shell, '_workbench_page', None)
    if page is not None:
        ui, *_ = _imports()
        with ui.element('footer').classes('cui-workbench-build-footer').props(f'data-build-id="{BUILD_ID}"'):
            ui.label(f'Build {BUILD_ID}').classes('cui-workbench-note')
        page.__exit__(None, None, None)
    shell.__exit__(None, None, None)


def _interactive_card(title: str, route: str):
    """Create one keyboard-equivalent card surface using native Workbench markup."""
    ui, *_ = _imports()

    def navigate(_e=None) -> None:
        ui.navigate.to(route)

    return (
        ui.element('article')
        .classes('cui-workbench-card')
        .props(f'role="link" tabindex="0" aria-label={json.dumps(title)}')
        .on('click', navigate)
        .on('keydown.enter', navigate)
        .on('keydown.space', navigate)
    )


def _card(entry: WorkbenchEntry) -> None:
    ui, *_ = _imports()
    with _interactive_card(entry.title, entry.route):
        with ui.element('div').classes('cui-workbench-card__meta'):
            ui.label(entry.kind.value)
            if entry.category:
                ui.label('•')
                ui.label(entry.category)
        ui.label(entry.title).classes('cui-workbench-card__title')
        ui.label(entry.description).classes('cui-workbench-card__body')
        badges = []
        if entry.live_preview:
            badges.append('Live preview')
        if entry.sample_data:
            badges.append('Sample data')
        tags = tuple(dict.fromkeys((*badges, *entry.tags)))[:4]
        if tags:
            with ui.element('div').classes('cui-workbench-chiprow'):
                for tag in tags:
                    ui.label(tag).classes('cui-workbench-chip')


def _action_card(title: str, description: str, route: str, meta: str) -> None:
    ui, *_ = _imports()
    with _interactive_card(title, route):
        ui.label(meta).classes('cui-workbench-card__meta')
        ui.label(title).classes('cui-workbench-card__title')
        ui.label(description).classes('cui-workbench-card__body')


def _section(title: str, copy: str | None = None):
    from contextlib import contextmanager
    ui, *_ = _imports()

    @contextmanager
    def section_context():
        with ui.element('section').classes('cui-workbench-section'):
            with ui.element('div').classes('cui-workbench-section-head'):
                with ui.element('div'):
                    ui.label(title).classes('cui-workbench-section-title')
                    if copy:
                        ui.label(copy).classes('cui-workbench-section-copy')
            yield

    return section_context()


def _search_box(*, autofocus: bool = False) -> None:
    ui, *_ = _imports()
    result_host = None

    def render_results(value: str) -> None:
        if result_host is None:
            return
        result_host.clear()
        query = (value or '').strip()
        if not query:
            return
        matches = search(query, limit=24)
        with result_host:
            if not matches:
                ui.label('No matching standard found. Try a task, component, chart, recipe, or engineering term.').classes('cui-workbench-note')
                return
            grouped: dict[WorkbenchKind, list[WorkbenchEntry]] = {}
            for result in matches:
                grouped.setdefault(result.entry.kind, []).append(result.entry)
            for kind in WorkbenchKind:
                entries = grouped.get(kind, ())
                if not entries:
                    continue
                with ui.element('section').classes('cui-workbench-search-group').props(f'aria-label={json.dumps(kind.value.title())}'):
                    ui.label(f'{kind.value.title()} · {len(entries)}').classes('cui-workbench-search-group__title')
                    with ui.element('div').classes('cui-workbench-grid cui-workbench-grid--3'):
                        for entry in entries:
                            _card(entry)

    field = _standard_search(
        'Search NiceGUI Base',
        placeholder='Components, patterns, SPC, FDC, Hotelling T², RCA, recipes…',
        on_change=lambda e: render_results(str(e.value or '')), autofocus=autofocus,
    )
    field.props('data-workbench-search')
    result_host = ui.element('div').classes('cui-workbench-list')


def home_page() -> None:
    stats = coverage()
    shell = _shell('/', 'Start Here', 'Start from the engineering intent, visually compare the governed authorities, then open only the reference you need.')
    from .explorer_gallery import render_start_here
    render_start_here(stats)
    _end_shell(shell)


def build_page() -> None:
    shell = _shell('/build', 'Developer Scaffolding', 'This saved-link route now points developers to deterministic pattern and recipe starters.')
    ui, *_ = _imports()
    ui.label('Compatibility authoring surface').classes('cui-workbench-chip')
    ui.label('Manual composition is retired from the normal reference journey. Start from a canonical pattern or recipe with the installed CLI; domain logic stays in your application services.').classes('cui-workbench-note')
    with ui.element('div').classes('cui-workbench-grid cui-workbench-grid--3'):
        _action_card('Choose a pattern', 'Use a registered page hierarchy and responsive slot contract.', '/patterns', 'CLI · create-pattern')
        _action_card('Choose a recipe', 'Use a bounded semiconductor workflow and its data contract.', '/recipes', 'CLI · create-recipe')
        _action_card('Read the agent path', 'Resolve a requirement into an authority before coding.', '/ai-guide', 'AGENT WORKFLOW')
    _end_shell(shell)


def _legacy_builder_surface() -> None:
    """Keep the compatibility implementation importable without exposing it in D6H UX."""
    from .builder import render_builder
    render_builder()


def layout_studio_page() -> None:
    _unified_patterns_compatibility_page()


def catalog_page(*, active_route: str = '/catalog', initial_kind: str = 'all', page_title: str = 'Design System', page_description: str = 'One discoverable inventory over canonical NiceGUI Base registries, grouped by the job each capability solves.') -> None:
    ui, *_ = _imports()
    entries = all_entries()
    filter_options = catalog_filter_options(entries)
    shell = _shell(active_route, page_title, page_description)
    host = None

    def render(kind: str = 'all', family: str = 'all', query: str = '', intent: str = 'all', data_shape: str = 'all', domain: str = 'all', related_to: str = 'all') -> None:
        if host is None:
            return
        host.clear()
        if query.strip() or any(value != 'all' for value in (intent, data_shape, domain, related_to)):
            visible = tuple(result.entry for result in search(
                query, limit=300,
                intent=None if intent == 'all' else intent,
                data_shape=None if data_shape == 'all' else data_shape,
                domain=None if domain == 'all' else domain,
                related_to=None if related_to == 'all' else related_to,
            ))
        else:
            visible = entries
        if kind != 'all':
            visible = tuple(entry for entry in visible if entry.kind.value == kind)
        if family != 'all':
            visible = tuple(entry for entry in visible if catalog_family(entry) == family)
        with host:
            if not visible:
                ui.label('No catalog entries match these filters.').classes('cui-workbench-note')
                return
            if not query.strip() and kind == 'all' and family == 'all':
                if all(value == 'all' for value in (intent, data_shape, domain, related_to)):
                    ui.label(f'{len(entries)} canonical Reference Explorer entries are searchable. Choose a family or search to inspect individual capabilities.').classes('cui-workbench-note')
                    with ui.element('div').classes('cui-workbench-quality-grid'):
                        overview_families = tuple(REQUIRED_CATALOG_FAMILIES) + ('other canonical capabilities',)
                        for family_name in overview_families:
                            group = tuple(entry for entry in entries if (catalog_family(entry) or 'other canonical capabilities') == family_name)
                            if not group:
                                continue
                            with ui.element('article').classes('cui-workbench-quality-card'):
                                ui.label(family_name.title()).classes('cui-workbench-card__title')
                                ui.label(f'{len(group)} canonical entr{"y" if len(group) == 1 else "ies"}').classes('cui-workbench-chip')
                                examples = ', '.join(entry.title for entry in group[:3])
                                if examples:
                                    ui.label(f'Examples: {examples}').classes('cui-workbench-note')
                                if family_name in REQUIRED_CATALOG_FAMILIES:
                                    _standard_button('Browse family', on_click=lambda _e=None, name=family_name: choose_family(name))
                    return
            ordered_families = tuple(REQUIRED_CATALOG_FAMILIES) + ('other canonical capabilities',)
            for family_name in ordered_families:
                group = tuple(
                    entry for entry in visible
                    if (catalog_family(entry) or 'other canonical capabilities') == family_name
                )
                if not group:
                    continue
                with _section(family_name.title(), f'{len(group)} discoverable canonical entr{"y" if len(group) == 1 else "ies"}'):
                    with ui.element('div').classes('cui-workbench-grid'):
                        for entry in group:
                            _card(entry)

    state = {'kind': initial_kind, 'family': 'all', 'query': '', 'intent': 'all', 'data_shape': 'all', 'domain': 'all', 'related_to': 'all'}
    family_control = None

    def choose_family(name: str) -> None:
        state['family'] = name
        if family_control is not None and hasattr(family_control, 'set_value'):
            family_control.set_value(name)
        render(**state)

    def query_changed(e) -> None:
        state['query'] = str(e.value or '')
        render(**state)
    def kind_changed(e) -> None:
        state['kind'] = str(e.value or 'all')
        render(**state)
    def family_changed(e) -> None:
        state['family'] = str(e.value or 'all')
        render(**state)
    def contract_filter_changed(key: str, event) -> None:
        state[key] = str(getattr(event, 'value', 'all') or 'all')
        render(**state)

    with ui.element('div').classes('cui-workbench-toolbar'):
        _standard_search('Search catalog', placeholder='Name, tag, intent, data shape, domain, related capability…', on_change=query_changed)
        with ui.element('details').classes('cui-catalog-refine'):
            with ui.element('summary').classes('cui-catalog-refine__summary').props('tabindex="0"'):
                ui.label('Refine results · type, family, intent, data, domain, relation')
            with ui.element('div').classes('cui-catalog-refine__controls'):
                _standard_select('Type', {'all':'All','component':'Components','pattern':'Patterns','analytic':'Analytics','recipe':'Recipes','reference':'Framework'}, value='all', on_change=kind_changed)
                family_options = {'all': 'All families', **{family: family.title() for family in REQUIRED_CATALOG_FAMILIES}}
                family_control = _standard_select('Family', family_options, value='all', on_change=family_changed)
                _standard_select('Intent / problem', {'all': 'All intents', **dict(CATALOG_INTENT_FILTERS)}, value='all', on_change=lambda event: contract_filter_changed('intent', event))
                _standard_select('Required data', {'all': 'Any data contract', 'rows': 'Rows / named fields', 'typed': 'Typed configuration', 'numeric': 'Finite numeric values'}, value='all', on_change=lambda event: contract_filter_changed('data_shape', event))
                domain_options = {'all': 'All domains', **{value: value.title() for value in filter_options['domains']}}
                _standard_select('Domain', domain_options, value='all', on_change=lambda event: contract_filter_changed('domain', event))
                related_options = {'all': 'Any relation'}
                lookup = {entry.key: entry.title for entry in entries}
                related_options.update({key: lookup[key] for key in filter_options['related'] if key in lookup})
                _standard_select('Related capability', related_options, value='all', on_change=lambda event: contract_filter_changed('related_to', event))
        _standard_button('Analytics Studio', on_click=lambda: ui.navigate.to('/analytics'))
    host = ui.element('div').classes('cui-workbench-catalog-results')
    render(**state)
    _end_shell(shell)


def design_system_page() -> None:
    from .design_system_reference import render_design_system_reference
    shell = _shell('/design', 'Design System', 'The deterministic visual contract used by the reference explorer, framework components, and generated applications.')
    render_design_system_reference()
    _end_shell(shell)


def settings_page() -> None:
    """The Explorer's real appearance/account surface.

    Settings intentionally uses the same AppShell and the same display
    preference callbacks as the compact header control.  It is not the
    registered Settings application pattern, which remains available as a
    reference specimen under the compatibility route.
    """
    from nicegui import ui
    from nicegui_base.version import FRAMEWORK_VERSION

    identity = resolve_explorer_identity()
    shell = _shell('/settings', 'Settings', 'Manage appearance and Explorer identity without leaving the department reference shell.')
    with ui.element('div').classes('cui-settings-page').props('data-settings-page'):
        with ui.element('div').classes('cui-settings-grid'):
            with ui.element('section').classes('cui-settings-card').props('aria-labelledby="settings-appearance-title"'):
                ui.label('Appearance').classes('cui-workbench-section-title').props('id="settings-appearance-title"')
                ui.label('These preferences apply to the Explorer and its mounted reference previews. System follows the operating-system color scheme.').classes('cui-workbench-note')
                _display_control_bar(inline=True)
            with ui.element('section').classes('cui-settings-card').props('aria-labelledby="settings-account-title"'):
                ui.label('Account').classes('cui-workbench-section-title').props('id="settings-account-title"')
                ui.label('Identity is read from the company environment and is display-only here.').classes('cui-workbench-note')
                for label, value in (
                    ('AccessKey', identity.access_key),
                    ('Role', identity.role),
                    ('Department', identity.department),
                ):
                    with ui.element('div').classes('cui-settings-row'):
                        with ui.element('div').classes('cui-settings-row__copy'):
                            ui.label(label).classes('cui-settings-row__label')
                            ui.label('Company identity value' if label == 'AccessKey' else 'Reference Explorer display value').classes('cui-settings-row__description')
                        ui.label(value).classes('cui-settings-row__value cui-tabular')
            with ui.element('section').classes('cui-settings-card').props('aria-labelledby="settings-about-title"'):
                ui.label('About this reference').classes('cui-workbench-section-title').props('id="settings-about-title"')
                ui.label('Use the canonical registries, patterns, tables, visualizations and recipes shown here in application code.').classes('cui-workbench-note')
                with ui.element('div').classes('cui-settings-facts'):
                    ui.label(f'NiceGUI Base {FRAMEWORK_VERSION}').classes('cui-settings-fact')
                    ui.label('NiceGUI 3.15.0').classes('cui-settings-fact')
                    ui.label('Reference Explorer').classes('cui-settings-fact')
            if identity.account_missing or identity.department_missing:
                with ui.element('details').classes('cui-settings-diagnostics'):
                    with ui.element('summary').props('tabindex="0"'):
                        ui.label('Development identity diagnostics').classes('cui-workbench-card__meta')
                    if identity.account_missing:
                        ui.label('AccessKey is not set; the neutral Member fallback is active.').classes('cui-workbench-note')
                    if identity.department_missing:
                        ui.label('DEPARTMENT is not set; the department fallback is active.').classes('cui-workbench-note')
    _end_shell(shell)


def _settings_compatibility_page() -> None:
    from nicegui import ui
    ui.navigate.to('/settings')


def _unified_patterns_compatibility_page() -> None:
    from nicegui import ui
    ui.navigate.to('/patterns')


def components_page() -> None:
    shell = _shell('/components', 'Components', 'Scan governed component specimens first; open a detail only for deeper states, configuration, accessibility, or code.')
    from .explorer_gallery import render_reference_gallery
    render_reference_gallery(
        reference_entries_for_section('components'), section='components',
        intro='Scan the decision aid first; open a live registered implementation when the capability fits.',
    )
    _end_shell(shell)


def patterns_page() -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, Select
    from nicegui_base.patterns.registry import PATTERN_REGISTRY
    from .pattern_specimens import PATTERN_SEMANTIC_ANATOMY, render_pattern
    from .full_applications import full_application_entries
    from .explorer_gallery import _preview_image
    from .preview_catalog import application_asset_key

    shell = _shell('/patterns', 'Application Patterns', 'Choose a finished application structure, see the real governed composition, then adapt business logic in your own services.')
    pattern_keys = tuple(pattern.value for pattern in PATTERN_REGISTRY)
    titles = {key: key.replace('_', ' ').title() for key in pattern_keys}
    selected = {'key': 'dashboard'}
    host = ui.element('div').classes('cui-unified-pattern-preview-host')

    def show_pattern(key: str) -> None:
        if key not in pattern_keys:
            return
        selected['key'] = key
        host.clear()
        with host:
            with ui.element('div').classes('cui-unified-pattern-context'):
                ui.label('Live governed composition').classes('cui-workbench-card__meta')
                ui.label(titles[key]).classes('cui-workbench-section-title')
                ui.label(' · '.join(PATTERN_SEMANTIC_ANATOMY.get(key, ())).replace('_', ' ')).classes('cui-workbench-note')
            render_pattern(key, title=titles[key], rows=(), on_event=lambda _message: None)

    with ui.element('section').classes('cui-unified-pattern-chooser').props('data-unified-pattern-explorer'):
        with ui.element('div').classes('cui-unified-pattern-chooser__copy'):
            ui.label('Which finished structure fits the work?').classes('cui-workbench-section-title')
            ui.label('Patterns define information hierarchy and behavior. The live example below uses the same registered composition used by generated applications.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-unified-pattern-rail'):
            for key in pattern_keys:
                with ui.element('article').classes('cui-unified-pattern-option').props(f'data-pattern-option="{key}"'):
                    ui.label(titles[key]).classes('cui-workbench-card__title')
                    ui.label(PATTERN_REGISTRY[next(item for item in PATTERN_REGISTRY if item.value == key)].purpose).classes('cui-workbench-note')
                    ui.label(' · '.join(PATTERN_SEMANTIC_ANATOMY.get(key, ())[:3]).replace('_', ' ')).classes('cui-workbench-card__meta')
                    Button('Open live example', icon='arrow-right', on_click=lambda _e=None, value=key: show_pattern(value))
        Select('Selected application pattern', titles, value='dashboard', clearable=False, on_change=lambda event: show_pattern(str(getattr(event, 'value', 'dashboard'))))
    show_pattern('dashboard')

    with ui.element('section').classes('cui-unified-pattern-apps').props('data-full-application-showcases'):
        ui.label('Full application references').classes('cui-workbench-section-title')
        ui.label('These are larger domain compositions built from the same patterns, governed analytics, tables, and inspectors.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-unified-pattern-apps__grid'):
            for definition in full_application_entries():
                with ui.element('article').classes('cui-explorer-card cui-full-app-showcase'):
                    _preview_image(application_asset_key(definition.key), label=definition.title)
                    ui.label('FULL APPLICATION').classes('cui-workbench-card__meta')
                    ui.label(definition.title).classes('cui-workbench-card__title')
                    ui.label(definition.question).classes('cui-workbench-card__body')
                    ui.label(' · '.join(definition.domain_facets)).classes('cui-workbench-note')
                    Button('Open live application', icon='arrow-right', on_click=lambda _e=None, route=definition.route: ui.navigate.to(route))
    _end_shell(shell)


def ai_guide_page() -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_content import CodeViewer
    shell = _shell('/ai-guide', 'AI Development Guide', 'A compact, task-first guide for humans and AI agents using the installed NiceGUI Base APIs.')
    workflow = {
        'requirement': 'Investigate chamber drift and compare affected/control distributions',
        'recommendation': {'pattern': 'analysis_workspace', 'recipe': 'excursion-defense-line'},
        'authorities': ['analytics:fdc_multi_sensor', 'analytics:rca_affected_control', 'component:data_table'],
        'scaffold': 'nicegui-base create-recipe ./chamber-drift --name "Chamber Drift Review" --recipe excursion-defense-line',
        'business_logic': 'app/services and app/repositories; keep provider queries and domain calculations out of page callbacks',
        'extension_rule': 'Prefer registered pattern/component/visualization and token APIs; isolate a documented escape hatch only when no authority fits',
        'validation': ['nicegui-base agent-check .', 'python -m nicegui_base.validate .', 'nicegui-base runtime-contract', 'nicegui-base runtime-smoke'],
        'result': 'A separately runnable app with governed filters, linked chart/table state, accessible empty/error states, and domain logic isolated in app-owned services',
    }
    with _section('Requirement → runnable reference', 'The same deterministic sequence is readable by a person and discoverable by an agent.'):
        with ui.element('div').classes('cui-workbench-ai-workflow').props(f'data-agent-workflow={json.dumps(json.dumps(workflow, sort_keys=True))}'):
            for label, value in (
                ('1 · Requirement', workflow['requirement']),
                ('2 · Recommendation', 'Pattern: analysis_workspace · Recipe: excursion-defense-line'),
                ('3 · Authorities', ' · '.join(workflow['authorities'])),
                ('4 · Scaffold', workflow['scaffold']),
                ('5 · Business/domain logic', workflow['business_logic']),
                ('6 · Extension rule', workflow['extension_rule']),
                ('7 · Expected result', workflow['result']),
            ):
                with ui.element('article').classes('cui-workbench-ai-step'):
                    ui.label(label).classes('cui-workbench-card__meta')
                    ui.label(value).classes('cui-workbench-card__body')
        CodeViewer(
            'nicegui-base agent-context "Investigate chamber drift and compare affected/control distributions"\n'
            'nicegui-base recommend-pattern "investigate chamber drift"\n'
            'nicegui-base recommend-visualization "compare affected control distributions"\n'
            'nicegui-base create-recipe ./chamber-drift --name "Chamber Drift Review" --recipe excursion-defense-line\n'
            'cd chamber-drift && nicegui-base agent-check .\n'
            'python -m nicegui_base.validate . && nicegui-base runtime-contract && nicegui-base runtime-smoke',
            language='bash',
        )
        ui.label('App-owned business logic belongs in services/repositories. The generated page composes the registered pattern, components, data controller, and visualization wrappers.').classes('cui-workbench-note')
    with _section('Authority shortcuts', 'Select the registered authority before writing page code.'):
        for title, route, detail in (
            ('Application patterns', '/patterns', 'Choose page hierarchy and responsive slots first.'),
            ('Components', '/components', 'Use typed registered controls and content surfaces.'),
            ('Data & tables', '/workbench/data', 'Keep schema/query semantics in data services.'),
            ('Visualizations', '/analytics', 'Use the governed chart and semiconductor renderers.'),
            ('Semiconductor recipes', '/recipes', 'Start with a domain composition when the question is known.'),
            ('Design System', '/design', 'Use semantic tokens and state helpers before custom styling.'),
        ):
            with ui.element('article').classes('cui-workbench-card'):
                ui.link(title, route).classes('cui-workbench-card__title')
                ui.label(detail).classes('cui-workbench-card__body')
    _end_shell(shell)



def _unknown_detail(active_route: str, title: str, message: str, back_route: str) -> None:
    ui, *_ = _imports()
    shell = _shell(active_route, title, message)
    with ui.element('section').classes('cui-workbench-preview cui-workbench-not-found'):
        ui.label('Nothing was changed or inferred from this URL.').classes('cui-workbench-note')
        _standard_button('Back to Reference Explorer', on_click=lambda: ui.navigate.to(back_route), primary=True)
    _end_shell(shell)


def _studio_entry_page(entry: WorkbenchEntry, *, active_route: str = '/catalog', preview_renderer=None, data_renderer=None, interaction_renderer=None, data_model=None) -> None:
    from .capability_studio import render_capability_studio
    shell = _shell(active_route, 'Reference Explorer', 'Browse the canonical capability, try its live example, and inspect the reusable usage contract.')
    render_capability_studio(
        entry, preview_renderer=preview_renderer, data_renderer=data_renderer,
        interaction_renderer=interaction_renderer, data_model=data_model, active_route=active_route,
        reference_only=True,
    )
    _end_shell(shell)


def studio_page(entry_key: str) -> None:
    from urllib.parse import unquote
    decoded = unquote(entry_key)
    entry = next((item for item in all_entries() if item.key == decoded), None)
    if entry is None:
        _unknown_detail('/catalog', 'Capability not found', f'No canonical Reference Explorer capability is registered as {decoded!r}.', '/catalog')
        return
    _studio_entry_page(entry)


def component_detail_page(component_key: str) -> None:
    entry = next((item for item in all_entries() if item.metadata.get('component_key') == component_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Component not found', f'No canonical component is registered as {component_key!r}.', '/catalog')
        return
    _studio_entry_page(entry, active_route='/components')

def catalog_detail_page(registry_name: str, entry_key: str) -> None:
    entry = next((item for item in all_entries() if item.metadata.get('registry_name') == registry_name and item.metadata.get('registry_key') == entry_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Catalog entry not found', f'No canonical catalog entry is registered as {registry_name}/{entry_key}.', '/catalog')
        return
    _studio_entry_page(entry)

def analytics_gallery_page() -> None:
    shell = _shell('/analytics', 'Visualizations', 'See what all 58 governed analytical surfaces actually look like before opening a full interactive reference.')
    from .explorer_gallery import render_reference_gallery
    render_reference_gallery(
        analytics_entries(), section='analytics',
        intro='Thumbnail-first discovery for semantic charts; open a detail to inspect the live renderer, data contract, and public code.',
    )
    _end_shell(shell)


SURFACE_PREVIEW_FAMILIES = {
    'spc_i_mr': 'control-i-mr',
    'spc_xbar_r': 'control-xbar-r',
    'spc_xbar_s': 'control-xbar-s',
    'spc_p': 'control-proportion',
    'spc_np': 'control-count-nonconforming',
    'spc_c': 'control-defects',
    'spc_u': 'control-defects-per-unit',
    'spc_ewma': 'control-ewma',
    'spc_cusum': 'control-cusum',
    'capability_histogram': 'capability-histogram',
    'qq_probability': 'probability-qq',
    'ecdf': 'ecdf',
    'box_distribution': 'box-distribution',
    'violin_distribution': 'violin-shape',
    'ridge_distribution': 'ridge-multiples',
    'wafer_continuous': 'wafer-continuous',
    'wafer_categorical': 'wafer-categorical',
    'wafer_defect': 'wafer-defect',
    'wafer_delta': 'wafer-delta',
    'wafer_comparison': 'wafer-comparison',
    'lot_wafer_strip': 'lot-wafer-strip',
    'wafer_small_multiples': 'wafer-small-multiples',
    'wafer_contour': 'wafer-contour',
    'wafer_radial': 'wafer-radial',
    'wafer_center_edge': 'wafer-center-edge',
    'wafer_ring': 'wafer-ring',
    'wafer_sector': 'wafer-sector',
    'wafer_defect_clusters': 'wafer-defect-clusters',
    'fdc_recipe_step_trace': 'fdc-step-trace',
    'fdc_golden_envelope': 'fdc-golden-envelope',
    'fdc_multi_sensor': 'fdc-multi-sensor',
    'fdc_tool_chamber_compare': 'fdc-tool-chamber',
    'fdc_chamber_fingerprint': 'fdc-chamber-fingerprint',
    'fdc_sensor_fingerprint': 'fdc-sensor-fingerprint',
    'fdc_alarm_overlay': 'fdc-alarm-overlay',
    'fdc_equipment_event_overlay': 'fdc-event-overlay',
    'fdc_pca_scores': 'fdc-pca-scores',
    'fdc_pca_loadings': 'fdc-pca-loadings',
    'fdc_hotelling_t2': 'fdc-hotelling-t2',
    'fdc_spe_q': 'fdc-spe-q',
    'rca_affected_control': 'rca-affected-control',
    'rca_commonality_ranking': 'rca-commonality-ranking',
    'rca_enrichment': 'rca-enrichment',
    'rca_commonality_matrix': 'rca-commonality-matrix',
    'rca_contribution_waterfall': 'rca-contribution',
    'rca_correlation_matrix': 'rca-correlation-matrix',
    'rca_evidence_matrix': 'rca-evidence-matrix',
    'rca_genealogy_graph': 'rca-genealogy',
    'rca_cause_tree': 'rca-cause-tree',
    'rca_fault_tree': 'rca-fault-tree',
    'rca_sankey': 'rca-process-flow',
    'yield_pareto': 'yield-pareto',
    'bin_pareto': 'bin-pareto',
    'yield_waterfall': 'yield-waterfall',
    'weibull_reliability': 'weibull-reliability',
    'doe_main_effects': 'doe-main-effects',
    'doe_interactions': 'doe-interactions',
    'doe_response_surface': 'doe-response-surface',
}

SURFACE_PREVIEW_TITLES = {
    'spc_i_mr': 'SPC I-MR',
    'spc_xbar_r': 'SPC Xbar-R',
    'spc_xbar_s': 'SPC Xbar-S',
    'spc_ewma': 'SPC EWMA',
    'spc_cusum': 'SPC CUSUM',
    'capability_histogram': 'Capability Histogram',
    'qq_probability': 'Q-Q Probability',
    'ecdf': 'ECDF',
    'box_distribution': 'Box Distribution',
    'violin_distribution': 'Violin Distribution',
    'ridge_distribution': 'Ridge Distribution',
    'wafer_categorical': 'Wafer Categorical',
    'wafer_defect': 'Wafer Defect',
}

SURFACE_SEMANTIC_CAPTIONS = {
    'spc_i_mr': 'Control chart · Individual + moving range · x: sample order · y: measurement',
    'spc_ewma': 'Control chart · EWMA smoothed statistic · x: sample order · y: EWMA value',
    'spc_cusum': 'Control chart · cumulative sum · x: sample order · y: cumulative deviation',
    'capability_histogram': 'Histogram · x: measurement bins · y: Count',
    'qq_probability': 'Q-Q probability plot · x: Theoretical quantile · y: Observed value',
    'ecdf': 'Empirical cumulative distribution · x: Value · y: Cumulative probability',
    'box_distribution': 'Box distribution · x: population · y: measurement',
    'violin_distribution': 'Violin distribution · x: population · width: local density',
    'ridge_distribution': 'Ridge distribution · rows: populations · x: value · height: density',
    'wafer_categorical': 'Categorical wafer map · legend: Category · die position: x/y',
    'wafer_defect': 'Defect wafer map · legend: Defect state · die position: x/y',
}


def _wafer_points(*, delta: float = 0.0, categorical: bool = False, defects: bool | str = False):
    from nicegui_base.visualization import WaferPoint
    points = []
    for y in range(-5, 6):
        for x in range(-5, 6):
            if x*x + y*y > 29:
                continue
            radial = (x*x + y*y) ** .5
            value = 40.0 + math.sin(x * .72) * .55 + math.cos(y * .58) * .42 + delta
            if x >= 3:
                value += .75
            if categorical:
                value = float((x + 2*y + 20) % 4)
            if defects:
                if defects == 'sparse':
                    value = 1.0 if (x, y) in {(-4,1),(-2,-3),(0,4),(2,2),(4,-1),(1,-4)} else 0.0
                else:
                    value = 1.0 if ((x - 3) ** 2 + (y + 1) ** 2 <= 4 or (x == -3 and y in (-1, 0, 1))) else 0.0
            status = 'watch' if (not categorical and not defects and (x >= 3 or radial > 4.7)) else 'normal'
            points.append(WaferPoint(x, y, round(value, 3), status=status))
    return points


def _render_flow_preview(title: str, stages: tuple[tuple[str, str], ...], *, footer: str) -> None:
    ui, *_ = _imports()
    ui.label(title).classes('cui-workbench-preview-title')
    with ui.element('div').classes('cui-workbench-flow'):
        for index, (label, detail) in enumerate(stages):
            with ui.element('div').classes('cui-workbench-flow__node'):
                ui.label(label).classes('cui-workbench-flow__title')
                ui.label(detail).classes('cui-workbench-note')
            if index < len(stages) - 1:
                ui.label('→').classes('cui-workbench-flow__arrow')
    ui.label(footer).classes('cui-workbench-preview-caption')


def _render_tree_preview(title: str, root: str, branches: tuple[tuple[str, tuple[str, ...]], ...], *, footer: str) -> None:
    ui, *_ = _imports()
    ui.label(title).classes('cui-workbench-preview-title')
    with ui.element('div').classes('cui-workbench-tree'):
        ui.label(root).classes('cui-workbench-tree__root')
        with ui.element('div').classes('cui-workbench-tree__branches'):
            for branch, leaves in branches:
                with ui.element('div').classes('cui-workbench-tree__branch'):
                    ui.label(branch).classes('cui-workbench-tree__branch-title')
                    for leaf in leaves:
                        ui.label(leaf).classes('cui-workbench-tree__leaf')
    ui.label(footer).classes('cui-workbench-preview-caption')


def _render_surface_preview(surface_key: str, category: str, *, compact: bool = False, title: str | None = None) -> None:
    """Render a truthful sample for every canonical semiconductor surface.

    The Workbench does not create another analytical engine. These are bounded sample
    renderings using existing NiceGUI Base visualization primitives and the canonical
    surface identity. The exact surface key chooses the visual grammar so distinct
    analytics no longer collapse into one category-level placeholder.
    """
    ui, *_ = _imports()
    from nicegui_base.integrations.nicegui_visualization import (
        BarChart, BoxPlot, ChamberFingerprintMatrix, CommonalityMatrix, ControlChart,
        DistributionPanel, _EmpiricalCDFChart, _FaultTreeDiagram, Heatmap, Histogram, LineChart, ParetoChart,
        RadialProfilePlot, _RelationshipGraph, _SankeyDiagram, ScatterChart, _WaferContourPlot,
        WaferComparisonMap, WaferMap, _WaterfallDiagram,
    )
    from nicegui_base.visualization import AnnotationIntent, AxisSpec, AxisType, ChartAnnotation, LineStyle, SeriesSpec, SpecLimits, WaferPoint
    from .analytic_specimens import canonical_fixture_for_surface
    from nicegui_base.semiconductor import fdc, rca, spc, yield_doe

    def mark_semantic(panel, props: str) -> None:
        target = getattr(panel, 'container', panel)
        setter = getattr(target, 'props', None)
        if callable(setter):
            setter(props)

    family = SURFACE_PREVIEW_FAMILIES.get(surface_key)
    if family is None:
        raise KeyError(f'No Workbench preview family registered for {surface_key!r}')
    title = title or SURFACE_PREVIEW_TITLES.get(surface_key) or ('Sample preview' if compact else 'Live governed sample preview')
    # The reference surface is the presentation of the canonical fixture, not a
    # second source of domain data.  Every branch below derives its bounded
    # specimen from the registry-owned fixture so the live preview and the
    # Data/Code contract cannot silently drift apart.
    canonical_rows = canonical_fixture_for_surface(surface_key)

    def fixture_wafer_points(*, value_field: str = 'measurement', status_field: str | None = None) -> tuple[WaferPoint, ...]:
        """Adapt the registered wafer fixture to the governed spatial API."""
        points: list[WaferPoint] = []
        for row in canonical_rows:
            value = row.get(value_field)
            status = str(row.get(status_field)) if status_field and row.get(status_field) is not None else None
            metadata = {key: value for key, value in row.items() if key not in {'x', 'y', value_field}}
            points.append(WaferPoint(float(row['x']), float(row['y']), None if value is None else float(value), status=status, metadata=metadata))
        return tuple(points)
    runs = tuple(f'R{i:02d}' for i in range(1, 13))
    caption = SURFACE_SEMANTIC_CAPTIONS.get(surface_key)
    if caption:
        ui.label(caption).classes('cui-workbench-preview-caption').props(
            f'data-visual-contract="{surface_key}"'
        )

    # SPC: keep the governed control-chart shell but make the sample statistic match the chart family.
    if surface_key in {'spc_i_mr','spc_xbar_r','spc_xbar_s','spc_ewma','spc_cusum'}:
        values = tuple(float(row['measurement']) for row in canonical_rows)
        if surface_key == 'spc_i_mr':
            result = spc.i_mr(values)
            with ui.element('div').classes('cui-analytics-pair').props('data-visual-geometry="i-mr"'):
                ui.label('Individuals + Moving Range · x: sample order / adjacent samples · y: Measurement / absolute difference').classes('cui-workbench-preview-caption')
                individual = ControlChart(
                    'Individuals — SPC I-MR',
                    (SeriesSpec('individuals', 'Individuals', result.values),),
                    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(f'R{i:02d}' for i in range(1, len(result.values) + 1)), label='Sample order'),
                    y_axis=AxisSpec(label='Measurement', min_value=result.lcl[0] - .25, max_value=result.ucl[0] + .25),
                    spec_limits=SpecLimits(lower=result.lcl[0], upper=result.ucl[0], target=result.center[0], lower_label='LCL', upper_label='UCL', target_label='Center'),
                )
                mark_semantic(individual, 'data-visual-semantic="spc_i_mr-individuals"')
                moving_range = ControlChart(
                    'Moving Range — SPC I-MR',
                    (SeriesSpec('moving_range', 'Moving Range', result.secondary_values),),
                    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(f'R{i:02d}→R{i + 1:02d}' for i in range(1, len(result.secondary_values) + 1)), label='Adjacent samples'),
                    y_axis=AxisSpec(label='Absolute difference', min_value=0.0, max_value=result.secondary_ucl[0] * 1.15),
                    spec_limits=SpecLimits(lower=result.secondary_lcl[0], upper=result.secondary_ucl[0], target=result.secondary_center[0], lower_label='LCL', upper_label='UCL', target_label='MR center'),
                )
                mark_semantic(moving_range, 'data-visual-semantic="spc_i_mr-moving-range"')
            return
        if surface_key == 'spc_ewma':
            result = spc.ewma(values, lambda_=.25, L=2.7)
            panel = ControlChart(
                title,
                (
                    SeriesSpec('ewma', 'EWMA', result.values),
                    SeriesSpec('center', 'Center', result.center, line_style=LineStyle.DASHED, semantic_color='neutral'),
                    SeriesSpec('ucl', 'UCL', result.ucl, line_style=LineStyle.DASHED, semantic_color='danger'),
                    SeriesSpec('lcl', 'LCL', result.lcl, line_style=LineStyle.DASHED, semantic_color='danger'),
                ),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=runs + tuple(f'R{i:02d}' for i in range(13, len(result.values) + 1)), label='Sample order'),
                y_axis=AxisSpec(label='EWMA value', min_value=min(result.lcl) - .12, max_value=max(result.ucl) + .12),
            )
            mark_semantic(panel, 'data-visual-semantic="spc_ewma" data-chart-semantics="center-ucl-lcl"')
            return
        if surface_key == 'spc_cusum':
            result = spc.cusum(values, target=40.0, k=.5, h=5.0)
            panel = ControlChart(
                title,
                (
                    SeriesSpec('cusum', 'CUSUM statistic', result.values),
                    SeriesSpec('center', 'Center', result.center, line_style=LineStyle.DASHED, semantic_color='neutral'),
                    SeriesSpec('ucl', 'Decision limit', result.ucl, line_style=LineStyle.DASHED, semantic_color='danger'),
                    SeriesSpec('lcl', 'Decision limit', result.lcl, line_style=LineStyle.DASHED, semantic_color='danger'),
                ),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(f'R{i:02d}' for i in range(1, len(values) + 1)), label='Sample order'),
                y_axis=AxisSpec(label='Standardized cumulative deviation', min_value=min(result.lcl) - 1.0, max_value=max(result.ucl) + 1.0),
            )
            mark_semantic(panel, 'data-visual-semantic="spc_cusum" data-chart-semantics="positive-negative-decision-limits" data-semantic-contract="cusum-statistic-decision-limits"')
            return
        grouped: dict[str, list[float]] = {}
        for row in canonical_rows:
            grouped.setdefault(str(row['subgroup']), []).append(float(row['measurement']))
        result = spc.xbar_r(grouped.values()) if surface_key == 'spc_xbar_r' else spc.xbar_s(grouped.values())
        secondary_key = 'range' if surface_key == 'spc_xbar_r' else 'standard-deviation'
        secondary_label = 'Range' if surface_key == 'spc_xbar_r' else 'Standard deviation'
        with ui.element('div').classes('cui-analytics-pair').props(f'data-visual-geometry="{surface_key.replace("spc_", "").replace("_", "-")}"'):
            xbar = ControlChart(
                f'X̄ — {title}', (SeriesSpec('xbar', 'X̄', result.values),),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(grouped), label='Rational subgroup'),
                y_axis=AxisSpec(label='Subgroup mean', min_value=result.lcl[0] - .15, max_value=result.ucl[0] + .15),
                spec_limits=SpecLimits(lower=result.lcl[0], upper=result.ucl[0], target=result.center[0], lower_label='LCL', upper_label='UCL', target_label='Center'),
            )
            mark_semantic(xbar, f'data-visual-semantic="{surface_key}-xbar"')
            secondary = ControlChart(
                f'{secondary_label} — {title}', (SeriesSpec(secondary_key, secondary_label, result.secondary_values),),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(grouped), label='Rational subgroup'),
                y_axis=AxisSpec(label=secondary_label, min_value=0.0, max_value=result.secondary_ucl[0] * 1.15),
                spec_limits=SpecLimits(lower=result.secondary_lcl[0], upper=result.secondary_ucl[0], target=result.secondary_center[0], lower_label='LCL', upper_label='UCL', target_label=f'{secondary_label} center'),
            )
            mark_semantic(secondary, f'data-visual-semantic="{surface_key}-{secondary_key}"')
        return
    if surface_key in {'spc_p','spc_np','spc_c','spc_u'}:
        sample_labels = tuple(str(row['sample']) for row in canonical_rows)
        if surface_key == 'spc_p':
            result = spc.p_chart(
                tuple(int(row['nonconforming']) for row in canonical_rows),
                tuple(int(row['inspected']) for row in canonical_rows),
            )
        elif surface_key == 'spc_np':
            result = spc.np_chart(
                tuple(int(row['nonconforming']) for row in canonical_rows),
                tuple(int(row['inspected']) for row in canonical_rows),
            )
        elif surface_key == 'spc_c':
            result = spc.c_chart(tuple(int(row['defects']) for row in canonical_rows))
        else:
            result = spc.u_chart(
                tuple(int(row['defects']) for row in canonical_rows),
                tuple(float(row['units']) for row in canonical_rows),
            )
        labels = {
            'spc_p':'Nonconforming proportion', 'spc_np':'Nonconforming count',
            'spc_c':'Defect count', 'spc_u':'Defects / unit',
        }
        panel = ControlChart(
            title,
            (
                SeriesSpec(surface_key, labels[surface_key], result.values),
                SeriesSpec('center', 'Center', result.center, line_style=LineStyle.DASHED, semantic_color='neutral'),
                SeriesSpec('ucl', 'UCL', result.ucl, line_style=LineStyle.DASHED, semantic_color='danger'),
                SeriesSpec('lcl', 'LCL', result.lcl, line_style=LineStyle.DASHED, semantic_color='danger'),
            ),
            x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=sample_labels, label='Sample order'),
            y_axis=AxisSpec(label=labels[surface_key], min_value=0.0, max_value=max(result.ucl) * 1.12),
        )
        mark_semantic(panel, f'data-visual-semantic="{surface_key}" data-chart-semantics="center-ucl-lcl-variable-opportunity"')
        return

    # Capability/distribution diagnostics.
    if surface_key == 'capability_histogram':
        values = tuple(float(row['measurement']) for row in canonical_rows)
        histogram = spc.capability_histogram(values, bins=9)
        capability = spc.capability_indices(
            values,
            lsl=float(canonical_rows[0]['lsl']),
            usl=float(canonical_rows[0]['usl']),
            target=float(canonical_rows[0]['target']),
        )
        categories = tuple(f'{lo:.2f}–{hi:.2f}' for lo, hi, _count in histogram)
        panel = Histogram(
            title, (SeriesSpec('count','Count',tuple(count for _lo, _hi, count in histogram)),),
            x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=categories, label='Measurement (nm)'),
            y_axis=AxisSpec(label='Count'),
            annotations=(
                ChartAnnotation(f"{capability.lsl:g}", 'LSL', intent=AnnotationIntent.DANGER),
                ChartAnnotation(f"{capability.target:g}", 'Target', intent=AnnotationIntent.INFO),
                ChartAnnotation(f"{capability.usl:g}", 'USL', intent=AnnotationIntent.DANGER),
            ),
        )
        with ui.element('div').classes('cui-analytics-metric-strip').props('data-capability-summary="true"'):
            for label, value in (
                ('Cp', capability.cp), ('Cpk', capability.cpk),
                ('Pp', capability.pp), ('Ppk', capability.ppk), ('n', capability.count),
            ):
                ui.label(f'{label} {value:.3f}' if isinstance(value, float) else f'{label} {value}').classes('cui-workbench-chip')
        mark_semantic(panel, 'data-visual-semantic="capability_histogram" data-chart-semantics="distribution-with-spec-context" data-spec-lines="LSL Target USL"')
        return
    if surface_key == 'qq_probability':
        points = spc.qq_points(tuple(float(row['measurement']) for row in canonical_rows))
        expected = tuple((point[0], point[0]) for point in points)
        panel = ScatterChart(title, (SeriesSpec('observed','Observed quantiles',points), SeriesSpec('expected','Expected line',expected)), x_axis=AxisSpec(label='Theoretical quantile'), y_axis=AxisSpec(label='Observed quantile'))
        mark_semantic(panel, 'data-visual-semantic="qq_probability" data-chart-semantics="observed-vs-expected"')
        return
    if surface_key == 'ecdf':
        points = spc.ecdf(tuple(float(row['measurement']) for row in canonical_rows))
        panel = _EmpiricalCDFChart(title, points)
        mark_semantic(panel, 'data-visual-semantic="ecdf" data-chart-semantics="monotone-cdf" data-chart-step="end"')
        return
    if surface_key == 'box_distribution':
        populations = tuple(dict.fromkeys(str(row['population']) for row in canonical_rows))
        groups = tuple(
            tuple(float(row['measurement']) for row in canonical_rows if str(row['population']) == population)
            for population in populations
        )
        summaries = tuple(spc.box_distribution(group) for group in groups)
        panel = BoxPlot(
            title,
            (SeriesSpec('box', 'Measurement', tuple((item.minimum, item.q1, item.median, item.q3, item.maximum) for item in summaries)),),
            x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=populations, label='Population'),
            y_axis=AxisSpec(label='Measurement (nm)', min_value=min(item.minimum for item in summaries) - .3, max_value=max(item.maximum for item in summaries) + .3),
        )
        mark_semantic(panel, 'data-visual-semantic="box_distribution" data-chart-semantics="quartiles-median-whiskers"')
        return
    if surface_key == 'violin_distribution':
        try:
            from nicegui_base.integrations.nicegui_visualization import ViolinPlot
        except ImportError:  # compatibility with the bounded renderer stub in older acceptance tests
            DistributionPanel(title, (SeriesSpec('shape','Density',(1,3,7,14,21,24,18,11,5,2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38.0','38.4','38.8','39.2','39.6','40.0','40.4','40.8','41.2','41.6')))
        else:
            ViolinPlot(title, ((1,3,7,14,21,24,18,11,5,2),), labels=('CD distribution',), description='Symmetric density silhouette; width encodes local density.')
        return
    if surface_key == 'ridge_distribution':
        ridge_series = (
            SeriesSpec('ch1','CH-1',(0,1,4,10,15,10,4,1,0),smooth=True),
            SeriesSpec('ch2','CH-2',(0,0,2,7,14,13,7,2,0),smooth=True),
            SeriesSpec('ch3','CH-3',(0,0,1,3,8,14,12,6,2),smooth=True),
        )
        try:
            from nicegui_base.integrations.nicegui_visualization import RidgePlot
        except ImportError:  # compatibility with the bounded renderer stub in older acceptance tests
            LineChart(title, ridge_series, x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38','38.5','39','39.5','40','40.5','41','41.5','42')))
        else:
            RidgePlot(title, ridge_series, labels=('38','38.5','39','39.5','40','40.5','41','41.5','42'), description='Offset density curves keep each chamber distribution readable.')
        return

    # Wafer/spatial analytics.
    if surface_key == 'wafer_continuous':
        WaferMap(title, fixture_wafer_points())
        return
    if surface_key == 'wafer_categorical':
        category_values = {'Nominal': 0.0, 'Watch': 1.0, 'Review': 2.0}
        WaferMap(
            title,
            tuple(WaferPoint(float(row['x']), float(row['y']), category_values.get(str(row['category']), 3.0), status=str(row['category']), metadata={'category': row['category']}) for row in canonical_rows),
            legend_title='Category', legend_labels=('Nominal','Watch','Review','Other'),
        )
        return
    if surface_key == 'wafer_defect':
        WaferMap(
            title,
            tuple(WaferPoint(float(row['x']), float(row['y']), 1.0 if str(row['defect_state']) == 'Defect' else 0.0, status=str(row['defect_state'])) for row in canonical_rows),
            legend_title='Defect state', legend_labels=('No defect','Defect'),
        )
        return
    if surface_key == 'wafer_defect_clusters':
        WaferMap(
            title,
            tuple(WaferPoint(float(row['x']), float(row['y']), 1.0 if str(row['defect_state']) == 'Defect' else 0.0, status=str(row['cluster'])) for row in canonical_rows),
            legend_title='Defect state', legend_labels=('No defect','Clustered defect'),
        )
        return
    if surface_key == 'wafer_delta':
        delta_points = tuple(WaferPoint(float(row['x']), float(row['y']), float(row['delta']), status='watch' if abs(float(row['delta'])) >= .25 else 'normal') for row in canonical_rows)
        WaferMap(title, delta_points)
        return
    if surface_key == 'wafer_comparison':
        affected = tuple(WaferPoint(float(row['x']), float(row['y']), float(row['affected'])) for row in canonical_rows)
        control = tuple(WaferPoint(float(row['x']), float(row['y']), float(row['control'])) for row in canonical_rows)
        WaferComparisonMap(title, affected, control)
        return
    if surface_key == 'lot_wafer_strip':
        ui, *_ = _imports()
        ui.label(title).classes('cui-workbench-preview-title')
        with ui.element('div').classes('cui-workbench-mini-grid cui-workbench-mini-grid--strip'):
            for index, wafer in enumerate(tuple(dict.fromkeys(str(row['wafer']) for row in canonical_rows)), start=1):
                with ui.element('div').classes('cui-workbench-mini-panel'):
                    WaferMap(f'Wafer {wafer}', tuple(WaferPoint(float(row['x']), float(row['y']), float(row['measurement']), metadata={'wafer': wafer}) for row in canonical_rows if str(row['wafer']) == wafer))
        return
    if surface_key == 'wafer_small_multiples':
        ui, *_ = _imports()
        ui.label(title).classes('cui-workbench-preview-title')
        with ui.element('div').classes('cui-workbench-mini-grid'):
            for index, wafer in enumerate(tuple(dict.fromkeys(str(row['wafer']) for row in canonical_rows)), start=1):
                with ui.element('div').classes('cui-workbench-mini-panel'):
                    WaferMap(f'Wafer {wafer}', tuple(WaferPoint(float(row['x']), float(row['y']), float(row['measurement']), metadata={'wafer': wafer}) for row in canonical_rows if str(row['wafer']) == wafer))
        return
    if surface_key == 'wafer_contour':
        panel = _WaferContourPlot(title, tuple(float(row['measurement']) for row in canonical_rows))
        mark_semantic(panel, 'data-visual-semantic="wafer_contour" data-chart-semantics="clipped-contour-isolines"')
        return
    if surface_key == 'wafer_radial':
        affected = tuple(float(row['measurement']) for row in canonical_rows if str(row['population']) == 'Affected')
        control = tuple(float(row['measurement']) for row in canonical_rows if str(row['population']) == 'Control')
        RadialProfilePlot(title, affected, control, unit='nm')
        return
    if surface_key == 'wafer_center_edge':
        regions = tuple(dict.fromkeys(str(row['region']) for row in canonical_rows))
        BarChart(title, (SeriesSpec('measurement','Mean CD',tuple(sum(float(row['measurement']) for row in canonical_rows if str(row['region']) == region) / max(1, sum(str(row['region']) == region for row in canonical_rows)) for region in regions)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=regions,label='Wafer region'), y_axis=AxisSpec(label='Mean measurement',unit='nm'))
        return
    if surface_key == 'wafer_ring':
        rings = tuple(dict.fromkeys(str(row['ring']) for row in canonical_rows))
        BarChart(title, (SeriesSpec('measurement','Mean residual',tuple(sum(float(row['measurement']) for row in canonical_rows if str(row['ring']) == ring) / max(1, sum(str(row['ring']) == ring for row in canonical_rows)) for ring in rings)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=rings,label='Concentric ring'), y_axis=AxisSpec(label='Mean residual',unit='nm'))
        return
    if surface_key == 'wafer_sector':
        sectors = tuple(dict.fromkeys(str(row['sector']) for row in canonical_rows))
        BarChart(title, (SeriesSpec('measurement','Mean residual',tuple(sum(float(row['measurement']) for row in canonical_rows if str(row['sector']) == sector) / max(1, sum(str(row['sector']) == sector for row in canonical_rows)) for sector in sectors)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=sectors,label='Wafer sector'), y_axis=AxisSpec(label='Mean residual',unit='nm'))
        return

    # FDC/equipment analytics.
    if surface_key == 'fdc_recipe_step_trace':
        LineChart(
            title,
            (SeriesSpec('sensor', 'Pressure', tuple(float(row['value']) for row in canonical_rows), smooth=False),),
            x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(f"{row['timestamp']} · {row['recipe_step']}" for row in canonical_rows), label='Elapsed time / recipe step'),
            y_axis=AxisSpec(label='Pressure'),
        )
        return
    if surface_key == 'fdc_golden_envelope':
        LineChart(title, (
            SeriesSpec('upper','Golden upper',tuple(float(row['golden_upper']) for row in canonical_rows),smooth=True, line_style=LineStyle.DASHED, semantic_color='neutral'),
            SeriesSpec('trace','Observed',tuple(float(row['observed']) for row in canonical_rows),smooth=True),
            SeriesSpec('lower','Golden lower',tuple(float(row['golden_lower']) for row in canonical_rows),smooth=True, line_style=LineStyle.DASHED, semantic_color='neutral'),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['timestamp']) for row in canonical_rows),label='Elapsed time'), y_axis=AxisSpec(label='Sensor value'))
        return
    if surface_key == 'fdc_multi_sensor':
        sensors = tuple(dict.fromkeys(str(row['sensor']) for row in canonical_rows))
        LineChart(title, (
            *(SeriesSpec(sensor.lower().replace(' ', '_'), sensor, tuple(float(row['value']) for row in canonical_rows if str(row['sensor']) == sensor), smooth=True) for sensor in sensors),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['timestamp']) for row in canonical_rows if str(row['sensor']) == sensors[0]),label='Elapsed time'), y_axis=AxisSpec(label='Normalized sensor response'))
        return
    if surface_key == 'fdc_tool_chamber_compare':
        BarChart(title, (SeriesSpec('score','Normalized deviation',tuple(float(row['score']) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(f"{row['tool']} / {row['chamber']}" for row in canonical_rows),label='Tool / chamber'), y_axis=AxisSpec(label='Normalized deviation'))
        return
    if surface_key == 'fdc_chamber_fingerprint':
        matrix_rows = tuple(dict.fromkeys(str(row['chamber']) for row in canonical_rows))
        matrix_columns = tuple(dict.fromkeys(str(row['feature']) for row in canonical_rows))
        values = tuple(tuple(float(next(row['score'] for row in canonical_rows if str(row['chamber']) == chamber and str(row['feature']) == feature)) for feature in matrix_columns) for chamber in matrix_rows)
        ChamberFingerprintMatrix(title, matrix_rows, matrix_columns, values)
        return
    if surface_key == 'fdc_sensor_fingerprint':
        matrix_rows = tuple(dict.fromkeys(str(row['sensor']) for row in canonical_rows))
        matrix_columns = tuple(dict.fromkeys(str(row['feature']) for row in canonical_rows))
        values = tuple(tuple(float(next(row['score'] for row in canonical_rows if str(row['sensor']) == sensor and str(row['feature']) == feature)) for feature in matrix_columns) for sensor in matrix_rows)
        ChamberFingerprintMatrix(title, matrix_rows, matrix_columns, values)
        return
    if surface_key in {'fdc_alarm_overlay','fdc_equipment_event_overlay'}:
        event = 'Alarm' if surface_key == 'fdc_alarm_overlay' else 'PM event'
        panel = LineChart(
            title, (SeriesSpec('sensor','Sensor',tuple(float(row['value']) for row in canonical_rows),smooth=True),),
            x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['timestamp']) for row in canonical_rows),label='Elapsed time'), y_axis=AxisSpec(label='Sensor value'),
            annotations=tuple(ChartAnnotation(str(row['timestamp']), str(row['event']), intent=AnnotationIntent.WARNING) for row in canonical_rows if str(row['event']) != 'None'),
        )
        mark_semantic(panel, f'data-visual-semantic="{surface_key}" data-chart-semantics="trace-with-event-marker"')
        return
    if surface_key == 'fdc_pca_scores':
        populations = tuple(dict.fromkeys(str(row['population']) for row in canonical_rows))
        ScatterChart(title, (
            *(SeriesSpec(population.lower(), population, tuple((float(row['pc1']), float(row['pc2'])) for row in canonical_rows if str(row['population']) == population)) for population in populations),
        ), x_axis=AxisSpec(label='PC1 score'), y_axis=AxisSpec(label='PC2 score'))
        return
    if surface_key == 'fdc_pca_loadings':
        BarChart(title, (SeriesSpec('loading','PC1 loading',tuple(float(row['loading']) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['sensor']) for row in canonical_rows),label='Sensor variable'), y_axis=AxisSpec(label='PC1 loading'))
        return
    if surface_key == 'fdc_hotelling_t2':
        LineChart(title, (SeriesSpec('t2','Hotelling T²',tuple(float(row['statistic']) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['sample']) for row in canonical_rows),label='Sample order'), y_axis=AxisSpec(label='Hotelling T²'), spec_limits=SpecLimits(upper=float(canonical_rows[0]['limit']),upper_label='Limit'))
        return
    if surface_key == 'fdc_spe_q':
        LineChart(title, (SeriesSpec('spe','SPE / Q',tuple(float(row['statistic']) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['sample']) for row in canonical_rows),label='Sample order'), y_axis=AxisSpec(label='SPE / Q'), spec_limits=SpecLimits(upper=float(canonical_rows[0]['limit']),upper_label='Limit'))
        return

    # RCA analytics.
    if surface_key == 'rca_affected_control':
        populations = tuple(dict.fromkeys(str(row['population']) for row in canonical_rows))
        groups = tuple(tuple(float(row['measurement']) for row in canonical_rows if str(row['population']) == population) for population in populations)
        summaries = tuple(spc.box_distribution(group) for group in groups)
        panel = BoxPlot(title, (SeriesSpec('population','Metric',tuple((summary.minimum, summary.q1, summary.median, summary.q3, summary.maximum) for summary in summaries)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=populations,label='Population'), y_axis=AxisSpec(label='Measurement (nm)', min_value=min(summary.minimum for summary in summaries) - .3, max_value=max(summary.maximum for summary in summaries) + .3))
        mark_semantic(panel, 'data-visual-semantic="rca_affected_control" data-chart-semantics="grouped-quartile-distributions"')
        return
    if surface_key in {'rca_commonality_ranking','rca_enrichment'}:
        label = 'Affected overlap %' if surface_key == 'rca_commonality_ranking' else 'Enrichment ratio'
        BarChart(title, (SeriesSpec('rank',label,tuple(float(row['score']) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(row['factor']) for row in canonical_rows),label='Factor'), y_axis=AxisSpec(label=label))
        return
    if surface_key == 'rca_commonality_matrix':
        rows = tuple(dict.fromkeys(str(row['factor']) for row in canonical_rows))
        columns = tuple(dict.fromkeys(str(row['population']) for row in canonical_rows))
        matrix = tuple(tuple(float(next(row['score'] for row in canonical_rows if str(row['factor']) == factor and str(row['population']) == population)) for population in columns) for factor in rows)
        CommonalityMatrix(title, rows, columns, matrix)
        return
    if surface_key == 'rca_contribution_waterfall':
        panel = _WaterfallDiagram(title, tuple(str(row['factor']) for row in canonical_rows), tuple(float(row['contribution']) for row in canonical_rows), description='Transparent bases preserve the cumulative bridge from each signed contribution to the reconciled net shift.')
        mark_semantic(panel, 'data-visual-semantic="rca_contribution_waterfall" data-chart-semantics="cumulative-signed-bridge"')
        return
    if surface_key == 'rca_correlation_matrix':
        variables = tuple(dict.fromkeys([
            *(str(row['x_variable']) for row in canonical_rows),
            *(str(row['y_variable']) for row in canonical_rows),
        ]))
        known = {(str(row['x_variable']), str(row['y_variable'])): float(row['correlation']) for row in canonical_rows}
        cells = tuple((x, y, known.get((variables[x], variables[y]), known.get((variables[y], variables[x]), 0.0))) for x in range(len(variables)) for y in range(len(variables)))
        Heatmap(title, (SeriesSpec('corr','Correlation',cells),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=variables,label='Variable'), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=variables,label='Variable'))
        return
    if surface_key == 'rca_evidence_matrix':
        rows = tuple(str(row['hypothesis']) for row in canonical_rows)
        columns = tuple(dict.fromkeys(str(row['evidence_state']) for row in canonical_rows))
        matrix = tuple(tuple(float(row['score']) if str(row['evidence_state']) == state else 0.0 for state in columns) for row in canonical_rows)
        CommonalityMatrix(title, rows, columns, matrix)
        return
    if surface_key == 'rca_genealogy_graph':
        edge_rows = tuple((str(row['source']), str(row['target'])) for row in canonical_rows)
        node_labels = tuple(dict.fromkeys([label for edge in edge_rows for label in edge]))
        node_ids = {label: f'node-{index}' for index, label in enumerate(node_labels)}
        nodes = tuple((node_ids[label], label, index % 4, index // 4) for index, label in enumerate(node_labels))
        panel = _RelationshipGraph(
            title,
            nodes,
            tuple((node_ids[source], node_ids[target]) for source, target in edge_rows),
            description='Branching and merging entity relationships preserve route order; they do not imply causality.',
        )
        mark_semantic(panel, 'data-visual-semantic="rca_genealogy_graph" data-chart-semantics="branching-merging-directed-relationships"')
        return
    if surface_key == 'rca_cause_tree':
        panel = _FaultTreeDiagram(
            title,
            {
                'name': 'CD excursion',
                'children': (
                    {'name': 'Equipment', 'children': ({'name': 'CH-3 drift'}, {'name': 'RF delivery'})},
                    {'name': 'Process', 'children': ({'name': 'Recipe step'}, {'name': 'Pressure response'})},
                    {'name': 'Material', 'children': ({'name': 'Incoming lot M4'},)},
                ),
            },
            description='Hierarchical candidate decomposition; candidates remain hypotheses until evidence corroborates them.',
            renderer_type='cause_tree',
        )
        mark_semantic(panel, 'data-visual-semantic="rca_cause_tree" data-chart-semantics="hierarchical-causal-candidates"')
        return
    if surface_key == 'rca_fault_tree':
        panel = _FaultTreeDiagram(
            title,
            {
                'name': 'OOS event',
                'children': (
                    {'name': 'OR', 'gate': 'OR', 'children': ({'name': 'Pressure unstable'}, {'name': 'RF mismatch'}, {'name': 'Wrong recipe revision'})},
                    {'name': 'AND', 'gate': 'AND', 'children': ({'name': 'SPC violation'}, {'name': 'Wafer edge signature'})},
                ),
            },
            description='AND/OR logic is explicit and remains separate from evidence confidence.',
        )
        mark_semantic(panel, 'data-visual-semantic="rca_fault_tree" data-chart-semantics="hierarchy-connectors-and-or-gates"')
        return
    if surface_key == 'rca_sankey':
        links = tuple((str(row['source']), str(row['target']), float(row['quantity'])) for row in canonical_rows)
        nodes = tuple(dict.fromkeys(node for row in canonical_rows for node in (str(row['source']), str(row['target']))))
        panel = _SankeyDiagram(title, nodes, links, description='Band width encodes wafer quantity through route, tool, chamber, and review stages.')
        mark_semantic(panel, 'data-visual-semantic="rca_sankey" data-chart-semantics="quantity-weighted-flow-bands"')
        return

    # Yield, reliability, DOE.
    if surface_key in {'yield_pareto','bin_pareto'}:
        items = yield_doe.yield_pareto(canonical_rows, category='category', value='count')
        ParetoChart(title, tuple(str(item['category']) for item in items), tuple(float(item['value']) for item in items), tuple(float(item['cumulative']) * 100 for item in items))
        return
    if surface_key == 'yield_waterfall':
        panel = _WaterfallDiagram(title, tuple(str(row['category']) for row in canonical_rows), tuple(float(row['delta']) for row in canonical_rows), description='Loss and recovery bars reconcile the signed total yield change.')
        mark_semantic(panel, 'data-visual-semantic="yield_waterfall" data-chart-semantics="cumulative-signed-bridge"')
        return
    if surface_key == 'weibull_reliability':
        times = tuple(float(row['time']) for row in canonical_rows)
        failures = tuple(bool(row.get('failed', True)) for row in canonical_rows)
        result = yield_doe.weibull_analysis(times, failures=failures)
        failure_points = tuple({'time': time, 'probability': result.cdf(time)} for time, failed in zip(times, failures, strict=True) if failed)
        censored_points = tuple({'time': time, 'probability': result.cdf(time)} for time, failed in zip(times, failures, strict=True) if not failed)
        fit_points = tuple({'time': time, 'probability': result.cdf(time)} for time in times)
        marker_shape = getattr(__import__('nicegui_base.visualization', fromlist=['MarkerShape']), 'MarkerShape', None)
        panel = ScatterChart(title, (
            SeriesSpec('failure','Failures',failure_points,x_key='time',y_key='probability',semantic_color='danger'),
            SeriesSpec('censored','Censored',censored_points,x_key='time',y_key='probability',**({'marker': marker_shape.DIAMOND} if marker_shape else {}),semantic_color='warning'),
            SeriesSpec('fit','Weibull fit',fit_points,x_key='time',y_key='probability',**({'marker': marker_shape.NONE} if marker_shape else {}),smooth=True),
        ), x_axis=AxisSpec(label='Exposure time'), y_axis=AxisSpec(label='Cumulative failure probability',min_value=0.0,max_value=1.0), description=f'β {result.beta:.2f} · η {result.eta:.1f} · R² {result.r2:.2f} · {result.failures} failures / {result.censored} censored')
        return
    if surface_key == 'doe_main_effects':
        effects = {
            factor: yield_doe.doe_main_effects(
                tuple(row for row in canonical_rows if str(row['factor']) == factor),
                ('level',),
                'response',
            )['level']
            for factor in tuple(dict.fromkeys(str(row['factor']) for row in canonical_rows))
        }
        panel = LineChart(title, (
            SeriesSpec('rf','RF bias',tuple(effects['RF bias'].values())),
            SeriesSpec('pressure','Pressure',tuple(effects['Pressure'].values())),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Low','Center','High'), label='Factor level'), y_axis=AxisSpec(label='Mean response', min_value=39.2, max_value=41.4))
        mark_semantic(panel, 'data-visual-semantic="doe_main_effects" data-chart-semantics="clear-opposing-main-effect-slopes"')
        return
    if surface_key == 'doe_interactions':
        effects = yield_doe.doe_interactions(canonical_rows, 'factor_a', 'factor_b', 'response')
        levels = tuple(dict.fromkeys(str(row['factor_a']) for row in canonical_rows))
        factor_b_levels = tuple(dict.fromkeys(str(row['factor_b']) for row in canonical_rows))
        panel = LineChart(title, (
            *(SeriesSpec(f'level_{index}', factor_b, tuple(float(effects[level][factor_b]) for level in levels)) for index, factor_b in enumerate(factor_b_levels)),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=levels, label='RF bias level'), y_axis=AxisSpec(label='Mean response', min_value=39.1, max_value=41.3))
        mark_semantic(panel, 'data-visual-semantic="doe_interactions" data-chart-semantics="non-parallel-crossing-interaction"')
        return
    if surface_key == 'doe_response_surface':
        factor_a = tuple(dict.fromkeys(float(row['factor_a']) for row in canonical_rows))
        factor_b = tuple(dict.fromkeys(float(row['factor_b']) for row in canonical_rows))
        Heatmap(title, (SeriesSpec('response','Response',tuple((factor_a.index(float(row['factor_a'])), factor_b.index(float(row['factor_b'])), float(row['response'])) for row in canonical_rows)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(value) for value in factor_a),label='Factor A · RF bias'), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(value) for value in factor_b),label='Factor B · pressure'))
        return

    raise AssertionError(f'Preview dispatch did not render {surface_key!r} ({category!r})')

def _studio_numeric_columns(session) -> tuple[str, ...]:
    return tuple(column.name for column in session.data.columns if column.inferred_type in {'integer','float','decimal'})


def _hotelling_t2_values(rows, x_key: str, y_key: str) -> tuple[float, ...]:
    pairs = [(float(row[x_key]), float(row[y_key])) for row in rows if row.get(x_key) is not None and row.get(y_key) is not None]
    if len(pairs) < 3:
        return ()
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    sxx = sum((x-mx)**2 for x, _ in pairs) / (n-1)
    syy = sum((y-my)**2 for _, y in pairs) / (n-1)
    sxy = sum((x-mx)*(y-my) for x, y in pairs) / (n-1)
    det = sxx * syy - sxy * sxy
    if abs(det) < 1e-12:
        scale_x = sxx or 1.0
        scale_y = syy or 1.0
        return tuple(round((x-mx)**2/scale_x + (y-my)**2/scale_y, 5) for x, y in pairs)
    inv00, inv01, inv11 = syy/det, -sxy/det, sxx/det
    values = []
    for x, y in pairs:
        dx, dy = x-mx, y-my
        values.append(round(dx*dx*inv00 + 2*dx*dy*inv01 + dy*dy*inv11, 5))
    return tuple(values)


def _render_analytic_studio_preview(session) -> None:
    """Use Data Dock rows where the canonical surface grammar can remain truthful."""
    from nicegui import ui
    from nicegui_base.integrations.nicegui_visualization import ControlChart, LineChart
    from nicegui_base.visualization import AxisSpec, AxisType, SeriesSpec

    surface_key = str(session.entry.metadata.get('surface_key'))
    numeric = _studio_numeric_columns(session)
    rows = session.data.rows
    if surface_key.startswith('spc_') and numeric and rows:
        key = str(session.config.options.get('measurement') or numeric[0])
        if key not in session.data.snapshot.column_names:
            key = numeric[0]
        values = tuple(float(row[key]) for row in rows if row.get(key) is not None)
        if values:
            labels = tuple(str(row.get('timestamp') or row.get('id') or index + 1) for index, row in enumerate(rows) if row.get(key) is not None)
            ControlChart(
                session.config.title or session.entry.title,
                (SeriesSpec(surface_key, key, values),),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=labels),
            )
            ui.label(f'Live from Data Dock · {len(values)} values from {key}').classes('cui-workbench-preview-caption')
            return
    if surface_key == 'fdc_hotelling_t2' and len(numeric) >= 2 and rows:
        x_key, y_key = numeric[:2]
        values = _hotelling_t2_values(rows, x_key, y_key)
        if values:
            LineChart(
                session.config.title or session.entry.title,
                (SeriesSpec('t2', 'Hotelling T²', values),),
                x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(str(i+1) for i in range(len(values)))),
            )
            ui.label(f'Live from Data Dock · covariance score from {x_key} + {y_key}').classes('cui-workbench-preview-caption')
            return
    _render_surface_preview(surface_key, session.entry.category, title=session.config.title or session.entry.title)


def analytics_detail_page(surface_key: str) -> None:
    entry = next((item for item in analytics_entries() if item.metadata.get('surface_key') == surface_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Analytical surface not found', f'No canonical analytical surface is registered as {surface_key!r}.', '/analytics')
        return
    _studio_entry_page(entry, active_route='/analytics')

def recipes_gallery_page() -> None:
    shell = _shell('/recipes', 'Semiconductor Recipes', 'Scan the domain workflows visually, compare their contracts, then open the recipe that matches the engineering question.')
    from .explorer_gallery import render_reference_gallery
    render_reference_gallery(
        recipe_entries(), section='recipes',
        intro='Choose a semiconductor workflow by engineering question, required data, and the governed composition it combines.',
    )
    _end_shell(shell)


def _render_recipe_support_panel(panel) -> None:
    """Render bounded sample content for non-analytical recipe panels."""
    ui, *_ = _imports()
    kind = panel.kind.value
    if kind == 'records':
        rows = (
            ('LOT-2471','W08','ETCH-021 / CH-3','41.72','Watch'),
            ('LOT-2471','W09','ETCH-021 / CH-3','41.55','Watch'),
            ('LOT-2468','W17','ETCH-014 / CH-2','40.08','Normal'),
            ('LOT-2468','W18','ETCH-014 / CH-2','39.96','Normal'),
        )
        with ui.element('div').classes('cui-workbench-records'):
            with ui.element('div').classes('cui-workbench-records__row cui-workbench-records__head'):
                for value in ('Lot','Wafer','Context','Metric','State'):
                    ui.label(value)
            for row in rows:
                with ui.element('div').classes('cui-workbench-records__row'):
                    for value in row:
                        ui.label(value)
        return
    if kind == 'evidence':
        _render_tree_preview('Evidence sample', 'Working hypothesis', (
            ('Supports', ('Affected/control separation','CH-3 commonality','Spatial edge signature')),
            ('Contradicts', ('Recipe R18 also appears in control',)),
            ('Unknown', ('Incoming material linkage',)),
        ), footer='Sample evidence keeps supporting, contradicting and unknown evidence visibly separate.')
        return
    if kind == 'detail':
        with ui.element('div').classes('cui-workbench-property-grid'):
            for key, value in (('Selected entity','ETCH-021 / CH-3'),('Population','Affected'),('Recipe','ETCH_R18'),('Freshness','2 minutes ago')):
                with ui.element('div').classes('cui-workbench-property-grid__item'):
                    ui.label(key).classes('cui-workbench-card__meta')
                    ui.label(value).classes('cui-workbench-card__title')
        return
    if kind == 'summary':
        with ui.element('div').classes('cui-workbench-kpis'):
            for value, label in (('84','affected'),('215','controls'),('6','evidence items'),('1','contradiction')):
                with ui.element('div').classes('cui-workbench-kpi'):
                    ui.label(value).classes('text-h6')
                    ui.label(label)
        return
    ui.label(panel.description or 'Canonical application support surface').classes('cui-workbench-note')


def _mount_recipe_panel(panel, host) -> None:
    host.clear()
    with host:
        if panel.surface_key:
            from nicegui_base.semiconductor.surfaces import get_semiconductor_surface
            surface = get_semiconductor_surface(panel.surface_key)
            _render_surface_preview(panel.surface_key, surface.category, compact=True)
        else:
            _render_recipe_support_panel(panel)


def recipe_detail_page(recipe_key: str) -> None:
    from nicegui_base.semiconductor.recipes import get_semiconductor_recipe
    try:
        recipe = get_semiconductor_recipe(recipe_key)
    except KeyError:
        _unknown_detail('/recipes', 'Recipe not found', f'No canonical semiconductor recipe is registered as {recipe_key!r}.', '/recipes')
        return

    from nicegui import ui
    from .capability_studio import render_data_dock
    from .data_dock import DataDockModel, DEFAULT_ENGINEERING_SAMPLE
    from .recipe_mapping import RecipeMappingModel, render_recipe_mapping
    entry = next((item for item in recipe_entries() if item.metadata.get('recipe_key') == recipe_key), None)
    if entry is None:
        _unknown_detail('/recipes', 'Recipe not found', f'No Reference Explorer recipe entry is registered as {recipe_key!r}.', '/recipes')
        return

    data = DataDockModel(DEFAULT_ENGINEERING_SAMPLE, sample_name=f'{recipe.application_name} development sample')
    mapping = RecipeMappingModel(recipe_key, data)

    def preview(session) -> None:
        result = mapping.evaluate()
        if mapping.confirmed:
            panel_ids = set(result.available_panels)
            ui.label('Mapped composition').classes('cui-workbench-section-title')
            ui.label(f'{len(result.available_panels)} panels available · {len(result.unavailable_panels)} unavailable with current data.').classes('cui-workbench-note')
        else:
            panel_ids = {panel.panel_id for panel in recipe.panels}
            ui.label('Canonical sample composition').classes('cui-workbench-section-title')
            ui.label('Confirm a Data mapping to restrict this composition to panels supported by your own development dataset.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-workbench-recipe-grid'):
            for panel in recipe.panels:
                available = panel.panel_id in panel_ids
                with ui.element('article').classes('cui-workbench-recipe-panel ' + ('is-unavailable' if not available else '')):
                    with ui.element('div').classes('cui-workbench-card__meta'):
                        ui.label(panel.kind.value)
                        if panel.surface_key:
                            ui.label('•'); ui.label(panel.surface_key)
                    ui.label(panel.title).classes('cui-workbench-card__title')
                    if not available:
                        ui.label('Unavailable: current mapped data does not satisfy this panel’s field requirements.').classes('cui-workbench-note')
                        continue
                    host = ui.element('div').classes('cui-workbench-panel-preview')
                    _mount_recipe_panel(panel, host)

    def interactions(session) -> None:
        if not recipe.interactions:
            ui.label('No cross-panel interaction contract is declared.').classes('cui-workbench-note')
            return
        for interaction in recipe.interactions:
            with ui.element('article').classes('cui-workbench-card'):
                ui.label(interaction.source_panel + ' → ' + ', '.join(interaction.target_panels)).classes('cui-workbench-card__title')
                ui.label('Selections: ' + ', '.join(kind.value for kind in interaction.selection_kinds)).classes('cui-workbench-note')
                ui.label('Crossfilter' if interaction.crossfilter else 'No crossfilter').classes('cui-workbench-chip')
                if interaction.linked_hover:
                    ui.label('Linked hover').classes('cui-workbench-chip')
                if interaction.description:
                    ui.label(interaction.description).classes('cui-workbench-note')

    def data_renderer(session) -> None:
        mapping_host = ui.element('div').classes('cui-recipe-mapping-host')

        def render_mapping_host() -> None:
            mapping_host.clear()
            with mapping_host:
                def confirmed(_model, summary) -> None:
                    session.log(f'Recipe mapping confirmed · {len(summary.available_panels)} panels available')
                    if session.refresh_preview:
                        session.refresh_preview()
                render_recipe_mapping(
                    mapping,
                    on_confirm=confirmed,
                    preview_panel=lambda panel: _mount_recipe_panel(panel, preview_host),
                )

        def data_changed(_model) -> None:
            mapping.confirmed = False
            session.log(f'Data revision {data.snapshot.revision} · recipe mapping requires confirmation')
            render_mapping_host()
            if session.refresh_preview:
                session.refresh_preview()

        render_data_dock(
            data,
            on_change=data_changed,
            mapping_targets=tuple(item.key for item in recipe.field_requirements),
        )
        ui.label('Recipe compatibility').classes('cui-workbench-section-title')
        preview_host = ui.element('div').classes('cui-workbench-panel-preview')
        with preview_host:
            ui.label('Confirm a mapping in the Data tab to inspect a panel with your own source.').classes('cui-workbench-preview-empty')
        render_mapping_host()

    _studio_entry_page(
        entry,
        active_route='/recipes',
        preview_renderer=preview,
        data_renderer=data_renderer,
        interaction_renderer=interactions,
        data_model=data,
    )

def data_page() -> None:
    from .data_table_lab import render_data_table_lab
    shell = _shell('/workbench/data', 'Data & Tables', 'A governed production reference for tables, record management, data exploration and provider-scale grids.')
    render_data_table_lab()
    _end_shell(shell)

def quality_page() -> None:
    ui, *_ = _imports()
    from nicegui_base.version import FRAMEWORK_VERSION
    entries = all_entries()
    stats = coverage()
    from nicegui_base.patterns.registry import PATTERN_REGISTRY
    from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY
    from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY
    canonical_patterns = len(PATTERN_REGISTRY)
    canonical_analytics = len(SEMICONDUCTOR_SURFACE_REGISTRY)
    canonical_recipes = len(SEMICONDUCTOR_RECIPE_REGISTRY)
    previewed_analytics = len(SURFACE_PREVIEW_FAMILIES)
    family_counts = catalog_family_coverage()
    catalog_audit = framework_catalog_audit(entries)
    contract_audit = catalog_contract_audit(entries)
    catalog_total, catalog_visible, catalog_missing = catalog_audit.canonical_total, catalog_audit.visible, catalog_audit.missing
    catalog_duplicates = catalog_audit.duplicates
    catalog_declared, catalog_identified = catalog_audit.declared, catalog_audit.identified
    shell = _shell('/quality', 'Diagnostics', 'Understand runtime health, framework coverage, and the few actions that need attention.')
    with _section('System health', 'A quick answer to whether the installed reference is ready to use.'):
        with ui.element('div').classes('cui-workbench-quality-grid'):
            with ui.element('article').classes('cui-workbench-quality-card'):
                ui.label('Reference Explorer').classes('cui-workbench-card__title')
                ui.label('Healthy').classes('cui-workbench-chip')
                ui.label(f'Candidate {BUILD_ID} · NiceGUI Base {FRAMEWORK_VERSION} · NiceGUI 3.15.0').classes('cui-workbench-note')
            for label, exists, visible, previewed in (
        ('Generic application patterns', canonical_patterns, stats.patterns, canonical_patterns),
        ('Semiconductor analytics', canonical_analytics, stats.analytics, previewed_analytics),
        ('Semiconductor recipes', canonical_recipes, stats.recipes, canonical_recipes),
            ):
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(label).classes('cui-workbench-card__title')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Available').classes('cui-workbench-note')
                        ui.label(str(exists)).classes('cui-workbench-chip')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Discoverable').classes('cui-workbench-note')
                        ui.label(f'{visible} / {exists}').classes('cui-workbench-chip')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Live examples').classes('cui-workbench-note')
                        ui.label(f'{previewed} / {exists}').classes('cui-workbench-chip')
    with _section('Catalog family coverage', 'Every capability family must be backed by at least one discoverable canonical authority entry.'):
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for family in REQUIRED_CATALOG_FAMILIES:
                count = family_counts.get(family, 0)
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(family).classes('cui-workbench-card__title')
                    ui.label(f'{count} discoverable entr{"y" if count == 1 else "ies"}').classes('cui-workbench-chip')
    with _section('Framework coverage', 'Every reusable family is reachable from the Explorer and has a clear live or nonvisual contract.'):
        with ui.element('article').classes('cui-workbench-quality-card'):
            ui.label(f'{catalog_visible} / {catalog_total} canonical catalog records visible').classes('cui-workbench-card__title')
            ui.label(f'Catalog shape: {catalog_identified} identified / {catalog_declared} declared').classes('cui-workbench-note')
            if catalog_missing:
                ui.label(f'{len(catalog_missing)} missing: ' + ', '.join(f'{registry}/{key}' for registry, key in catalog_missing[:8])).classes('cui-workbench-note')
            elif catalog_duplicates:
                ui.label(f'{len(catalog_duplicates)} duplicated: ' + ', '.join(f'{registry}/{key}' for registry, key in catalog_duplicates[:8])).classes('cui-workbench-note')
            else:
                ui.label('No canonical framework-catalog records are hidden or duplicated in the Reference Explorer.').classes('cui-workbench-note')
    with _section('Developer-ready references', 'Live examples and concise contracts are the material engineers copy into applications.'):
        with ui.element('article').classes('cui-workbench-quality-card'):
            ui.label(f'{contract_audit.conforming} / {contract_audit.total} complete').classes('cui-workbench-card__title')
            ui.label('Live examples use registered renderers; nonvisual capabilities declare their explicit contract variant.').classes('cui-workbench-note')
            if contract_audit.issues:
                ui.label('; '.join(contract_audit.issues[:4])).classes('cui-workbench-note')
    with _section('Current source checks'):
        checks = (
            (catalog_declared == EXPECTED_FRAMEWORK_CATALOG_RECORDS and catalog_declared == catalog_identified == catalog_total, f'Generated framework catalog has a stable identity for all {EXPECTED_FRAMEWORK_CATALOG_RECORDS} reviewed records'),
            (catalog_total > 0 and catalog_visible == catalog_total and not catalog_missing and not catalog_duplicates, 'Every packaged canonical framework-catalog record is discoverable exactly once'),
            (all(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES), 'Every required Reference Explorer catalog family contributes discoverable canonical entries'),
            (canonical_patterns == stats.patterns == 10, f'{stats.patterns}/{canonical_patterns} canonical generic application patterns are discoverable'),
            (canonical_analytics == stats.analytics == 58, f'{stats.analytics}/{canonical_analytics} canonical semiconductor analytical surfaces are discoverable'),
            (set(SURFACE_PREVIEW_FAMILIES) == set(SEMICONDUCTOR_SURFACE_REGISTRY), 'Every canonical analytical surface has an exact-key sample preview contract'),
            (canonical_recipes == stats.recipes == 8, f'{stats.recipes}/{canonical_recipes} canonical semiconductor recipes are discoverable'),
            (all(recipe.panels for recipe in SEMICONDUCTOR_RECIPE_REGISTRY.values()), 'Every canonical recipe has a renderable panel composition'),
            (contract_audit.complete, f'{contract_audit.conforming}/{contract_audit.total} catalog entries have complete typed reference contracts'),
            (bool(search('hotelling')), 'Hotelling T² is searchable by name'),
            (any(r.entry.metadata.get('surface_key') == 'fdc_hotelling_t2' for r in search('t2')), 'Hotelling T² is searchable by T2'),
            (any(r.entry.metadata.get('surface_key') == 'fdc_hotelling_t2' for r in search('fdc', limit=100)), 'Hotelling T² is reachable through FDC search'),
            (all(entry.route for entry in all_entries()), 'Every catalog entry has a route/action'),
        )
        for passed, text in checks:
            ui.label(f"{'✓' if passed else '✕'} {text}").classes('cui-workbench-note')
    with ui.element('details').classes('cui-workbench-section cui-diagnostics-advanced'):
        with ui.element('summary').props('tabindex="0"'):
            ui.label('Advanced implementation details').classes('cui-workbench-section-title')
        from .coverage_matrix import render_developer_readiness
        render_developer_readiness(entries)
        ui.label('Registry, packaging, browser, and visual evidence belong here for maintainers; they do not lead normal discovery.').classes('cui-workbench-note')
    from .explorer_performance import render_explorer_performance
    render_explorer_performance()
    _end_shell(shell)


def applications_page() -> None:
    _unified_patterns_compatibility_page()


def full_application_detail_page(application_key: str) -> None:
    from .full_applications import FULL_APPLICATION_REGISTRY, render_full_application

    definition = FULL_APPLICATION_REGISTRY.get(application_key)
    if definition is None:
        _unknown_detail('/applications', 'Application not found', f'No complete reference application is registered as {application_key!r}.', '/applications')
        return
    # The governed PatternPage is the single owner of the application title and
    # description; the outer Reference Explorer shell stays stable on detail routes.
    shell = _shell('/applications', 'Full Applications', 'Open a complete reference composition built from the department pattern and recipe authorities.')
    render_full_application(definition)
    _end_shell(shell)

REFERENCE_PATTERN_ROUTES = {
    '/patterns/dashboard': 'dashboard',
    '/patterns/explorer': 'data_explorer',
    '/patterns/master-detail': 'master_detail',
    '/patterns/crud': 'crud',
    '/patterns/monitoring': 'monitoring',
    '/patterns/search': 'search',
    '/patterns/settings': 'settings',
    '/patterns/wizard': 'wizard',
    '/patterns/comparison': 'comparison',
    '/patterns/analysis': 'analysis_workspace',
}


def _install_workbench_reference_preview(mac_lab) -> None:
    """Add Workbench-owned preview chrome to canonical reference-pattern shells."""
    if getattr(mac_lab, '_nicegui_base_workbench_reference_preview_bridge', False):
        return
    original_reference_shell = mac_lab._reference_shell

    def workbench_reference_shell(route: str):
        shell = original_reference_shell(route)
        pattern_key = REFERENCE_PATTERN_ROUTES.get(route)
        if not pattern_key:
            return shell
        from nicegui import ui
        from nicegui_base.integrations.nicegui_components import Button

        with ui.element('section').classes('cui-studio-header cui-workbench-reference-preview').props(
            'role="region" aria-label="Reference app preview"'
        ):
            with ui.element('div').classes('cui-workbench-card__meta'):
                ui.label('REFERENCE APP PREVIEW')
                ui.label('•')
                ui.label(pattern_key.replace('_', ' ').upper())
            ui.label(pattern_key.replace('_', ' ').title()).classes('cui-workbench-section-title')
            ui.label('Interactive canonical pattern. Explore the real behavior here, then use the same registered pattern from the developer scaffolding CLI.').classes('cui-workbench-note')
            with ui.element('div').classes('cui-workbench-toolbar'):
                Button('Back to Reference Explorer', on_click=lambda: ui.navigate.to('/layouts'))
        return shell

    mac_lab._reference_shell = workbench_reference_shell
    mac_lab._nicegui_base_workbench_reference_preview_bridge = True

def _register_reference_routes() -> None:
    """Mount the established reference routes with Workbench-owned preview chrome."""
    from nicegui import ui
    from nicegui_base.certification import mac_lab
    mac_lab._lab_css()
    _install_workbench_reference_preview(mac_lab)
    for route in mac_lab.ROUTES:
        if route.path in {'/', '/patterns/settings'}:
            continue
        def page_builder(_route=route):
            _route.builder(None)
        page_builder.__name__ = 'workbench_reference_' + (route.path.strip('/').replace('/','_').replace('-','_') or 'overview')
        ui.page(route.path)(page_builder)
    # The former Settings pattern URL remains a safe compatibility alias; it
    # must never replace the normal Explorer shell with a pattern shell.
    ui.page('/patterns/settings')(_settings_compatibility_page)

def register_workbench_pages(*, include_reference: bool = True, root_path: str = '') -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_theme import install_framework_css
    from .explorer_state import EXPLORER_BROWSER_STATE_SCRIPT
    install_framework_css(ui)
    install_workbench_css()
    ui.add_head_html(EXPLORER_BROWSER_STATE_SCRIPT, shared=True)
    root_prefix = '/' + root_path.strip('/') if root_path.strip('/') else ''
    palette_fallback = f'{root_prefix}/?palette=1'
    ui.add_head_html(f"""<script>(function(){{if(window.__niceguiBaseWorkbenchGlobalKeys)return;window.__niceguiBaseWorkbenchGlobalKeys=true;window.__niceguiBaseWorkbenchHome={json.dumps(palette_fallback)};document.addEventListener('keydown',function(e){{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){{e.preventDefault();const id=window.__niceguiBaseWorkbenchCommandTarget;const target=id?getHtmlElement(id):null;if(target){{target.click();}}else{{window.location.href=window.__niceguiBaseWorkbenchHome;}}}}}});}})();</script>""", shared=True)
    ui.page('/')(home_page)
    ui.page('/build')(build_page)
    ui.page('/design')(design_system_page)
    ui.page('/settings')(settings_page)
    ui.page('/catalog')(catalog_page)
    ui.page('/components')(components_page)
    ui.page('/patterns')(patterns_page)
    ui.page('/layouts')(layout_studio_page)
    ui.page('/studio/{entry_key}')(studio_page)
    ui.page('/catalog/component/{component_key}')(component_detail_page)
    ui.page('/catalog/{registry_name}/{entry_key}')(catalog_detail_page)
    ui.page('/analytics')(analytics_gallery_page)
    ui.page('/analytics/{surface_key}')(analytics_detail_page)
    ui.page('/recipes')(recipes_gallery_page)
    ui.page('/applications')(applications_page)
    ui.page('/applications/{application_key}')(full_application_detail_page)
    ui.page('/recipes/{recipe_key}')(recipe_detail_page)
    ui.page('/workbench/data')(data_page)
    ui.page('/quality')(quality_page)
    ui.page('/ai-guide')(ai_guide_page)
    if include_reference:
        _register_reference_routes()


def run_workbench(*, host: str = '127.0.0.1', port: int = 8080, show: bool = False, root_path: str = '') -> None:
    from nicegui import app, ui
    from nicegui_base.diagnostics import HealthCheck, HealthResult, HealthState
    from nicegui_base.integrations.nicegui_runtime import NiceGUIRuntimeAdapter
    from nicegui_base.runtime import ProxyConfig, RuntimeConfig, RuntimeEnvironment
    from nicegui_base.version import FRAMEWORK_VERSION
    from nicegui_base.security import SecurityHeaders
    config = RuntimeConfig(app_name=WORKBENCH_TITLE, app_version=FRAMEWORK_VERSION, environment=RuntimeEnvironment.TEST, host=host, port=port, title=WORKBENCH_TITLE, show_browser=show, reload=False, proxy=ProxyConfig(root_path=root_path))
    runtime = NiceGUIRuntimeAdapter(config, security_headers=SecurityHeaders(frame_options='SAMEORIGIN'))

    def workbench_contract_health():
        try:
            from nicegui_base.patterns.registry import PATTERN_REGISTRY
            stats = coverage()
            entries = all_entries()
            canonical_pattern_keys = {getattr(key, 'value', str(key)) for key in PATTERN_REGISTRY}
            visible_pattern_keys = {entry.metadata.get('pattern_key') for entry in entries if entry.kind is WorkbenchKind.PATTERN}
            analytic_keys = {entry.metadata.get('surface_key') for entry in analytics_entries()}
            recipe_keys = {entry.metadata.get('recipe_key') for entry in recipe_entries()}
            preview_keys = set(SURFACE_PREVIEW_FAMILIES)
            family_counts = catalog_family_coverage()
            catalog_audit = framework_catalog_audit(entries)
            contract_audit = catalog_contract_audit(entries)
            catalog_total, catalog_visible, catalog_missing = catalog_audit.canonical_total, catalog_audit.visible, catalog_audit.missing
            catalog_duplicates = catalog_audit.duplicates
            catalog_declared, catalog_identified = catalog_audit.declared, catalog_audit.identified
            ok = (
                catalog_declared == EXPECTED_FRAMEWORK_CATALOG_RECORDS
                and catalog_declared == catalog_identified == catalog_total
                and catalog_total > 0
                and catalog_visible == catalog_total
                and not catalog_missing
                and not catalog_duplicates
                and stats.patterns == 10
                and len(canonical_pattern_keys) == 10
                and visible_pattern_keys == canonical_pattern_keys
                and stats.analytics == 58
                and stats.recipes == 8
                and len(analytic_keys) == 58
                and len(recipe_keys) == 8
                and analytic_keys == preview_keys
                and all(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES)
                and contract_audit.complete
            )
            covered_families = sum(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES)
            detail = f'catalog={catalog_visible}/{catalog_total} shape={catalog_identified}/{catalog_declared}/{EXPECTED_FRAMEWORK_CATALOG_RECORDS} duplicates={len(catalog_duplicates)} contracts={contract_audit.conforming}/{contract_audit.total} patterns={stats.patterns}/{len(canonical_pattern_keys)} analytics={stats.analytics}/{len(analytic_keys)} recipes={stats.recipes}/{len(recipe_keys)} previews={len(preview_keys)}/{len(analytic_keys)} families={covered_families}/{len(REQUIRED_CATALOG_FAMILIES)}'
            return HealthResult('workbench-contract', HealthState.HEALTHY if ok else HealthState.UNHEALTHY, detail)
        except Exception as exc:
            return HealthResult('workbench-contract', HealthState.UNHEALTHY, f'{type(exc).__name__}: {exc}')

    runtime.health.register(HealthCheck('workbench-contract', workbench_contract_health, critical=False, timeout_seconds=5.0))
    runtime.install_middleware(app)
    runtime.install_operational_endpoints(app)

    @app.get('/_nicegui_base/workbench', include_in_schema=False)
    async def nicegui_base_workbench_identity():
        from fastapi.responses import JSONResponse
        report = await runtime.health.run()
        payload = {
            'product': 'nicegui-base',
            'application': 'workbench',
            'version': FRAMEWORK_VERSION,
            'build_id': BUILD_ID,
            'ready': report.ready,
            'state': report.state.value,
        }
        return JSONResponse(payload, status_code=200 if report.ready else 503)

    register_workbench_pages(root_path=root_path)
    kwargs = config.nicegui_run_kwargs({'NICEGUI_BASE_STORAGE_SECRET': os.environ.get('NICEGUI_BASE_STORAGE_SECRET') or secrets.token_urlsafe(48)})
    ui.run(**kwargs)


__all__ = ['WORKBENCH_TITLE','WORKBENCH_SUBTITLE','reference_entries_for_section','register_workbench_pages','run_workbench','workbench_navigation']
