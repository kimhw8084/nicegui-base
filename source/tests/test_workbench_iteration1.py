from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
from types import MappingProxyType, ModuleType, SimpleNamespace
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SOURCE_AVAILABLE = (ROOT / "source" / "nicegui_base" / "semiconductor" / "surfaces.py").exists()
requires_canonical_source = pytest.mark.skipif(not CANONICAL_SOURCE_AVAILABLE, reason="canonical full repository source is not materialized in this overlay")

SURFACE_KEYS = (
    'spc_i_mr','spc_xbar_r','spc_xbar_s','spc_p','spc_np','spc_c','spc_u','spc_ewma','spc_cusum',
    'capability_histogram','qq_probability','ecdf','box_distribution','violin_distribution','ridge_distribution',
    'wafer_continuous','wafer_categorical','wafer_defect','wafer_delta','wafer_comparison','lot_wafer_strip','wafer_small_multiples','wafer_contour','wafer_radial','wafer_center_edge','wafer_ring','wafer_sector','wafer_defect_clusters',
    'fdc_recipe_step_trace','fdc_golden_envelope','fdc_multi_sensor','fdc_tool_chamber_compare','fdc_chamber_fingerprint','fdc_sensor_fingerprint','fdc_alarm_overlay','fdc_equipment_event_overlay','fdc_pca_scores','fdc_pca_loadings','fdc_hotelling_t2','fdc_spe_q',
    'rca_affected_control','rca_commonality_ranking','rca_enrichment','rca_commonality_matrix','rca_contribution_waterfall','rca_correlation_matrix','rca_evidence_matrix','rca_genealogy_graph','rca_cause_tree','rca_fault_tree','rca_sankey',
    'yield_pareto','bin_pareto','yield_waterfall','weibull_reliability','doe_main_effects','doe_interactions','doe_response_surface',
)
RECIPE_KEYS = ('spc-monitor','excursion-defense-line','fdc-tool-health','lot-wafer-explorer','yield-loss','pm-effect-analysis','chamber-matching','rca-cockpit')


def test_contract_counts_are_exact():
    assert len(SURFACE_KEYS) == 58
    assert len(set(SURFACE_KEYS)) == 58
    assert len(RECIPE_KEYS) == 8
    assert len(set(RECIPE_KEYS)) == 8


def test_every_surface_has_exact_semantic_preview_family():
    from nicegui_base.workbench.app import SURFACE_PREVIEW_FAMILIES
    assert set(SURFACE_PREVIEW_FAMILIES) == set(SURFACE_KEYS)
    assert len(set(SURFACE_PREVIEW_FAMILIES.values())) == 58
    assert SURFACE_PREVIEW_FAMILIES['fdc_hotelling_t2'] == 'fdc-hotelling-t2'
    assert SURFACE_PREVIEW_FAMILIES['doe_response_surface'] == 'doe-response-surface'
    assert SURFACE_PREVIEW_FAMILIES['rca_genealogy_graph'] == 'rca-genealogy'


def test_recipe_ui_has_real_lazy_sample_composition_contract():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'Canonical sample composition' in source
    assert '_mount_recipe_panel' in source
    assert 'render_recipe_mapping' in source
    assert 'Confirm mapping' in (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'recipe_mapping.py').read_text()
    assert "_standard_button('Use My Data', disabled=True)" not in source
    assert "_standard_button('Generate Starter', disabled=True)" not in source


@requires_canonical_source
def test_every_recipe_analytic_panel_resolves_to_a_live_preview_family():
    from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY
    from nicegui_base.workbench.app import SURFACE_PREVIEW_FAMILIES
    panel_surfaces = {panel.surface_key for recipe in SEMICONDUCTOR_RECIPE_REGISTRY.values() for panel in recipe.panels if panel.surface_key}
    assert panel_surfaces <= set(SURFACE_PREVIEW_FAMILIES)
    assert panel_surfaces


@requires_canonical_source
def test_current_canonical_registries_have_full_workbench_coverage():
    from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY
    from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY
    from nicegui_base.workbench.catalog import analytics_entries, recipe_entries
    assert set(SEMICONDUCTOR_SURFACE_REGISTRY) == set(SURFACE_KEYS)
    assert set(SEMICONDUCTOR_RECIPE_REGISTRY) == set(RECIPE_KEYS)
    analytics = analytics_entries()
    recipes = recipe_entries()
    assert len(analytics) == 58
    assert len(recipes) == 8
    assert {e.metadata['surface_key'] for e in analytics} == set(SURFACE_KEYS)
    assert {e.metadata['recipe_key'] for e in recipes} == set(RECIPE_KEYS)
    assert all(e.route.startswith('/analytics/') for e in analytics)
    assert all(e.route.startswith('/recipes/') for e in recipes)


@pytest.mark.parametrize('query', ['hotelling','t2','fdc'])
@requires_canonical_source
def test_hotelling_t2_is_directly_searchable(query):
    from nicegui_base.workbench.catalog import search
    keys = [result.entry.metadata.get('surface_key') for result in search(query, limit=100)]
    assert 'fdc_hotelling_t2' in keys


@requires_canonical_source
def test_every_catalog_entry_has_stable_unique_key_and_action():
    from nicegui_base.workbench.catalog import all_entries
    entries = all_entries()
    keys = [entry.key for entry in entries]
    assert len(keys) == len(set(keys))
    assert all(entry.route.startswith('/') for entry in entries)


@requires_canonical_source
def test_analytics_categories_match_canonical_taxonomy():
    from nicegui_base.workbench.catalog import analytics_entries
    counts = {}
    for entry in analytics_entries():
        counts[entry.category] = counts.get(entry.category, 0) + 1
    assert counts == {'spc':9,'capability':6,'wafer':13,'fdc':12,'rca':11,'yield':3,'reliability':1,'doe':3}



@requires_canonical_source
def test_current_canonical_catalog_covers_every_required_plan_family():
    from nicegui_base.workbench.catalog import REQUIRED_CATALOG_FAMILIES, catalog_family_coverage
    counts = catalog_family_coverage()
    assert set(counts) == set(REQUIRED_CATALOG_FAMILIES)
    assert all(counts[family] > 0 for family in REQUIRED_CATALOG_FAMILIES), counts

def test_readiness_rejects_generic_health_and_wrong_identity():
    from nicegui_base.workbench.readiness import identity_is_ready
    assert not identity_is_ready({'state':'ok'})
    assert not identity_is_ready({'product':'other','application':'workbench','version':'3.0.0a8','ready':True})
    assert not identity_is_ready({'product':'nicegui-base','application':'workbench','version':'3.0.0a7','ready':True})
    assert identity_is_ready({'product':'nicegui-base','application':'workbench','version':'3.0.0a8','ready':True})


def test_setup_scripts_verify_source_manifest_from_source_directory():
    root = ROOT
    for filename, checker in [('setup_mac.sh','/usr/bin/shasum -a 256 -c SHA256SUMS.txt'),('setup_linux.sh','sha256sum -c SHA256SUMS.txt')]:
        text=(root/filename).read_text()
        assert 'ROOT/source/SHA256SUMS.txt' in text
        assert '(cd "$ROOT/source"' in text
        assert checker in text


def test_launchers_require_workbench_identity_not_generic_health():
    root = ROOT
    for filename in ('run_lab_mac.sh','run_lab_linux.sh'):
        text=(root/filename).read_text()
        assert '/_nicegui_base/workbench' in text
        assert '-m nicegui_base.workbench.readiness' in text
        assert '$URL/healthz' not in text


def test_all_58_preview_dispatch_paths_construct_with_bounded_ui_stubs(monkeypatch):
    """Exercise every exact-key preview branch without requiring NiceGUI in the overlay sandbox."""
    import nicegui_base.workbench.app as workbench_app

    class Chain:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def classes(self, *args, **kwargs): return self
        def props(self, *args, **kwargs): return self
        def on(self, *args, **kwargs): return self

    class FakeUI:
        def element(self, *args, **kwargs): return Chain()
        def column(self, *args, **kwargs): return Chain()
        def row(self, *args, **kwargs): return Chain()
        def label(self, *args, **kwargs): return Chain()

    class Value:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            if len(args) >= 3:
                self.x, self.y, self.value = args[:3]
            else:
                self.x = self.y = self.value = 0

    calls = []
    def renderer(name):
        def render(*args, **kwargs):
            calls.append((name, args, kwargs))
            return Chain()
        return render

    viz = ModuleType('nicegui_base.integrations.nicegui_visualization')
    for name in ('BarChart','BoxPlot','ChamberFingerprintMatrix','CommonalityMatrix','ControlChart','DistributionPanel','_EmpiricalCDFChart','_FaultTreeDiagram','Heatmap','Histogram','LineChart','ParetoChart','RadialProfilePlot','_RelationshipGraph','_SankeyDiagram','ScatterChart','_WaferContourPlot','WaferComparisonMap','WaferMap','_WaterfallDiagram'):
        setattr(viz, name, renderer(name))
    models = ModuleType('nicegui_base.visualization')
    models.AnnotationIntent = SimpleNamespace(DANGER='danger', INFO='info', WARNING='warning')
    models.AxisSpec = Value
    models.AxisType = SimpleNamespace(CATEGORY='category', VALUE='value')
    models.ChartAnnotation = Value
    models.LineStyle = SimpleNamespace(DASHED='dashed')
    models.SeriesSpec = Value
    models.SpecLimits = Value
    models.WaferPoint = Value
    monkeypatch.setitem(sys.modules, 'nicegui_base.integrations.nicegui_visualization', viz)
    monkeypatch.setitem(sys.modules, 'nicegui_base.visualization', models)
    monkeypatch.setattr(workbench_app, '_imports', lambda: (FakeUI(), None, None, None, None, None, None))

    categories = {}
    for key in SURFACE_KEYS:
        if key.startswith('spc_'): category = 'spc'
        elif key in {'capability_histogram','qq_probability','ecdf','box_distribution','violin_distribution','ridge_distribution'}: category = 'capability'
        elif key.startswith('wafer_') or key == 'lot_wafer_strip': category = 'wafer'
        elif key.startswith('fdc_'): category = 'fdc'
        elif key.startswith('rca_'): category = 'rca'
        elif key in {'yield_pareto','bin_pareto','yield_waterfall'}: category = 'yield'
        elif key == 'weibull_reliability': category = 'reliability'
        else: category = 'doe'
        categories[key] = category
        workbench_app._render_surface_preview(key, category, compact=True)

    assert set(categories) == set(SURFACE_KEYS)
    # Custom tree/flow previews use Workbench DOM rather than a chart renderer; all other
    # surfaces must invoke at least one existing visualization primitive.
    custom = {'rca_genealogy_graph','rca_cause_tree','rca_fault_tree','rca_sankey'}
    assert len(calls) >= len(SURFACE_KEYS) - len(custom)


def test_global_search_uses_framework_command_palette_not_home_redirect():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'CommandPalette' in source
    assert 'CommandRegistry' in source
    assert "f'entry:{entry.key}'" in source
    assert "e.key.toLowerCase()==='k'" in source
    assert 'window.__niceguiBaseWorkbenchHome' in source
    assert 'palette_fallback' in source
    assert "params.get('palette')==='1'" in source


def test_registry_adapters_cover_58_and_8_against_canonical_shape_stubs(monkeypatch):
    from nicegui_base.workbench.registry_adapters import semiconductor_recipe_entries, semiconductor_surface_entries
    from nicegui_base.workbench.search import search_entries

    category_sets = {
        'spc': SURFACE_KEYS[0:9],
        'capability': SURFACE_KEYS[9:15],
        'wafer': SURFACE_KEYS[15:28],
        'fdc': SURFACE_KEYS[28:40],
        'rca': SURFACE_KEYS[40:51],
        'yield': SURFACE_KEYS[51:54],
        'reliability': SURFACE_KEYS[54:55],
        'doe': SURFACE_KEYS[55:58],
    }
    surface_registry = {}
    for category, keys in category_sets.items():
        for key in keys:
            surface_registry[key] = SimpleNamespace(
                purpose=f'{key} purpose', category=category, use_when=(f'use {key}',),
                avoid_when=(f'avoid {key}',), linked_hover=category in {'wafer','fdc','rca'}, spatial=category == 'wafer',
            )
    recipe_registry = {
        key: SimpleNamespace(
            application_name=''.join(part.title() for part in key.split('-')),
            purpose=f'{key} purpose', use_when=(f'use {key}',), avoid_when=(f'avoid {key}',),
            tags=(key.split('-')[0],),
            surface_keys=('fdc_hotelling_t2',) if key == 'fdc-tool-health' else (),
            panels=(), interactions=(), populations=(),
        )
        for key in RECIPE_KEYS
    }
    surfaces_mod = ModuleType('nicegui_base.semiconductor.surfaces')
    surfaces_mod.SEMICONDUCTOR_SURFACE_REGISTRY = MappingProxyType(surface_registry)
    recipes_mod = ModuleType('nicegui_base.semiconductor.recipes')
    recipes_mod.SEMICONDUCTOR_RECIPE_REGISTRY = MappingProxyType(recipe_registry)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.surfaces', surfaces_mod)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.recipes', recipes_mod)

    analytics = semiconductor_surface_entries()
    recipes = semiconductor_recipe_entries()
    assert len(analytics) == 58
    assert len(recipes) == 8
    assert {entry.metadata['surface_key'] for entry in analytics} == set(SURFACE_KEYS)
    assert {entry.metadata['recipe_key'] for entry in recipes} == set(RECIPE_KEYS)
    for query in ('hotelling','t2','fdc'):
        assert any(result.entry.metadata.get('surface_key') == 'fdc_hotelling_t2' for result in search_entries(analytics, query, limit=100))


def test_catalog_metadata_exposes_authority_preview_sample_and_relationship_contract(monkeypatch):
    from nicegui_base.workbench.registry_adapters import semiconductor_recipe_entries, semiconductor_surface_entries

    surfaces_mod = ModuleType('nicegui_base.semiconductor.surfaces')
    surfaces_mod.SEMICONDUCTOR_SURFACE_REGISTRY = MappingProxyType({
        'fdc_hotelling_t2': SimpleNamespace(
            purpose='Hotelling multivariate anomaly magnitude', category='fdc',
            use_when=('multivariate process monitoring',), avoid_when=('variables are not comparable',),
            linked_hover=False, spatial=False,
        )
    })
    recipe = SimpleNamespace(
        application_name='FdcToolHealth', purpose='Equipment health',
        use_when=('monitor equipment health',), avoid_when=('sensor semantics unavailable',),
        tags=('fdc','equipment'), surface_keys=('fdc_hotelling_t2',), panels=(), interactions=(), populations=('baseline',),
    )
    recipes_mod = ModuleType('nicegui_base.semiconductor.recipes')
    recipes_mod.SEMICONDUCTOR_RECIPE_REGISTRY = MappingProxyType({'fdc-tool-health': recipe})
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.surfaces', surfaces_mod)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.recipes', recipes_mod)

    surface = semiconductor_surface_entries()[0]
    recipe_entry = semiconductor_recipe_entries()[0]
    assert surface.source_authority == 'SEMICONDUCTOR_SURFACE_REGISTRY'
    assert surface.live_preview and surface.sample_data
    assert surface.related_keys == ('recipe:fdc-tool-health',)
    assert recipe_entry.source_authority == 'SEMICONDUCTOR_RECIPE_REGISTRY'
    assert recipe_entry.live_preview and recipe_entry.sample_data
    assert recipe_entry.related_keys == ('analytics:fdc_hotelling_t2',)
    assert 'Hotelling T²' in recipe_entry.aliases

    # Interaction/spatial capabilities must be visible in gallery metadata, not only on detail pages.
    surfaces_mod.SEMICONDUCTOR_SURFACE_REGISTRY = MappingProxyType({
        'wafer_continuous': SimpleNamespace(
            purpose='Wafer map', category='wafer', use_when=('spatial analysis',), avoid_when=(),
            linked_hover=True, spatial=True,
        )
    })
    wafer = semiconductor_surface_entries()[0]
    assert 'linked hover' in wafer.tags
    assert 'spatial' in wafer.tags


def test_search_plan_examples_resolve_through_registry_adapters(monkeypatch):
    from nicegui_base.workbench.registry_adapters import (
        framework_catalog_entries, pattern_entries, semiconductor_recipe_entries, semiconductor_surface_entries,
    )
    from nicegui_base.workbench.search import search_entries

    # Small canonical-shaped surface slice: enough to verify intent relationships without
    # duplicating the full registry truth in this overlay test.
    surface_registry = {
        'fdc_hotelling_t2': SimpleNamespace(purpose='Hotelling T² multivariate anomaly magnitude', category='fdc', use_when=('multivariate FDC monitoring',), avoid_when=(), linked_hover=False, spatial=False),
        'rca_commonality_ranking': SimpleNamespace(purpose='Rank common factors for an investigation', category='rca', use_when=('root cause investigation',), avoid_when=(), linked_hover=False, spatial=False),
        'wafer_continuous': SimpleNamespace(purpose='Continuous wafer spatial map', category='wafer', use_when=('wafer spatial analysis',), avoid_when=(), linked_hover=True, spatial=True),
    }
    surfaces_mod = ModuleType('nicegui_base.semiconductor.surfaces')
    surfaces_mod.SEMICONDUCTOR_SURFACE_REGISTRY = MappingProxyType(surface_registry)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.surfaces', surfaces_mod)

    def recipe(key, name, surfaces, tags):
        return SimpleNamespace(
            application_name=name, purpose=f'{name} application', use_when=(f'use {name}',), avoid_when=(),
            tags=tags, surface_keys=surfaces, panels=(), interactions=(), populations=(),
        )
    recipe_registry = {
        'spc-monitor': recipe('spc-monitor','SPCMonitor',(),('spc','monitoring')),
        'fdc-tool-health': recipe('fdc-tool-health','FdcToolHealth',('fdc_hotelling_t2',),('fdc','equipment')),
        'excursion-defense-line': recipe('excursion-defense-line','ExcursionDefenseLine',('rca_commonality_ranking',),('excursion','rca')),
        'lot-wafer-explorer': recipe('lot-wafer-explorer','LotWaferExplorer',('wafer_continuous',),('wafer','spatial')),
        'rca-cockpit': recipe('rca-cockpit','RcaCockpit',('rca_commonality_ranking',),('rca','evidence')),
    }
    recipes_mod = ModuleType('nicegui_base.semiconductor.recipes')
    recipes_mod.SEMICONDUCTOR_RECIPE_REGISTRY = MappingProxyType(recipe_registry)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.recipes', recipes_mod)

    patterns_mod = ModuleType('nicegui_base.patterns.registry')
    patterns_mod.PATTERN_REGISTRY = MappingProxyType({
        'data_explorer': SimpleNamespace(purpose='Interactive filtering, analysis and records.'),
        'crud': SimpleNamespace(purpose='Search, create, inspect and edit records.'),
        'monitoring': SimpleNamespace(purpose='Operational health and alerts.'),
        'analysis_workspace': SimpleNamespace(purpose='Dense analysis workspace.'),
    })
    monkeypatch.setitem(sys.modules, 'nicegui_base.patterns.registry', patterns_mod)

    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {
        'registries': {
            'data_table': [{'_registry_key':'editable_table','public_name':'EditableTable','purpose':'Editable tabular records'}],
            'visualization': [{'_registry_key':'wafer_map','public_name':'WaferMap','purpose':'Wafer spatial visualization'}],
        }
    }
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)

    entries = (
        *pattern_entries(), *semiconductor_surface_entries(), *semiconductor_recipe_entries(),
        *framework_catalog_entries(known_entries=set()),
    )

    def keys(query):
        return {result.entry.key for result in search_entries(entries, query, limit=100)}

    hotelling = keys('hotelling')
    assert 'analytics:fdc_hotelling_t2' in hotelling
    assert 'recipe:fdc-tool-health' in hotelling

    editable = keys('editable table')
    assert 'framework:data_table:editable_table' in editable
    assert 'pattern:data_explorer' in editable
    assert 'pattern:crud' in editable

    wafer = keys('wafer')
    assert 'analytics:wafer_continuous' in wafer
    assert 'recipe:lot-wafer-explorer' in wafer
    assert 'framework:visualization:wafer_map' in wafer

    investigation = keys('investigation')
    assert 'pattern:analysis_workspace' in investigation
    assert 'recipe:excursion-defense-line' in investigation
    assert 'analytics:rca_commonality_ranking' in investigation

    monitoring = keys('new monitoring app')
    assert 'pattern:monitoring' in monitoring
    assert 'recipe:spc-monitor' in monitoring
    assert 'recipe:fdc-tool-health' in monitoring


def test_inline_search_is_grouped_and_cards_are_keyboard_navigable():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "for kind in WorkbenchKind:" in source
    assert "cui-workbench-search-group" in source
    assert "role=\"link\" tabindex=\"0\"" in source
    assert ".on('keydown.enter', navigate)" in source
    assert ".on('keydown.space', navigate)" in source
    # AppShell already owns the sole document main landmark.
    assert "ui.element('main').classes('cui-page" not in source


def test_readiness_reports_exact_identity_mismatch():
    from nicegui_base.workbench.readiness import identity_problem
    problem = identity_problem({'product':'nicegui-base','application':'workbench','version':'3.0.0a7','ready':False}, version='3.0.0a8')
    assert "version='3.0.0a7'" in problem
    assert "ready=False" in problem
    assert identity_problem({'product':'nicegui-base','application':'workbench','version':'3.0.0a8','ready':True}, version='3.0.0a8') is None


def test_framework_catalog_suppression_is_registry_qualified(monkeypatch):
    from nicegui_base.workbench.registry_adapters import framework_catalog_entries

    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {
        'registries': {
            'components': [{'_registry_key':'shared_key','public_name':'Component Shared','purpose':'component'}],
            'visualization': [{'_registry_key':'shared_key','public_name':'Visualization Shared','purpose':'visual'}],
        }
    }
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = framework_catalog_entries(known_entries={('components','shared_key')})
    assert {entry.key for entry in entries} == {'framework:visualization:shared_key'}


def test_home_does_not_expose_fake_recent_or_favorite_actions():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "_action_card('Recent'" not in source
    assert "_action_card('Favorites'" not in source
    assert 'render_home_project_resume()' not in source


def test_workbench_page_builders_construct_with_bounded_ui_stubs(monkeypatch):
    """Construct every Iteration 1 Workbench page shape without the external NiceGUI runtime."""
    import nicegui_base.workbench.app as workbench_app
    from nicegui_base.workbench.models import WorkbenchCoverage, WorkbenchEntry, WorkbenchKind, SearchResult

    class Chain:
        _next_id = 1
        def __init__(self, value=None):
            self.value = value
            self.id = Chain._next_id
            Chain._next_id += 1
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def classes(self, *args, **kwargs): return self
        def props(self, *args, **kwargs): return self
        def on(self, *args, **kwargs): return self
        def clear(self): return None
        def set_text(self, *args, **kwargs): return self
        def set_visibility(self, *args, **kwargs): return self

    class Navigate:
        def to(self, route): return route

    class FakeUI:
        def __init__(self): self.navigate = Navigate()
        def element(self, *args, **kwargs): return Chain()
        def column(self, *args, **kwargs): return Chain()
        def row(self, *args, **kwargs): return Chain()
        def label(self, *args, **kwargs): return Chain()
        def html(self, *args, **kwargs): return Chain()
        def image(self, *args, **kwargs): return Chain()
        def button(self, *args, **kwargs): return Chain()
        def input(self, *args, **kwargs): return Chain('')
        def select(self, *args, **kwargs): return Chain(kwargs.get('value'))

    fake_ui = FakeUI()
    monkeypatch.setattr(workbench_app, '_imports', lambda: (fake_ui, None, None, None, None, None, None))
    monkeypatch.setattr(workbench_app, '_shell', lambda *args, **kwargs: Chain())
    monkeypatch.setattr(workbench_app, '_end_shell', lambda shell: None)
    monkeypatch.setattr(workbench_app, '_render_surface_preview', lambda *args, **kwargs: None)
    monkeypatch.setattr(workbench_app, '_standard_button', lambda *args, **kwargs: Chain())
    monkeypatch.setattr(workbench_app, '_standard_search', lambda *args, **kwargs: Chain(''))
    monkeypatch.setattr(workbench_app, '_standard_select', lambda *args, **kwargs: Chain(kwargs.get('value')))

    component = WorkbenchEntry(
        'component:button', WorkbenchKind.COMPONENT, 'Button', 'Action', '/catalog/component/button',
        'actions', source_authority='COMPONENT_REGISTRY', live_preview=True, metadata={'component_key':'button'},
    )
    framework = WorkbenchEntry(
        'framework:runtime:doctor', WorkbenchKind.REFERENCE, 'Doctor', 'Runtime diagnostics',
        '/catalog/runtime/doctor', 'runtime', source_authority='framework_catalog:runtime',
        metadata={'registry_name':'runtime','registry_key':'doctor','catalog_item':{'key':'doctor','purpose':'Runtime diagnostics'}},
    )
    analytic = WorkbenchEntry(
        'analytics:fdc_hotelling_t2', WorkbenchKind.ANALYTIC, 'FDC Hotelling T²', 'Multivariate anomaly',
        '/analytics/fdc_hotelling_t2', 'fdc', aliases=('hotelling','t2'), use_when=('multivariate FDC',),
        avoid_when=('sensor semantics unavailable',), source_authority='SEMICONDUCTOR_SURFACE_REGISTRY',
        live_preview=True, sample_data=True, metadata={'surface_key':'fdc_hotelling_t2','linked_hover':False,'spatial':False},
    )
    recipe_entry = WorkbenchEntry(
        'recipe:fdc-tool-health', WorkbenchKind.RECIPE, 'FdcToolHealth', 'Equipment health',
        '/recipes/fdc-tool-health', 'semiconductor recipe', aliases=('hotelling',),
        use_when=('monitor equipment',), avoid_when=('sensor semantics unavailable',), tags=('fdc',),
        source_authority='SEMICONDUCTOR_RECIPE_REGISTRY', live_preview=True, sample_data=True,
        related_keys=('analytics:fdc_hotelling_t2',), metadata={'recipe_key':'fdc-tool-health','surfaces':('fdc_hotelling_t2',),'variants':()},
    )
    entries = (component, framework, analytic, recipe_entry)
    monkeypatch.setattr(workbench_app, 'all_entries', lambda: entries)
    monkeypatch.setattr(workbench_app, 'analytics_entries', lambda: (analytic,))
    monkeypatch.setattr(workbench_app, 'recipe_entries', lambda: (recipe_entry,))
    monkeypatch.setattr(workbench_app, 'coverage', lambda: WorkbenchCoverage(4,1,0,1,1,('actions','fdc','runtime','semiconductor recipe')))
    monkeypatch.setattr(workbench_app, 'catalog_family_coverage', lambda: {family: 1 for family in workbench_app.REQUIRED_CATALOG_FAMILIES})
    monkeypatch.setattr(workbench_app, 'search', lambda query, limit=30: (SearchResult(analytic, 100, ('hotelling',)),))

    panel = SimpleNamespace(
        panel_id='summary', title='Summary', kind=SimpleNamespace(value='summary'), surface_key=None,
        description='Summary panel', field_requirements=(),
    )
    requirement = SimpleNamespace(required=True, key='measurement', candidates=('value','measurement'))
    recipe = SimpleNamespace(
        application_name='FdcToolHealth', purpose='Equipment health', use_when=('monitor equipment',),
        avoid_when=('sensor semantics unavailable',), field_requirements=(requirement,),
        filters=(SimpleNamespace(label='Tool'),), panels=(panel,), interactions=(), populations=('baseline',), tags=('fdc',),
        surface_keys=(),
    )
    recipes_mod = ModuleType('nicegui_base.semiconductor.recipes')
    recipes_mod.get_semiconductor_recipe = lambda key: recipe if key == 'fdc-tool-health' else (_ for _ in ()).throw(KeyError(key))
    recipes_mod.SEMICONDUCTOR_RECIPE_REGISTRY = MappingProxyType({'fdc-tool-health': recipe})
    surfaces_mod = ModuleType('nicegui_base.semiconductor.surfaces')
    surfaces_mod.SEMICONDUCTOR_SURFACE_REGISTRY = MappingProxyType({'fdc_hotelling_t2': SimpleNamespace()})
    patterns_pkg = ModuleType('nicegui_base.patterns')
    patterns_mod = ModuleType('nicegui_base.patterns.registry')
    patterns_mod.PATTERN_REGISTRY = MappingProxyType({f'pattern_{i}': SimpleNamespace() for i in range(10)})
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.recipes', recipes_mod)
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.surfaces', surfaces_mod)
    monkeypatch.setitem(sys.modules, 'nicegui_base.patterns', patterns_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.patterns.registry', patterns_mod)

    nicegui_mod = ModuleType('nicegui'); nicegui_mod.ui = fake_ui
    nicegui_mod.app = SimpleNamespace(storage=SimpleNamespace(user={}, browser={}))
    monkeypatch.setitem(sys.modules, 'nicegui', nicegui_mod)
    import nicegui_base.workbench.builder as builder_mod
    import nicegui_base.workbench.capability_studio as studio_mod
    monkeypatch.setattr(builder_mod, 'render_builder', lambda *args, **kwargs: None)
    monkeypatch.setattr(studio_mod, 'render_data_dock', lambda *args, **kwargs: None)
    monkeypatch.setattr(workbench_app, '_studio_entry_page', lambda *args, **kwargs: None)

    workbench_app.home_page()
    workbench_app.build_page()
    workbench_app.catalog_page()
    workbench_app.component_detail_page('button')
    workbench_app.catalog_detail_page('runtime', 'doctor')
    workbench_app.analytics_gallery_page()
    workbench_app.analytics_detail_page('fdc_hotelling_t2')
    workbench_app.recipes_gallery_page()
    workbench_app.recipe_detail_page('fdc-tool-health')
    workbench_app.data_page()
    workbench_app.quality_page()


def test_global_palette_fallback_is_root_path_aware():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "def register_workbench_pages(*, include_reference: bool = True, root_path: str = '')" in source
    assert "root_prefix = '/' + root_path.strip('/') if root_path.strip('/') else ''" in source
    assert "register_workbench_pages(root_path=root_path)" in source


def test_invalid_detail_urls_render_governed_workbench_state(monkeypatch):
    import nicegui_base.workbench.app as workbench_app

    class Chain:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def classes(self, *args, **kwargs): return self
        def props(self, *args, **kwargs): return self
        def on(self, *args, **kwargs): return self
    class Navigate:
        def to(self, route): return route
    class FakeUI:
        navigate = Navigate()
        def element(self, *args, **kwargs): return Chain()
        def label(self, *args, **kwargs): return Chain()
        def button(self, *args, **kwargs): return Chain()
    fake = FakeUI()
    monkeypatch.setattr(workbench_app, '_imports', lambda: (fake,None,None,None,None,None,None))
    monkeypatch.setattr(workbench_app, '_shell', lambda *args, **kwargs: Chain())
    monkeypatch.setattr(workbench_app, '_end_shell', lambda shell: None)
    monkeypatch.setattr(workbench_app, 'all_entries', lambda: ())
    monkeypatch.setattr(workbench_app, 'analytics_entries', lambda: ())
    monkeypatch.setattr(workbench_app, '_standard_button', lambda *args, **kwargs: Chain())

    recipes_mod = ModuleType('nicegui_base.semiconductor.recipes')
    recipes_mod.get_semiconductor_recipe = lambda key: (_ for _ in ()).throw(KeyError(key))
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor.recipes', recipes_mod)

    workbench_app.component_detail_page('missing')
    workbench_app.catalog_detail_page('missing', 'missing')
    workbench_app.analytics_detail_page('missing')
    workbench_app.recipe_detail_page('missing')


def test_workbench_uses_governed_controls_not_raw_nicegui_controls():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'ui.button(' not in source
    assert 'ui.input(' not in source
    assert 'ui.select(' not in source
    assert '_standard_button' in source
    assert '_standard_search' in source
    assert '_standard_select' in source


def test_catalog_toolbar_precedes_results_container_in_dom_order():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    start = source.index('def catalog_page(')
    end = source.index('def _unknown_detail', start)
    catalog_source = source[start:end]
    toolbar = catalog_source.index("with ui.element('div').classes('cui-workbench-toolbar')")
    results = catalog_source.index("host = ui.element('div').classes('cui-workbench-catalog-results')")
    assert toolbar < results


def test_identity_endpoint_is_bound_to_workbench_health_contract():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "HealthCheck('workbench-contract'" in source
    assert "stats.analytics == 58" in source
    assert "stats.recipes == 8" in source
    assert "analytic_keys == preview_keys" in source
    assert "all(family_counts.get(family, 0) > 0 for family in REQUIRED_CATALOG_FAMILIES)" in source
    assert "report = await runtime.health.run()" in source
    assert "status_code=200 if report.ready else 503" in source
    assert "'ready': True" not in source[source.index("@app.get('/_nicegui_base/workbench'"):]


def test_global_palette_keywords_cover_purpose_guidance_authority_and_relationships():
    from nicegui_base.workbench.app import _command_keywords
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    entry = WorkbenchEntry(
        'analytics:test', WorkbenchKind.ANALYTIC, 'Test Surface', 'detect subtle chamber drift', '/analytics/test', 'fdc',
        aliases=('multivariate',), use_when=('monitor process health',), avoid_when=('sensor semantics unavailable',),
        tags=('equipment',), source_authority='SEMICONDUCTOR_SURFACE_REGISTRY', maturity='stable',
        related_keys=('recipe:fdc-tool-health',),
    )
    keywords = _command_keywords(entry)
    for expected in (
        'detect subtle chamber drift', 'monitor process health', 'sensor semantics unavailable',
        'SEMICONDUCTOR_SURFACE_REGISTRY', 'recipe:fdc-tool-health', 'multivariate', 'equipment', 'stable',
    ):
        assert expected in keywords


def _load_apply_helper_for_test():
    helper = ROOT / 'apply_iteration1.py'
    spec = importlib.util.spec_from_file_location('nicegui_base_iteration1_apply_test', helper)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_apply_helper_verifies_baseline_checksum_manifest_contents(tmp_path):
    helper = _load_apply_helper_for_test()
    target = tmp_path / 'source'
    target.mkdir()
    payload = target / 'payload.txt'
    payload.write_text('canonical', encoding='utf-8')
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    (target / 'SHA256SUMS.txt').write_text(f'{digest}  payload.txt\n', encoding='utf-8')
    helper._verify_checksum_manifest(target, 'SHA256SUMS.txt')
    payload.write_text('tampered', encoding='utf-8')
    with pytest.raises(SystemExit, match='baseline checksum verification failed'):
        helper._verify_checksum_manifest(target, 'SHA256SUMS.txt')


def test_apply_helper_anchors_source_and_package_manifest_git_blobs():
    helper = _load_apply_helper_for_test()
    assert helper.BASELINE_BLOB_SHA1['source/SHA256SUMS.txt'] == 'aeec80df96d202b58380bb8e9841ba1bc5a654b0'
    assert helper.BASELINE_BLOB_SHA1['PACKAGE_SHA256SUMS.txt'] == '9b0c19039141183efd360526e681bede938cac14'


def test_ai_construction_registry_closes_plan_level_catalog_families(monkeypatch):
    from nicegui_base.workbench.catalog import REQUIRED_CATALOG_FAMILIES, catalog_family_coverage
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    import nicegui_base.workbench.registry_adapters as adapters

    construction_defs = {
        key: SimpleNamespace(
            requirement_signal=f'{key} requirement', preferred_api=f'nicegui_base.{key}',
            inspect_first=f'{key.upper()}_REGISTRY', prohibited_shortcut=f'raw {key}', rationale=f'{key} rationale',
        )
        for key in (
            'page_pattern','layout','component','content','form_filter_overlay','table','data_source',
            'visualization','visual_asset','state_async','jobs','engineering','semiconductor','performance','security_runtime',
        )
    }
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_registry = ModuleType('nicegui_base.ai.registry')
    ai_registry.AI_CONSTRUCTION_REGISTRY = MappingProxyType(construction_defs)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.registry', ai_registry)

    construction = adapters.construction_entries()
    assert len(construction) == 15
    assert all(entry.source_authority == 'AI_CONSTRUCTION_REGISTRY' for entry in construction)
    assert any(entry.metadata.get('catalog_family') == 'shell/layout' for entry in construction)
    assert any(entry.metadata.get('catalog_family') == 'forms/overlays' for entry in construction)
    assert any(entry.metadata.get('catalog_family') == 'performance/quality utilities' for entry in construction)

    analytic = WorkbenchEntry('analytics:test', WorkbenchKind.ANALYTIC, 'Analytic', 'Purpose', '/analytics/test')
    recipe = WorkbenchEntry('recipe:test', WorkbenchKind.RECIPE, 'Recipe', 'Purpose', '/recipes/test')
    pattern = WorkbenchEntry('pattern:test', WorkbenchKind.PATTERN, 'Pattern', 'Purpose', '/patterns/test')
    component = WorkbenchEntry('component:test', WorkbenchKind.COMPONENT, 'Control', 'Purpose', '/catalog/component/test')
    counts = catalog_family_coverage((*construction, analytic, recipe, pattern, component))
    missing = tuple(family for family in REQUIRED_CATALOG_FAMILIES if counts[family] < 1)
    assert missing == ()


def test_quality_page_exposes_plan_level_catalog_family_gate():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "with _section('Catalog family coverage'" in source
    assert 'Every required Reference Explorer catalog family contributes discoverable canonical entries' in source
    assert "families={covered_families}/{len(REQUIRED_CATALOG_FAMILIES)}" in source


def test_catalog_groups_entries_by_plan_family_and_exposes_family_filter():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    start = source.index('def catalog_page(')
    end = source.index('def _unknown_detail', start)
    catalog_source = source[start:end]
    assert "_standard_select('Family'" in catalog_source
    assert "ordered_families = tuple(REQUIRED_CATALOG_FAMILIES) + ('other canonical capabilities',)" in catalog_source
    assert "catalog_family(entry)" in catalog_source
    assert "cui-workbench-catalog-results" in catalog_source


def test_workbench_owns_display_controls_instead_of_private_certification_lab_control_bar():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'def _display_control_bar()' in source
    assert '_display_control_bar()' in source[source.index('def _shell('):source.index('def _end_shell', source.index('def _shell('))]
    assert 'from nicegui_base.certification.mac_lab import _control_bar' not in source
    assert "SegmentedControl({'system': 'System', 'light': 'Light', 'dark': 'Dark'}" in source
    assert "SegmentedControl({'comfortable': 'Comfort', 'compact': 'Compact', 'dense': 'Dense'}" in source
    assert "SegmentedControl({'normal': 'Normal', 'reduced': 'Reduced'}" in source
    # Compatibility preference keys intentionally stay aligned with deep reference routes.
    assert "app.storage.user.get('cui_lab_theme'" in source
    assert "app.storage.user.get('cui_lab_density'" in source
    assert "app.storage.user.get('cui_lab_motion'" in source


@requires_canonical_source
def test_all_10_canonical_patterns_are_discoverable_and_open_live_reference_routes():
    from nicegui_base.certification.mac_lab import ROUTES
    from nicegui_base.patterns.registry import PATTERN_REGISTRY
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.models import WorkbenchKind

    canonical = {getattr(key, 'value', str(key)) for key in PATTERN_REGISTRY}
    entries = tuple(entry for entry in all_entries() if entry.kind is WorkbenchKind.PATTERN)
    visible = {entry.metadata.get('pattern_key') for entry in entries}
    live_routes = {route.path for route in ROUTES}
    assert len(canonical) == 10
    assert visible == canonical
    assert len(entries) == 10
    assert all(entry.metadata.get('full_reference_route') in live_routes for entry in entries)


def test_quality_and_readiness_explicitly_gate_10_generic_application_patterns():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "canonical_patterns == stats.patterns == 10" in source
    assert 'canonical generic application patterns are discoverable' in source
    assert 'visible_pattern_keys == canonical_pattern_keys' in source
    assert "patterns={stats.patterns}/{len(canonical_pattern_keys)}" in source


def test_setup_scripts_verify_package_manifest_before_source_manifest_and_install():
    for filename, checker in (
        ('setup_mac.sh', '/usr/bin/shasum -a 256 -c PACKAGE_SHA256SUMS.txt'),
        ('setup_linux.sh', 'sha256sum -c PACKAGE_SHA256SUMS.txt'),
    ):
        text = (ROOT / filename).read_text()
        assert 'verify_package_manifest()' in text
        assert 'ROOT/PACKAGE_SHA256SUMS.txt' in text
        assert checker in text
        package_call = text.index('verify_package_manifest\n', text.index('echo "NiceGUI Base'))
        source_call = text.index('verify_source_manifest\n', package_call)
        install = text.index('pip install -r', source_call)
        assert package_call < source_call < install


def test_workbench_display_controls_do_not_depend_on_legacy_lab_css_classes():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    css = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'workbench_css.py').read_text()
    control_source = source[source.index('def _display_control_bar'):source.index('def workbench_navigation')]
    assert 'cui-lab-controlbar' not in control_source
    assert 'cui-workbench-display-controls' in control_source
    assert '.cui-workbench-display-controls{' in css
    assert '.cui-workbench-display-controls__label{' in css


def test_home_promotes_gate2_data_and_generation_through_governed_routes():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    home = source[source.index('def home_page()'):source.index('def build_page()')]
    assert "_action_card('Paste Data'" not in home
    assert "_action_card('Create App'" not in home
    gallery = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'explorer_gallery.py').read_text()
    assert "('Data & Tables'" in gallery
    assert "('Components'" in gallery
    assert "('Full Applications'" in gallery
    assert 'engineering intent' in gallery


def _load_materializer_for_test():
    helper = ROOT / 'materialize_full_repository.py'
    spec = importlib.util.spec_from_file_location('nicegui_base_iteration1_materializer_test', helper)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_materializer_local_repository_input_copies_without_mutating_source(tmp_path):
    helper = _load_materializer_for_test()
    source = tmp_path / 'source-repo'
    (source / 'source').mkdir(parents=True)
    (source / 'source' / 'pyproject.toml').write_text('[project]\nname="nicegui-base"\n', encoding='utf-8')
    (source / 'payload.txt').write_text('original', encoding='utf-8')
    (source / '.git').mkdir()
    (source / '.git' / 'config').write_text('private checkout metadata', encoding='utf-8')
    copied = helper._copy_repository(source, tmp_path / 'materialized')
    assert copied != source
    assert (copied / 'payload.txt').read_text() == 'original'
    assert not (copied / '.git').exists()
    (copied / 'payload.txt').write_text('changed copy', encoding='utf-8')
    assert (source / 'payload.txt').read_text() == 'original'


def test_materializer_cli_supports_download_local_zip_and_local_repository_inputs():
    source = (ROOT / 'materialize_full_repository.py').read_text()
    assert "--source-repo" in source
    assert "--source-zip" in source
    assert '_download_baseline' in source
    assert '_copy_repository' in source
    assert '_safe_extract' in source


def test_final_package_overlay_carries_reconstruction_provenance_helpers():
    helper = _load_apply_helper_for_test()
    assert 'apply_iteration1.py' in helper.OVERLAY_FILES
    assert 'materialize_full_repository.py' in helper.OVERLAY_FILES


def test_wafer_sample_points_bind_status_by_keyword_not_die_coordinate(monkeypatch):
    import nicegui_base.workbench.app as workbench_app

    captured = []
    class StrictWaferPoint:
        def __init__(self, x, y, value=None, die_x=None, die_y=None, status=None, metadata=None):
            assert die_x is None, 'Workbench sample status leaked into die_x positional argument'
            assert die_y is None
            captured.append((x, y, value, status))
            self.x, self.y, self.value, self.status = x, y, value, status

    module = ModuleType('nicegui_base.visualization')
    module.WaferPoint = StrictWaferPoint
    monkeypatch.setitem(sys.modules, 'nicegui_base.visualization', module)
    points = workbench_app._wafer_points()
    assert points
    assert {status for *_rest, status in captured} <= {'normal', 'watch'}
    assert 'watch' in {status for *_rest, status in captured}


def test_full_zip_writer_is_authoritative_package_manifest_allowlisted(tmp_path):
    helper = _load_materializer_for_test()
    root = tmp_path / 'repo'
    root.mkdir()
    # Build the minimum required final-package shape plus one unrelated local file.
    required_payloads = {
        'source/nicegui_base/workbench/app.py': b'app',
        'source/tests/test_workbench_iteration1.py': b'test-iteration1',
        'source/tests/test_workbench_iteration2.py': b'test-iteration2',
        'WORKBENCH_ITERATION2_REPORT.md': b'report-iteration2',
        'apply_iteration2.py': b'apply-iteration2',
        'materialize_full_repository.py': b'materialize',
        'wheel/nicegui_base-3.0.0a8-py3-none-any.whl': b'wheel',
        'source/SHA256SUMS.txt': b'source manifest',
    }
    rows = []
    for rel, data in required_payloads.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rows.append(f'{hashlib.sha256(data).hexdigest()}  {rel}')
    (root / 'PACKAGE_SHA256SUMS.txt').write_text('\n'.join(sorted(rows)) + '\n', encoding='utf-8')
    (root / 'local-secret.txt').write_text('must not ship', encoding='utf-8')
    output = tmp_path / 'full.zip'
    helper._write_full_zip(root, output)
    import zipfile
    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
    assert 'local-secret.txt' not in names
    assert names == set(required_payloads) | {'PACKAGE_SHA256SUMS.txt'}


def test_palette_auto_open_consumes_only_palette_query_parameter():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    install = source[source.index('def _install_command_palette'):source.index('def _shell(')]
    assert "params.delete('palette')" in install
    assert "const remaining=params.toString()" in install
    assert "window.location.pathname+(remaining?'?'+remaining:'')+window.location.hash" in install
    assert "history.replaceState(null,'',window.location.pathname+window.location.hash)" not in install


def test_framework_catalog_item_level_parity_accepts_rich_and_fallback_adapters(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_parity
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind

    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {'registries': {
        'components': [{'_registry_key': 'button'}],
        'page_patterns': [{'_registry_key': 'monitoring'}],
        'runtime': [{'_registry_key': 'doctor'}],
    }}
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = (
        WorkbenchEntry('component:button', WorkbenchKind.COMPONENT, 'Button', 'Action', '/catalog/component/button', metadata={'component_key':'button'}),
        WorkbenchEntry('pattern:monitoring', WorkbenchKind.PATTERN, 'Monitoring', 'Pattern', '/patterns/monitoring', metadata={'pattern_key':'monitoring'}),
        WorkbenchEntry('framework:runtime:doctor', WorkbenchKind.REFERENCE, 'Doctor', 'Runtime', '/catalog/runtime/doctor', metadata={'registry_name':'runtime','registry_key':'doctor'}),
    )
    total, visible, missing = framework_catalog_parity(entries)
    assert (total, visible, missing) == (3, 3, ())
    total, visible, missing = framework_catalog_parity(entries[:-1])
    assert (total, visible) == (3, 2)
    assert missing == (('runtime', 'doctor'),)


def test_quality_and_readiness_gate_item_level_framework_catalog_parity():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert "with _section('Framework coverage'" in source
    assert 'Every packaged canonical framework-catalog record is discoverable' in source
    assert 'catalog_visible == catalog_total' in source
    assert 'not catalog_missing' in source
    assert "catalog={catalog_visible}/{catalog_total}" in source


def test_framework_catalog_parity_covers_string_and_recipe_key_record_shapes(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_parity
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {'registries': {
        'visualizations': ['LineChart', 'WaferMap'],
        'semiconductor_operational_runbooks': [{'recipe_key': 'spc-monitor'}],
    }}
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = (
        WorkbenchEntry('framework:visualizations:LineChart', WorkbenchKind.REFERENCE, 'LineChart', 'Chart', '/catalog/visualizations/LineChart', metadata={'registry_name':'visualizations','registry_key':'LineChart'}),
        WorkbenchEntry('framework:visualizations:WaferMap', WorkbenchKind.REFERENCE, 'WaferMap', 'Chart', '/catalog/visualizations/WaferMap', metadata={'registry_name':'visualizations','registry_key':'WaferMap'}),
        WorkbenchEntry('framework:runbook:spc', WorkbenchKind.REFERENCE, 'SPC runbook', 'Runbook', '/catalog/semiconductor_operational_runbooks/spc-monitor', metadata={'registry_name':'semiconductor_operational_runbooks','registry_key':'spc-monitor'}),
    )
    assert framework_catalog_parity(entries) == (3, 3, ())


def test_framework_catalog_duplicate_detection_uses_authoritative_registry_names(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_duplicate_keys
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {'registries': {
        'page_patterns': [{'_registry_key':'monitoring'}],
        'semiconductor': [{'_registry_key':'fdc_hotelling_t2'}],
    }}
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = (
        WorkbenchEntry('pattern:monitoring', WorkbenchKind.PATTERN, 'Monitoring', 'Pattern', '/patterns/monitoring', metadata={'pattern_key':'monitoring'}),
        WorkbenchEntry('fallback:monitoring', WorkbenchKind.REFERENCE, 'Monitoring fallback', 'Pattern', '/catalog/page_patterns/monitoring', metadata={'registry_name':'page_patterns','registry_key':'monitoring'}),
        WorkbenchEntry('analytics:fdc_hotelling_t2', WorkbenchKind.ANALYTIC, 'T²', 'Analytic', '/analytics/fdc_hotelling_t2', metadata={'surface_key':'fdc_hotelling_t2'}),
    )
    assert framework_catalog_duplicate_keys(entries) == (('page_patterns','monitoring'),)


def test_rich_adapter_fallback_suppression_uses_catalog_registry_names():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'registry_adapters.py').read_text()
    assert "('page_patterns', str(entry.metadata.get('pattern_key')))" in source
    assert "('semiconductor', str(entry.metadata.get('surface_key')))" in source
    assert "('patterns', str(entry.metadata.get('pattern_key')))" not in source
    assert "('semiconductor_surfaces', str(entry.metadata.get('surface_key')))" not in source


def test_framework_catalog_fallback_exposes_string_visualizations_and_recipe_key_records(monkeypatch):
    from nicegui_base.workbench.registry_adapters import framework_catalog_entries
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {'registries': {
        'visualizations': ['LineChart', 'WaferMap'],
        'semiconductor_operational_runbooks': [{'recipe_key':'spc-monitor','use_when':'operate SPC'}],
    }}
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = framework_catalog_entries(known_entries=set())
    identities = {(e.metadata['registry_name'], e.metadata['registry_key']) for e in entries}
    assert identities == {
        ('visualizations','LineChart'), ('visualizations','WaferMap'),
        ('semiconductor_operational_runbooks','spc-monitor'),
    }
    line = next(e for e in entries if e.metadata['registry_key'] == 'LineChart')
    assert line.title == 'LineChart'
    assert line.route == '/studio/framework%3Avisualizations%3ALineChart'
    assert line.metadata['full_reference_route'] == '/charts'
    runbook = next(e for e in entries if e.metadata['registry_name'] == 'semiconductor_operational_runbooks')
    assert runbook.use_when == ('operate SPC',)


def test_build_registry_entries_has_canonical_identity_duplicate_guard():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'registry_adapters.py').read_text()
    assert 'duplicate Workbench canonical catalog identities' in source


def test_framework_catalog_shape_counts_detects_unidentified_declared_records(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_shape_counts
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {
        'registry_counts': {'visualizations': 2, 'runbooks': 1},
        'registries': {'visualizations':['LineChart','WaferMap'], 'runbooks':[{}]},
    }
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    assert framework_catalog_shape_counts() == (3, 2)


def test_framework_catalog_shape_counts_accepts_all_supported_identity_shapes(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_shape_counts
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {
        'registry_counts': {'visualizations': 1, 'runbooks': 1, 'patterns': 1},
        'registries': {
            'visualizations':['LineChart'],
            'runbooks':[{'recipe_key':'spc-monitor'}],
            'page_patterns':[{'_registry_key':'monitoring'}],
        },
    }
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    assert framework_catalog_shape_counts() == (3, 3)


def test_quality_and_health_gate_framework_catalog_declared_shape():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'catalog_declared == catalog_identified == catalog_total' in source
    assert 'Generated framework catalog has a stable identity for all' in source
    assert 'shape={catalog_identified}/{catalog_declared}' in source


def test_wave77_framework_catalog_record_count_is_explicit_readiness_contract():
    from nicegui_base.workbench.catalog import EXPECTED_FRAMEWORK_CATALOG_RECORDS
    assert EXPECTED_FRAMEWORK_CATALOG_RECORDS == 450
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert 'catalog_declared == EXPECTED_FRAMEWORK_CATALOG_RECORDS' in source
    assert 'shape={catalog_identified}/{catalog_declared}/{EXPECTED_FRAMEWORK_CATALOG_RECORDS}' in source


def test_catalog_default_view_is_family_overview_not_full_450_card_dump():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    catalog = source[source.index('def catalog_page'):source.index('def _unknown_detail')]
    assert "if not query.strip() and kind == 'all' and family == 'all':" in catalog
    assert "Choose a family or search to inspect individual capabilities" in catalog
    assert "_standard_button('Browse family'" in catalog


def test_framework_fallbacks_expose_governed_reference_routes(monkeypatch):
    from nicegui_base.workbench.registry_adapters import framework_catalog_entries
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    ai_catalog.load_framework_catalog = lambda: {'registries': {
        'visualizations':['LineChart'], 'tables':[{'_registry_key':'editable_table','purpose':'Edit records'}],
        'runtime':[{'_registry_key':'runtime_doctor','rule':'Validate runtime before deployment.'}],
    }}
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries = framework_catalog_entries(known_entries=set())
    by_registry = {e.metadata['registry_name']:e for e in entries}
    assert by_registry['visualizations'].metadata['full_reference_route'] == '/charts'
    assert by_registry['tables'].metadata['full_reference_route'] == '/data'
    assert by_registry['runtime'].metadata['full_reference_route'] == '/performance'
    assert by_registry['runtime'].description == 'Validate runtime before deployment.'


def test_catalog_detail_delegates_to_capability_studio_with_reference_metadata_preserved():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    detail = source[source.index('def catalog_detail_page'):source.index('def analytics_gallery_page')]
    assert '_studio_entry_page(entry)' in detail
    studio = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'capability_studio.py').read_text()
    assert 'render_catalog_example' in studio
    assert "cui-studio-preview-frame" in studio


def test_framework_catalog_audit_uses_one_payload_snapshot(monkeypatch):
    from nicegui_base.workbench.catalog import framework_catalog_audit
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    calls = {'count':0}
    ai_pkg = ModuleType('nicegui_base.ai')
    ai_catalog = ModuleType('nicegui_base.ai.catalog')
    def load():
        calls['count'] += 1
        return {'registry_counts': {'components':1}, 'registries': {'components':[{'_registry_key':'button'}]}}
    ai_catalog.load_framework_catalog = load
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai', ai_pkg)
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.catalog', ai_catalog)
    entries=(WorkbenchEntry('component:button',WorkbenchKind.COMPONENT,'Button','Action','/catalog/component/button',metadata={'component_key':'button'}),)
    audit=framework_catalog_audit(entries)
    assert calls['count'] == 1
    assert (audit.declared,audit.identified,audit.canonical_total,audit.visible,audit.missing,audit.duplicates) == (1,1,1,1,(),())


def test_quality_and_health_use_single_framework_catalog_audit_snapshot():
    source = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text()
    assert source.count('catalog_audit = framework_catalog_audit(entries)') == 2
    assert 'framework_catalog_parity(entries)' not in source
    assert 'framework_catalog_duplicate_keys(entries)' not in source


def test_search_ranking_prefers_engineering_capability_over_generic_asset_for_bare_noun():
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    from nicegui_base.workbench.search import search_entries
    entries=(
        WorkbenchEntry('recipe:lot-wafer-explorer',WorkbenchKind.RECIPE,'LotWaferExplorer','Explore wafer spatial signatures','/recipes/lot-wafer-explorer',aliases=('wafer',),metadata={'recipe_key':'lot-wafer-explorer'}),
        WorkbenchEntry('analytics:wafer_continuous',WorkbenchKind.ANALYTIC,'Wafer Continuous','Continuous wafer map','/analytics/wafer_continuous',aliases=('wafer map',),metadata={'surface_key':'wafer_continuous'}),
        WorkbenchEntry('framework:icons:wafer',WorkbenchKind.REFERENCE,'Wafer','Canonical wafer icon','/catalog/icons/wafer',metadata={'registry_name':'icons','registry_key':'wafer'}),
    )
    results=search_entries(entries,'wafer',limit=10)
    assert results[0].entry.kind in {WorkbenchKind.RECIPE, WorkbenchKind.ANALYTIC}
    assert results[-1].entry.metadata.get('registry_name') == 'icons'


def test_search_ranking_restores_asset_priority_when_asset_intent_is_explicit():
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    from nicegui_base.workbench.search import search_entries
    entries=(
        WorkbenchEntry('recipe:lot-wafer-explorer',WorkbenchKind.RECIPE,'LotWaferExplorer','Explore wafer signatures','/recipes/lot-wafer-explorer',aliases=('wafer',),metadata={'recipe_key':'lot-wafer-explorer'}),
        WorkbenchEntry('framework:icons:wafer',WorkbenchKind.REFERENCE,'Wafer Icon','Canonical wafer SVG icon','/catalog/icons/wafer',aliases=('wafer icon',),metadata={'registry_name':'icons','registry_key':'wafer'}),
    )
    results=search_entries(entries,'wafer icon',limit=10)
    assert results[0].entry.metadata.get('registry_name') == 'icons'


def test_search_ranking_boosts_patterns_and_recipes_for_explicit_app_intent():
    from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind
    from nicegui_base.workbench.search import search_entries
    entries=(
        WorkbenchEntry('pattern:monitoring',WorkbenchKind.PATTERN,'Monitoring','Operational health and alerts','/patterns/monitoring',aliases=('monitoring app',),metadata={'pattern_key':'monitoring'}),
        WorkbenchEntry('framework:content:monitoring',WorkbenchKind.REFERENCE,'Monitoring','Monitoring metadata','/catalog/content/monitoring',aliases=('monitoring',),metadata={'registry_name':'content','registry_key':'monitoring'}),
    )
    assert search_entries(entries,'monitoring app')[0].entry.kind is WorkbenchKind.PATTERN
