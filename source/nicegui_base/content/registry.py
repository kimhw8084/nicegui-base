from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True, slots=True)
class ContentDefinition:
    key:str; category:str; public_name:str; purpose:str; use_when:tuple[str,...]

_ITEMS={
 'metric_card':ContentDefinition('metric_card','metrics','MetricCard','Canonical KPI/metric presentation',('dashboard KPI','engineering summary','clickable metric')),
 'metric_strip':ContentDefinition('metric_strip','metrics','MetricStrip','Responsive metric grouping',('KPI row','summary metrics')),
 'comparison_metric':ContentDefinition('comparison_metric','metrics','ComparisonMetric','Current/baseline/delta comparison',('baseline comparison','performance delta')),
 'key_value_list':ContentDefinition('key_value_list','details','KeyValueList','Readable entity properties',('detail drawer','metadata')),
 'property_grid':ContentDefinition('property_grid','details','PropertyGrid','Dense multi-property presentation',('engineering properties','settings summary')),
 'entity_header':ContentDefinition('entity_header','details','EntityHeader','Canonical identity/status header',('detail drawer','entity page')),
 'tree_view':ContentDefinition('tree_view','hierarchy','TreeView','Hierarchical navigation/data exploration',('equipment hierarchy','process tree','folders')),
 'markdown_viewer':ContentDefinition('markdown_viewer','viewers','MarkdownViewer','Sanitized Markdown presentation',('documentation','AI explanation')),
 'code_viewer':ContentDefinition('code_viewer','viewers','CodeViewer','Read-only syntax-highlighted code',('SQL preview','generated code')),
 'json_viewer':ContentDefinition('json_viewer','viewers','JsonViewer','Structured JSON inspection',('API payload','diagnostics')),
 'log_viewer':ContentDefinition('log_viewer','viewers','LogViewer','Bounded log inspection',('diagnostics','run logs')),
 'image_viewer':ContentDefinition('image_viewer','viewers','ImageViewer','Image inspection with local-first security',('wafer image','metrology image')),
 'search_results':ContentDefinition('search_results','search','SearchResults','Canonical search result list',('entity search','global search')),
 'stepper':ContentDefinition('stepper','workflow','Stepper','Multi-step workflow navigation',('wizard','setup process')),
 'progress_steps':ContentDefinition('progress_steps','workflow','ProgressSteps','Read-only workflow progress',('job progression','approval stages')),
 'compare_panel':ContentDefinition('compare_panel','comparison','ComparePanel','Side-by-side comparison surface',('baseline/current','two entities')),
 'difference_table':ContentDefinition('difference_table','comparison','DifferenceTable','Field-level differences',('configuration diff','record comparison')),
 'command_palette':ContentDefinition('command_palette','commands','CommandPalette','Keyboard-first search and command execution',('global navigation','power-user commands')),
 'background_task':ContentDefinition('background_task','activity','BackgroundTaskIndicator','Compact long-running task state',('analysis running','export running')),
 'notification_center':ContentDefinition('notification_center','activity','NotificationCenter','Persistent bounded notification history',('notification history','user alerts')),
 'activity_feed':ContentDefinition('activity_feed','activity','ActivityFeed','Chronological system or entity activity',('audit history','recent activity')),
}
CONTENT_REGISTRY:Mapping[str,ContentDefinition]=MappingProxyType(_ITEMS)
def get_content(key:str)->ContentDefinition:
    try:return CONTENT_REGISTRY[key]
    except KeyError as exc:raise KeyError(f'Unknown content component: {key}') from exc
__all__=['ContentDefinition','CONTENT_REGISTRY','get_content']
