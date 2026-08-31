from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode
from typing import Any, Mapping, Sequence


_TRUE = {'1', 'true', 'yes', 'on'}
_FALSE = {'0', 'false', 'no', 'off'}


def _encode_value(value: Any) -> str | list[str] | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return str(value)


def _coerce(value: str, kind: type | None) -> Any:
    if kind is None or kind is str:
        return value
    if kind is bool:
        lowered = value.lower()
        if lowered in _TRUE: return True
        if lowered in _FALSE: return False
        raise ValueError(f'Invalid boolean query value: {value}')
    return kind(value)


@dataclass(frozen=True, slots=True)
class UrlField:
    key: str
    kind: type = str
    multiple: bool = False
    default: Any = None


class UrlState:
    def __init__(self, fields: Sequence[UrlField] = ()): self.fields = {f.key: f for f in fields}

    def encode(self, values: Mapping[str, Any]) -> str:
        params: list[tuple[str, str]] = []
        for key in sorted(values):
            encoded = _encode_value(values[key])
            if encoded is None: continue
            if isinstance(encoded, list): params.extend((key, item) for item in encoded)
            else: params.append((key, encoded))
        return urlencode(params, doseq=True)

    def decode(self, query: str) -> dict[str, Any]:
        raw = parse_qs(query.lstrip('?'), keep_blank_values=True)
        result: dict[str, Any] = {}
        for key, values in raw.items():
            field = self.fields.get(key)
            if field is None:
                result[key] = values if len(values) > 1 else values[0]
            elif field.multiple:
                result[key] = [_coerce(v, field.kind) for v in values]
            else:
                result[key] = _coerce(values[-1], field.kind)
        for key, field in self.fields.items():
            if key not in result and field.default is not None:
                result[key] = field.default
        return result
