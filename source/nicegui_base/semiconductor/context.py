from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from nicegui_base.analysis import AnalysisContext, EntityContext, PopulationDefinition, Selection, SelectionBus, SelectionKind, SelectionMutationMode
from nicegui_base.data_sources import And, Between, Comparison, ComparisonOperator, DataSource, Query


@dataclass(frozen=True, slots=True)
class SemiconductorFieldMap:
    fab:str='fab'; area:str='area'; bay:str='bay'; product:str='product'; route:str='route'; operation:str='operation'; recipe:str='recipe'; recipe_version:str='recipe_version'
    tool:str='tool'; chamber:str='chamber'; lot:str='lot'; wafer:str='wafer'; carrier:str='carrier'; technology:str='technology'
    def field(self, key:str)->str:
        try: return getattr(self,key)
        except AttributeError as exc: raise KeyError(f'unknown semiconductor dimension: {key}') from exc


DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    'product': ('route',), 'route': ('operation',),
    'area': ('tool',), 'tool': ('chamber',),
    'lot': ('wafer',), 'recipe': ('recipe_version',),
}


class SemiconductorAnalysisContext:
    """Semiconductor-aware facade over the Wave 60 AnalysisContext authority.

    Selected manufacturing dimensions are persisted inside AnalysisContext metadata and
    represented as ordinary Wave 59 comparison filters. The facade therefore adds domain
    semantics without becoming a competing state or persistence authority.
    """
    METADATA_KEY='semiconductor_context'

    def __init__(self, context: AnalysisContext, *, fields: SemiconductorFieldMap | None=None) -> None:
        self.context=context
        self.fields=fields or SemiconductorFieldMap()
        self._values:dict[str,Any]={}
        self._owned_filters:dict[str,Comparison]={}
        self._applied_filters:tuple[Comparison,...]=()
        self._syncing=False
        self._hydrate_from_context()
        self._unsubscribe=self.context.watch(self._on_context_change)

    @property
    def values(self)->dict[str,Any]: return dict(self._values)
    def get(self,key:str,default=None): return self._values.get(key,default)

    def _on_context_change(self, _:AnalysisContext)->None:
        if not self._syncing: self._hydrate_from_context()

    def _hydrate_from_context(self)->None:
        raw=self.context.metadata.get(self.METADATA_KEY,{})
        values={}
        if isinstance(raw,Mapping):
            for key,value in raw.items():
                if key in self.fields.__dataclass_fields__ and value is not None: values[key]=value
        self._values=values
        owned={}
        used:set[int]=set()
        for key,value in values.items():
            field_name=self.fields.field(key)
            match=next((f for f in self.context.filters if id(f) not in used and isinstance(f,Comparison) and f.field==field_name and f.operator is ComparisonOperator.EQ and f.value==value),None)
            if match is not None:
                used.add(id(match)); owned[key]=match
            else:
                owned[key]=Comparison(field_name,ComparisonOperator.EQ,value)
        self._owned_filters=owned
        self._applied_filters=tuple(f for f in owned.values() if any(f is current for current in self.context.filters))

    def set(self,key:str,value:Any|None, *, clear_dependents:bool=True)->None:
        self.fields.field(key)
        self._syncing=True
        try:
            with self.context.transaction():
                if clear_dependents: self._clear_descendants(key)
                if value is None:
                    self._values.pop(key,None); self._owned_filters.pop(key,None)
                else:
                    self._values[key]=value; self._owned_filters[key]=Comparison(self.fields.field(key),ComparisonOperator.EQ,value)
                self._sync()
        finally:
            self._syncing=False

    def set_many(self, **values:Any)->None:
        # Treat one multi-field update as a single dependency transaction independent of
        # keyword ordering. Explicitly supplied descendants survive a parent change;
        # descendants omitted from the update are cleared.
        for key in values:
            self.fields.field(key)
        supplied=set(values)
        self._syncing=True
        try:
            with self.context.transaction():
                for key in values:
                    for child in self._descendants(key):
                        if child not in supplied:
                            self._values.pop(child,None); self._owned_filters.pop(child,None)
                for key,value in values.items():
                    if value is None:
                        self._values.pop(key,None); self._owned_filters.pop(key,None)
                    else:
                        self._values[key]=value; self._owned_filters[key]=Comparison(self.fields.field(key),ComparisonOperator.EQ,value)
                self._sync()
        finally:
            self._syncing=False

    @staticmethod
    def _descendants(key:str)->tuple[str,...]:
        out:list[str]=[]
        stack=list(DEPENDENCIES.get(key,()))
        while stack:
            child=stack.pop(0)
            if child in out: continue
            out.append(child); stack.extend(DEPENDENCIES.get(child,()))
        return tuple(out)

    def _clear_descendants(self,key:str)->None:
        for child in DEPENDENCIES.get(key,()):
            self._values.pop(child,None); self._owned_filters.pop(child,None); self._clear_descendants(child)

    def _sync(self)->None:
        # Remove only filters previously owned by this facade. External Wave 60 filters are
        # preserved even when they happen to use a semiconductor field. Identity is used
        # deliberately so an equal filter installed by another controller is not stolen.
        keep=tuple(f for f in self.context.filters if not any(f is owned for owned in self._applied_filters))
        self._applied_filters=tuple(self._owned_filters.values())
        self.context.set_filters(keep+self._applied_filters)
        metadata=self.context.metadata
        if self._values: metadata[self.METADATA_KEY]=dict(self._values)
        else: metadata.pop(self.METADATA_KEY,None)
        self.context.set_metadata(metadata)
        if self._values:
            key=next(reversed(self._values)); self.context.set_entity(EntityContext(key,self._values[key]))
        elif self.context.entity and self.context.entity.entity_type in self.fields.__dataclass_fields__:
            self.context.set_entity(None)

    def population(self, role:str, definition:PopulationDefinition|None)->None:
        if role=='affected': self.context.set_affected(definition)
        elif role=='control': self.context.set_control(definition)
        elif role=='baseline': self.context.set_baseline(definition)
        else: raise KeyError(role)

    def close(self)->None:
        self._unsubscribe()


class ManufacturingFilterController:
    """Governed dependent filters backed by DataSource.distinct and the shared context."""
    def __init__(self, source:DataSource, context:SemiconductorAnalysisContext)->None:
        self.source=source; self.context=context
    def set(self,key:str,value:Any|None)->None: self.context.set(key,value)
    async def options(self,key:str)->tuple[Any,...]:
        field=self.context.fields.field(key)
        # Preserve the complete Wave 60 analytical context (unrelated filters, time
        # range, search, and manufacturing ancestors), while removing only this
        # facade's own target/descendant filters so a stale child selection cannot
        # collapse its option universe. External filters remain authoritative.
        excluded_keys=(key,)+SemiconductorAnalysisContext._descendants(key)
        excluded=tuple(self.context._owned_filters[k] for k in excluded_keys if k in self.context._owned_filters)
        terms=[f for f in self.context.context.filters if not any(f is owned for owned in excluded)]
        time_range=self.context.context.time_range
        if time_range is not None:
            terms.append(Between(time_range.field,time_range.start,time_range.end))
        q=Query(
            filter=(terms[0] if len(terms)==1 else And(tuple(terms)) if terms else None),
            search=self.context.context.search,
        )
        return (await self.source.distinct(field,q)).values
    @staticmethod
    def _ancestors(key:str)->tuple[str,...]:
        parents=[]
        changed=True
        while changed:
            changed=False
            for parent,children in DEPENDENCIES.items():
                if key in children and parent not in parents:
                    parents.insert(0,parent); key=parent; changed=True; break
        return tuple(parents)


def semiconductor_selection(bus:SelectionBus, key:str, value:Any, *, field_map:SemiconductorFieldMap|None=None, source:str='semiconductor'):
    fields=field_map or SemiconductorFieldMap(); expr=Comparison(fields.field(key),ComparisonOperator.EQ,value)
    return bus.apply(Selection(SelectionKind.ENTITY,f'{key}:{value}',{'entity_type':key,'entity_id':value,'filter':expr},source=source),mode=SelectionMutationMode.REPLACE,source=source)


__all__=['DEPENDENCIES','ManufacturingFilterController','SemiconductorAnalysisContext','SemiconductorFieldMap','semiconductor_selection']
