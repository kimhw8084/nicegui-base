from __future__ import annotations

import re
from typing import Callable


def required(message: str = 'Required') -> Callable[[object | None], str | None]:
    def validate(value: object | None) -> str | None:
        if value is None:
            return message
        if isinstance(value, str) and not value.strip():
            return message
        if isinstance(value, (list, tuple, set, dict)) and not value:
            return message
        return None
    return validate


def min_length(length: int, message: str | None = None):
    if length < 0:
        raise ValueError('length must be >= 0')
    text = message or f'Must be at least {length} characters'
    def validate(value: object | None) -> str | None:
        if value is None:
            return None
        return text if len(str(value)) < length else None
    return validate


def numeric_range(minimum: float | None = None, maximum: float | None = None, message: str | None = None):
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError('minimum cannot exceed maximum')
    def validate(value: object | None) -> str | None:
        if value in (None, ''):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 'Must be a number'
        if minimum is not None and number < minimum:
            return message or f'Must be at least {minimum:g}'
        if maximum is not None and number > maximum:
            return message or f'Must be no more than {maximum:g}'
        return None
    return validate


def pattern(regex: str, message: str = 'Invalid format'):
    compiled = re.compile(regex)
    def validate(value: object | None) -> str | None:
        if value in (None, ''):
            return None
        return None if compiled.fullmatch(str(value)) else message
    return validate
