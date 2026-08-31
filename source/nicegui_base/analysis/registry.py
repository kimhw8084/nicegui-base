from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AnalysisDefinition:
    key: str
    public_name: str
    purpose: str
    use_when: tuple[str, ...]
    avoid_when: tuple[str, ...] = ()


_ITEMS = {
    item.key: item for item in (
        AnalysisDefinition('analysis_context','AnalysisContext','Single authority for filters, time, populations, entity, source and freshness.',('two or more analytical surfaces share state','saved analytical views')),
        AnalysisDefinition('selection_bus','SelectionBus','Typed row/entity/time/wafer/chart/population selection and drill history.',('table/chart/wafer selections must coordinate','crossfilter and drill-down')),
        AnalysisDefinition('analysis_binding','AnalysisBinding','Latest-request-wins context-to-data refresh binding.',('context changes trigger async queries','stale requests must never overwrite fresh results')),
        AnalysisDefinition('analytical_panel','AnalyticalPanel','Canonical analytical loading/error/empty/stale/partial/action shell.',('any data-driven chart/table/domain visualization',)),
        AnalysisDefinition('data_source_table','DataSourceTable','Server-paged table directly backed by DataSource and AnalysisContext.',('large provider-backed tables','shared context filtering')),
        AnalysisDefinition('workspace_controller','WorkspaceController','Persistent move/resize/collapse/hide/lock/dock/split/duplicate/reset/undo workspace state.',('analysis workspaces','user-customizable panel layout')),
        AnalysisDefinition('nicegui_workspace','NiceGUIWorkspace','Company-owned interactive NiceGUI renderer for WorkspaceController.',('draggable/resizable analytical workspaces',)),
    )
}
ANALYSIS_REGISTRY: Mapping[str,AnalysisDefinition] = MappingProxyType(_ITEMS)


def get_analysis(key: str) -> AnalysisDefinition:
    try:return ANALYSIS_REGISTRY[key]
    except KeyError as exc:raise KeyError(f'Unknown analysis primitive: {key}') from exc


__all__=['ANALYSIS_REGISTRY','AnalysisDefinition','get_analysis']
