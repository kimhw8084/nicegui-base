from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class DialogRequest:
    kind: str
    title: str
    message: str | None = None
    destructive: bool = False


class DialogService:
    def __init__(self, sink: Callable[[DialogRequest], Any] | None = None): self.sink = sink
    def request(self, title: str, *, message: str | None = None, kind: str = 'dialog', destructive: bool = False) -> DialogRequest:
        if not title.strip(): raise ValueError('Dialog title is required')
        req = DialogRequest(kind, title, message, destructive)
        if self.sink: self.sink(req)
        return req


class LoggingService:
    def __init__(self, logger: logging.Logger | None = None): self.logger = logger or logging.getLogger('nicegui_base')
    def event(self, name: str, *, level: int = logging.INFO, **fields: Any) -> None:
        payload = {'event': name, **fields}
        self.logger.log(level, name, extra={'nicegui_base': payload})
    def timed(self, name: str, duration_ms: float, **fields: Any) -> None:
        self.event(name, duration_ms=round(duration_ms, 3), **fields)


@dataclass(frozen=True, slots=True)
class UserFacingError:
    error_id: str
    message: str
    retryable: bool = False


class ErrorService:
    def __init__(self, logger: LoggingService | None = None, *, prefix: str = 'UI'):
        self.logger = logger or LoggingService(); self.prefix = prefix.upper()
    def capture(self, exc: BaseException, *, message: str = 'Unable to complete the request.', retryable: bool = False, context: dict[str, Any] | None = None) -> UserFacingError:
        error_id = f'{self.prefix}-{secrets.token_hex(3).upper()}'
        self.logger.event('ui_error', level=logging.ERROR, error_id=error_id, exception_type=type(exc).__name__, exception=str(exc), **(context or {}))
        return UserFacingError(error_id, message, retryable)
