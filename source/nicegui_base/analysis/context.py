from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from typing import Any

from nicegui_base.data_sources import And, Between, FilterExpression, Query

from .models import AnalysisContextSnapshot, EntityContext, PopulationDefinition, TimeRange

ContextWatcher = Callable[['AnalysisContext'], Any]


class AnalysisContext:
    """Shared, framework-neutral analytical state for one workspace.

    The context is the authority for filters/search/time/populations/entity/source and
    freshness metadata. Mutations are atomic: watchers observe one revision after the
    outermost successful transaction, and failed transactions restore the prior state.
    """

    def __init__(self, *, source_key: str | None = None) -> None:
        self._snapshot = AnalysisContextSnapshot(revision=0, source_key=source_key)
        self._watchers: list[ContextWatcher] = []
        self._transaction_depth = 0
        self._transaction_origin: AnalysisContextSnapshot | None = None
        self._dirty = False
        self._closed = False

    @property
    def revision(self) -> int: return self._snapshot.revision
    @property
    def filters(self): return self._snapshot.filters
    @property
    def search(self): return self._snapshot.search
    @property
    def time_range(self): return self._snapshot.time_range
    @property
    def affected(self): return self._snapshot.affected
    @property
    def control(self): return self._snapshot.control
    @property
    def baseline(self): return self._snapshot.baseline
    @property
    def entity(self): return self._snapshot.entity
    @property
    def source_key(self): return self._snapshot.source_key
    @property
    def as_of(self): return self._snapshot.as_of
    @property
    def freshness_at(self): return self._snapshot.freshness_at
    @property
    def metadata(self): return deepcopy(dict(self._snapshot.metadata))
    @property
    def closed(self) -> bool: return self._closed

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError('AnalysisContext is closed')

    def watch(self, callback: ContextWatcher) -> Callable[[], None]:
        self._ensure_open(); self._watchers.append(callback)
        def unsubscribe() -> None:
            if callback in self._watchers: self._watchers.remove(callback)
        return unsubscribe

    @contextmanager
    def transaction(self) -> Iterator['AnalysisContext']:
        self._ensure_open(); outer = self._transaction_depth == 0
        if outer:
            self._transaction_origin = self._snapshot
            self._dirty = False
        self._transaction_depth += 1
        try:
            yield self
        except BaseException:
            self._transaction_depth -= 1
            if outer and self._transaction_origin is not None:
                self._snapshot = self._transaction_origin
                self._transaction_origin = None; self._dirty = False
            raise
        else:
            self._transaction_depth -= 1
            if outer:
                origin = self._transaction_origin
                self._transaction_origin = None
                if self._dirty and origin is not None:
                    self._snapshot = replace(self._snapshot, revision=origin.revision + 1)
                    for callback in tuple(self._watchers): callback(self)
                self._dirty = False

    @contextmanager
    def _auto(self):
        if self._transaction_depth:
            yield self
        else:
            with self.transaction(): yield self

    def _set(self, **changes: Any) -> None:
        with self._auto():
            candidate = replace(self._snapshot, **changes)
            if candidate != self._snapshot:
                self._snapshot = candidate
                self._dirty = True

    def set_filters(self, filters: tuple[FilterExpression, ...] | list[FilterExpression]) -> None:
        self._set(filters=tuple(filters))

    def add_filter(self, expression: FilterExpression) -> None:
        self._set(filters=self.filters + (expression,))

    def clear_filters(self) -> None: self._set(filters=())
    def set_search(self, value: str) -> None: self._set(search=str(value))
    def set_time_range(self, value: TimeRange | None) -> None: self._set(time_range=value)
    def set_affected(self, value: PopulationDefinition | None) -> None: self._set(affected=value)
    def set_control(self, value: PopulationDefinition | None) -> None: self._set(control=value)
    def set_baseline(self, value: PopulationDefinition | None) -> None: self._set(baseline=value)
    def set_entity(self, value: EntityContext | None) -> None: self._set(entity=value)
    def set_source(self, key: str | None) -> None:
        if key is not None and not key.strip(): raise ValueError('source key must not be empty')
        self._set(source_key=key)
    def set_freshness(self, *, as_of: str | None = None, freshness_at: str | None = None) -> None:
        self._set(as_of=as_of, freshness_at=freshness_at)
    def set_metadata(self, metadata: Mapping[str, Any]) -> None: self._set(metadata=dict(metadata))

    def effective_filter(self, *, population: PopulationDefinition | None = None) -> FilterExpression | None:
        terms: list[FilterExpression] = list(self.filters)
        if self.time_range is not None:
            terms.append(Between(self.time_range.field, self.time_range.start, self.time_range.end))
        if population is not None and population.filter is not None:
            terms.append(population.filter)
        if not terms: return None
        if len(terms) == 1: return terms[0]
        return And(tuple(terms))

    def query(self, base: Query = Query(), *, population: PopulationDefinition | None = None) -> Query:
        context_filter = self.effective_filter(population=population)
        if base.filter is not None and context_filter is not None:
            merged = And((context_filter, base.filter))
        else:
            merged = context_filter or base.filter
        search = base.search or self.search
        return replace(base, filter=merged, search=search)

    def snapshot(self) -> AnalysisContextSnapshot:
        self._ensure_open()
        return deepcopy(self._snapshot)

    def restore(self, snapshot: AnalysisContextSnapshot) -> None:
        self._ensure_open()
        with self.transaction():
            current_revision = self._snapshot.revision
            self._snapshot = replace(deepcopy(snapshot), revision=current_revision)
            self._dirty = True

    def close(self) -> None:
        if self._closed: return
        self._closed = True; self._watchers.clear()


__all__ = ['AnalysisContext', 'ContextWatcher']
