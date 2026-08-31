from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.analysis import AnalysisContext

from .benchmarking import SemiconductorBenchmarkReport
from .conformance import AdapterConformanceReport
from .recipes import SEMICONDUCTOR_RECIPE_REGISTRY, SemiconductorRecipeDefinition, get_semiconductor_recipe


class OperationalSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class OperationalGuardrailKind(str, Enum):
    REQUIRED_BINDING = 'required_binding'
    RECOMMENDED_BINDING = 'recommended_binding'
    REQUIRED_POPULATION = 'required_population'
    RECOMMENDED_CONTEXT = 'recommended_context'
    PROVIDER_CONFORMANCE = 'provider_conformance'
    REPRESENTATIVE_BENCHMARK = 'representative_benchmark'


@dataclass(frozen=True, slots=True)
class RecipeOperationalGuardrail:
    key: str
    recipe_key: str
    kind: OperationalGuardrailKind
    target: str
    severity: OperationalSeverity
    message: str
    remediation: str

    def __post_init__(self) -> None:
        if not all((self.key.strip(), self.recipe_key.strip(), self.target.strip(), self.message.strip(), self.remediation.strip())):
            raise ValueError('operational guardrail text fields must not be empty')
        object.__setattr__(self, 'kind', OperationalGuardrailKind(self.kind))
        object.__setattr__(self, 'severity', OperationalSeverity(self.severity))
        get_semiconductor_recipe(self.recipe_key)


@dataclass(frozen=True, slots=True)
class OperationalFinding:
    guardrail_key: str
    severity: OperationalSeverity
    passed: bool
    message: str
    remediation: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'details', MappingProxyType(dict(self.details)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'guardrail_key': self.guardrail_key,
            'severity': self.severity.value,
            'passed': self.passed,
            'message': self.message,
            'remediation': self.remediation,
            'details': dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class RecipeConfigurationReview:
    recipe_key: str
    variant_key: str | None
    provider: str
    source_key: str
    bindings: Mapping[str, str]
    manufacturing_context: Mapping[str, Any]
    panel_ids: tuple[str, ...]
    findings: tuple[OperationalFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'bindings', MappingProxyType(dict(self.bindings)))
        object.__setattr__(self, 'manufacturing_context', MappingProxyType(dict(self.manufacturing_context)))
        object.__setattr__(self, 'panel_ids', tuple(self.panel_ids))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def blocking(self) -> tuple[OperationalFinding, ...]:
        return tuple(item for item in self.findings if not item.passed and item.severity is OperationalSeverity.ERROR)

    @property
    def warnings(self) -> tuple[OperationalFinding, ...]:
        return tuple(item for item in self.findings if not item.passed and item.severity is OperationalSeverity.WARNING)

    @property
    def safe_to_run(self) -> bool:
        return not self.blocking

    @property
    def safe_to_promote(self) -> bool:
        return self.safe_to_run and not self.warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'variant_key': self.variant_key,
            'provider': self.provider,
            'source_key': self.source_key,
            'bindings': dict(self.bindings),
            'manufacturing_context': dict(self.manufacturing_context),
            'panel_ids': self.panel_ids,
            'safe_to_run': self.safe_to_run,
            'safe_to_promote': self.safe_to_promote,
            'findings': [item.to_dict() for item in self.findings],
        }


def _g(recipe: str, suffix: str, kind: OperationalGuardrailKind, target: str, severity: OperationalSeverity, message: str, remediation: str) -> RecipeOperationalGuardrail:
    return RecipeOperationalGuardrail(f'{recipe}:{suffix}', recipe, kind, target, severity, message, remediation)


_RECIPE_GUARDRAILS: dict[str, tuple[RecipeOperationalGuardrail, ...]] = {
    'spc-monitor': (
        _g('spc-monitor','measurement','required_binding','measurement',OperationalSeverity.ERROR,'SPC requires a governed measurement binding.','Map the process measurement explicitly if smart onboarding cannot bind it unambiguously.'),
        _g('spc-monitor','time','recommended_binding','time',OperationalSeverity.WARNING,'Production drift review should use an explicit time field.','Bind timestamp/event time so control-chart order is auditable and event overlays align correctly.'),
        _g('spc-monitor','context','recommended_context','chamber',OperationalSeverity.WARNING,'SPC is safer when scoped to a reviewed manufacturing population.','Set tool/chamber, product, operation, recipe, or lot context before interpreting control limits.'),
    ),
    'excursion-defense-line': (
        _g('excursion-defense-line','metric','required_binding','metric',OperationalSeverity.ERROR,'Excursion defense requires the governed response metric.','Bind the affected response metric explicitly.'),
        _g('excursion-defense-line','affected','required_population','affected',OperationalSeverity.ERROR,'Excursion analysis requires an affected population.','Define the affected population in the shared AnalysisContext.'),
        _g('excursion-defense-line','control','required_population','control',OperationalSeverity.ERROR,'Excursion analysis requires a control population.','Define the control population in the shared AnalysisContext.'),
    ),
    'fdc-tool-health': (
        _g('fdc-tool-health','trace_time','required_binding','trace_time',OperationalSeverity.ERROR,'FDC trace analysis requires trace time.','Bind the trace timestamp/sample-time field.'),
        _g('fdc-tool-health','sensor_value','required_binding','sensor_value',OperationalSeverity.ERROR,'FDC analysis requires sensor values.','Bind the governed sensor-value field.'),
        _g('fdc-tool-health','sensor','required_binding','sensor',OperationalSeverity.ERROR,'FDC analysis requires sensor identity.','Bind sensor/parameter identity explicitly.'),
        _g('fdc-tool-health','chamber','recommended_context','chamber',OperationalSeverity.WARNING,'Tool-health interpretation should be scoped to a tool or chamber.','Choose tool/chamber context before comparing traces or fingerprints.'),
    ),
    'lot-wafer-explorer': (
        _g('lot-wafer-explorer','wafer','required_binding','wafer',OperationalSeverity.ERROR,'Wafer exploration requires wafer identity.','Bind wafer_id or the equivalent governed entity field.'),
        _g('lot-wafer-explorer','x','required_binding','x',OperationalSeverity.ERROR,'Spatial wafer analysis requires x coordinates.','Bind die/wafer x coordinates.'),
        _g('lot-wafer-explorer','y','required_binding','y',OperationalSeverity.ERROR,'Spatial wafer analysis requires y coordinates.','Bind die/wafer y coordinates.'),
        _g('lot-wafer-explorer','lot','recommended_context','lot',OperationalSeverity.WARNING,'Lot-wafer comparison is safer when a lot is selected.','Set lot context before comparing wafers unless the workflow intentionally spans lots.'),
    ),
    'yield-loss': (
        _g('yield-loss','category','required_binding','category',OperationalSeverity.ERROR,'Yield loss requires a governed loss/bin category.','Bind bin, yield-bin, category, or reviewed defect-class field.'),
        _g('yield-loss','value','required_binding','value',OperationalSeverity.ERROR,'Yield loss requires a loss/count value.','Bind the governed loss/count measurement.'),
        _g('yield-loss','product','recommended_context','product',OperationalSeverity.WARNING,'Yield decomposition should normally be scoped to product/technology context.','Set product or equivalent manufacturing context before comparing loss contributors.'),
    ),
    'pm-effect-analysis': (
        _g('pm-effect-analysis','metric','required_binding','metric',OperationalSeverity.ERROR,'PM-effect analysis requires a response metric.','Bind the reviewed process/equipment response metric.'),
        _g('pm-effect-analysis','affected','required_population','affected',OperationalSeverity.ERROR,'PM-effect analysis requires a post-PM/affected population.','Define the affected population in shared AnalysisContext.'),
        _g('pm-effect-analysis','control','required_population','control',OperationalSeverity.ERROR,'PM-effect analysis requires a comparison/control population.','Define the pre-PM/control population in shared AnalysisContext.'),
    ),
    'chamber-matching': (
        _g('chamber-matching','feature','required_binding','feature',OperationalSeverity.ERROR,'Chamber matching requires the comparison feature.','Bind the governed chamber-comparison feature.'),
        _g('chamber-matching','chamber','required_binding','chamber',OperationalSeverity.ERROR,'Chamber matching requires chamber identity.','Bind the chamber entity field.'),
        _g('chamber-matching','tool','recommended_context','tool',OperationalSeverity.WARNING,'Chamber matching is safer within reviewed tool/recipe context.','Set tool and recipe context before interpreting chamber deltas.'),
    ),
    'rca-cockpit': (
        _g('rca-cockpit','affected','required_population','affected',OperationalSeverity.ERROR,'RCA requires an affected population.','Define the affected population before ranking commonality.'),
        _g('rca-cockpit','control','required_population','control',OperationalSeverity.ERROR,'RCA requires a control population.','Define a defensible control population before interpreting enrichment/commonality.'),
        _g('rca-cockpit','context','recommended_context','operation',OperationalSeverity.WARNING,'RCA should record a reviewed process scope.','Set operation/route/product or equivalent context to prevent accidental cross-process comparisons.'),
    ),
}

RECIPE_OPERATIONAL_GUARDRAILS: Mapping[str, tuple[RecipeOperationalGuardrail, ...]] = MappingProxyType(_RECIPE_GUARDRAILS)


def get_recipe_operational_guardrails(recipe: str | SemiconductorRecipeDefinition) -> tuple[RecipeOperationalGuardrail, ...]:
    key = recipe.key if isinstance(recipe, SemiconductorRecipeDefinition) else str(recipe)
    get_semiconductor_recipe(key)
    return RECIPE_OPERATIONAL_GUARDRAILS.get(key, ())


def _population_present(context: AnalysisContext, key: str) -> bool:
    return getattr(context, key, None) is not None


def review_recipe_configuration(
    runtime,
    *,
    adapter_conformance: AdapterConformanceReport | None = None,
    benchmark: SemiconductorBenchmarkReport | None = None,
) -> RecipeConfigurationReview:
    findings: list[OperationalFinding] = []
    values = runtime.assembly.semiconductor.values
    for guardrail in get_recipe_operational_guardrails(runtime.recipe):
        passed = True
        details: dict[str, Any] = {}
        if guardrail.kind in {OperationalGuardrailKind.REQUIRED_BINDING, OperationalGuardrailKind.RECOMMENDED_BINDING}:
            passed = guardrail.target in runtime.bindings
            details['source_field'] = runtime.bindings.get(guardrail.target)
        elif guardrail.kind is OperationalGuardrailKind.REQUIRED_POPULATION:
            passed = _population_present(runtime.context, guardrail.target)
        elif guardrail.kind is OperationalGuardrailKind.RECOMMENDED_CONTEXT:
            passed = values.get(guardrail.target) is not None
            details['context_value'] = values.get(guardrail.target)
        findings.append(OperationalFinding(guardrail.key, guardrail.severity, passed, guardrail.message, guardrail.remediation, details))

    if adapter_conformance is None:
        findings.append(OperationalFinding(
            f'{runtime.recipe.key}:provider-conformance', OperationalSeverity.WARNING, False,
            'No production provider-conformance evidence is attached to this configuration review.',
            'Run the provider conformance suite against the approved target adapter before release.',
        ))
    else:
        findings.append(OperationalFinding(
            f'{runtime.recipe.key}:provider-conformance', OperationalSeverity.ERROR, adapter_conformance.passed,
            'Approved provider conformance must pass.',
            'Resolve conformance errors before release.',
            {'errors': tuple(item.code for item in adapter_conformance.errors)},
        ))
    if benchmark is None:
        findings.append(OperationalFinding(
            f'{runtime.recipe.key}:benchmark', OperationalSeverity.WARNING, False,
            'No representative provider benchmark is attached to this configuration review.',
            'Run the governed provider-rc benchmark on representative target data before release.',
        ))
    else:
        findings.append(OperationalFinding(
            f'{runtime.recipe.key}:benchmark', OperationalSeverity.ERROR, benchmark.passed,
            'Representative provider benchmark must pass.',
            'Resolve benchmark/pushdown findings or rerun with representative target data.',
            {'profile_key': benchmark.profile_key, 'errors': tuple(item.code for item in benchmark.errors)},
        ))
    return RecipeConfigurationReview(
        runtime.recipe.key,
        runtime.configuration.variant_key,
        runtime.source.provider,
        runtime.source.key,
        runtime.bindings,
        values,
        tuple(runtime.assembly.workspace.layout.panels),
        tuple(findings),
    )


__all__ = [
    'OperationalFinding','OperationalGuardrailKind','OperationalSeverity','RECIPE_OPERATIONAL_GUARDRAILS',
    'RecipeConfigurationReview','RecipeOperationalGuardrail','get_recipe_operational_guardrails','review_recipe_configuration',
]
