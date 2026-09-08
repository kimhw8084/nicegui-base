from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Sequence

from .explorer_performance import measure
from .explorer_state import ExplorerState, ExplorerStateStore, MAX_COMPARE
from .preview_catalog import application_asset_key, data_uri, entry_asset_key, primary_asset_key


@dataclass(frozen=True, slots=True)
class IntentSpec:
    title: str
    description: str
    section: str
    route: str
    query: str
    badge: str
    icon: str
    example: str


INTENTS: tuple[IntentSpec, ...] = (
    IntentSpec('Monitor a process', 'Health, trends, limits, alerts and review queues.', 'patterns', '/patterns', 'monitoring', 'MONITOR', 'process', 'Recurring health and exception review'),
    IntentSpec('Investigate an excursion', 'Affected/control evidence, commonality and drill-down.', 'recipes', '/recipes', 'excursion investigation', 'INVESTIGATE', 'excursion', 'Evidence-led root-cause investigation'),
    IntentSpec('Compare tools or populations', 'Aligned distributions, deltas and supporting records.', 'patterns', '/patterns', 'comparison', 'COMPARE', 'split', 'Side-by-side population or tool decisions'),
    IntentSpec('Explore engineering data', 'Filter, inspect, chart and drill into arbitrary records.', 'patterns', '/patterns', 'data explorer', 'EXPLORE', 'table', 'Filter-first record exploration'),
    IntentSpec('Build an operational dashboard', 'KPI hierarchy, trends and exception-focused detail.', 'patterns', '/patterns', 'dashboard', 'DASHBOARD', 'chart-line', 'KPI, trend and exception overview'),
    IntentSpec('Manage records', 'Canonical create, edit, delete and validation anatomy.', 'patterns', '/patterns', 'crud managed records', 'MANAGE', 'edit', 'Validated operational record maintenance'),
    IntentSpec('Review wafer / yield / defects', 'Wafer signatures, Pareto, yield and defect semantics.', 'analytics', '/analytics', 'wafer yield defect', 'WAFER', 'wafer', 'Spatial and yield review'),
    IntentSpec('Analyze SPC', 'Control charts, capability and sequential stability.', 'analytics', '/analytics', 'spc control capability', 'SPC', 'spc', 'Stability and capability decisions'),
    IntentSpec('Review FDC / tool health', 'Traces, fingerprints, events and multivariate health.', 'analytics', '/analytics', 'fdc tool chamber health', 'FDC', 'tool', 'Signal, chamber and event review'),
    IntentSpec('Configure an application', 'Settings, forms, validation and governed state.', 'patterns', '/patterns', 'settings configuration', 'CONFIGURE', 'settings', 'Durable settings and workflow state'),
)


@lru_cache(maxsize=32)
def _intent_authorities(description: str, query: str):
    from nicegui_base.ai.discovery import catalog_search, scaffold_plan
    return scaffold_plan(description), catalog_search(query, limit=8)


PRIMARY_AUTHORITIES = (
    ('Design System', 'Visual tokens, states, density and responsive rules.', '/design', 'design', 'FOUNDATION'),
    ('Components', 'Reusable controls and content primitives with states and code.', '/components', 'components', 'FOUNDATION'),
    ('Data & Tables', 'Schema, table and query-ready data contracts.', '/workbench/data', 'data', 'FOUNDATION'),
    ('Visualizations', 'Scan analytical visuals before opening a detail.', '/analytics', 'analytics', 'FOUNDATION'),
    ('Layouts', 'Desktop, tablet and phone shell anatomy.', '/layouts', 'layouts', 'COMPOSE'),
    ('Application Patterns', 'Canonical application information hierarchies.', '/patterns', 'patterns', 'COMPOSE'),
    ('Semiconductor Recipes', 'Bounded engineering workflows and caveats.', '/recipes', 'recipes', 'DOMAIN'),
    ('Full Applications', 'Production-shaped reference compositions.', '/applications', 'applications', 'DOMAIN'),
    ('AI Development Guide', 'Requirement → authority → scaffold → validation.', '/ai-guide', 'ai-guide', 'DEVELOP'),
)


def _store() -> ExplorerStateStore:
    from nicegui import app
    return ExplorerStateStore(app.storage.user)


def _navigate(route: str, *, section: str | None = None, key: str | None = None) -> None:
    from nicegui import ui
    if section and key:
        _store().add_recent(section, key)
    ui.navigate.to(route)


def _preview_image(asset_key: str | None, *, label: str) -> None:
    from nicegui import ui
    uri = data_uri(asset_key) if asset_key else None
    with ui.element('div').classes('cui-explorer-preview'):
        if uri:
            ui.image(uri).classes('cui-explorer-preview__image').props(
                f'loading="eager" decoding="async" alt="{label} governed preview"'
            )
        else:
            with ui.element('div').classes('cui-explorer-preview__placeholder'):
                ui.label('Live reference available').classes('cui-workbench-note')


def _entry_search(entries: Sequence[Any], query: str) -> tuple[Any, ...]:
    source = tuple(entries)
    text = str(query or '').strip()
    if not text:
        return source
    from .search import search_entries
    return tuple(result.entry for result in measure('catalog_search', lambda: search_entries(source, text, limit=max(1, len(source)))))


def filtered_entries(entries: Sequence[Any], state: ExplorerState) -> tuple[Any, ...]:
    visible = _entry_search(entries, state.query)
    if state.category != 'all':
        visible = tuple(entry for entry in visible if str(getattr(entry, 'category', '') or '') == state.category)
    if state.favorites_only:
        favorite = set(state.favorites)
        visible = tuple(entry for entry in visible if str(entry.key) in favorite)
    return visible


def _comparison(entries: Sequence[Any], state: ExplorerState, section: str, rerender) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button
    lookup = {str(entry.key): entry for entry in entries}
    selected = tuple(lookup[key] for key in state.compare if key in lookup)
    if not selected:
        return
    with ui.element('section').classes('cui-explorer-compare').props('aria-label="Reference comparison"'):
        with ui.element('div').classes('cui-explorer-compare__head'):
            with ui.element('div'):
                ui.label(f'Compare · {len(selected)} / {MAX_COMPARE}').classes('cui-workbench-section-title')
                ui.label('Compare the contract without opening and backing out of each reference.').classes('cui-workbench-note')
            Button('Clear comparison', on_click=lambda: (_store().clear_compare(section), rerender()))
        with ui.element('div').classes('cui-explorer-compare__grid'):
            for entry in selected:
                contract = entry.reference_contract
                with ui.element('article').classes('cui-explorer-compare-card'):
                    _preview_image(entry_asset_key(entry), label=entry.title)
                    ui.label(entry.title).classes('cui-workbench-card__title')
                    ui.label(entry.description).classes('cui-workbench-card__body')
                    for heading, values in (
                        ('Best for', contract.best_for[:2]),
                        ('Requires', contract.requires[:2]),
                        ('Avoid when', contract.avoid_for[:1]),
                    ):
                        ui.label(heading).classes('cui-explorer-compare-card__label')
                        ui.label(' · '.join(values)).classes('cui-workbench-note')
                    Button('Open live reference', on_click=lambda _e=None, e=entry: _navigate(e.route, section=section, key=e.key))


def _gallery_card(entry, *, section: str, state: ExplorerState, rerender) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button

    favorite = str(entry.key) in set(state.favorites)
    compared = str(entry.key) in set(state.compare)
    contract = entry.reference_contract
    with ui.element('article').classes('cui-explorer-card').props(f'data-entry-key="{entry.key}"'):
        with ui.element('div').classes('cui-explorer-card__open').props('role="link" tabindex="0"').on(
            'click', lambda _e=None: _navigate(entry.route, section=section, key=entry.key)
        ).on('keydown.enter', lambda _e=None: _navigate(entry.route, section=section, key=entry.key)):
            _preview_image(entry_asset_key(entry), label=entry.title)
            with ui.element('div').classes('cui-explorer-card__copy'):
                with ui.element('div').classes('cui-workbench-card__meta'):
                    ui.label(entry.category or entry.kind.value)
                    if entry.live_preview:
                        ui.label('• LIVE')
                ui.label(entry.title).classes('cui-workbench-card__title')
                ui.label(entry.description).classes('cui-workbench-card__body')
                if contract.best_for:
                    ui.label('Best for · ' + ' · '.join(contract.best_for[:2])).classes('cui-workbench-note')
        with ui.element('div').classes('cui-explorer-card__actions'):
            Button('Open example', icon='arrow-right', on_click=lambda _e=None: _navigate(entry.route, section=section, key=entry.key))
            Button('★ Saved' if favorite else '☆ Favorite', on_click=lambda _e=None: (_store().toggle_favorite(section, entry.key), rerender()))
            Button('✓ Compare' if compared else 'Compare', on_click=lambda _e=None: (_store().toggle_compare(section, entry.key), rerender()))


def render_reference_gallery(entries: Iterable[Any], *, section: str, intro: str) -> None:
    """Render one visual, stateful gallery over existing canonical registry entries."""
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, SearchInput, Select

    source = tuple(entries)
    store = _store()
    state = store.load(section)
    categories = tuple(sorted({str(entry.category) for entry in source if str(entry.category)}))
    if state.category not in {'all', *categories}:
        state.category = 'all'
        state = store.save(section, state)
    host = ui.element('div').classes('cui-explorer-gallery-host')
    status = ui.label('').classes('cui-workbench-note')

    def persist_and_render() -> None:
        nonlocal state
        state = store.save(section, state)
        render()

    def query_changed(event) -> None:
        state.query = str(getattr(event, 'value', '') or '')
        persist_and_render()

    def category_changed(event) -> None:
        state.category = str(getattr(event, 'value', 'all') or 'all')
        persist_and_render()

    def toggle_favorites() -> None:
        state.favorites_only = not state.favorites_only
        persist_and_render()

    with ui.element('section').classes('cui-explorer-controls').props('aria-label="Explorer filters"'):
        with ui.element('details').classes('cui-explorer-refine'):
            with ui.element('summary').props('tabindex="0"'):
                ui.label('Refine references').classes('cui-workbench-card__meta')
            with ui.element('div').classes('cui-explorer-refine__body'):
                search = SearchInput('Search', value=state.query, placeholder='Name, intent, data, domain, alias…', debounce_ms=120, on_change=query_changed)
                search.element.props(f'data-explorer-search="{section}"')
                Select('Family', {'all': 'All families', **{item: item.replace('_', ' ').title() for item in categories}}, value=state.category if state.category in {'all', *categories} else 'all', clearable=False, on_change=category_changed)
                Button('All references' if state.favorites_only else 'Favorites only', on_click=toggle_favorites)
        ui.label(intro).classes('cui-explorer-controls__hint')

    def render() -> None:
        nonlocal state
        state = store.load(section)
        host.clear()
        visible = filtered_entries(source, state)
        status.set_text(f'{len(visible)} of {len(source)} visible · {len(state.favorites)} saved · {len(state.compare)} comparing')
        with host:
            _comparison(source, state, section, render)
            if not visible:
                with ui.element('section').classes('cui-workbench-preview-empty'):
                    ui.label('No governed reference matches the current search/filter. Clear the filter or try an engineering intent.')
                return
            with ui.element('div').classes('cui-explorer-gallery-grid').props(f'data-explorer-section="{section}"'):
                for entry in visible:
                    _gallery_card(entry, section=section, state=state, rerender=render)

    render()


def _authority_card(title: str, description: str, route: str, asset: str, badge: str) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button
    with ui.element('article').classes('cui-explorer-authority-card'):
        _preview_image(primary_asset_key(asset), label=title)
        ui.label(badge.title()).classes('cui-workbench-card__meta')
        ui.label(title).classes('cui-workbench-card__title')
        ui.label(description).classes('cui-workbench-card__body')
        Button('Open reference', icon='arrow-right', on_click=lambda: ui.navigate.to(route))


def render_start_here(stats) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, SearchInput
    from nicegui_base.visual import render_icon_svg

    store = _store()
    with ui.element('section').classes('cui-explorer-start-hero'):
        with ui.element('div').classes('cui-explorer-start-hero__copy'):
            ui.label('NICEGUI BASE · DEPARTMENT STANDARD').classes('cui-workbench-eyebrow')
            ui.label('What are you building?').classes('cui-workbench-title')
            ui.label('Start from intent. NiceGUI Base will lead you to the governed pattern, layout, visualization, component, recipe and scaffold instead of making you browse hundreds of references one by one.').classes('cui-workbench-subtitle')
        with ui.element('div').classes('cui-explorer-start-hero__metrics'):
            metrics = (
                (stats.patterns, 'Patterns', 'Information hierarchy and workflow structure for complete pages.'),
                (stats.analytics, 'Analytics', 'Governed visualization and analysis surfaces for engineering questions.'),
                (stats.components, 'Components', 'Reusable controls, content primitives, and state behavior.'),
                (stats.recipes, 'Recipes', 'Semiconductor-domain compositions that combine the authorities.'),
            )
            for value, label, help_text in metrics:
                with ui.element('div').classes('cui-workbench-kpi').props(f'tabindex="0" title="{help_text}" aria-label="{label}: {help_text}"'):
                    ui.label(str(value)).classes('text-h5')
                    ui.label(label)

    ui.label('Choose an intent').classes('cui-workbench-section-title')
    ui.label('See the recommended pattern, recipe, scaffold, and related governed references before leaving this page.').classes('cui-workbench-note')
    recommendation_host = ui.element('div').classes('cui-explorer-intent-recommendation-host')

    def show_intent(item: IntentSpec) -> None:
        recommendation_host.clear()
        plan, matches = measure('intent_recommendation', lambda: _intent_authorities(item.description, item.query))
        with recommendation_host:
            with ui.element('section').classes('cui-explorer-intent-recommendation').props('aria-live=polite'):
                with ui.element('div').classes('cui-explorer-intent-recommendation__head'):
                    with ui.element('div'):
                        ui.label(item.title).classes('cui-workbench-section-title')
                        ui.label(item.description).classes('cui-workbench-note')
                    ui.label(f'Pattern · {plan.pattern.replace("_", " ").title()}').classes('cui-workbench-chip')
                    if plan.recipe:
                        ui.label(f'Recipe · {plan.recipe}').classes('cui-workbench-chip')
                    Button('Clear recommendation', icon='close', on_click=lambda: recommendation_host.clear())
                with ui.element('div').classes('cui-explorer-intent-recommendation__body'):
                    with ui.element('article').classes('cui-explorer-intent-plan'):
                        ui.label('Recommended scaffold').classes('cui-explorer-compare-card__label')
                        ui.label(plan.recipe_command or plan.pattern_command).classes('cui-explorer-command')
                        ui.label('Domain/data logic stays in the generated application services and repositories.').classes('cui-workbench-note')
                    with ui.element('div').classes('cui-explorer-intent-matches'):
                        for match in matches[:6]:
                            with ui.element('article').classes('cui-explorer-intent-match'):
                                ui.label(match.kind.upper()).classes('cui-workbench-card__meta')
                                ui.label(match.title).classes('cui-workbench-card__title')
                                if match.best_for:
                                    ui.label('Best for · ' + ' · '.join(match.best_for[:2])).classes('cui-workbench-note')
                                Button('Open example', icon='arrow-right', on_click=lambda _e=None, route=match.route: ui.navigate.to(route))
                def explore_all(_e=None):
                    store.prime(item.section, query=item.query)
                    ui.navigate.to(item.route)
                Button('View matching references', icon='arrow-right', on_click=explore_all)

    with ui.element('div').classes('cui-explorer-intent-grid'):
        for intent in INTENTS:
            with ui.element('article').classes('cui-explorer-intent-card'):
                html = getattr(ui, 'html', None)
                if callable(html):
                    html(render_icon_svg(intent.icon, size='md', label=intent.title), sanitize=False).classes('cui-explorer-intent-card__icon')
                else:
                    with ui.element('span').classes('cui-explorer-intent-card__icon').props('aria-hidden="true"'):
                        ui.label(intent.badge[:1])
                ui.label(intent.badge.title()).classes('cui-workbench-card__meta')
                ui.label(intent.title).classes('cui-workbench-card__title')
                ui.label(intent.description).classes('cui-workbench-card__body')
                ui.label(intent.example).classes('cui-workbench-note')
                Button('View recommendation', icon='arrow-right', on_click=lambda _e=None, item=intent: show_intent(item))

    ui.label('Explore the authority').classes('cui-workbench-section-title')
    ui.label('Visual previews let you understand the available standard before opening individual detail pages.').classes('cui-workbench-note')
    with ui.element('div').classes('cui-explorer-authority-grid'):
        for item in PRIMARY_AUTHORITIES:
            _authority_card(*item)

    recent_keys = []
    for section in ('components', 'analytics', 'patterns', 'recipes'):
        recent_keys.extend((section, key) for key in store.load(section).recents[:3])
    if recent_keys:
        from .catalog import all_entries
        lookup = {entry.key: entry for entry in all_entries()}
        ui.label('Recently viewed').classes('cui-workbench-section-title')
        with ui.element('div').classes('cui-explorer-recent-row'):
            shown = set()
            for section, key in recent_keys:
                if key in shown or key not in lookup:
                    continue
                shown.add(key)
                entry = lookup[key]
                Button(entry.title, on_click=lambda _e=None, e=entry, s=section: _navigate(e.route, section=s, key=e.key))
                if len(shown) >= 6:
                    break


def render_application_gallery(entries: Iterable[Any]) -> None:
    from nicegui import app, ui
    from nicegui_base.integrations.nicegui_components import Button
    entries = tuple(entries)
    storage_key = 'nicegui_base_full_app_favorites_v1'
    raw = app.storage.user.get(storage_key, ())
    favorites = list(dict.fromkeys(str(v) for v in raw if str(v))) if isinstance(raw, (list, tuple)) else []

    def toggle(key: str) -> None:
        if key in favorites:
            favorites.remove(key)
        else:
            favorites.insert(0, key)
        app.storage.user[storage_key] = list(favorites)
        render()

    host = ui.element('div').classes('cui-explorer-gallery-host')
    def render() -> None:
        host.clear()
        with host:
            with ui.element('div').classes('cui-explorer-gallery-grid cui-explorer-gallery-grid--apps'):
                for entry in entries:
                    with ui.element('article').classes('cui-explorer-card cui-full-app-showcase').props(f'data-application-key="{entry.key}"'):
                        _preview_image(application_asset_key(entry.key), label=entry.title)
                        ui.label(entry.pattern_key.replace('_', ' ').upper()).classes('cui-workbench-card__meta')
                        ui.label(entry.title).classes('cui-workbench-card__title')
                        ui.label(entry.description).classes('cui-workbench-card__body')
                        ui.label(entry.question).classes('cui-workbench-note')
                        with ui.element('div').classes('cui-full-app-showcase__facets'):
                            for facet in entry.domain_facets:
                                ui.label(facet).classes('cui-workbench-chip')
                        ui.label('Demonstrates · ' + ' · '.join(entry.composition_apis[:4])).classes('cui-workbench-note')
                        with ui.element('details').classes('cui-full-app-showcase__architecture'):
                            with ui.element('summary').props('tabindex="0"'):
                                ui.label('View architecture').classes('cui-workbench-card__meta')
                            ui.label(f'Pattern · {entry.pattern_key.replace("_", " ").title()}').classes('cui-workbench-note')
                            ui.label(f'Primary governed analysis · {entry.primary_surface_key.replace("_", " ").title()}').classes('cui-workbench-note')
                            ui.label('Fixture · ' + str(entry.fixture_signature[1]) + ' representative records').classes('cui-workbench-note')
                        with ui.element('div').classes('cui-explorer-card__actions'):
                            Button('Open live app', icon='arrow-right', on_click=lambda _e=None, route=entry.route: ui.navigate.to(route))
                            Button(
                                'View architecture', icon='code',
                                on_click=lambda _e=None, route=entry.route: ui.navigate.to(route),
                            )
                            Button('★ Saved' if entry.key in favorites else '☆ Favorite', on_click=lambda _e=None, key=entry.key: toggle(key))
    render()


__all__ = ['INTENTS', 'filtered_entries', 'render_application_gallery', 'render_reference_gallery', 'render_start_here']
