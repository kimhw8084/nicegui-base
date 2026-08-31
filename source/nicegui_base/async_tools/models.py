from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class DuplicatePolicy(str, Enum):
    IGNORE = 'ignore'
    CANCEL_PREVIOUS = 'cancel_previous'
    ALLOW = 'allow'


class TaskStatus(str, Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    SUCCESS = 'success'
    ERROR = 'error'
    CANCELLED = 'cancelled'


@dataclass(slots=True)
class RefreshStatus:
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    refreshing: bool = False
    stale_after_seconds: float = 300.0

    @property
    def stale(self) -> bool:
        if self.last_success is None:
            return True
        return datetime.now(timezone.utc) - self.last_success > timedelta(seconds=self.stale_after_seconds)

    @property
    def age_seconds(self) -> float | None:
        if self.last_success is None:
            return None
        return max(0.0, (datetime.now(timezone.utc) - self.last_success).total_seconds())
