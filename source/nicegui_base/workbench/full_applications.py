"""Small, runnable full-application compositions for the Reference Explorer."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.patterns.composition import get_application_pattern


@dataclass(frozen=True, slots=True)
class FullApplicationDefinition:
    key: str
    title: str
    description: str
    pattern_key: str
    recipe_key: str
    route: str
    question: str
    fixture: tuple[Mapping[str, Any], ...]
    caveats: tuple[str, ...]
    primary_surface_key: str = 'LineChart'
    domain_facets: tuple[str, ...] = ()
    composition_apis: tuple[str, ...] = (
        'shell', 'page_section', 'filter_bar', 'kpi_strip', 'chart_table_detail', 'inspector', 'state_panel',
    )

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.key, self.title, self.description, self.route, self.question)):
            raise ValueError('full application identity and question must not be empty')
        get_application_pattern(self.pattern_key)
        if not self.recipe_key.strip() or not self.fixture or not self.caveats:
            raise ValueError(f'{self.key}: recipe, fixture and caveats are required')
        if not self.route.startswith('/applications/'):
            raise ValueError(f'{self.key}: full application route must be under /applications/')
        object.__setattr__(self, 'fixture', tuple(dict(row) for row in self.fixture))
        object.__setattr__(self, 'caveats', tuple(self.caveats))
        object.__setattr__(self, 'domain_facets', tuple(self.domain_facets))

    @property
    def fixture_signature(self) -> tuple[tuple[str, ...], int]:
        """Stable shape identity used to keep golden applications domain-distinct."""
        return tuple(sorted({str(key) for row in self.fixture for key in row})), len(self.fixture)


FULL_APPLICATION_REGISTRY: Mapping[str, FullApplicationDefinition] = MappingProxyType({
    'spc-control-center': FullApplicationDefinition(
        'spc-control-center', 'SPC Control Center',
        'A complete stability review composed from monitoring, dashboard, comparison and drill-down surfaces.',
        'monitoring', 'spc-monitor', '/applications/spc-control-center',
        'Is the critical-dimension process stable, and which observations need review?',
        tuple(
            {'id': f'M-{index:03d}', 'timestamp': f'{8 + index // 4:02d}:{(index % 4) * 15:02d}', 'parameter': 'CD',
             'value': value, 'tool': 'ETCH-021' if index < 8 else 'ETCH-024',
             'state': 'Watch' if value > 40.2 else 'Normal'}
            for index, value in enumerate((40.02, 40.18, 40.07, 40.28, 40.11, 40.22, 40.09, 40.31, 40.14, 40.26, 40.13, 40.19), start=1)
        ),
        ('Control limits and specification limits are different contracts.', 'Synthetic rows demonstrate composition only; no root cause is inferred.'),
        primary_surface_key='spc_i_mr',
        domain_facets=('critical dimension', 'control limits', 'review queue'),
    ),
    'fdc-health-center': FullApplicationDefinition(
        'fdc-health-center', 'FDC Tool Health Center',
        'A full operational surface for aligned traces, chamber context, event review and affected records.',
        'monitoring', 'fdc-tool-health', '/applications/fdc-health-center',
        'Which tool or chamber signal changed around the observed equipment event?',
        tuple(
            {'id': f'T-{100 + index}', 'timestamp': f'S{index}', 'sensor': sensor, 'value': value,
             'tool': tool, 'chamber': chamber, 'state': state}
            for index, (sensor, value, tool, chamber, state) in enumerate((
                ('pressure', 1.02, 'ETCH-021', 'CH-3', 'Normal'), ('rf_bias', .84, 'ETCH-021', 'CH-3', 'Normal'),
                ('pressure', 1.18, 'ETCH-021', 'CH-3', 'Normal'), ('rf_bias', .91, 'ETCH-021', 'CH-3', 'Normal'),
                ('pressure', 1.76, 'ETCH-021', 'CH-3', 'Watch'), ('rf_bias', 1.32, 'ETCH-021', 'CH-3', 'Watch'),
                ('pressure', 1.52, 'ETCH-021', 'CH-3', 'Review'), ('rf_bias', 1.19, 'ETCH-021', 'CH-3', 'Review'),
                ('pressure', 1.11, 'ETCH-014', 'CH-2', 'Normal'), ('rf_bias', .88, 'ETCH-014', 'CH-2', 'Normal'),
                ('pressure', 1.08, 'ETCH-014', 'CH-2', 'Normal'), ('rf_bias', .86, 'ETCH-014', 'CH-2', 'Normal'),
            ), start=1)
        ),
        ('Event coincidence is not causal evidence.', 'Provider alignment and event-clock quality must be reviewed before action.'),
        primary_surface_key='fdc_recipe_step_trace',
        domain_facets=('pressure trace', 'tool/chamber', 'event review'),
    ),
    'excursion-investigation': FullApplicationDefinition(
        'excursion-investigation', 'Excursion Investigation',
        'An evidence-first investigation workspace for affected/control separation, commonality and supporting records.',
        'analysis_workspace', 'excursion-defense-line', '/applications/excursion-investigation',
        'What affected/control differences are worth investigating for this excursion?',
        tuple(
            {'id': f'E-{index:03d}', 'lot': lot, 'wafer': wafer, 'factor': factor, 'value': value, 'population': population}
            for index, (lot, wafer, factor, value, population) in enumerate((
                ('LOT-2471', 'W08', 'CH-3', 41.20, 'Affected'), ('LOT-2471', 'W09', 'CH-3', 44.80, 'Affected'),
                ('LOT-2471', 'W10', 'CH-3', 47.10, 'Affected'), ('LOT-2471', 'W11', 'Recipe R18', 43.60, 'Affected'),
                ('LOT-2468', 'W17', 'CH-2', 34.80, 'Control'), ('LOT-2468', 'W18', 'CH-2', 38.10, 'Control'),
                ('LOT-2468', 'W19', 'CH-2', 40.40, 'Control'), ('LOT-2468', 'W20', 'Recipe R17', 36.20, 'Control'),
            ), start=1)
        ),
        ('Commonality ranks evidence overlap; it is not a causal probability.', 'Hypotheses require corroborating evidence and governed population definitions.'),
        primary_surface_key='rca_affected_control',
        domain_facets=('affected vs control', 'evidence ledger', 'hypothesis review'),
    ),
})


def full_application_entries() -> tuple[FullApplicationDefinition, ...]:
    return tuple(FULL_APPLICATION_REGISTRY.values())


def render_full_application(definition: FullApplicationDefinition) -> None:
    """Render one complete example with the same public primitives used by apps."""
    from nicegui import ui
    from nicegui_base.content import KeyValueItem
    from nicegui_base.feedback import StateKind, StateViewSpec
    from nicegui_base.filters import FilterBarSpec, FilterDefinition, FilterKind
    from nicegui_base.integrations.nicegui_components import Button, SearchInput, Select
    from nicegui_base.integrations.nicegui_content import MetricCard, PropertyGrid
    from nicegui_base.layouts import LayoutSlot
    from nicegui_base.patterns import AnalysisWorkspacePage, ComparisonPage, DataExplorerPage, DashboardPage, MasterDetailPage, MonitoringPage
    from nicegui_base.patterns.composition import chart_table_detail, filter_bar, inspector, kpi_strip, page_section, state_panel
    from .visual_specimens import render_table, render_visualization

    page_classes = {
        'dashboard': DashboardPage, 'monitoring': MonitoringPage, 'analysis_workspace': AnalysisWorkspacePage,
        'investigation': AnalysisWorkspacePage, 'comparison': ComparisonPage,
        'master_detail': MasterDetailPage, 'drill_down': MasterDetailPage, 'upload_review': DataExplorerPage,
        'full_screen_operations': MonitoringPage,
    }
    page_class = page_classes[get_application_pattern(definition.pattern_key).key]
    pattern_label = get_application_pattern(definition.pattern_key).page_pattern.value.replace('_', ' ').title()
    rows = [dict(row) for row in definition.fixture]
    state: dict[str, Any] = {'query': '', 'refresh': None}
    def apply_query(event: Any) -> None:
        state['query'] = str(getattr(event, 'value', '') or '').casefold()
        refresh = state.get('refresh')
        if callable(refresh):
            refresh()
    with page_class(definition.title, definition.description) as page:
        page._page.element.classes(add='cui-full-application')
        with page_section(page, LayoutSlot.FILTERS, aria_label='Application filters'):
            with ui.element('div').classes('cui-full-application__identity').props(
                f'data-full-application="{definition.key}"'
            ):
                ui.label(definition.question).classes('cui-full-application__question')
                ui.label(' · '.join(definition.domain_facets)).classes('cui-workbench-note')
            with filter_bar(FilterBarSpec(filters=(FilterDefinition('query', 'Search records', FilterKind.TEXT, placeholder='Search records'),))):
                SearchInput('Search records', placeholder='Filter this application example', on_change=apply_query)
                Select('View', {'all': 'All records', 'review': 'Review state'}, value='all', clearable=False)
            with ui.element('div').classes('cui-workbench-chiprow').props('aria-label="Domain context"'):
                for facet in definition.domain_facets:
                    ui.label(facet).classes('cui-workbench-chip')

        def render_kpis() -> None:
            with kpi_strip():
                MetricCard('Records', len(rows), description='Synthetic reference fixture')
                MetricCard('Review focus', definition.domain_facets[0] if definition.domain_facets else 'Evidence-led review', description='Domain context')
                MetricCard('Pattern', pattern_label)

        if LayoutSlot.METRICS in page.allowed_slots:
            with page_section(page, LayoutSlot.METRICS, aria_label='Application metrics'):
                render_kpis()

        with page_section(page, LayoutSlot.PRIMARY, aria_label='Primary analysis'):
            with chart_table_detail('Primary analytical view', 'Chart and supporting records stay linked to the same filtered fixture.'):
                if LayoutSlot.METRICS not in page.allowed_slots:
                    render_kpis()
                chart_host = ui.element('div').props(
                    f'data-governed-analytic="{definition.primary_surface_key}"'
                )

                def render_primary_chart(current: tuple[dict[str, Any], ...]) -> None:
                    if definition.primary_surface_key == 'spc_i_mr':
                        # Reuse the exact registered paired Individuals + Moving Range
                        # renderer; a full application may not approximate its named
                        # governed analytical capability with a generic line chart.
                        from .app import _render_surface_preview
                        _render_surface_preview('spc_i_mr', 'spc', title='SPC I-MR stability review')
                        return
                    if definition.primary_surface_key == 'fdc_recipe_step_trace':
                        from nicegui_base.integrations.nicegui_visualization import LineChart
                        from nicegui_base.visualization import AxisSpec, AxisType, SeriesSpec
                        sensors = tuple(dict.fromkeys(str(row.get('sensor') or 'signal') for row in current))
                        series = tuple(
                            SeriesSpec(sensor, sensor.replace('_', ' ').title(), tuple(float(row['value']) for row in current if str(row.get('sensor') or 'signal') == sensor), smooth=True)
                            for sensor in sensors
                        )
                        LineChart('Aligned sensor traces', series, x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(str(row['id']) for row in current)))
                        ui.label('Signals remain grouped by sensor; event coincidence is shown for review, not causal inference.').classes('cui-workbench-note')
                        return
                    if definition.primary_surface_key == 'rca_affected_control':
                        from nicegui_base.integrations.nicegui_visualization import BoxPlot
                        from nicegui_base.visualization import AxisSpec, AxisType, SeriesSpec
                        from nicegui_base.semiconductor.spc import box_distribution
                        populations = tuple(dict.fromkeys(str(row.get('population') or 'Unknown') for row in current))
                        boxes = tuple(
                            tuple(float(value) for value in (
                                summary.minimum, summary.q1, summary.median, summary.q3, summary.maximum,
                            ))
                            for population in populations
                            for summary in (box_distribution(float(row['value']) for row in current if str(row.get('population') or 'Unknown') == population),)
                        )
                        if all(boxes):
                            panel = BoxPlot('Affected vs control distribution', (SeriesSpec('population', 'CD measurement', boxes),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=populations, label='Population'), y_axis=AxisSpec(label='CD measurement', min_value=32.0, max_value=49.0))
                            panel.container.props('data-visual-semantic="rca_affected_control" data-chart-semantics="grouped-quartile-distributions"')
                            ui.label('Population separation is descriptive evidence; it does not establish a root cause.').classes('cui-workbench-note')
                            return
                    render_visualization(
                        'ControlChart' if definition.primary_surface_key == 'spc_i_mr' else 'LineChart',
                        title=definition.title + ' · ' + definition.primary_surface_key.replace('_', ' '),
                        rows=current,
                        options={'measurement': 'value', 'label_field': 'id'},
                    )

                def redraw_chart() -> None:
                    chart_host.clear()
                    current = _filtered(rows, state['query'])
                    with chart_host:
                        if not current:
                            state_panel(StateViewSpec(StateKind.NO_RESULTS, 'No matching records', 'Clear the search to restore this linked example.'))
                        else:
                            render_primary_chart(current)
                redraw_chart()

        with page_section(page, LayoutSlot.DATA, aria_label='Supporting records'):
            table_host = ui.element('div')
            def redraw_table() -> None:
                table_host.clear()
                current = _filtered(rows, state['query'])
                with table_host:
                    if current:
                        render_table('data_table', title='Supporting records', rows=current)
                    else:
                        state_panel(StateViewSpec(StateKind.NO_RESULTS, 'No matching records', 'Clear the search to restore this linked example.'))
            redraw_table()
            state['refresh'] = lambda: (redraw_chart(), redraw_table())

        details_slot = (
            page_section(page, LayoutSlot.DETAILS, aria_label='Selected record details')
            if definition.pattern_key != 'analysis_workspace'
            else ui.element('div').classes('cui-full-application__inline-details')
        )
        with details_slot:
            selected = rows[0]
            detail = inspector('Selected record', subtitle='Bounded contextual detail')
            with detail.body:
                PropertyGrid(tuple(KeyValueItem(str(key), str(key).replace('_', ' ').title(), value) for key, value in selected.items()))
            Button('Open selected detail', on_click=detail.open)
            with ui.element('details').classes('cui-full-application__caveats'):
                with ui.element('summary').props('tabindex="0"'):
                    ui.label('Evidence caveats').classes('cui-workbench-card__meta')
                for caveat in definition.caveats:
                    ui.label(caveat).classes('cui-workbench-note')


def _filtered(rows: list[dict[str, Any]], query: str) -> tuple[dict[str, Any], ...]:
    if not query:
        return tuple(rows)
    return tuple(row for row in rows if query in ' '.join(str(value) for value in row.values()).casefold())


__all__ = ['FullApplicationDefinition', 'FULL_APPLICATION_REGISTRY', 'full_application_entries', 'render_full_application']
