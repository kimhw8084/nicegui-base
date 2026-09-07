from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from nicegui_base.ai.scaffold import install_ai_materials
from nicegui_base.version import FRAMEWORK_VERSION

_PROJECT_NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9 _.-]{1,79}$')
_TEMPLATE_NAMES = ('dashboard', 'data-explorer', 'crud', 'analysis-workspace', 'responsive-operations', 'async-workflow')
_PATTERN_TEMPLATE_MAP = {
    'dashboard': 'dashboard', 'data_explorer': 'data-explorer', 'master_detail': 'analysis-workspace',
    'crud': 'crud', 'monitoring': 'dashboard', 'search': 'data-explorer', 'settings': 'analysis-workspace',
    'wizard': 'analysis-workspace', 'comparison': 'analysis-workspace', 'analysis_workspace': 'analysis-workspace',
}


@dataclass(frozen=True, slots=True)
class CreatedApplication:
    root: Path
    name: str
    template: str
    framework_version: str
    written: tuple[Path, ...]
    recipe: str | None = None
    recipe_variant: str | None = None
    pattern: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            'root': str(self.root),
            'name': self.name,
            'template': self.template,
            'framework_version': self.framework_version,
            'written': [str(path) for path in self.written],
            'recipe': self.recipe,
            'recipe_variant': self.recipe_variant,
            'pattern': self.pattern,
        }


def _module_name(name: str) -> str:
    value = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    return value or 'company_app'


def _home_source(template: str) -> str:
    if template == 'dashboard':
        return '''from nicegui_base import AxisSpec, AxisType, DashboardPage, Icons, LayoutSlot, LineChart, MetricCard, MetricStrip, SeriesSpec, StatusIntent, TrendDirection\n\n\ndef build_page() -> None:\n    with DashboardPage('Operations overview', 'Fast status, trend and exception scanning.') as page:\n        with page.slot(LayoutSlot.METRICS):\n            with MetricStrip():\n                MetricCard('Availability', '99.4%', delta='+0.3 pp', trend=TrendDirection.UP, intent=StatusIntent.SUCCESS, icon=Icons.CHECK)\n                MetricCard('Open alerts', 7, delta='-3', trend=TrendDirection.DOWN, intent=StatusIntent.SUCCESS, icon=Icons.WARNING)\n        with page.slot(LayoutSlot.PRIMARY):\n            LineChart('Throughput trend', (SeriesSpec('throughput', 'Throughput', (84, 87, 91, 93, 96), smooth=True),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('06:00','09:00','12:00','15:00','18:00')))\n'''
    if template == 'data-explorer':
        return '''from nicegui_base import Aggregation, AxisSpec, AxisType, BarChart, ColumnKind, DataExplorerPage, DataSession, Dataset, Dimension, LayoutSlot, Metric, MetricCard, MetricStrip, SeriesSpec, TableColumn, DataTable\n\n_ROWS = (\n    {'id':'A-101','area':'ETCH','output':112,'yield_pct':98.7},\n    {'id':'A-102','area':'ETCH','output':104,'yield_pct':97.9},\n    {'id':'A-103','area':'CVD','output':121,'yield_pct':99.1},\n)\n\ndef make_session() -> DataSession:\n    return DataSession(Dataset('production', _ROWS, row_key='id', dimensions=(Dimension('area'),), metrics=(Metric('output', aggregation=Aggregation.SUM), Metric('yield_pct', aggregation=Aggregation.AVG))))\n\ndef build_page() -> None:\n    session = make_session()\n    grouped = session.aggregate(dimensions=('area',), metrics=('output',)).rows\n    with DataExplorerPage('Production explorer', 'One governed data session drives every analytical surface.') as page:\n        with page.slot(LayoutSlot.METRICS):\n            with MetricStrip():\n                MetricCard('Total output', session.metric('output'))\n                MetricCard('Average yield', f"{session.metric('yield_pct'):.1f}%")\n        with page.slot(LayoutSlot.PRIMARY):\n            BarChart('Output by area', (SeriesSpec('output','Output',[row['output'] for row in grouped]),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=tuple(row['area'] for row in grouped)))\n        with page.slot(LayoutSlot.DATA):\n            DataTable(session.rows().rows, (TableColumn('id','Record'), TableColumn('area','Area'), TableColumn('output','Output',kind=ColumnKind.INTEGER), TableColumn('yield_pct','Yield',kind=ColumnKind.PERCENT,decimals=1)), row_key='id', title='Production records')\n'''
    if template == 'crud':
        return '''from nicegui_base import Button, ButtonIntent, CrudPage, DataTable, Icons, LayoutSlot, TableColumn\nfrom services.equipment import EquipmentService\n\n\ndef build_page(service: EquipmentService | None = None) -> None:\n    service = service or EquipmentService()\n    with CrudPage('Equipment', 'Search, inspect and manage equipment records.') as page:\n        with page.slot(LayoutSlot.ACTIONS):\n            Button('Add equipment', intent=ButtonIntent.PRIMARY, icon=Icons.ADD)\n        with page.slot(LayoutSlot.DATA):\n            DataTable(service.rows(), (TableColumn('equipment_id','Equipment'), TableColumn('area','Area'), TableColumn('owner','Owner')), row_key='equipment_id', title='Equipment records')\n'''
    if template == 'analysis-workspace':
        return '''from nicegui_base import Aggregation, AnalysisWorkspacePage, ApplicationRuntime, Dataset, Dimension, LayoutSlot, Metric, MetricCard, MetricStrip, PanelSpec, StateKey, StateNamespace, WorkspaceBreakpoint\n\n_RUNTIME = ApplicationRuntime()\n_RUNTIME.data.register(Dataset('analysis', ({'id':1,'area':'ETCH','value':12.4},{'id':2,'area':'CVD','value':13.1}), row_key='id', dimensions=(Dimension('area'),), metrics=(Metric('value', aggregation=Aggregation.AVG),)))\n_WORKSPACE = _RUNTIME.open_workspace('analysis')\n_WORKSPACE.open_data_session('analysis', session_id='primary')\n_WORKSPACE.layout.register_panel(PanelSpec('primary', preferred_columns=8, preferred_rows=5))\n_WORKSPACE.layout.register_panel(PanelSpec('detail', preferred_columns=4, preferred_rows=5))\n_WORKSPACE.layout.derive_breakpoint(WorkspaceBreakpoint.PHONE, source=WorkspaceBreakpoint.DESKTOP)\n_SELECTION = StateKey[str | None]('selected_record', namespace=StateNamespace.WORKSPACE, default=None)\n_WORKSPACE.state.set(_SELECTION, None, source='initial')\n\n\ndef build_page() -> None:\n    session = _WORKSPACE.data_session('primary')\n    with AnalysisWorkspacePage('Analysis workspace', 'Shared runtime, data and layout ownership.') as page:\n        with page.slot(LayoutSlot.PRIMARY):\n            with MetricStrip():\n                MetricCard('Average value', f"{session.metric('value'):.2f}")\n'''
    if template == 'responsive-operations':
        return '''from nicegui_base import DashboardPage, LayoutSlot, MetricCard, MetricStrip, PanelSpec, WorkspaceLayoutEngine, WorkspaceBreakpoint\n\n_LAYOUT = WorkspaceLayoutEngine()\n_LAYOUT.register_panel(PanelSpec('summary', preferred_columns=12, preferred_rows=3))\n_LAYOUT.register_panel(PanelSpec('operations', preferred_columns=8, preferred_rows=6))\n_LAYOUT.register_panel(PanelSpec('exceptions', preferred_columns=4, preferred_rows=6))\n_LAYOUT.derive_breakpoint(WorkspaceBreakpoint.TABLET, source=WorkspaceBreakpoint.DESKTOP)\n_LAYOUT.derive_breakpoint(WorkspaceBreakpoint.PHONE, source=WorkspaceBreakpoint.TABLET)\n\n\ndef build_page() -> None:\n    with DashboardPage('Responsive operations', 'NiceGUI Base owns breakpoint geometry; page code owns composition.') as page:\n        with page.slot(LayoutSlot.METRICS):\n            with MetricStrip():\n                MetricCard('Running', 42)\n                MetricCard('Attention', 3)\n'''
    if template == 'async-workflow':
        return '''from nicegui_base import AsyncAction, Button, ButtonIntent, DashboardPage, DuplicatePolicy, LayoutSlot, MetricCard, MetricStrip\n\n_SAVE = AsyncAction[str](timeout=10.0, duplicate_policy=DuplicatePolicy.IGNORE)\n\nasync def save_record() -> str:\n    async def operation() -> str:\n        return 'saved'\n    return await _SAVE.run(operation) or 'saved'\n\ndef build_page() -> None:\n    with DashboardPage('Async workflow', 'Runtime-owned async actions prevent duplicate submissions and lifecycle leaks.') as page:\n        with page.slot(LayoutSlot.METRICS):\n            with MetricStrip():\n                MetricCard('Queue', 0)\n        with page.slot(LayoutSlot.ACTIONS):\n            Button('Save', intent=ButtonIntent.PRIMARY, on_click=save_record)\n'''
    raise KeyError(template)


def _semiconductor_home_source(recipe_key: str, variant_key: str | None = None) -> str:
    return f'''from __future__ import annotations\nfrom nicegui_base import AnalysisContext, AnalysisWorkspacePage, LayoutSlot, MetricCard, MetricStrip, NiceGUIWorkspace, RecipePanelKind, SelectionBus, SemiconductorAnalyticalPanel, SemiconductorSetupWizard, WorkspaceController, create_semiconductor_recipe_runtime, get_semiconductor_recipe, resolve_recipe_configuration\nfrom recipe_config import BENCHMARK_PROFILE, CUSTOMIZATION, FIELD_OVERRIDES, RECIPE_VARIANT, RUNTIME_POLICY\nfrom services.data_adapter import ProjectSemiconductorAdapter, conformance_report\n\n_RECIPE = get_semiconductor_recipe({recipe_key!r})\n_CONFIGURATION = resolve_recipe_configuration(_RECIPE, variant=RECIPE_VARIANT, customization=CUSTOMIZATION)\n_CONTEXT = AnalysisContext(source_key="semiconductor")\n_SELECTIONS = SelectionBus()\n_WORKSPACE = WorkspaceController()\nfor _panel in _CONFIGURATION.recipe.panels:\n    _WORKSPACE.register_panel(_panel.workspace_spec())\n\n\nasync def prepare_runtime(source=None):\n    provider = source if source is not None else ProjectSemiconductorAdapter()\n    return await create_semiconductor_recipe_runtime(\n        _RECIPE.key, provider, variant=RECIPE_VARIANT, customization=CUSTOMIZATION,\n        field_overrides=FIELD_OVERRIDES, context=_CONTEXT, selections=_SELECTIONS, policy=RUNTIME_POLICY,\n    )\n\n\nasync def prepare_runtime_setup(source=None):\n    runtime = await prepare_runtime(source)\n    probe = await runtime.refresh()\n    return runtime, runtime.onboarding_view(), runtime.experience_state(probe)\n\n\nasync def prepare_guided_setup(source=None, *, include_conformance=False, include_benchmark=False):\n    runtime = await prepare_runtime(source)\n    probe = await runtime.refresh()\n    conformance = await conformance_report(_RECIPE) if include_conformance and source is None else None\n    benchmark = await runtime.benchmark(profile=BENCHMARK_PROFILE) if include_benchmark else None\n    return runtime, runtime.setup_workflow(probe=probe, adapter_conformance=conformance, benchmark=benchmark)\n\n\ndef render_guided_setup(workflow) -> None:\n    SemiconductorSetupWizard(workflow)\n\n\ndef review_runtime_configuration(runtime, *, adapter_conformance=None, benchmark=None):\n    return runtime.configuration_review(adapter_conformance=adapter_conformance, benchmark=benchmark)\n\n\nasync def prepare_analysis(source=None):\n    # Compatibility boundary retained for Wave 62 generated-app integrations.\n    return (await prepare_runtime(source)).assembly\n\n\ndef _render_recipe_panel(panel) -> None:\n    if panel.kind is RecipePanelKind.ANALYTICAL:\n        with SemiconductorAnalyticalPanel(panel.surface_key, _CONTEXT, _SELECTIONS, title=panel.title, description=panel.description):\n            MetricCard("Surface", panel.surface_key.replace("_", " "))\n    else:\n        MetricCard(panel.title, panel.kind.value.replace("_", " " ).title())\n\n\ndef build_page() -> None:\n    with AnalysisWorkspacePage(_CONFIGURATION.recipe.application_name, _CONFIGURATION.recipe.purpose) as page:\n        with page.slot(LayoutSlot.PRIMARY):\n            with MetricStrip():\n                MetricCard("Recipe", _CONFIGURATION.recipe.application_name)\n                MetricCard("Variant", _CONFIGURATION.variant_key or "Canonical")\n                MetricCard("Panels", len(_CONFIGURATION.recipe.panels))\n            workspace = NiceGUIWorkspace(_WORKSPACE)\n            for panel in _CONFIGURATION.recipe.panels:\n                workspace.add_panel(panel.workspace_spec(), lambda panel=panel: _render_recipe_panel(panel))\n'''


def _service_source() -> str:
    return '''from dataclasses import dataclass\n\n@dataclass(frozen=True, slots=True)\nclass Equipment:\n    equipment_id: str\n    area: str\n    owner: str\n\nclass EquipmentService:\n    def rows(self) -> list[dict[str, str]]:\n        records = (Equipment('ETCH-01','ETCH','A. Kim'), Equipment('CVD-04','CVD','J. Lee'))\n        return [{'equipment_id': item.equipment_id, 'area': item.area, 'owner': item.owner} for item in records]\n'''


def _semiconductor_source_source() -> str:
    return '''from __future__ import annotations\nfrom nicegui_base import InMemoryDataSource\n\n# Replace this governed fixture with a production DataSource provider adapter. Keep the\n# page/recipe layer provider-neutral so SQL/CSV/company backends can preserve pushdown.\n_ROWS = (\n    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},\n    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},\n    {'id':'M3','timestamp':'2026-08-29T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L2','wafer':'W02','x':1.0,'y':0.0,'value':9.9,'sensor':'pressure','sensor_value':1.1,'bin':'B2','count':2.0,'yield_pct':99.0,'category':'B2','defect_class':'scratch'},\n)\n\n\ndef build_source() -> InMemoryDataSource:\n    return InMemoryDataSource('semiconductor', _ROWS)\n'''


def _semiconductor_adapter_source() -> str:
    return '''from __future__ import annotations\nfrom nicegui_base import ProviderAdapterManifest, ProviderConformanceFixture, SemiconductorProviderAdapterBase, run_provider_conformance_suite\nfrom services.data_source import build_source\n\n\nclass ProjectSemiconductorAdapter(SemiconductorProviderAdapterBase):\n    """Replace build_source internals with the approved provider; keep page code provider-neutral."""\n    manifest = ProviderAdapterManifest("project", "Project semiconductor provider")\n\n    async def build_source(self, recipe):\n        return build_source()\n\n    def field_overrides(self, recipe):\n        return {}\n\n\nasync def conformance_report(recipe, *, profile="development"):\n    # Development fixtures deliberately do not claim production pushdown.\n    fixture = ProviderConformanceFixture(f"{recipe.key}-{profile}", recipe.key, profile)\n    suite = await run_provider_conformance_suite(ProjectSemiconductorAdapter(), (fixture,))\n    return suite.results[0].report\n'''


def _semiconductor_recipe_config_source(variant_key: str | None) -> str:
    return f'''from nicegui_base import RecipeCustomization, RecipeRuntimePolicy\n\n# Governed app-specific configuration. Keep provider semantics in services/data_adapter.py.\nRECIPE_VARIANT = {variant_key!r}\nFIELD_OVERRIDES = {{}}\nCUSTOMIZATION = RecipeCustomization()\nRUNTIME_POLICY = RecipeRuntimePolicy(strict_bindings=True, smart_bindings=True, record_page_size=100)\nBENCHMARK_PROFILE = "development-smoke"  # change to provider-rc only on representative target data\n'''


def _semiconductor_release_evidence_source() -> str:
    return '''from __future__ import annotations
from nicegui_base import (
    apply_target_execution_intake, assess_semiconductor_operational_readiness, assimilate_enterprise_target_evidence,
    build_promotion_operation_record, build_provider_qualification_pack, build_release_audit_closure,
    build_semiconductor_operational_runbook, build_semiconductor_promotion_decision, build_semiconductor_target_evidence_bundle,
    build_incident_rollback_audit_closure, build_operational_assurance_continuity_dossier, build_operational_assurance_renewal_ledger, build_longitudinal_operational_assurance_dossier, build_evidence_exception_governance_dossier, build_post_release_stability_evidence, build_stable_promotion_candidate, build_stable_promotion_operational_handoff, build_stable_post_promotion_verification, build_stable_release_promotion_closure, build_stable_rollback_readiness_verification, build_sustained_operations_evidence_acceptance, build_sustained_operations_evidence_renewal,
    load_incident_rollback_audit_manifest, load_longitudinal_assurance_review_manifest, load_promotion_execution_adapter_qualification_manifest, load_post_release_stability_manifest, load_stable_post_promotion_verification_manifest, load_stable_release_evidence_acceptance_manifest, load_stable_release_publication_evidence_manifest, load_stable_rollback_readiness_manifest, load_sustained_operations_evidence_acceptance_manifest, load_sustained_operations_evidence_renewal_manifest, load_target_execution_intake_manifest,
    package_incident_rollback_audit_closure, package_operational_assurance_continuity_dossier, package_longitudinal_operational_assurance_dossier, package_evidence_exception_governance_dossier, package_promotion_operational_handoff, package_release_audit_closure, package_stable_post_promotion_verification, package_stable_promotion_candidate, package_stable_release_promotion_closure, package_stable_rollback_readiness_verification,
    verify_incident_rollback_audit_archive, verify_longitudinal_operational_assurance_archive, verify_operational_assurance_continuity_archive, verify_operational_assurance_renewal_ledger, verify_post_release_stability_evidence, verify_promotion_execution_adapter_qualification, verify_release_audit_archive, verify_stable_post_promotion_archive, verify_stable_promotion_closure_archive, verify_stable_release_evidence_acceptance, verify_stable_release_publication_evidence, verify_stable_rollback_readiness_archive, verify_sustained_operations_evidence_acceptance, verify_sustained_operations_evidence_renewal, write_semiconductor_target_evidence,
)


def capture_release_evidence(path, runtime, *, adapter_conformance=None, performance=None, benchmark=None, installed_nicegui_pass=None, server_websocket_pass=None, browser_pass=None, human_visual_baseline_pass=None, artifacts=()):
    bundle = build_semiconductor_target_evidence_bundle(
        runtime.recipe.key, adapter_conformance=adapter_conformance, performance=performance, benchmark=benchmark,
        installed_nicegui_pass=installed_nicegui_pass, server_websocket_pass=server_websocket_pass,
        browser_pass=browser_pass, human_visual_baseline_pass=human_visual_baseline_pass, artifacts=tuple(artifacts),
        metadata={"variant_key": runtime.configuration.variant_key, "source_key": runtime.source.key, "provider": runtime.source.provider},
    )
    write_semiconductor_target_evidence(path, bundle)
    return bundle


def evaluate_stable_promotion(runtime, bundle, *, adapter_conformance=None, performance=None, benchmark=None, base_dir=None):
    readiness = assess_semiconductor_operational_readiness(
        runtime, adapter_conformance=adapter_conformance, performance=performance, benchmark=benchmark,
    )
    qualification = build_provider_qualification_pack((bundle,), provider=runtime.source.provider, base_dir=base_dir)
    decision = build_semiconductor_promotion_decision(qualification, operational_readiness={runtime.recipe.key: readiness})
    return readiness, qualification, decision, build_semiconductor_operational_runbook(runtime.recipe.key)


def assemble_stable_promotion_candidate(runtime, bundles, *, adapter_conformance=None, performance=None, benchmark=None, rehearsals=(), base_dir=None):
    readiness = assess_semiconductor_operational_readiness(
        runtime, adapter_conformance=adapter_conformance, performance=performance, benchmark=benchmark,
    )
    evidence = assimilate_enterprise_target_evidence(
        tuple(bundles), operational_readiness=(readiness,), provider=runtime.source.provider,
        required_recipe_keys=(runtime.recipe.key,), base_dir=base_dir,
    )
    return build_stable_promotion_candidate(evidence, rehearsals=tuple(rehearsals))


def package_release_candidate(path, candidate, *, artifact_base_dir=None, include_verified_artifacts=True):
    return package_stable_promotion_candidate(
        path, candidate, artifact_base_dir=artifact_base_dir, include_verified_artifacts=include_verified_artifacts,
    )


def assimilate_target_execution(bundle, manifest_path, *, artifact_base_dir=None):
    intake = load_target_execution_intake_manifest(manifest_path, artifact_base_dir=artifact_base_dir)
    return apply_target_execution_intake(bundle, intake)


def prepare_operational_handoff(candidate, candidate_package_path, *, change_reference=None, package_path=None):
    handoff = build_stable_promotion_operational_handoff(
        candidate, candidate_package_path, change_reference=change_reference,
    )
    package = None if package_path is None else package_promotion_operational_handoff(package_path, handoff)
    return handoff, package


def record_operational_execution(handoff, recipe_key, kind, *, completed_step_keys=(), failed_step_keys=(), evidence=(), notes=()):
    return build_promotion_operation_record(
        handoff, recipe_key, kind, completed_step_keys=completed_step_keys, failed_step_keys=failed_step_keys,
        evidence=evidence, notes=notes,
    )


def qualify_promotion_execution_adapter(manifest_path, *, artifact_base_dir=None):
    qualification = load_promotion_execution_adapter_qualification_manifest(manifest_path, artifact_base_dir=artifact_base_dir)
    return qualification, verify_promotion_execution_adapter_qualification(qualification, base_dir=artifact_base_dir)


def close_release_audit(handoff, execution_adapter_qualification, operation_records=(), *, artifact_base_dir=None, package_path=None):
    audit = build_release_audit_closure(
        handoff, execution_adapter_qualification, tuple(operation_records), artifact_base_dir=artifact_base_dir,
    )
    package = None if package_path is None else package_release_audit_closure(package_path, audit, artifact_base_dir=artifact_base_dir)
    return audit, package


def accept_stable_release_evidence(audit, audit_package_path, manifest_path, *, artifact_base_dir=None):
    archive_verification = verify_release_audit_archive(audit_package_path, expected_audit=audit)
    acceptance = load_stable_release_evidence_acceptance_manifest(
        manifest_path, audit, audit_package_path, artifact_base_dir=artifact_base_dir,
    )
    verification = verify_stable_release_evidence_acceptance(
        acceptance, audit=audit, audit_archive_path=audit_package_path, base_dir=artifact_base_dir,
    )
    return acceptance, verification, archive_verification


def close_stable_promotion_evidence(audit, audit_package_path, acceptance, *, artifact_base_dir=None, package_path=None):
    closure = build_stable_release_promotion_closure(
        audit, audit_package_path, acceptance, artifact_base_dir=artifact_base_dir,
    )
    package = None if package_path is None else package_stable_release_promotion_closure(
        package_path, closure, artifact_base_dir=artifact_base_dir,
    )
    return closure, package


def intake_stable_release_publication(closure, closure_package_path, manifest_path, *, artifact_base_dir=None):
    archive_verification = verify_stable_promotion_closure_archive(closure_package_path, expected_closure=closure)
    publication = load_stable_release_publication_evidence_manifest(
        manifest_path, closure, closure_package_path, artifact_base_dir=artifact_base_dir,
    )
    verification = verify_stable_release_publication_evidence(
        publication, closure=closure, closure_archive_path=closure_package_path, base_dir=artifact_base_dir,
    )
    return publication, verification, archive_verification


def verify_post_promotion_release(closure, closure_package_path, publication, manifest_path, *, artifact_base_dir=None, package_path=None):
    verification = load_stable_post_promotion_verification_manifest(
        manifest_path, closure, closure_package_path, publication, artifact_base_dir=artifact_base_dir,
    )
    package = None if package_path is None else package_stable_post_promotion_verification(
        package_path, verification, artifact_base_dir=artifact_base_dir,
    )
    return verification, package


def intake_post_release_stability(post_verification, post_promotion_package_path, manifest_path, *, artifact_base_dir=None):
    archive_verification = verify_stable_post_promotion_archive(post_promotion_package_path, expected_verification=post_verification)
    evidence = load_post_release_stability_manifest(
        manifest_path, post_verification, post_promotion_package_path, artifact_base_dir=artifact_base_dir,
    )
    verification = verify_post_release_stability_evidence(
        evidence, post_verification=post_verification, post_promotion_archive_path=post_promotion_package_path, base_dir=artifact_base_dir,
    )
    return evidence, verification, archive_verification


def verify_rollback_readiness(post_verification, post_promotion_package_path, stability_evidence, manifest_path, *, artifact_base_dir=None, package_path=None):
    verification = load_stable_rollback_readiness_manifest(
        manifest_path, post_verification, post_promotion_package_path, stability_evidence, artifact_base_dir=artifact_base_dir,
    )
    package = None if package_path is None else package_stable_rollback_readiness_verification(
        package_path, verification, artifact_base_dir=artifact_base_dir,
    )
    return verification, package



def accept_sustained_operations(readiness, readiness_package_path, manifest_path, *, artifact_base_dir=None):
    archive_verification = verify_stable_rollback_readiness_archive(readiness_package_path, expected_readiness=readiness)
    acceptance = load_sustained_operations_evidence_acceptance_manifest(
        manifest_path, readiness, readiness_package_path, artifact_base_dir=artifact_base_dir,
    )
    verification = verify_sustained_operations_evidence_acceptance(
        acceptance, readiness, readiness_package_path, base_dir=artifact_base_dir,
    )
    return acceptance, verification, archive_verification


def close_incident_rollback_audit(readiness, readiness_package_path, sustained_operations_acceptance, manifest_path, *, artifact_base_dir=None, package_path=None):
    closure = load_incident_rollback_audit_manifest(
        manifest_path, readiness, readiness_package_path, sustained_operations_acceptance, artifact_base_dir=artifact_base_dir,
    )
    package = None if package_path is None else package_incident_rollback_audit_closure(
        package_path, closure, artifact_base_dir=artifact_base_dir,
    )
    return closure, package


def renew_sustained_operations(incident_rollback_audit, audit_package_path, manifest_path, *, artifact_base_dir=None, now=None):
    archive_verification = verify_incident_rollback_audit_archive(audit_package_path, expected_closure=incident_rollback_audit)
    renewal = load_sustained_operations_evidence_renewal_manifest(
        manifest_path, incident_rollback_audit, audit_package_path, artifact_base_dir=artifact_base_dir,
    )
    verification = verify_sustained_operations_evidence_renewal(
        renewal, incident_rollback_audit, audit_package_path, base_dir=artifact_base_dir, now=now,
    )
    return renewal, verification, archive_verification


def build_operational_assurance_continuity(incident_rollback_audit, audit_package_path, renewal, *, artifact_base_dir=None, now=None, package_path=None):
    dossier = build_operational_assurance_continuity_dossier(
        incident_rollback_audit, audit_package_path, renewal, artifact_base_dir=artifact_base_dir, now=now,
    )
    package = None if package_path is None else package_operational_assurance_continuity_dossier(
        package_path, dossier, artifact_base_dir=artifact_base_dir, now=now,
    )
    return dossier, package


def build_operational_assurance_history(continuity_package_paths, *, now=None):
    return build_operational_assurance_renewal_ledger(tuple(continuity_package_paths), now=now)


def build_longitudinal_assurance(ledger, *, now=None, review_reference=None, package_path=None):
    dossier = build_longitudinal_operational_assurance_dossier(ledger, now=now, review_reference=review_reference)
    package = None if package_path is None else package_longitudinal_operational_assurance_dossier(package_path, dossier, now=now)
    return dossier, package


def review_longitudinal_assurance(dossier, dossier_package_path, review_manifest_path, *, artifact_base_dir=None, now=None):
    archive_verification = verify_longitudinal_operational_assurance_archive(dossier_package_path, expected_dossier=dossier)
    review = load_longitudinal_assurance_review_manifest(
        review_manifest_path, dossier, dossier_package_path, artifact_base_dir=artifact_base_dir, now=now,
    )
    return review, archive_verification


def govern_evidence_exceptions(review, *, artifact_base_dir=None, now=None, package_path=None):
    dossier = build_evidence_exception_governance_dossier(review, artifact_base_dir=artifact_base_dir, now=now)
    package = None if package_path is None else package_evidence_exception_governance_dossier(
        package_path, dossier, artifact_base_dir=artifact_base_dir, now=now,
    )
    return dossier, package
'''

def create_application(destination: str | Path, *, name: str, template: str = 'analysis-workspace', recipe: str | None = None, recipe_variant: str | None = None, pattern: str | None = None, overwrite: bool = False) -> CreatedApplication:
    if not _PROJECT_NAME_RE.match(name.strip()):
        raise ValueError('name must start with a letter and contain 2-80 letters, numbers, spaces, dot, underscore or dash characters')
    if template not in _TEMPLATE_NAMES:
        raise ValueError(f'unknown template {template!r}; choose one of: {", ".join(_TEMPLATE_NAMES)}')
    pattern_key = None
    if pattern is not None:
        pattern_key = str(pattern).strip()
        required_template = _PATTERN_TEMPLATE_MAP.get(pattern_key)
        if required_template is None:
            raise ValueError(f'unknown canonical application pattern {pattern!r}; choose one of: {", ".join(_PATTERN_TEMPLATE_MAP)}')
        if template != required_template:
            raise ValueError(f'pattern {pattern_key!r} requires template {required_template!r}')
    recipe_key = None
    variant_key = None
    if recipe is not None:
        from nicegui_base.semiconductor import get_semiconductor_recipe, get_semiconductor_recipe_variant
        if template != 'analysis-workspace':
            raise ValueError('semiconductor recipes require the analysis-workspace base template')
        recipe_key = get_semiconductor_recipe(recipe).key
        if recipe_variant is not None:
            variant = get_semiconductor_recipe_variant(recipe_variant)
            if variant.recipe_key != recipe_key:
                raise ValueError(f'recipe variant {variant.key!r} belongs to {variant.recipe_key!r}, not {recipe_key!r}')
            variant_key = variant.key
    elif recipe_variant is not None:
        raise ValueError('recipe_variant requires a semiconductor recipe')

    root = Path(destination).resolve()
    if root.exists() and any(root.iterdir()) and not overwrite:
        raise FileExistsError(f'{root} is not empty; use --overwrite only when replacement is intentional')
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def write(rel: str, content: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise FileExistsError(path)
        path.write_text(content, encoding='utf-8')
        written.append(path)

    module_name = _module_name(name)
    write('app.py', f'''from __future__ import annotations\nimport os\nfrom nicegui_base import NiceGUIRuntimeAdapter, RuntimeConfig\nfrom pages.home import build_page\n\n\ndef runtime() -> NiceGUIRuntimeAdapter:\n    return NiceGUIRuntimeAdapter(RuntimeConfig({name!r}, app_version='0.1.0', host=os.getenv('NICEGUI_BASE_HOST','127.0.0.1'), port=int(os.getenv('NICEGUI_BASE_PORT','8080')), require_storage_secret=False, show_browser=False))\n\ndef main() -> None:\n    runtime().run(root=build_page)\n\nif __name__ == '__main__':\n    main()\n''')
    write('pages/__init__.py', '')
    write('pages/home.py', _semiconductor_home_source(recipe_key, variant_key) if recipe_key else _home_source(template))
    write('services/__init__.py', '')
    write('services/equipment.py', _service_source())
    if recipe_key:
        write('services/data_source.py', _semiconductor_source_source())
        write('services/data_adapter.py', _semiconductor_adapter_source())
        write('services/release_evidence.py', _semiconductor_release_evidence_source())
        write('services/provider_fixtures.json', '{\n  "schema_version": 1,\n  "fixtures": [{"name": "'+recipe_key+'-development", "recipe_key": "'+recipe_key+'", "profile_key": "development", "field_overrides": {}, "metadata": {}}]\n}\n')
        write('recipe_config.py', _semiconductor_recipe_config_source(variant_key))
    write('domain/__init__.py', '')
    write('data/__init__.py', '')

    project_test = f'''from nicegui_base import FRAMEWORK_VERSION\nimport app\n\ndef test_framework_contract() -> None:\n    assert FRAMEWORK_VERSION == {FRAMEWORK_VERSION!r}\n    assert callable(app.runtime)\n    assert callable(app.main)\n'''
    if recipe_key:
        project_test += f'''\nimport asyncio\nfrom pages.home import _RECIPE, prepare_analysis, prepare_guided_setup\n\ndef test_semiconductor_recipe_contract() -> None:\n    assert _RECIPE.key == {recipe_key!r}\n    assembly = asyncio.run(prepare_analysis())\n    assert assembly.recipe.key == {recipe_key!r}\n    assert assembly.compatibility.compatible\n    assert assembly.surfaces\n    asyncio.run(assembly.aclose(close_source=True))\n'''
    write('tests/test_project_contract.py', project_test)
    write('requirements.txt', f'nicegui-base=={FRAMEWORK_VERSION}\n')
    write('requirements-dev.txt', '-r requirements.txt\npytest>=8,<9\n')
    recipe_line = f'recipe = {recipe_key!r}\n' if recipe_key else ''
    variant_line = f'recipe_variant = {variant_key!r}\n' if variant_key else ''
    pattern_line = f'pattern = {pattern_key!r}\n' if pattern_key else ''
    write('nicegui_base.toml', f'''[nicegui_base]\nframework_version = {FRAMEWORK_VERSION!r}\napplication_name = {name!r}\nmodule_name = {module_name!r}\ntemplate = {template!r}\n{recipe_line}{variant_line}{pattern_line}entrypoint = "app:main"\nbuild_page = "pages.home:build_page"\n\n[nicegui_base.gates]\nrequire_zero_validator_findings = true\nrequire_tests = true\nrequire_exact_framework_pin = true\nrequire_live_for_release = true\n''')
    write('.gitignore', '.venv/\n__pycache__/\n.pytest_cache/\n.nicegui_base_runtime/\ndist/\nbuild/\n')
    recipe_text = f' and the `{recipe_key}` semiconductor application recipe' if recipe_key else ''
    write('README.md', f'''# {name}\n\nGenerated by NiceGUI Base {FRAMEWORK_VERSION} using the `{template}` golden path{recipe_text}.\n\n## Development\n\n```bash\npython -m venv .venv\n. .venv/bin/activate\npython -m pip install -r requirements-dev.txt\nnicegui-base agent-context "describe the current task"\nnicegui-base agent-check .\npython app.py\n```\n\n## Project checks\n\n```bash\nnicegui-base gate .\nnicegui-base gate . --release\n```\n\nThe full runtime check uses the exact NiceGUI/browser environment when available; source checks and rendered-runtime checks are reported separately.\n''')
    written.extend(install_ai_materials(root, overwrite=overwrite))
    return CreatedApplication(root=root, name=name, template=template, framework_version=FRAMEWORK_VERSION, written=tuple(dict.fromkeys(written)), recipe=recipe_key, recipe_variant=variant_key, pattern=pattern_key)


def create_pattern_application(destination: str | Path, *, name: str, pattern: str, overwrite: bool = False) -> CreatedApplication:
    """Create a starter from one canonical registered application pattern."""
    key = str(pattern).strip()
    template = _PATTERN_TEMPLATE_MAP.get(key)
    if template is None:
        raise ValueError(f'unknown canonical application pattern {pattern!r}; choose one of: {", ".join(_PATTERN_TEMPLATE_MAP)}')
    return create_application(destination, name=name, template=template, pattern=key, overwrite=overwrite)


def create_recipe_application(destination: str | Path, *, name: str, recipe: str, variant: str | None = None, overwrite: bool = False) -> CreatedApplication:
    """Create a starter from one canonical semiconductor recipe."""
    return create_application(destination, name=name, recipe=recipe, recipe_variant=variant, overwrite=overwrite)


__all__ = ['CreatedApplication', 'create_application', 'create_pattern_application', 'create_recipe_application']
