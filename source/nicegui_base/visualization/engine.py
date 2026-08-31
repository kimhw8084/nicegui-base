from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from statistics import fmean, median
from typing import Any

from .models import ChartEvent, CrossFilterBinding, FilterMutation, FilterMutationAction, SpatialPoint, WaferPoint


class CrossFilterEngine:
    """Small deterministic event-to-filter coordinator for linked analytical views."""

    def __init__(self, bindings: Sequence[CrossFilterBinding] = ()) -> None:
        self._bindings = list(bindings)
        self._listeners: list[Callable[[FilterMutation], Any]] = []
        self._active: dict[str, FilterMutation] = {}

    def bind(self, binding: CrossFilterBinding) -> None:
        self._bindings.append(binding)

    def subscribe(self, listener: Callable[[FilterMutation], Any]) -> Callable[[], None]:
        self._listeners.append(listener)
        def unsubscribe() -> None:
            if listener in self._listeners: self._listeners.remove(listener)
        return unsubscribe

    def dispatch(self, event: ChartEvent) -> tuple[FilterMutation, ...]:
        mutations: list[FilterMutation] = []
        for binding in self._bindings:
            if binding.source_id != event.source_id or binding.event_type != event.event_type:
                continue
            value = event.value if event.key is None else event.payload.get(event.key, event.value)
            mutation = FilterMutation(binding.target_key, value, binding.operator, event.source_id)
            self._active[binding.target_key] = mutation
            mutations.append(mutation)
            for listener in tuple(self._listeners):
                listener(mutation)
        return tuple(mutations)

    def clear(self, key: str | None = None) -> tuple[FilterMutation, ...]:
        removed = tuple(self._active.values()) if key is None else tuple(filter(None, (self._active.get(key),)))
        if key is None:
            self._active.clear()
        else:
            self._active.pop(key, None)
        mutations = tuple(FilterMutation(item.key, None, item.operator, item.source_id, FilterMutationAction.REMOVE) for item in removed)
        for mutation in mutations:
            for listener in tuple(self._listeners):
                listener(mutation)
        return mutations

    @property
    def active_filters(self) -> Mapping[str, FilterMutation]:
        return dict(self._active)


def histogram(values: Iterable[float], bins: int = 10) -> list[dict[str, float | int]]:
    vals = [float(v) for v in values]
    if bins < 1:
        raise ValueError('bins must be >= 1')
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return [{'start': lo, 'end': hi, 'count': len(vals)}]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        idx = min(int((v - lo) / width), bins - 1)
        counts[idx] += 1
    return [{'start': lo + i*width, 'end': lo + (i+1)*width, 'count': counts[i]} for i in range(bins)]


def pareto(rows: Iterable[Mapping[str, Any]], category_key: str, value_key: str) -> list[dict[str, Any]]:
    totals: dict[Any, float] = defaultdict(float)
    for row in rows:
        totals[row.get(category_key)] += float(row.get(value_key, 0) or 0)
    ordered = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    grand = sum(v for _, v in ordered)
    cumulative = 0.0
    result=[]
    for category, value in ordered:
        cumulative += value
        result.append({'category': category, 'value': value, 'cumulative_pct': (cumulative/grand*100) if grand else 0.0})
    return result


def box_summary(values: Iterable[float]) -> dict[str, float] | None:
    vals = sorted(float(v) for v in values)
    if not vals:
        return None
    def quantile(p: float) -> float:
        if len(vals)==1: return vals[0]
        pos=(len(vals)-1)*p; lower=int(pos); upper=min(lower+1,len(vals)-1); frac=pos-lower
        return vals[lower]*(1-frac)+vals[upper]*frac
    return {'min': vals[0], 'q1': quantile(.25), 'median': median(vals), 'q3': quantile(.75), 'max': vals[-1], 'mean': fmean(vals)}


def wafer_bounds(points: Sequence[WaferPoint]) -> tuple[float,float,float,float] | None:
    if not points: return None
    xs=[p.x for p in points]; ys=[p.y for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def spatial_bounds(points: Sequence[SpatialPoint]) -> tuple[float,float,float,float] | None:
    if not points: return None
    xs=[p.x for p in points]; ys=[p.y for p in points]
    return min(xs), max(xs), min(ys), max(ys)



def series_rows(series: Sequence[Any]) -> list[dict[str, Any]]:
    rows=[]
    for s in series:
        for i, value in enumerate(s.data):
            rows.append({'series':s.label,'series_key':s.key,'index':i,'value':value})
    return rows


class LinkedAnalysisController:
    """Coordinates semantic analytical filters without coupling charts, tables, or KPIs to each other."""
    def __init__(self, engine: CrossFilterEngine | None=None) -> None:
        self.engine=engine or CrossFilterEngine()
        self._targets: dict[str, list[Callable[[FilterMutation], Any]]] = defaultdict(list)
        self.engine.subscribe(self._route)

    def register_target(self, filter_key: str, callback: Callable[[FilterMutation], Any]) -> Callable[[], None]:
        self._targets[filter_key].append(callback)
        def unsubscribe() -> None:
            items=self._targets.get(filter_key, [])
            if callback in items: items.remove(callback)
            if not items: self._targets.pop(filter_key, None)
        return unsubscribe

    def _route(self, mutation: FilterMutation) -> None:
        for callback in tuple(self._targets.get(mutation.key, ())): callback(mutation)

    def dispatch(self, event: ChartEvent) -> tuple[FilterMutation, ...]: return self.engine.dispatch(event)
    def clear(self, key: str | None=None) -> tuple[FilterMutation, ...]: return self.engine.clear(key)


__all__=['CrossFilterEngine','LinkedAnalysisController','box_summary','histogram','pareto','series_rows','spatial_bounds','wafer_bounds']
