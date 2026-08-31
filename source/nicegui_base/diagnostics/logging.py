from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from nicegui_base.security import redact
from .correlation import get_correlation_id


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': redact(record.getMessage()),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload['correlation_id'] = correlation_id
        context = getattr(record, 'context', None)
        if not isinstance(context, Mapping):
            context = getattr(record, 'nicegui_base', None)
        if isinstance(context, Mapping):
            payload['context'] = redact(context)
        if record.exc_info:
            payload['exception_type'] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload['exception'] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, separators=(',', ':'))


def configure_structured_logging(*, level: str = 'INFO', logger_name: str = 'nicegui_base') -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
    logger.log(level, message, extra={'context': context})
