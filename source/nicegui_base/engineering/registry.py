from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EngineeringDefinition:
    name: str
    category: str
    purpose: str
    when_to_use: str


_ITEMS = {
    'EngineeringEntityCard': ('entity','Canonical presentation for tool/lot/wafer/recipe/process entities','When a named engineering entity needs status + compact properties'),
    'InvestigationContextBar': ('rca','Persistent investigation orientation strip','At the top of RCA workspaces to keep investigation, owner, stage and freshness visible'),
    'EngineeringStatusBadge': ('status','Canonical engineering operational status','For normal/watch/warning/critical/offline/maintenance/hold state'),
    'SpecLimitIndicator': ('spec','Value relative to warning/spec limits','Whenever a numeric measurement must communicate in-spec/watch/OOS state'),
    'OutOfSpecIndicator': ('spec','Prominent OOS treatment','When a spec violation needs explicit user attention'),
    'BaselineComparison': ('comparison','Current vs reference/baseline semantic delta','For KPI or engineering parameter comparison'),
    'ProcessTrendSpec': ('analysis','Process trend with spec/control limit context','For time/order trends of process measurements'),
    'DistributionComparisonSpec': ('analysis','Affected vs control population distribution contract','For population-shift analysis without implying causality'),
    'PopulationComparisonPanel': ('analysis','Summaries and effect-size context for affected/control populations','For exploratory comparison of two populations'),
    'CommonalityTable': ('analysis','Affected/control exposure commonality table','For ranking overlaps/enrichment while keeping routing vs causal interpretation explicit'),
    'EvidenceCard': ('rca','One typed evidence item with direction/strength/source','For root-cause evidence presentation'),
    'ConfidenceIndicator': ('rca','Confidence label that does not masquerade as probability','For qualitative/model confidence; show percentage only when explicitly calibrated'),
    'RcaEvidencePanel': ('rca','Evidence + contradiction view for one hypothesis','For transparent hypothesis review'),
    'RcaWorkspaceSpec': ('rca','Reusable hypothesis-oriented RCA workspace contract','For comparing several candidate root-cause hypotheses'),
    'EngineeringTimeline': ('history','Chronological engineering events','For PM, alarm, recipe, process, and investigation history'),
}

ENGINEERING_REGISTRY = {k: EngineeringDefinition(k, *v) for k, v in _ITEMS.items()}


def get_engineering(name: str) -> EngineeringDefinition:
    try:
        return ENGINEERING_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f'Unknown engineering component/pattern: {name}') from exc


__all__ = ['ENGINEERING_REGISTRY','EngineeringDefinition','get_engineering']
