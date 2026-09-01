from __future__ import annotations

import json
import logging
import os
import platform
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from typing import Any, Mapping

from nicegui_base.security import redact


@dataclass(frozen=True, slots=True)
class DebugEvent:
    timestamp: str
    level: str
    logger: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)
    exception_type: str | None = None
    exception: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiagnosticBuffer(logging.Handler):
    """Bounded, redacted in-process log buffer for development diagnostics.

    It intentionally stores no HTTP bodies, cookies, form values, local-storage
    contents, authorization headers, or arbitrary browser state. Existing
    ``nicegui_base.security.redact`` remains the data-loss-prevention boundary.
    """

    def __init__(self, *, capacity: int = 500) -> None:
        super().__init__(level=logging.DEBUG)
        if capacity < 25:
            raise ValueError('capacity must be at least 25')
        self.capacity = capacity
        self._events: deque[DebugEvent] = deque(maxlen=capacity)
        self._lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            context = getattr(record, 'context', None)
            if not isinstance(context, Mapping):
                context = getattr(record, 'nicegui_base', None)
            safe_context = redact(dict(context)) if isinstance(context, Mapping) else {}
            exception_type = None
            exception = None
            if record.exc_info:
                exc_type = record.exc_info[0]
                exception_type = exc_type.__name__ if exc_type else None
                exception = redact(logging.Formatter().formatException(record.exc_info))
            event = DebugEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level=record.levelname,
                logger=record.name,
                message=str(redact(record.getMessage())),
                context=safe_context,
                exception_type=exception_type,
                exception=str(exception) if exception is not None else None,
            )
            with self._lock:
                self._events.append(event)
        except Exception:
            # Diagnostics must never make the application less reliable.
            return

    def snapshot(self, *, minimum_level: int = logging.DEBUG, limit: int = 250) -> tuple[DebugEvent, ...]:
        with self._lock:
            values = tuple(self._events)
        threshold = int(minimum_level)
        filtered = [event for event in values if logging._nameToLevel.get(event.level, logging.INFO) >= threshold]
        return tuple(filtered[-max(1, int(limit)):])

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def counts(self) -> dict[str, int]:
        result = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
        with self._lock:
            for event in self._events:
                if event.level in result:
                    result[event.level] += 1
        return result


_BUFFER = DiagnosticBuffer()
_INSTALLED = False


def install_diagnostic_logging() -> DiagnosticBuffer:
    global _INSTALLED
    if _INSTALLED:
        return _BUFFER
    root = logging.getLogger()
    if not any(isinstance(handler, DiagnosticBuffer) for handler in root.handlers):
        root.addHandler(_BUFFER)
    framework_logger = logging.getLogger('nicegui_base')
    if not framework_logger.propagate and not any(isinstance(handler, DiagnosticBuffer) for handler in framework_logger.handlers):
        framework_logger.addHandler(_BUFFER)
    _INSTALLED = True
    return _BUFFER


def diagnostic_buffer() -> DiagnosticBuffer:
    return install_diagnostic_logging()


def runtime_snapshot(*, app_name: str = '', app_version: str = '', environment: str = '') -> dict[str, Any]:
    def package_version(name: str) -> str:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            return 'not-installed'

    return {
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'app': {'name': app_name, 'version': app_version, 'environment': environment},
        'python': {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'executable': sys.executable,
        },
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
        },
        'packages': {
            'nicegui-base': package_version('nicegui-base'),
            'nicegui': package_version('nicegui'),
        },
        'process': {
            'pid': os.getpid(),
            'thread_count': threading.active_count(),
            'monotonic_seconds': round(time.monotonic(), 3),
        },
    }


def build_diagnostic_bundle(
    *,
    app_name: str = '',
    app_version: str = '',
    environment: str = '',
    browser: Mapping[str, Any] | None = None,
    health: Mapping[str, Any] | None = None,
    event_limit: int = 500,
) -> bytes:
    buffer = diagnostic_buffer()
    payload = {
        'schema': 'nicegui-base-diagnostic-bundle/v1',
        'runtime': runtime_snapshot(app_name=app_name, app_version=app_version, environment=environment),
        'log_counts': buffer.counts(),
        'logs': [event.to_dict() for event in buffer.snapshot(limit=event_limit)],
        'browser': redact(dict(browser or {})),
        'health': redact(dict(health or {})),
        'privacy': {
            'redacted': True,
            'http_bodies_collected': False,
            'cookies_collected': False,
            'authorization_headers_collected': False,
            'form_values_collected': False,
            'local_storage_values_collected': False,
        },
    }
    return (json.dumps(payload, indent=2, sort_keys=True, default=str) + '\n').encode('utf-8')


__all__ = [
    'DebugEvent', 'DiagnosticBuffer', 'build_diagnostic_bundle', 'diagnostic_buffer',
    'install_diagnostic_logging', 'runtime_snapshot',
]
