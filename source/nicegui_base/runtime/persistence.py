from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from nicegui_base.analysis import (
    AnalysisContextSnapshot, EntityContext, PopulationDefinition, Selection, SelectionKind, SelectionSnapshot, TimeRange,
)
from nicegui_base.data_engine import DataSessionSnapshot, FilterClause, FilterOperation
from nicegui_base.data_sources import (
    And, Between, Comparison, ComparisonOperator, FilterExpression, In, IsNull, Not, Or, TextMatch, TextMatchMode,
)
from nicegui_base.workspace import (
    DockPosition, GridPlacement, PanelInteractionState, PanelSpec, WorkspaceBreakpoint,
    WorkspaceInteractionSnapshot, WorkspaceLayoutSnapshot,
)

from .kernel import ApplicationSnapshot, StateSnapshot, WorkspaceSnapshot

_SCHEMA_VERSION = 1
_TAG='__nicegui_base_type__'


def _encode_value(value: Any) -> Any:
    if isinstance(value, datetime): return {_TAG:'datetime','value':value.isoformat()}
    if isinstance(value, date): return {_TAG:'date','value':value.isoformat()}
    if isinstance(value, Decimal): return {_TAG:'decimal','value':str(value)}
    if isinstance(value, tuple): return {_TAG:'tuple','items':[_encode_value(item) for item in value]}
    if isinstance(value, list): return [_encode_value(item) for item in value]
    if isinstance(value, Mapping): return {str(key):_encode_value(item) for key,item in value.items()}
    if value is None or isinstance(value,(str,int,float,bool)): return value
    raise TypeError(f'value is not runtime-snapshot serializable: {type(value).__name__}')


def _decode_value(value: Any) -> Any:
    if isinstance(value,list): return [_decode_value(item) for item in value]
    if isinstance(value,Mapping):
        kind=value.get(_TAG)
        if kind=='datetime':return datetime.fromisoformat(str(value['value']))
        if kind=='date':return date.fromisoformat(str(value['value']))
        if kind=='decimal':return Decimal(str(value['value']))
        if kind=='tuple':return tuple(_decode_value(item) for item in value.get('items',()))
        return {str(key):_decode_value(item) for key,item in value.items()}
    return value


def _filter_to_dict(clause: FilterClause) -> dict[str, Any]:
    return {'field':clause.field,'operation':clause.operation.value,'value':_encode_value(clause.value),'value2':_encode_value(clause.value2),'filter_id':clause.filter_id}


def _filter_from_dict(payload: Mapping[str, Any]) -> FilterClause:
    return FilterClause(field=str(payload['field']),operation=FilterOperation(str(payload['operation'])),value=_decode_value(payload.get('value')),value2=_decode_value(payload.get('value2')),filter_id=payload.get('filter_id'))


def _query_filter_to_dict(item: FilterExpression | None) -> Any:
    if item is None:return None
    if isinstance(item,Comparison):return {'kind':'comparison','field':item.field,'operator':item.operator.value,'value':_encode_value(item.value)}
    if isinstance(item,In):return {'kind':'in','field':item.field,'values':_encode_value(item.values),'negate':item.negate}
    if isinstance(item,Between):return {'kind':'between','field':item.field,'lower':_encode_value(item.lower),'upper':_encode_value(item.upper)}
    if isinstance(item,TextMatch):return {'kind':'text','field':item.field,'value':item.value,'mode':item.mode.value,'case_sensitive':item.case_sensitive,'negate':item.negate}
    if isinstance(item,IsNull):return {'kind':'null','field':item.field,'negate':item.negate}
    if isinstance(item,And):return {'kind':'and','terms':[_query_filter_to_dict(term) for term in item.terms]}
    if isinstance(item,Or):return {'kind':'or','terms':[_query_filter_to_dict(term) for term in item.terms]}
    if isinstance(item,Not):return {'kind':'not','term':_query_filter_to_dict(item.term)}
    raise TypeError(f'unsupported analysis filter: {type(item).__name__}')


def _query_filter_from_dict(payload: Any) -> FilterExpression | None:
    if payload is None:return None
    if not isinstance(payload,Mapping):raise TypeError('analysis filter must be a mapping')
    kind=str(payload['kind'])
    if kind=='comparison':return Comparison(str(payload['field']),ComparisonOperator(str(payload['operator'])),_decode_value(payload.get('value')))
    if kind=='in':return In(str(payload['field']),tuple(_decode_value(payload.get('values',()))),bool(payload.get('negate',False)))
    if kind=='between':return Between(str(payload['field']),_decode_value(payload.get('lower')),_decode_value(payload.get('upper')))
    if kind=='text':return TextMatch(str(payload['field']),str(payload.get('value','')),TextMatchMode(str(payload.get('mode','contains'))),bool(payload.get('case_sensitive',False)),bool(payload.get('negate',False)))
    if kind=='null':return IsNull(str(payload['field']),bool(payload.get('negate',False)))
    if kind=='and':return And(tuple(_query_filter_from_dict(term) for term in payload.get('terms',())))
    if kind=='or':return Or(tuple(_query_filter_from_dict(term) for term in payload.get('terms',())))
    if kind=='not':return Not(_query_filter_from_dict(payload.get('term')))
    raise ValueError(f'unknown analysis filter kind: {kind}')


def _population_to_dict(item:PopulationDefinition|None):
    if item is None:return None
    return {'key':item.key,'label':item.label,'filter':_query_filter_to_dict(item.filter),'metadata':_encode_value(item.metadata)}

def _population_from_dict(payload):
    if payload is None:return None
    return PopulationDefinition(str(payload['key']),payload.get('label'),_query_filter_from_dict(payload.get('filter')),_decode_value(payload.get('metadata',{})))


def _analysis_to_dict(item:AnalysisContextSnapshot|None):
    if item is None:return None
    return {
        'revision':item.revision,'filters':[_query_filter_to_dict(f) for f in item.filters],'search':item.search,
        'time_range':None if item.time_range is None else {'field':item.time_range.field,'start':_encode_value(item.time_range.start),'end':_encode_value(item.time_range.end)},
        'affected':_population_to_dict(item.affected),'control':_population_to_dict(item.control),'baseline':_population_to_dict(item.baseline),
        'entity':None if item.entity is None else {'entity_type':item.entity.entity_type,'entity_id':_encode_value(item.entity.entity_id),'label':item.entity.label,'attributes':_encode_value(item.entity.attributes)},
        'source_key':item.source_key,'as_of':item.as_of,'freshness_at':item.freshness_at,'metadata':_encode_value(item.metadata),
    }


def _analysis_from_dict(payload):
    if payload is None:return None
    tr=payload.get('time_range');entity=payload.get('entity')
    return AnalysisContextSnapshot(
        revision=int(payload.get('revision',0)),filters=tuple(_query_filter_from_dict(f) for f in payload.get('filters',())),search=str(payload.get('search','')),
        time_range=None if tr is None else TimeRange(str(tr['field']),_decode_value(tr['start']),_decode_value(tr['end'])),
        affected=_population_from_dict(payload.get('affected')),control=_population_from_dict(payload.get('control')),baseline=_population_from_dict(payload.get('baseline')),
        entity=None if entity is None else EntityContext(str(entity['entity_type']),_decode_value(entity.get('entity_id')),entity.get('label'),_decode_value(entity.get('attributes',{}))),
        source_key=payload.get('source_key'),as_of=payload.get('as_of'),freshness_at=payload.get('freshness_at'),metadata=_decode_value(payload.get('metadata',{})),
    )


def _selection_to_dict(item:Selection):return {'kind':item.kind.value,'selection_id':item.selection_id,'values':_encode_value(item.values),'source':item.source,'label':item.label}
def _selection_from_dict(payload):return Selection(SelectionKind(str(payload['kind'])),str(payload['selection_id']),_decode_value(payload.get('values',{})),payload.get('source'),payload.get('label'))
def _selections_to_dict(item:SelectionSnapshot|None):
    if item is None:return None
    return {'revision':item.revision,'selections':[_selection_to_dict(s) for s in item.selections],'history':[[_selection_to_dict(s) for s in batch] for batch in item.history]}
def _selections_from_dict(payload):
    if payload is None:return None
    return SelectionSnapshot(int(payload.get('revision',0)),tuple(_selection_from_dict(s) for s in payload.get('selections',())),tuple(tuple(_selection_from_dict(s) for s in batch) for batch in payload.get('history',())))


def _panel_to_dict(panel: PanelSpec) -> dict[str, Any]:
    return {'panel_id':panel.panel_id,'preferred_columns':panel.preferred_columns,'preferred_rows':panel.preferred_rows,'min_columns':panel.min_columns,'max_columns':panel.max_columns,'min_rows':panel.min_rows,'max_rows':panel.max_rows,'phone_full_width':panel.phone_full_width,'locked':panel.locked,'metadata':_encode_value(dict(panel.metadata))}

def _panel_from_dict(payload: Mapping[str, Any]) -> PanelSpec:
    return PanelSpec(panel_id=str(payload['panel_id']),preferred_columns=int(payload.get('preferred_columns',6)),preferred_rows=int(payload.get('preferred_rows',4)),min_columns=int(payload.get('min_columns',2)),max_columns=None if payload.get('max_columns') is None else int(payload['max_columns']),min_rows=int(payload.get('min_rows',2)),max_rows=None if payload.get('max_rows') is None else int(payload['max_rows']),phone_full_width=bool(payload.get('phone_full_width',True)),locked=bool(payload.get('locked',False)),metadata=_decode_value(payload.get('metadata',{})))

def _placement_to_dict(item: GridPlacement) -> dict[str, Any]:return {'panel_id':item.panel_id,'breakpoint':item.breakpoint.value,'column':item.column,'row':item.row,'column_span':item.column_span,'row_span':item.row_span}
def _placement_from_dict(payload: Mapping[str, Any]) -> GridPlacement:return GridPlacement(str(payload['panel_id']),WorkspaceBreakpoint(str(payload['breakpoint'])),int(payload['column']),int(payload['row']),int(payload['column_span']),int(payload['row_span']))

def _interactions_to_dict(item:WorkspaceInteractionSnapshot|None):
    if item is None:return None
    return {'revision':item.revision,'states':[{'panel_id':s.panel_id,'collapsed':s.collapsed,'hidden':s.hidden,'locked':s.locked,'dock':s.dock.value,'split_group':s.split_group} for s in item.states]}
def _interactions_from_dict(payload):
    if payload is None:return None
    return WorkspaceInteractionSnapshot(int(payload.get('revision',0)),tuple(PanelInteractionState(str(s['panel_id']),bool(s.get('collapsed',False)),bool(s.get('hidden',False)),bool(s.get('locked',False)),DockPosition(str(s.get('dock','none'))),s.get('split_group')) for s in payload.get('states',())))


def workspace_snapshot_to_dict(snapshot: WorkspaceSnapshot) -> dict[str, Any]:
    return {
        'schema_version':_SCHEMA_VERSION,'workspace_id':snapshot.workspace_id,
        'state':{'revision':snapshot.state.revision,'values':_encode_value(dict(snapshot.state.values))},
        'layout':{'schema_version':snapshot.layout.schema_version,'revision':snapshot.layout.revision,'panels':[_panel_to_dict(i) for i in snapshot.layout.panels],'placements':[_placement_to_dict(i) for i in snapshot.layout.placements]},
        'data_sessions':{sid:{'dataset_key':key,'revision':session.revision,'filters':[_filter_to_dict(i) for i in session.filters],'search':session.search} for sid,(key,session) in snapshot.data_sessions.items()},
        'analysis':_analysis_to_dict(snapshot.analysis),'selections':_selections_to_dict(snapshot.selections),'interactions':_interactions_to_dict(snapshot.interactions),
    }


def workspace_snapshot_from_dict(payload: Mapping[str, Any]) -> WorkspaceSnapshot:
    if int(payload.get('schema_version',0))!=_SCHEMA_VERSION:raise ValueError(f'unsupported runtime snapshot schema {payload.get("schema_version")!r}')
    state_payload=payload['state'];layout_payload=payload['layout']
    if not isinstance(state_payload,Mapping) or not isinstance(layout_payload,Mapping):raise TypeError('workspace snapshot state/layout must be mappings')
    raw_sessions=payload.get('data_sessions',{})
    if not isinstance(raw_sessions,Mapping):raise TypeError('workspace snapshot data_sessions must be a mapping')
    sessions={}
    for sid,raw in raw_sessions.items():
        if not isinstance(raw,Mapping):raise TypeError('data session snapshot must be a mapping')
        sessions[str(sid)]=(str(raw['dataset_key']),DataSessionSnapshot(int(raw.get('revision',0)),tuple(_filter_from_dict(i) for i in raw.get('filters',())),str(raw.get('search',''))))
    return WorkspaceSnapshot(
        workspace_id=str(payload['workspace_id']),state=StateSnapshot(int(state_payload.get('revision',0)),_decode_value(state_payload.get('values',{}))),
        layout=WorkspaceLayoutSnapshot(int(layout_payload.get('schema_version',0)),int(layout_payload.get('revision',0)),tuple(_panel_from_dict(i) for i in layout_payload.get('panels',())),tuple(_placement_from_dict(i) for i in layout_payload.get('placements',()))),
        data_sessions=sessions,analysis=_analysis_from_dict(payload.get('analysis')),selections=_selections_from_dict(payload.get('selections')),interactions=_interactions_from_dict(payload.get('interactions')),
    )


def application_snapshot_to_dict(snapshot: ApplicationSnapshot) -> dict[str, Any]:
    return {'schema_version':_SCHEMA_VERSION,'state':{'revision':snapshot.state.revision,'values':_encode_value(dict(snapshot.state.values))},'workspaces':[workspace_snapshot_to_dict(item) for item in snapshot.workspaces]}


def application_snapshot_from_dict(payload: Mapping[str, Any]) -> ApplicationSnapshot:
    if int(payload.get('schema_version',0))!=_SCHEMA_VERSION:raise ValueError(f'unsupported runtime snapshot schema {payload.get("schema_version")!r}')
    state_payload=payload['state']
    if not isinstance(state_payload,Mapping):raise TypeError('application snapshot state must be a mapping')
    workspaces=payload.get('workspaces',())
    if not isinstance(workspaces,(list,tuple)):raise TypeError('application snapshot workspaces must be a sequence')
    return ApplicationSnapshot(StateSnapshot(int(state_payload.get('revision',0)),_decode_value(state_payload.get('values',{}))),tuple(workspace_snapshot_from_dict(item) for item in workspaces))


def serialize_application_snapshot(snapshot: ApplicationSnapshot, *, indent: int | None = None) -> str:return json.dumps(application_snapshot_to_dict(snapshot),indent=indent,sort_keys=True,ensure_ascii=False)
def deserialize_application_snapshot(value: str) -> ApplicationSnapshot:
    payload=json.loads(value)
    if not isinstance(payload,dict):raise TypeError('application snapshot JSON must contain an object')
    return application_snapshot_from_dict(payload)


__all__=['application_snapshot_from_dict','application_snapshot_to_dict','deserialize_application_snapshot','serialize_application_snapshot','workspace_snapshot_from_dict','workspace_snapshot_to_dict']
