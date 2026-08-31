from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class FeedbackIntent(str, Enum):
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    DANGER = 'danger'
    NEUTRAL = 'neutral'


class ToastPlacement(str, Enum):
    TOP_RIGHT = 'top-right'
    TOP_CENTER = 'top-center'
    BOTTOM_RIGHT = 'bottom-right'
    BOTTOM_CENTER = 'bottom-center'


class AsyncState(str, Enum):
    IDLE = 'idle'
    LOADING = 'loading'
    READY = 'ready'
    EMPTY = 'empty'
    ERROR = 'error'
    REFRESHING = 'refreshing'
    STALE = 'stale'


class StateKind(str, Enum):
    EMPTY = 'empty'
    NO_RESULTS = 'no-results'
    ERROR = 'error'
    PERMISSION = 'permission'
    NOT_FOUND = 'not-found'
    OFFLINE = 'offline'


@dataclass(frozen=True, slots=True)
class ToastSpec:
    message: str
    intent: FeedbackIntent = FeedbackIntent.INFO
    duration_ms: int = 3500
    placement: ToastPlacement = ToastPlacement.TOP_RIGHT
    dismissible: bool = True
    action_label: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError('Toast message must not be empty')
        if self.duration_ms < 0:
            raise ValueError('duration_ms must be >= 0')


@dataclass(frozen=True, slots=True)
class AlertSpec:
    title: str
    message: str | None = None
    intent: FeedbackIntent = FeedbackIntent.INFO
    dismissible: bool = False
    action_label: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('Alert title must not be empty')

    @property
    def classes(self) -> str:
        return f'cui-alert cui-alert--{self.intent.value}'


@dataclass(frozen=True, slots=True)
class BannerSpec(AlertSpec):
    persistent: bool = True

    @property
    def classes(self) -> str:
        return f'cui-banner cui-banner--{self.intent.value}'


@dataclass(frozen=True, slots=True)
class ProgressSpec:
    value: float | None = None
    label: str | None = None
    indeterminate: bool = False

    def __post_init__(self) -> None:
        if self.value is not None and not 0 <= self.value <= 1:
            raise ValueError('Progress value must be between 0 and 1')
        if self.indeterminate and self.value is not None:
            raise ValueError('Indeterminate progress cannot specify value')


@dataclass(frozen=True, slots=True)
class SkeletonSpec:
    kind: str = 'content'
    rows: int = 3

    def __post_init__(self) -> None:
        if self.rows < 1:
            raise ValueError('Skeleton rows must be >= 1')


@dataclass(frozen=True, slots=True)
class AsyncContentSpec:
    state: AsyncState = AsyncState.IDLE
    preserve_content_while_refreshing: bool = True
    retry_label: str = 'Retry'


@dataclass(frozen=True, slots=True)
class StateViewSpec:
    kind: StateKind
    title: str
    message: str | None = None
    action_label: str | None = None
    secondary_action_label: str | None = None
    error_id: str | None = None
    compact: bool = False

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('StateViewSpec title must not be empty')

    @property
    def classes(self) -> str:
        suffix = ' cui-state-view--compact' if self.compact else ''
        return f'cui-state-view cui-state-view--{self.kind.value}{suffix}'
