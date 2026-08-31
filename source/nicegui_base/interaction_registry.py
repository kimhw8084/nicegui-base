from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class InteractionDefinition:
    key: str
    category: str
    public_name: str
    purpose: str
    use_when: tuple[str, ...]
    avoid_when: tuple[str, ...] = ()


_ITEMS = {
    'form': InteractionDefinition('form','forms','Form','Own validation, dirty state and submission anatomy',('structured data entry','edit/create workflow')),
    'filter_bar': InteractionDefinition('filter_bar','filters','FilterBar','Primary analytical filtering surface',('analysis filtering','search + facets')),
    'filter_drawer': InteractionDefinition('filter_drawer','filters','AdvancedFilterDrawer','Keep complex filters out of primary page flow',('many filters','mobile filters')),
    'detail_drawer': InteractionDefinition('detail_drawer','drawers','DetailDrawer','Inspect an entity without losing page context',('quick entity detail','contextual drilldown'),('long standalone workflow',)),
    'form_drawer': InteractionDefinition('form_drawer','drawers','FormDrawer','Create or edit while retaining current context',('short/medium edit','contextual create'),('very long multi-step workflow',)),
    'dialog': InteractionDefinition('dialog','dialogs','Dialog','Focused blocking decision or short task',('confirmation','small focused task'),('whole application views','deep analysis')),
    'danger_dialog': InteractionDefinition('danger_dialog','dialogs','DangerConfirmDialog','Confirm irreversible or high-risk action',('irreversible deletion','high-risk mutation')),
    'popover': InteractionDefinition('popover','overlays','Popover','Light contextual information or controls',('small secondary details','compact actions')),
    'menu': InteractionDefinition('menu','overlays','ActionMenu','Compact set of contextual actions',('overflow actions','row/context actions')),
    'toast': InteractionDefinition('toast','feedback','Toast','Transient operation result',('save success','short nonblocking failure')),
    'alert': InteractionDefinition('alert','feedback','Alert','Persistent message scoped to a region',('data quality','recoverable warning','inline failure')),
    'banner': InteractionDefinition('banner','feedback','Banner','Broad page/application condition',('system degradation','page-wide warning')),
    'state_view': InteractionDefinition('state_view','feedback','StateView','Durable empty/error/permission/offline condition',('no data','no results','load failure','permission','offline')),
    'async_content': InteractionDefinition('async_content','feedback','AsyncContent','Standard content lifecycle semantics',('loading','refreshing','empty/error transitions')),
}

INTERACTION_REGISTRY: Mapping[str, InteractionDefinition] = MappingProxyType(_ITEMS)


def get_interaction(key: str) -> InteractionDefinition:
    try:
        return INTERACTION_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f'Unknown interaction pattern: {key}') from exc

__all__ = ['INTERACTION_REGISTRY','InteractionDefinition','get_interaction']
