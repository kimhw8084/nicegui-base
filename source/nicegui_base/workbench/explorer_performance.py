from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, TypeVar

T = TypeVar('T')
_MAX = 96
_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_MAX))
_counts: dict[str, int] = defaultdict(int)


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    count: int
    latest_ms: float
    average_ms: float
    max_ms: float


def measure(name: str, fn: Callable[[], T]) -> T:
    started = perf_counter()
    try:
        return fn()
    finally:
        elapsed = (perf_counter() - started) * 1000.0
        _samples[name].append(elapsed)
        _counts[name] += 1


def snapshot() -> tuple[Metric, ...]:
    result = []
    for name in sorted(_samples):
        values = tuple(_samples[name])
        if not values:
            continue
        result.append(Metric(name, _counts[name], values[-1], sum(values) / len(values), max(values)))
    return tuple(result)


def render_explorer_performance() -> None:
    from nicegui import ui
    metrics = snapshot()
    ui.label('Explorer performance').classes('cui-workbench-section-title')
    ui.label('Local process timings only; no user data or provider payloads are recorded.').classes('cui-workbench-note')
    with ui.element('div').classes('cui-workbench-quality-grid'):
        if not metrics:
            with ui.element('article').classes('cui-workbench-quality-card'):
                ui.label('No Explorer timings recorded yet.').classes('cui-workbench-note')
        for metric in metrics:
            with ui.element('article').classes('cui-workbench-quality-card'):
                ui.label(metric.name).classes('cui-workbench-card__title')
                ui.label(f'{metric.latest_ms:.1f} ms latest · {metric.average_ms:.1f} ms avg · {metric.count} calls').classes('cui-workbench-note')


__all__ = ['Metric', 'measure', 'render_explorer_performance', 'snapshot']
