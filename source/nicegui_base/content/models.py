from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from nicegui_base.components import StatusIntent


class TrendDirection(str, Enum):
    UP='up'; DOWN='down'; STABLE='stable'; UNKNOWN='unknown'

class StepState(str, Enum):
    UPCOMING='upcoming'; ACTIVE='active'; COMPLETE='complete'; ERROR='error'

@dataclass(frozen=True, slots=True)
class MetricCardSpec:
    label: str
    value: str | int | float
    description: str | None = None
    delta: str | None = None
    trend: TrendDirection = TrendDirection.UNKNOWN
    intent: StatusIntent = StatusIntent.NEUTRAL
    icon: str | None = None
    clickable: bool = False
    help_text: str | None = None
    def __post_init__(self):
        if not self.label.strip(): raise ValueError('MetricCardSpec label must not be empty')

@dataclass(frozen=True, slots=True)
class ComparisonMetricSpec:
    label: str
    current: str | int | float
    baseline: str | int | float | None = None
    delta: str | int | float | None = None
    intent: StatusIntent = StatusIntent.NEUTRAL
    description: str | None = None

@dataclass(frozen=True, slots=True)
class KeyValueItem:
    key: str
    label: str
    value: Any
    description: str | None = None
    copyable: bool = False
    intent: StatusIntent = StatusIntent.NEUTRAL
    def __post_init__(self):
        if not self.key.strip() or not self.label.strip(): raise ValueError('KeyValueItem requires key and label')

@dataclass(frozen=True, slots=True)
class EntityHeaderSpec:
    title: str
    subtitle: str | None = None
    entity_type: str | None = None
    status: str | None = None
    status_intent: StatusIntent = StatusIntent.NEUTRAL
    icon: str | None = None
    metadata: Sequence[KeyValueItem] = field(default_factory=tuple)
    def __post_init__(self):
        if not self.title.strip(): raise ValueError('EntityHeaderSpec title must not be empty')

@dataclass(frozen=True, slots=True)
class TreeNode:
    key: str
    label: str
    children: Sequence['TreeNode'] = field(default_factory=tuple)
    icon: str | None = None
    disabled: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.key.strip() or not self.label.strip(): raise ValueError('TreeNode requires key and label')

@dataclass(frozen=True, slots=True)
class SearchResultSpec:
    key: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    icon: str | None = None
    status: str | None = None
    metadata: Sequence[KeyValueItem] = field(default_factory=tuple)
    def __post_init__(self):
        if not self.key.strip() or not self.title.strip(): raise ValueError('SearchResultSpec requires key and title')

@dataclass(frozen=True, slots=True)
class StepSpec:
    key: str
    label: str
    description: str | None = None
    state: StepState = StepState.UPCOMING
    icon: str | None = None
    def __post_init__(self):
        if not self.key.strip() or not self.label.strip(): raise ValueError('StepSpec requires key and label')

@dataclass(frozen=True, slots=True)
class ComparisonItem:
    key: str
    label: str
    left: Any
    right: Any
    delta: Any | None = None
    changed: bool | None = None
    def __post_init__(self):
        if not self.key.strip() or not self.label.strip(): raise ValueError('ComparisonItem requires key and label')

@dataclass(frozen=True, slots=True)
class BackgroundTaskSpec:
    label: str
    progress: float | None = None
    status: str = 'running'
    detail: str | None = None
    def __post_init__(self):
        if not self.label.strip(): raise ValueError('BackgroundTaskSpec label must not be empty')
        if self.progress is not None and not 0 <= self.progress <= 1: raise ValueError('progress must be 0..1')

@dataclass(frozen=True, slots=True)
class ActivityItem:
    key: str
    title: str
    timestamp: str | None = None
    detail: str | None = None
    icon: str | None = None
    intent: StatusIntent = StatusIntent.NEUTRAL
    actor: str | None = None
    def __post_init__(self):
        if not self.key.strip() or not self.title.strip(): raise ValueError('ActivityItem requires key and title')

__all__=[
 'TrendDirection','StepState','MetricCardSpec','ComparisonMetricSpec','KeyValueItem','EntityHeaderSpec','TreeNode',
 'SearchResultSpec','StepSpec','ComparisonItem','BackgroundTaskSpec','ActivityItem'
]
