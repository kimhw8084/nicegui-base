from __future__ import annotations

import json
import math
from typing import Any, Callable

from .catalog import EXPECTED_FRAMEWORK_CATALOG_RECORDS, REQUIRED_CATALOG_FAMILIES, all_entries, analytics_entries, catalog_family, catalog_family_coverage, coverage, framework_catalog_audit, recipe_entries, search
from .models import WorkbenchEntry, WorkbenchKind
from .workbench_css import install_workbench_css

WORKBENCH_TITLE = 'NiceGUI Base Workbench'
WORKBENCH_SUBTITLE = 'Find the right standard, understand it, and open a governed live example.'


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



def _display_control_bar() -> Any:
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
        ui.run_javascript(f"document.documentElement.dataset.theme={value!r};try{{localStorage.setItem(\'nicegui_base_theme\',{value!r});localStorage.setItem(\'cui_lab_theme\',{value!r});}}catch(_){{}}")
        if value in {'light', 'dark'}:
            apply_all_chart_themes(value)

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

    trigger = _standard_button('Preferences', classes='cui-workbench-preferences-trigger')
    trigger.props('aria-label="Open display preferences"')
    with trigger:
        with ui.menu().props('anchor="bottom left" self="top left"'):
            with ui.element('div').classes('cui-workbench-display-controls').props(
                'role="group" aria-label="Workbench display preferences"'
            ):
                ui.label('Theme').classes('cui-workbench-display-controls__label')
                SegmentedControl({'system': 'System', 'light': 'Light', 'dark': 'Dark'}, value=theme, on_change=theme_changed)
                ui.label('Density').classes('cui-workbench-display-controls__label')
                SegmentedControl({'comfortable': 'Comfort', 'compact': 'Compact', 'dense': 'Dense'}, value=density, on_change=density_changed)
                ui.label('Motion').classes('cui-workbench-display-controls__label')
                SegmentedControl({'normal': 'Normal', 'reduced': 'Reduced'}, value=motion, on_change=motion_changed)
    return trigger

def workbench_navigation():
    _, _, _, NavigationModel, NavItem, NavSection, Icons = _imports()
    return NavigationModel((
        NavSection('workbench', 'WORKBENCH', (
            NavItem('workbench_home', 'Home', '/', Icons.HOME),
            NavItem('workbench_build', 'Build', '/build', Icons.FORWARD),
            NavItem('workbench_catalog', 'Catalog', '/catalog', Icons.GRID),
            NavItem('workbench_layouts', 'Layouts', '/layouts', Icons.GRID),
            NavItem('workbench_recipes', 'Recipes', '/recipes', Icons.FILE),
            NavItem('workbench_data', 'Data', '/workbench/data', Icons.TABLE),
            NavItem('workbench_quality', 'Quality', '/quality', Icons.DIAGNOSTICS),
        )),
    ))


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
        ('workbench:home','Home','/','Workbench','home start launch'),
        ('workbench:build','Build','/build','Workbench','build create app starter'),
        ('workbench:catalog','Catalog','/catalog','Workbench','catalog components patterns standards'),
        ('workbench:layouts','Layouts & Shells','/layouts','Workbench','layouts shells patterns responsive page composition'),
        ('workbench:analytics','Analytics Studio','/analytics','Workbench','analytics semiconductor spc fdc wafer rca'),
        ('workbench:recipes','Recipes','/recipes','Workbench','recipes semiconductor application starters'),
        ('workbench:data','Data','/workbench/data','Workbench','data table explorer schema'),
        ('workbench:quality','Quality','/quality','Workbench','quality discoverability coverage'),
    )
    for key, label, route, group, words in top_level:
        registry.register(Command(key, label, lambda route=route: ui.navigate.to(route), keywords=tuple(words.split()), group=group))
    from .project_codegen import is_composable_entry
    from .project_state import queue_entry, set_project_pattern
    for entry in all_entries():
        registry.register(Command(
            f'entry:{entry.key}', entry.title, lambda route=entry.route: ui.navigate.to(route),
            keywords=_command_keywords(entry),
            group=entry.kind.value.title(), description=entry.description,
        ))
        if is_composable_entry(entry):
            registry.register(Command(
                f'project:add:{entry.key}', f'Add to Project · {entry.title}', lambda key=entry.key: (queue_entry(key), ui.navigate.to('/build')),
                keywords=('add','project','builder',*_command_keywords(entry)),
                group='Project', description='Queue this canonical capability and open the current Builder project.',
            ))
        elif entry.kind is WorkbenchKind.PATTERN and entry.metadata.get('pattern_key'):
            registry.register(Command(
                f'project:pattern:{entry.key}', f'Use Pattern · {entry.title}', lambda key=str(entry.metadata.get('pattern_key')): (set_project_pattern(key), ui.navigate.to('/build')),
                keywords=('use','pattern','layout','shell','project',*_command_keywords(entry)),
                group='Project', description='Use this canonical application pattern for the current Builder project.',
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
    shell = AppShell(
        'NiceGUI Base', workbench_navigation(), active_route=route,
        environment='WORKBENCH', subtitle='Golden-standard application framework',
        greeting='Build from the standard', user_name='Engineer', user_initials='EN',
        on_settings=lambda: ui.navigate.to('/patterns/settings'), on_about=None,
        owner='NiceGUI Base', on_support=lambda: ui.navigate.to('/catalog'),
        on_feedback=lambda: ui.navigate.to('/quality'), on_docs=lambda: ui.navigate.to('/catalog'),
    )
    shell.__enter__()
    # AppShell already owns the document's single main landmark. Keep the Workbench
    # page as content inside that landmark rather than nesting a second <main>.
    page = ui.element('div').classes('cui-page cui-page--wide cui-workbench-page')
    page.__enter__()
    PageHeader(title, description)
    with ui.element('div').classes('cui-workbench-toolbar cui-workbench-global-tools').props(
        'role="toolbar" aria-label="Workbench global tools"'
    ):
        _install_command_palette(ui)
        _display_control_bar()
    shell._workbench_page = page
    return shell


def _end_shell(shell) -> None:
    page = getattr(shell, '_workbench_page', None)
    if page is not None:
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
    ui, *_ = _imports()
    stats = coverage()
    shell = _shell('/', 'Workbench', 'Start with the application outcome; search the standard only when you need a specific capability.')
    with ui.element('section').classes('cui-workbench-hero'):
        with ui.element('div'):
            ui.label('NICEGUI BASE · 3.0.0a8').classes('cui-workbench-eyebrow')
            ui.label('What are you building?').classes('cui-workbench-title')
            ui.label('Describe the outcome in Builder. NiceGUI Base recommends the application structure, then guides data, composition, review, and generation in order.').classes('cui-workbench-subtitle')
            with ui.element('div').classes('cui-workbench-toolbar'):
                _standard_button('Start with your goal', on_click=lambda: ui.navigate.to('/build'), primary=True)
                ui.label('Need a specific standard instead? Use Search or ⌘K / Ctrl+K.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-workbench-kpis'):
            for value, label in ((stats.analytics, 'analytics'), (stats.recipes, 'recipes'), (stats.patterns, 'app patterns'), (stats.components, 'core components')):
                with ui.element('div').classes('cui-workbench-kpi'):
                    ui.label(str(value)).classes('text-h5')
                    ui.label(label)

    from .project_state import project_snapshot, render_home_project_resume
    project = project_snapshot()
    if project.get('goal') or project.get('pattern_key') or project.get('queued_entry_keys') or project.get('placements'):
        render_home_project_resume()

    with _section('Common starting points', 'Use these only when the application shape is already obvious; otherwise start with your goal and let Builder recommend it.'):
        with ui.element('div').classes('cui-workbench-grid'):
            pattern_routes = {str(item.metadata.get('pattern_key')): item.route for item in all_entries() if item.kind is WorkbenchKind.PATTERN}
            for item in (
                ('Monitoring', 'Health, alerts, KPIs and periodic refresh.', pattern_routes.get('monitoring','/catalog'), 'PATTERN'),
                ('Investigation', 'Affected/control evidence with context and drill-down.', '/recipes/rca-cockpit', 'ENGINEERING'),
                ('Data Explorer', 'Filtering, records, analytics and detail.', pattern_routes.get('data_explorer','/catalog'), 'PATTERN'),
                ('Managed Records', 'Search, create, inspect and edit governed records.', pattern_routes.get('crud','/catalog'), 'PATTERN'),
            ):
                _action_card(*item)

    with _section('Explore the standard', 'Secondary paths for engineers who already know which framework area they need.'):
        with ui.element('div').classes('cui-workbench-grid cui-workbench-grid--3'):
            _action_card('Data Workspace', 'Paste, upload, inspect, map, and edit development data.', '/workbench/data', 'DATA')
            _action_card('Catalog', 'Find the governed component, pattern, analytic, or framework capability.', '/catalog', 'CATALOG')
            _action_card('Recipes', 'Open complete semiconductor application compositions.', '/recipes', 'RECIPES')
    _end_shell(shell)


def build_page() -> None:
    from .builder import render_builder
    shell = _shell('/build', 'Build', 'Goal → Recommendation → Data → Compose → Review → Generate, with one guided decision at a time.')
    render_builder()
    _end_shell(shell)


def layout_studio_page() -> None:
    from .layout_studio import render_layout_studio
    shell = _shell('/layouts', 'Layouts & Shells', 'Canonical application patterns, real slots, and responsive behavior before individual component choices.')
    render_layout_studio()
    _end_shell(shell)


def catalog_page() -> None:
    ui, *_ = _imports()
    entries = all_entries()
    shell = _shell('/catalog', 'Catalog', 'One discoverable inventory over canonical NiceGUI Base registries, grouped by the job each capability solves.')
    host = None

    def render(kind: str = 'all', family: str = 'all', query: str = '') -> None:
        if host is None:
            return
        host.clear()
        if query.strip():
            visible = tuple(result.entry for result in search(query, limit=300))
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
                ui.label(f'{len(entries)} canonical Workbench entries are searchable. Choose a family or search to inspect individual capabilities.').classes('cui-workbench-note')
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

    state = {'kind': 'all', 'family': 'all', 'query': ''}
    family_control = None

    def choose_family(name: str) -> None:
        state['family'] = name
        if family_control is not None and hasattr(family_control, 'set_value'):
            family_control.set_value(name)
        render(state['kind'], state['family'], state['query'])

    def query_changed(e) -> None:
        state['query'] = str(e.value or '')
        render(state['kind'], state['family'], state['query'])
    def kind_changed(e) -> None:
        state['kind'] = str(e.value or 'all')
        render(state['kind'], state['family'], state['query'])
    def family_changed(e) -> None:
        state['family'] = str(e.value or 'all')
        render(state['kind'], state['family'], state['query'])

    with ui.element('div').classes('cui-workbench-toolbar'):
        _standard_search('Search catalog', placeholder='Component, pattern, analytic, recipe, standard…', on_change=query_changed)
        _standard_select('Type', {'all':'All','component':'Components','pattern':'Patterns','analytic':'Analytics','recipe':'Recipes','reference':'Framework'}, value='all', on_change=kind_changed)
        family_options = {'all': 'All families', **{family: family.title() for family in REQUIRED_CATALOG_FAMILIES}}
        family_control = _standard_select('Family', family_options, value='all', on_change=family_changed)
        _standard_button('Analytics Studio', on_click=lambda: ui.navigate.to('/analytics'))
    host = ui.element('div').classes('cui-workbench-catalog-results')
    render()
    _end_shell(shell)



def _unknown_detail(active_route: str, title: str, message: str, back_route: str) -> None:
    ui, *_ = _imports()
    shell = _shell(active_route, title, message)
    with ui.element('section').classes('cui-workbench-preview cui-workbench-not-found'):
        ui.label('Nothing was changed or inferred from this URL.').classes('cui-workbench-note')
        _standard_button('Back to Workbench', on_click=lambda: ui.navigate.to(back_route), primary=True)
    _end_shell(shell)


def _studio_entry_page(entry: WorkbenchEntry, *, active_route: str = '/catalog', preview_renderer=None, data_renderer=None, interaction_renderer=None, data_model=None) -> None:
    from .capability_studio import render_capability_studio
    shell = _shell(active_route, 'Capability Studio', 'Evaluate the canonical capability with one consistent development workflow.')
    render_capability_studio(
        entry, preview_renderer=preview_renderer, data_renderer=data_renderer,
        interaction_renderer=interaction_renderer, data_model=data_model, active_route=active_route,
    )
    _end_shell(shell)


def studio_page(entry_key: str) -> None:
    from urllib.parse import unquote
    decoded = unquote(entry_key)
    entry = next((item for item in all_entries() if item.key == decoded), None)
    if entry is None:
        _unknown_detail('/catalog', 'Capability not found', f'No canonical Workbench capability is registered as {decoded!r}.', '/catalog')
        return
    _studio_entry_page(entry)


def component_detail_page(component_key: str) -> None:
    entry = next((item for item in all_entries() if item.metadata.get('component_key') == component_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Component not found', f'No canonical component is registered as {component_key!r}.', '/catalog')
        return
    _studio_entry_page(entry)

def catalog_detail_page(registry_name: str, entry_key: str) -> None:
    entry = next((item for item in all_entries() if item.metadata.get('registry_name') == registry_name and item.metadata.get('registry_key') == entry_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Catalog entry not found', f'No canonical catalog entry is registered as {registry_name}/{entry_key}.', '/catalog')
        return
    _studio_entry_page(entry)

def analytics_gallery_page() -> None:
    ui, *_ = _imports()
    entries = analytics_entries()
    shell = _shell('/catalog', 'Analytics Studio', 'All 58 canonical semiconductor analytical surfaces, grouped by the registry taxonomy.')
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.category] = counts.get(entry.category, 0) + 1
    with ui.element('div').classes('cui-workbench-toolbar'):
        ui.label(f'{len(entries)} / 58 visible').classes('cui-workbench-chip')
        for category, count in sorted(counts.items()):
            ui.label(f'{category.upper()} · {count}').classes('cui-workbench-chip')
    for category in ('spc','capability','wafer','fdc','rca','yield','reliability','doe'):
        group = tuple(entry for entry in entries if entry.category == category)
        with _section(category.upper(), f'{len(group)} canonical surfaces'):
            with ui.element('div').classes('cui-workbench-grid'):
                for entry in group:
                    _card(entry)
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


def _render_surface_preview(surface_key: str, category: str, *, compact: bool = False) -> None:
    """Render a truthful sample for every canonical semiconductor surface.

    The Workbench does not create another analytical engine. These are bounded sample
    renderings using existing NiceGUI Base visualization primitives and the canonical
    surface identity. The exact surface key chooses the visual grammar so distinct
    analytics no longer collapse into one category-level placeholder.
    """
    from nicegui_base.integrations.nicegui_visualization import (
        BarChart, BoxPlot, ChamberFingerprintMatrix, CommonalityMatrix, ControlChart,
        DistributionPanel, Heatmap, Histogram, LineChart, ParetoChart, RadialProfilePlot,
        ScatterChart, WaferComparisonMap, WaferMap,
    )
    from nicegui_base.visualization import AxisSpec, AxisType, SeriesSpec, SpecLimits, WaferPoint

    family = SURFACE_PREVIEW_FAMILIES.get(surface_key)
    if family is None:
        raise KeyError(f'No Workbench preview family registered for {surface_key!r}')
    title = 'Sample preview' if compact else 'Live governed sample preview'
    runs = tuple(f'R{i:02d}' for i in range(1, 13))

    # SPC: keep the governed control-chart shell but make the sample statistic match the chart family.
    if surface_key in {'spc_i_mr','spc_xbar_r','spc_xbar_s','spc_ewma','spc_cusum'}:
        values = {
            'spc_i_mr': (39.8,40.0,39.9,40.3,40.5,40.9,41.2,41.0,40.7,40.9,41.3,41.5),
            'spc_xbar_r': (39.9,40.1,40.0,40.2,40.4,40.3,40.6,40.5,40.7,40.9,41.0,41.1),
            'spc_xbar_s': (40.0,39.9,40.1,40.15,40.22,40.28,40.35,40.41,40.50,40.63,40.71,40.82),
            'spc_ewma': (39.9,39.94,39.98,40.04,40.11,40.20,40.31,40.42,40.55,40.67,40.79,40.91),
            'spc_cusum': (0.0,.05,.08,.16,.28,.44,.63,.84,1.08,1.34,1.63,1.95),
        }[surface_key]
        limits = SpecLimits(lower=-.4, upper=2.2, target=0.0) if surface_key == 'spc_cusum' else SpecLimits(lower=38.0, upper=42.0, target=40.0)
        label = {'spc_i_mr':'Individual','spc_xbar_r':'X̄','spc_xbar_s':'X̄','spc_ewma':'EWMA','spc_cusum':'CUSUM'}[surface_key]
        ControlChart(title, (SeriesSpec(surface_key, label, values),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=runs), spec_limits=limits)
        return
    if surface_key in {'spc_p','spc_np','spc_c','spc_u'}:
        values = {
            'spc_p': (.021,.018,.024,.019,.027,.031,.025,.029,.034,.041,.036,.033),
            'spc_np': (4,3,5,4,6,7,5,6,8,10,8,7),
            'spc_c': (2,4,3,5,4,6,5,7,9,8,10,7),
            'spc_u': (.18,.21,.16,.24,.20,.27,.25,.31,.35,.33,.39,.30),
        }[surface_key]
        labels = {'spc_p':'Nonconforming proportion','spc_np':'Nonconforming count','spc_c':'Defect count','spc_u':'Defects / unit'}
        ControlChart(title, (SeriesSpec(surface_key, labels[surface_key], values),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=runs))
        return

    # Capability/distribution diagnostics.
    if surface_key == 'capability_histogram':
        Histogram(title, (SeriesSpec('count','Count',(2,5,9,15,22,19,12,7,3)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38','38.5','39','39.5','40','40.5','41','41.5','42')))
        return
    if surface_key == 'qq_probability':
        points = tuple((q, q + (.10 * math.sin(q * 1.7))) for q in (-2.0,-1.5,-1.0,-.5,0,.5,1.0,1.5,2.0))
        ScatterChart(title, (SeriesSpec('qq','Observed vs theoretical',points),))
        return
    if surface_key == 'ecdf':
        xs = ('38.4','38.8','39.2','39.6','40.0','40.4','40.8','41.2','41.6')
        LineChart(title, (SeriesSpec('ecdf','Cumulative probability',(.03,.08,.17,.31,.49,.68,.82,.93,.985)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=xs))
        return
    if surface_key == 'box_distribution':
        BoxPlot(title, (SeriesSpec('box','CD',((38.4,39.2,40.0,40.8,41.7),(38.8,39.5,40.2,41.0,42.1),(39.0,39.6,40.1,40.6,41.3))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Control','Affected','Post-PM')))
        return
    if surface_key == 'violin_distribution':
        DistributionPanel(title, (SeriesSpec('shape','Density',(1,3,7,14,21,24,18,11,5,2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38.0','38.4','38.8','39.2','39.6','40.0','40.4','40.8','41.2','41.6')))
        return
    if surface_key == 'ridge_distribution':
        LineChart(title, (
            SeriesSpec('ch1','CH-1',(0,1,4,10,15,10,4,1,0),smooth=True),
            SeriesSpec('ch2','CH-2',(0,0,2,7,14,13,7,2,0),smooth=True),
            SeriesSpec('ch3','CH-3',(0,0,1,3,8,14,12,6,2),smooth=True),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38','38.5','39','39.5','40','40.5','41','41.5','42')))
        return

    # Wafer/spatial analytics.
    if surface_key == 'wafer_continuous':
        WaferMap(title, _wafer_points())
        return
    if surface_key == 'wafer_categorical':
        WaferMap(title, _wafer_points(categorical=True))
        return
    if surface_key == 'wafer_defect':
        WaferMap(title, _wafer_points(defects='sparse'))
        return
    if surface_key == 'wafer_defect_clusters':
        WaferMap(title, _wafer_points(defects='clusters'))
        return
    if surface_key == 'wafer_delta':
        affected = _wafer_points(delta=.45)
        control = _wafer_points(delta=-.35)
        delta_points = []
        for a, c in zip(affected, control, strict=True):
            delta = round(float(a.value) - float(c.value), 3)
            delta_points.append(WaferPoint(a.x, a.y, delta, status='watch' if abs(delta) >= .75 else 'normal'))
        WaferMap(title, delta_points)
        return
    if surface_key == 'wafer_comparison':
        WaferComparisonMap(title, _wafer_points(delta=.45), _wafer_points(delta=-.35))
        return
    if surface_key == 'lot_wafer_strip':
        ui, *_ = _imports()
        ui.label(title).classes('cui-workbench-preview-title')
        with ui.element('div').classes('cui-workbench-mini-grid cui-workbench-mini-grid--strip'):
            for index, delta in enumerate((-.42,-.18,0.0,.17,.34), start=1):
                with ui.element('div').classes('cui-workbench-mini-panel'):
                    WaferMap(f'W{index:02d}', _wafer_points(delta=delta))
        return
    if surface_key == 'wafer_small_multiples':
        ui, *_ = _imports()
        ui.label(title).classes('cui-workbench-preview-title')
        with ui.element('div').classes('cui-workbench-mini-grid'):
            for index, delta in enumerate((-.30,.0,.25,.52), start=1):
                with ui.element('div').classes('cui-workbench-mini-panel'):
                    WaferMap(f'Wafer {index:02d}', _wafer_points(delta=delta))
        return
    if surface_key == 'wafer_contour':
        Heatmap(title, (SeriesSpec('field','Smoothed spatial field',tuple((x,y,round(math.sin(x*.65)+math.cos(y*.55)+.15*x,3)) for x in range(7) for y in range(7))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(i-3) for i in range(7))), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(i-3) for i in range(7))))
        return
    if surface_key == 'wafer_radial':
        RadialProfilePlot(title, (39.91,39.94,40.02,40.14,40.35,40.71,41.12,41.53,41.84), (39.85,39.88,39.92,39.96,40.01,40.06,40.12,40.18,40.23), unit='nm')
        return
    if surface_key == 'wafer_center_edge':
        BarChart(title, (SeriesSpec('delta','Mean CD',(40.06,40.18,40.61,41.12)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Center','Middle','Edge','Outer edge')))
        return
    if surface_key == 'wafer_ring':
        BarChart(title, (SeriesSpec('ring','Mean residual',(.02,.08,.21,.48,.83)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('R0','R1','R2','R3','R4')))
        return
    if surface_key == 'wafer_sector':
        BarChart(title, (SeriesSpec('sector','Mean residual',(.12,.20,.58,.91,.44,.18,.09,.15)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('N','NE','E','SE','S','SW','W','NW')))
        return

    # FDC/equipment analytics.
    if surface_key == 'fdc_recipe_step_trace':
        LineChart(title, (SeriesSpec('pressure','Pressure',(1.0,1.1,1.15,1.2,1.65,1.72,1.68,2.10,2.15,1.55,1.45,1.40),smooth=False),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('S1','S1','S2','S2','S3','S3','S3','S4','S4','S5','S5','S5')))
        return
    if surface_key == 'fdc_golden_envelope':
        LineChart(title, (
            SeriesSpec('upper','Golden upper',(1.25,1.32,1.38,1.48,1.61,1.75,1.84,1.90,1.86,1.77,1.62,1.50),smooth=True),
            SeriesSpec('trace','Observed',(1.10,1.18,1.25,1.36,1.54,1.71,1.92,2.06,2.02,1.88,1.70,1.56),smooth=True),
            SeriesSpec('lower','Golden lower',(.95,1.02,1.08,1.18,1.31,1.45,1.54,1.60,1.56,1.47,1.32,1.20),smooth=True),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=runs))
        return
    if surface_key == 'fdc_multi_sensor':
        LineChart(title, (
            SeriesSpec('pressure','Pressure',(1.0,1.2,1.4,1.5,1.7,1.8,1.9,1.8,1.7,1.6,1.5,1.4),smooth=True),
            SeriesSpec('rf','RF bias',(.8,.9,1.0,1.2,1.4,1.6,1.7,1.75,1.65,1.5,1.25,1.0),smooth=True),
            SeriesSpec('flow','Gas flow',(1.15,1.13,1.12,1.10,1.08,1.05,1.03,1.02,1.04,1.08,1.10,1.12),smooth=True),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=runs))
        return
    if surface_key == 'fdc_tool_chamber_compare':
        BarChart(title, (SeriesSpec('score','Normalized deviation',(.12,.18,.84,.23,.16,.31)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('T1/C1','T1/C2','T2/C1','T2/C2','T3/C1','T3/C2')))
        return
    if surface_key == 'fdc_chamber_fingerprint':
        ChamberFingerprintMatrix(title, ('ETCH-014 / CH-2','ETCH-021 / CH-3','ETCH-024 / CH-1','ETCH-031 / CH-4'), ('CD Δ','Pressure','RF bias','PM age','OOS rate'), ((-.18,.06,-.10,.12,.04),(.91,.62,.73,.84,.78),(.11,-.08,.04,.22,.09),(.24,.16,.12,.31,.18)))
        return
    if surface_key == 'fdc_sensor_fingerprint':
        ChamberFingerprintMatrix(title, ('Pressure','RF bias','Gas A','Gas B'), ('Mean Δ','Slope','Noise','Step lag'), ((.15,.08,.12,.04),(.72,.64,.81,.55),(.11,.16,.09,.14),(.38,.42,.29,.31)))
        return
    if surface_key in {'fdc_alarm_overlay','fdc_equipment_event_overlay'}:
        event = 'Alarm' if surface_key == 'fdc_alarm_overlay' else 'PM event'
        LineChart(f'{title} · {event} at R07', (SeriesSpec('sensor','Sensor',(1.0,1.1,1.2,1.3,1.45,1.62,2.15,2.05,1.72,1.55,1.42,1.34),smooth=True),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=runs))
        return
    if surface_key == 'fdc_pca_scores':
        ScatterChart(title, (
            SeriesSpec('baseline','Baseline',((-1.6,-.8),(-1.1,.2),(-.8,-.4),(-.3,.5),(.2,-.2),(.6,.3))),
            SeriesSpec('affected','Affected',((1.3,.9),(1.6,1.4),(2.0,.8),(2.2,1.7),(2.5,1.2))),
        ))
        return
    if surface_key == 'fdc_pca_loadings':
        BarChart(title, (SeriesSpec('loading','PC1 loading',(.72,.61,-.48,.33,.18)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('RF bias','Pressure','Gas A','Temp','Endpoint')))
        return
    if surface_key == 'fdc_hotelling_t2':
        LineChart(title, (SeriesSpec('t2','Hotelling T²',(1.1,1.4,1.2,1.7,1.5,2.0,2.4,3.1,4.8,6.2,7.0,5.9)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=runs), spec_limits=SpecLimits(upper=5.0))
        return
    if surface_key == 'fdc_spe_q':
        LineChart(title, (SeriesSpec('spe','SPE / Q',(.4,.5,.6,.55,.72,.81,1.1,1.4,2.1,2.8,3.4,3.0)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=runs), spec_limits=SpecLimits(upper=2.5))
        return

    # RCA analytics.
    if surface_key == 'rca_affected_control':
        BoxPlot(title, (SeriesSpec('population','Metric',((38.8,39.4,40.0,40.5,41.1),(40.2,40.9,41.6,42.2,43.0))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Control','Affected')))
        return
    if surface_key in {'rca_commonality_ranking','rca_enrichment'}:
        values = (92,78,63,42,25) if surface_key == 'rca_commonality_ranking' else (4.8,3.6,2.9,1.8,1.2)
        label = 'Affected overlap %' if surface_key == 'rca_commonality_ranking' else 'Enrichment ratio'
        BarChart(title, (SeriesSpec('rank',label,values),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('CH-3','ETCH-021','Recipe R18','PM < 3d','Material M4')))
        return
    if surface_key == 'rca_commonality_matrix':
        CommonalityMatrix(title, ('CH-3','Recipe R18','PM < 3 d','Material M4','Route A17'), ('Affected','Matched control','Baseline'), ((.94,.18,.12),(.88,.31,.22),(.76,.15,.19),(.61,.55,.48),(.42,.39,.41)))
        return
    if surface_key == 'rca_contribution_waterfall':
        BarChart(title, (SeriesSpec('delta','Signed contribution',(2.2,-.4,1.1,.6,-.2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('CH-3','Recipe','PM age','Material','Controls')))
        return
    if surface_key == 'rca_correlation_matrix':
        Heatmap(title, (SeriesSpec('corr','Correlation',tuple((x,y,round(math.sin((x+1)*(y+1))*.8,2)) for x in range(5) for y in range(5))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('CD','Pressure','RF','Flow','Temp')), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('CD','Pressure','RF','Flow','Temp')))
        return
    if surface_key == 'rca_evidence_matrix':
        CommonalityMatrix(title, ('CH-3 drift','Recipe mismatch','Material lot','PM recovery'), ('Supports','Contradicts','Unknown'), ((.90,.10,0),(.22,.61,.17),(.35,.18,.47),(.71,.12,.17)))
        return
    if surface_key == 'rca_genealogy_graph':
        _render_flow_preview(title, (('LOT-2471','affected lot'),('ETCH-021 / CH-3','common tool/chamber'),('ETCH_R18','shared recipe'),('WAFER-08','selected evidence')), footer='Genealogy preview preserves entity and route order; it does not imply causality.')
        return
    if surface_key == 'rca_cause_tree':
        _render_tree_preview(title, 'CD excursion', (('Equipment',('CH-3 drift','RF delivery')),('Process',('Recipe step','Pressure response')),('Material',('Incoming lot M4',))), footer='Candidates are hypotheses until evidence corroborates them.')
        return
    if surface_key == 'rca_fault_tree':
        _render_tree_preview(title, 'OOS event', (('OR · Equipment',('Pressure unstable','RF mismatch')),('OR · Process',('Wrong recipe revision','Endpoint shift')),('AND · Detection',('SPC violation','Wafer edge signature'))), footer='Logical decomposition is shown separately from evidence confidence.')
        return
    if surface_key == 'rca_sankey':
        _render_flow_preview(title, (('Affected wafers','84'),('ETCH-021','61'),('CH-3','54'),('Recipe R18','49'),('OOS signature','43')), footer='Process-flow sample shows population narrowing through route/tool context.')
        return

    # Yield, reliability, DOE.
    if surface_key in {'yield_pareto','bin_pareto'}:
        labels = ('Bin 3','Bin 7','Edge','Scratch','Other') if surface_key == 'bin_pareto' else ('CD OOS','Edge defect','Overlay','Scratch','Other')
        ParetoChart(title, labels, (34,22,13,8,5), (41.5,68.3,84.1,93.9,100.0))
        return
    if surface_key == 'yield_waterfall':
        BarChart(title, (SeriesSpec('delta','Yield delta',(-1.8,-.9,-.6,.3,-.2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('CD OOS','Edge','Overlay','Recovery','Other')))
        return
    if surface_key == 'weibull_reliability':
        LineChart(title, (SeriesSpec('failure','Cumulative failure probability',(.01,.02,.04,.07,.12,.19,.29,.42,.57,.71,.83,.91)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('10','20','30','40','50','60','70','80','90','100','110','120')))
        return
    if surface_key == 'doe_main_effects':
        LineChart(title, (
            SeriesSpec('rf','RF bias',(39.6,40.2,41.1)),
            SeriesSpec('pressure','Pressure',(40.8,40.3,39.9)),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Low','Center','High')))
        return
    if surface_key == 'doe_interactions':
        LineChart(title, (
            SeriesSpec('low-pressure','Pressure low',(39.7,40.0,40.4)),
            SeriesSpec('high-pressure','Pressure high',(40.8,40.5,39.9)),
        ), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('RF low','RF center','RF high')))
        return
    if surface_key == 'doe_response_surface':
        Heatmap(title, (SeriesSpec('response','Response',tuple((x,y,round(39.5+.18*x-.12*y+.06*x*y-.035*x*x,3)) for x in range(7) for y in range(6))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('RF-3','RF-2','RF-1','RF0','RF+1','RF+2','RF+3')), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('P-2','P-1','P0','P+1','P+2','P+3')))
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
    _render_surface_preview(surface_key, session.entry.category)


def analytics_detail_page(surface_key: str) -> None:
    entry = next((item for item in analytics_entries() if item.metadata.get('surface_key') == surface_key), None)
    if entry is None:
        _unknown_detail('/catalog', 'Analytical surface not found', f'No canonical analytical surface is registered as {surface_key!r}.', '/analytics')
        return
    _studio_entry_page(entry, active_route='/catalog', preview_renderer=_render_analytic_studio_preview)

def recipes_gallery_page() -> None:
    ui, *_ = _imports()
    entries = recipe_entries()
    shell = _shell('/recipes', 'Recipes', 'Eight governed semiconductor application compositions, visible as first-class starters.')
    with ui.element('div').classes('cui-workbench-toolbar'):
        ui.label(f'{len(entries)} / 8 visible').classes('cui-workbench-chip')
    with ui.element('div').classes('cui-workbench-grid cui-workbench-grid--3'):
        for entry in entries:
            _card(entry)
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
        _unknown_detail('/recipes', 'Recipe not found', f'No Workbench recipe entry is registered as {recipe_key!r}.', '/recipes')
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
                    with host:
                        ui.label('Preview mounts on demand.').classes('cui-workbench-preview-empty')
                    from nicegui_base.integrations.nicegui_components import Button
                    Button('Load sample preview', on_click=lambda panel=panel, host=host: _mount_recipe_panel(panel, host))

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
            ui.label('Choose “Preview panel” in the mapping result to inspect one mapped panel here.').classes('cui-workbench-preview-empty')
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
    from .capability_studio import render_data_dock
    from .data_dock import default_data_dock
    shell = _shell('/workbench/data', 'Data', 'Review and edit development data first; paste or upload only when you need to replace the current dataset.')
    model = default_data_dock()
    render_data_dock(model)
    _end_shell(shell)

def quality_page() -> None:
    ui, *_ = _imports()
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
    catalog_total, catalog_visible, catalog_missing = catalog_audit.canonical_total, catalog_audit.visible, catalog_audit.missing
    catalog_duplicates = catalog_audit.duplicates
    catalog_declared, catalog_identified = catalog_audit.declared, catalog_audit.identified
    shell = _shell('/quality', 'Quality', 'Capability existence and Workbench discoverability are measured separately so hidden framework depth cannot look complete.')
    with _section('Existence vs discoverability', 'Canonical authority counts are compared with what an engineer can actually find and open from the Workbench.'):
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for label, exists, visible, previewed in (
                ('Generic application patterns', canonical_patterns, stats.patterns, canonical_patterns),
                ('Semiconductor analytics', canonical_analytics, stats.analytics, previewed_analytics),
                ('Semiconductor recipes', canonical_recipes, stats.recipes, canonical_recipes),
            ):
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(label).classes('cui-workbench-card__title')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Canonical existence').classes('cui-workbench-note')
                        ui.label(str(exists)).classes('cui-workbench-chip')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Workbench discoverability').classes('cui-workbench-note')
                        ui.label(f'{visible} / {exists}').classes('cui-workbench-chip')
                    with ui.element('div').classes('cui-workbench-quality-row'):
                        ui.label('Sample preview contract').classes('cui-workbench-note')
                        ui.label(f'{previewed} / {exists}').classes('cui-workbench-chip')
    with _section('Catalog family coverage', 'Every plan-level capability family must be backed by at least one discoverable canonical authority entry.'):
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for family in REQUIRED_CATALOG_FAMILIES:
                count = family_counts.get(family, 0)
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(family).classes('cui-workbench-card__title')
                    ui.label(f'{count} discoverable entr{"y" if count == 1 else "ies"}').classes('cui-workbench-chip')
    with _section('Canonical catalog parity', 'Every packaged framework-catalog record must resolve to either a richer Workbench adapter or a canonical fallback entry.'):
        with ui.element('article').classes('cui-workbench-quality-card'):
            ui.label(f'{catalog_visible} / {catalog_total} canonical catalog records visible').classes('cui-workbench-card__title')
            ui.label(f'Catalog shape: {catalog_identified} identified / {catalog_declared} declared').classes('cui-workbench-note')
            if catalog_missing:
                ui.label(f'{len(catalog_missing)} missing: ' + ', '.join(f'{registry}/{key}' for registry, key in catalog_missing[:8])).classes('cui-workbench-note')
            elif catalog_duplicates:
                ui.label(f'{len(catalog_duplicates)} duplicated: ' + ', '.join(f'{registry}/{key}' for registry, key in catalog_duplicates[:8])).classes('cui-workbench-note')
            else:
                ui.label('No canonical framework-catalog records are hidden or duplicated in the Workbench.').classes('cui-workbench-note')
    with _section('Current source checks'):
        checks = (
            (catalog_declared == EXPECTED_FRAMEWORK_CATALOG_RECORDS and catalog_declared == catalog_identified == catalog_total, f'Generated framework catalog has a stable identity for all {EXPECTED_FRAMEWORK_CATALOG_RECORDS} reviewed records'),
            (catalog_total > 0 and catalog_visible == catalog_total and not catalog_missing and not catalog_duplicates, 'Every packaged canonical framework-catalog record is discoverable exactly once'),
            (all(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES), 'Every required Workbench catalog family contributes discoverable canonical entries'),
            (canonical_patterns == stats.patterns == 10, f'{stats.patterns}/{canonical_patterns} canonical generic application patterns are discoverable'),
            (canonical_analytics == stats.analytics == 58, f'{stats.analytics}/{canonical_analytics} canonical semiconductor analytical surfaces are discoverable'),
            (set(SURFACE_PREVIEW_FAMILIES) == set(SEMICONDUCTOR_SURFACE_REGISTRY), 'Every canonical analytical surface has an exact-key sample preview contract'),
            (canonical_recipes == stats.recipes == 8, f'{stats.recipes}/{canonical_recipes} canonical semiconductor recipes are discoverable'),
            (all(recipe.panels for recipe in SEMICONDUCTOR_RECIPE_REGISTRY.values()), 'Every canonical recipe has a renderable panel composition'),
            (bool(search('hotelling')), 'Hotelling T² is searchable by name'),
            (any(r.entry.metadata.get('surface_key') == 'fdc_hotelling_t2' for r in search('t2')), 'Hotelling T² is searchable by T2'),
            (any(r.entry.metadata.get('surface_key') == 'fdc_hotelling_t2' for r in search('fdc', limit=100)), 'Hotelling T² is reachable through FDC search'),
            (all(entry.route for entry in all_entries()), 'Every catalog entry has a route/action'),
        )
        for passed, text in checks:
            ui.label(f"{'✓' if passed else '✕'} {text}").classes('cui-workbench-note')
    from .coverage_matrix import render_developer_readiness
    render_developer_readiness(entries)
    ui.label('Runtime, browser, target-environment, and human visual evidence stay separate from source coverage until actually executed.').classes('cui-workbench-note')
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
        from nicegui_base.integrations.nicegui_components import ActionButton, Button

        def use_in_builder() -> None:
            from .project_state import set_project_pattern
            set_project_pattern(pattern_key)
            ui.navigate.to('/build')

        with ui.element('section').classes('cui-studio-header cui-workbench-reference-preview').props(
            'role="region" aria-label="Reference app preview"'
        ):
            with ui.element('div').classes('cui-workbench-card__meta'):
                ui.label('REFERENCE APP PREVIEW')
                ui.label('•')
                ui.label(pattern_key.replace('_', ' ').upper())
            ui.label(pattern_key.replace('_', ' ').title()).classes('cui-workbench-section-title')
            ui.label('Interactive canonical pattern. Explore the real behavior here, then carry this same governed structure into Builder.').classes('cui-workbench-note')
            with ui.element('div').classes('cui-workbench-toolbar'):
                ActionButton('Use this pattern in Builder', on_click=use_in_builder)
                Button('Back to Workbench', on_click=lambda: ui.navigate.to('/layouts'))
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
        if route.path == '/':
            continue
        def page_builder(_route=route):
            _route.builder(None)
        page_builder.__name__ = 'workbench_reference_' + (route.path.strip('/').replace('/','_').replace('-','_') or 'overview')
        ui.page(route.path)(page_builder)

def register_workbench_pages(*, include_reference: bool = True, root_path: str = '') -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_theme import install_framework_css
    install_framework_css(ui)
    install_workbench_css()
    root_prefix = '/' + root_path.strip('/') if root_path.strip('/') else ''
    palette_fallback = f'{root_prefix}/?palette=1'
    ui.add_head_html(f"""<script>(function(){{if(window.__niceguiBaseWorkbenchGlobalKeys)return;window.__niceguiBaseWorkbenchGlobalKeys=true;window.__niceguiBaseWorkbenchHome={json.dumps(palette_fallback)};document.addEventListener('keydown',function(e){{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){{e.preventDefault();const id=window.__niceguiBaseWorkbenchCommandTarget;const target=id?getHtmlElement(id):null;if(target){{target.click();}}else{{window.location.href=window.__niceguiBaseWorkbenchHome;}}}}}});}})();</script>""", shared=True)
    ui.page('/')(home_page)
    ui.page('/build')(build_page)
    ui.page('/catalog')(catalog_page)
    ui.page('/layouts')(layout_studio_page)
    ui.page('/studio/{entry_key}')(studio_page)
    ui.page('/catalog/component/{component_key}')(component_detail_page)
    ui.page('/catalog/{registry_name}/{entry_key}')(catalog_detail_page)
    ui.page('/analytics')(analytics_gallery_page)
    ui.page('/analytics/{surface_key}')(analytics_detail_page)
    ui.page('/recipes')(recipes_gallery_page)
    ui.page('/recipes/{recipe_key}')(recipe_detail_page)
    ui.page('/workbench/data')(data_page)
    ui.page('/quality')(quality_page)
    if include_reference:
        _register_reference_routes()


def run_workbench(*, host: str = '127.0.0.1', port: int = 8080, show: bool = False, root_path: str = '') -> None:
    from nicegui import app, ui
    from nicegui_base.diagnostics import HealthCheck, HealthResult, HealthState
    from nicegui_base.integrations.nicegui_runtime import NiceGUIRuntimeAdapter
    from nicegui_base.runtime import ProxyConfig, RuntimeConfig, RuntimeEnvironment
    from nicegui_base.version import FRAMEWORK_VERSION
    config = RuntimeConfig(app_name=WORKBENCH_TITLE, app_version=FRAMEWORK_VERSION, environment=RuntimeEnvironment.TEST, host=host, port=port, title=WORKBENCH_TITLE, show_browser=show, reload=False, proxy=ProxyConfig(root_path=root_path))
    runtime = NiceGUIRuntimeAdapter(config)

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
            )
            covered_families = sum(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES)
            detail = f'catalog={catalog_visible}/{catalog_total} shape={catalog_identified}/{catalog_declared}/{EXPECTED_FRAMEWORK_CATALOG_RECORDS} duplicates={len(catalog_duplicates)} patterns={stats.patterns}/{len(canonical_pattern_keys)} analytics={stats.analytics}/{len(analytic_keys)} recipes={stats.recipes}/{len(recipe_keys)} previews={len(preview_keys)}/{len(analytic_keys)} families={covered_families}/{len(REQUIRED_CATALOG_FAMILIES)}'
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
            'ready': report.ready,
            'state': report.state.value,
        }
        return JSONResponse(payload, status_code=200 if report.ready else 503)

    register_workbench_pages(root_path=root_path)
    kwargs = config.nicegui_run_kwargs({'NICEGUI_BASE_STORAGE_SECRET': f'nicegui-base-workbench-v{FRAMEWORK_VERSION}'})
    ui.run(**kwargs)


__all__ = ['WORKBENCH_TITLE','register_workbench_pages','run_workbench','workbench_navigation']
