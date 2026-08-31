from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Mapping


VISUAL_MODULE_ROUTES: Mapping[str, str] = {
    'nicegui_base.integrations.nicegui_components': '/controls',
    'nicegui_base.integrations.nicegui_content': '/content',
    'nicegui_base.integrations.nicegui_data_table': '/data',
    'nicegui_base.integrations.nicegui_engineering': '/engineering',
    'nicegui_base.integrations.nicegui_interactions': '/forms',
    'nicegui_base.integrations.nicegui_layout': '/controls',
    'nicegui_base.integrations.nicegui_visual_assets': '/foundation',
    'nicegui_base.integrations.nicegui_visualization': '/charts',
}

EXCLUDED_CLASSES = {'ShellConfig'}

# The route-builder names are intentionally explicit so coverage can be derived from
# source without importing mac_lab (which imports this module indirectly during
# preflight). Keeping this map synchronized is itself covered by Phase 17 tests.
ROUTE_BUILDERS: Mapping[str, str] = {
    '/': '_overview',
    '/foundation': '_foundation',
    '/shell': '_shell_primitives',
    '/controls': '_controls',
    '/forms': '_forms',
    '/data': '_data',
    '/charts': '_charts',
    '/content': '_content',
    '/engineering': '_engineering',
    '/states': '_states',
    '/performance': '_performance',
    '/patterns/dashboard': '_pattern_dashboard',
    '/patterns/explorer': '_pattern_explorer',
    '/patterns/master-detail': '_pattern_master_detail',
    '/patterns/crud': '_pattern_crud',
    '/patterns/monitoring': '_pattern_monitoring',
    '/patterns/search': '_pattern_search',
    '/patterns/settings': '_pattern_settings',
    '/patterns/wizard': '_pattern_wizard',
    '/patterns/comparison': '_pattern_comparison',
    '/patterns/analysis': '_pattern_analysis',
}


@dataclass(frozen=True, slots=True)
class CompositeCoverage:
    route: str
    via: str
    evidence: str


# These classes are not separate visible samples by design. They are implementation
# surfaces that are instantiated/used by a live parent component on the indicated
# route. This ledger is intentionally small and explicit; adding a new public visual
# class without direct use or an entry here fails coverage certification.
COMPOSITE_COVERAGE: Mapping[str, CompositeCoverage] = {
    'AppShell': CompositeCoverage('/patterns/dashboard', '_reference_shell', 'All ten canonical reference applications construct the production AppShell through the shared _reference_shell helper.'),
    'FilterBar': CompositeCoverage('/patterns/explorer', '_pattern_filter_controls', 'Canonical dashboard/explorer/monitoring routes render their filter control cluster through the shared pattern filter composition.'),
    'AppHeader': CompositeCoverage('/shell', 'AppShell', 'The canonical AppShell owns the exact Company header anatomy; AppHeader is the standalone compatibility facade for that anatomy.'),
    'AppSidebar': CompositeCoverage('/shell', 'AppShell', 'The canonical AppShell owns the desktop navigation rail; AppSidebar is the standalone compatibility facade for the same rail contract.'),
    'MobileNavigationDrawer': CompositeCoverage('/shell', 'AppShell', 'AppShell instantiates the Company-owned temporary mobile navigation overlay used below the responsive breakpoint.'),
    'PageHeader': CompositeCoverage('/patterns/dashboard', 'PatternPage', 'Every canonical PatternPage constructs PageHeader before rendering its semantic slots.'),
    'Toast': CompositeCoverage('/forms', '_toast', 'Multiple live buttons route feedback through the Company Toast surface.'),
    'AdvancedFilterDrawer': CompositeCoverage('/forms', 'open_filter_drawer', 'Live Advanced filters button passes AdvancedFilterDrawer into the drawer factory.'),
    'FilterDrawer': CompositeCoverage('/forms', 'open_filter_drawer', 'Live Filter drawer button passes FilterDrawer into the drawer factory.'),
    'ChartPanel': CompositeCoverage('/charts', 'typed charts', 'Every typed ECharts wrapper subclasses and renders ChartPanel.'),
    'ChartLegend': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.legend for every rendered chart.'),
    'ChartTooltip': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.tooltip for every rendered chart.'),
    'ChartSelection': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.selection for every rendered chart.'),
    'ChartZoom': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.zoom for every rendered chart.'),
    'ChartBrush': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.brush for every rendered chart.'),
    'ChartDataView': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs accessible panel.data_view used by the live toolbar.'),
    'ChartFullscreen': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.fullscreen used by the live toolbar.'),
    'ChartExport': CompositeCoverage('/charts', 'ChartPanel', 'ChartPanel constructs panel.export used by the live toolbar.'),
    'ChartToolbar': CompositeCoverage('/charts', 'ChartPanel', 'Every ChartPanel renders the Company toolbar into toolbar_host.'),
    'ConditionalCellFormatter': CompositeCoverage('/data', 'DataTable', 'TABLE_COLUMNS include conditional rules compiled by _column_def.'),
    'StatusCell': CompositeCoverage('/data', 'DataTable', 'TABLE_COLUMNS include a STATUS column rendered through StatusCell.'),
    'SparklineCell': CompositeCoverage('/data', 'DataTable', 'TABLE_COLUMNS include a SPARKLINE column rendered through SparklineCell.'),
    'TableToolbar': CompositeCoverage('/data', 'DataTable', 'The full enterprise DataTable renders its toolbar.'),
    'TableColumnManager': CompositeCoverage('/data', 'TableToolbar', 'TableToolbar renders the column manager.'),
    'TableDensitySelector': CompositeCoverage('/data', 'TableToolbar', 'TableToolbar renders the density selector.'),
    'TableSelectionBar': CompositeCoverage('/data', 'DataTable', 'The full enterprise table declares bulk actions, causing a live selection bar.'),
    'TableContextMenu': CompositeCoverage('/data', 'DataTable', 'The full enterprise table declares row actions, causing a live context menu.'),
    'TableRowActions': CompositeCoverage('/data', 'TableContextMenu', 'TableContextMenu inherits the row-action behavior and is exercised with live row actions.'),
}


@dataclass(frozen=True, slots=True)
class ComponentCoverage:
    component: str
    module: str
    route: str
    coverage_kind: str
    via: str | None = None
    evidence: str | None = None

    @property
    def direct(self) -> bool:
        return self.coverage_kind == 'direct'


def required_visual_classes() -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for module_name in VISUAL_MODULE_ROUTES:
        module = import_module(module_name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if name.startswith('_') or name in EXCLUDED_CLASSES:
                continue
            if cls.__module__ != module_name:
                continue
            result.append((name, module_name))
    return tuple(sorted(result))


def _mac_lab_path() -> Path:
    return Path(__file__).with_name('mac_lab.py')


def _route_direct_calls() -> dict[str, set[str]]:
    tree = ast.parse(_mac_lab_path().read_text(encoding='utf-8'))
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    result: dict[str, set[str]] = {}
    for route, builder in ROUTE_BUILDERS.items():
        node = functions.get(builder)
        calls: set[str] = set()
        if node is not None:
            for item in ast.walk(node):
                if not isinstance(item, ast.Call):
                    continue
                fn = item.func
                if isinstance(fn, ast.Name):
                    calls.add(fn.id)
                elif isinstance(fn, ast.Attribute):
                    calls.add(fn.attr)
        result[route] = calls
    return result


def live_component_coverage() -> tuple[ComponentCoverage, ...]:
    direct_by_route = _route_direct_calls()
    output: list[ComponentCoverage] = []
    for name, module in required_visual_classes():
        routes = [route for route in ROUTE_BUILDERS if name in direct_by_route.get(route, set())]
        if routes:
            output.append(ComponentCoverage(name, module, routes[0], 'direct', evidence='AST-observed constructor/function call in live route builder.'))
            continue
        composite = COMPOSITE_COVERAGE.get(name)
        if composite is not None:
            output.append(ComponentCoverage(name, module, composite.route, 'composite', composite.via, composite.evidence))
            continue
        # Keep the uncovered item in the report instead of silently assigning a
        # module-default route. This is what makes the ledger release-blocking.
        output.append(ComponentCoverage(name, module, VISUAL_MODULE_ROUTES[module], 'uncovered'))
    return tuple(output)


def uncovered_components(valid_routes: set[str] | None = None) -> tuple[str, ...]:
    coverage = live_component_coverage()
    missing = [item.component for item in coverage if item.coverage_kind == 'uncovered']
    if valid_routes is not None:
        missing.extend(f'{item.component}:invalid-route:{item.route}' for item in coverage if item.route not in valid_routes)
    return tuple(sorted(missing))


def coverage_summary() -> dict[str, object]:
    coverage = live_component_coverage()
    by_route: dict[str, int] = {}
    by_kind: dict[str, int] = {'direct': 0, 'composite': 0, 'uncovered': 0}
    for item in coverage:
        by_route[item.route] = by_route.get(item.route, 0) + 1
        by_kind[item.coverage_kind] = by_kind.get(item.coverage_kind, 0) + 1
    missing = uncovered_components(set(ROUTE_BUILDERS))
    return {
        'required_visual_components': len(coverage),
        'covered_visual_components': len(coverage) - by_kind.get('uncovered', 0),
        'direct_visual_components': by_kind.get('direct', 0),
        'composite_visual_components': by_kind.get('composite', 0),
        'uncovered': list(missing),
        'by_kind': by_kind,
        'by_route': dict(sorted(by_route.items())),
        'ledger': [
            {
                'component': item.component,
                'module': item.module,
                'route': item.route,
                'coverage_kind': item.coverage_kind,
                'via': item.via,
                'evidence': item.evidence,
            }
            for item in coverage
        ],
    }


__all__ = [
    'ComponentCoverage', 'CompositeCoverage', 'VISUAL_MODULE_ROUTES', 'ROUTE_BUILDERS', 'COMPOSITE_COVERAGE',
    'required_visual_classes', 'live_component_coverage', 'uncovered_components', 'coverage_summary',
]
