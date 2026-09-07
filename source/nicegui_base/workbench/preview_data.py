"""Shared, bounded data contract for Studio, examples and project snapshots."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

MAX_PROJECT_ROWS = 5000
MAX_PROJECT_BYTES = 2 * 1024 * 1024
MAX_PROJECT_COLUMNS = 128
MAX_VALUE_DEPTH = 20

_NUMERIC_TYPES = frozenset({'integer', 'float', 'decimal'})
_NON_MEASUREMENT_ROLES = frozenset({'identifier', 'dimension', 'entity', 'timestamp'})
_IDENTIFIER_TOKENS = frozenset({'id', 'key', 'uuid', 'identifier', 'record', 'trace', 'serial', 'code'})
_CATEGORY_TOKENS = frozenset({
    'area', 'batch', 'bin', 'category', 'chamber', 'class', 'group', 'lot', 'name', 'status',
    'state', 'tool', 'type', 'wafer', 'zone', 'label',
})


def _json_value(value: Any, _depth: int = 0) -> Any:
    if _depth > MAX_VALUE_DEPTH:
        raise ValueError("Data nesting exceeds 20 levels.")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Data contains a non-finite number; correct it before saving.')
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('JSON object keys must be strings.')
        return {k: _json_value(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v, _depth + 1) for v in value]
    raise ValueError(f'Unsupported data value: {type(value).__name__}. Convert it to JSON-compatible data.')


def checked_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Retain all permitted rows or reject; never silently save a prefix."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise ValueError('Data rows must be a sequence of objects.')
    if len(rows) > MAX_PROJECT_ROWS:
        raise ValueError(f'This development project supports {MAX_PROJECT_ROWS:,} rows, but received {len(rows):,}. '
                         'Use a provider for larger datasets. No rows were saved or discarded.')
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError('Each data row must be an object. No rows were saved or discarded.')
    names = set(key for row in rows for key in row)
    if len(names) > MAX_PROJECT_COLUMNS:
        raise ValueError(f'Development data supports at most {MAX_PROJECT_COLUMNS} columns.')
    if any(not isinstance(k, str) or not k.strip() or len(k) > 160 for k in names):
        raise ValueError('Column names must be nonempty strings of at most 160 characters.')
    result = [_json_value(row) for row in rows]
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(payload) > MAX_PROJECT_BYTES:
        raise ValueError('Development data exceeds the 2 MiB project limit. Use a provider or a smaller explicit sample. '
                         'No rows were saved or discarded.')
    return result


def _enum_value(value: Any) -> str:
    return str(getattr(value, 'value', value) or '').strip().casefold()


def _schema_items(schema: Any) -> tuple[dict[str, Any], ...]:
    """Normalize DataSchema and serialized Workbench schema metadata.

    The Workbench intentionally accepts both forms here. Generated applications use
    ``DataSchema`` while Studio previews still own a serializable Data Dock schema.
    Keeping this adapter local prevents the preview module from taking a dependency
    on a particular storage representation.
    """
    if schema is None:
        return ()
    source = getattr(schema, 'fields', schema)
    if isinstance(source, Mapping):
        source = source.get('fields', ())
    if not isinstance(source, (list, tuple)):
        return ()
    result: list[dict[str, Any]] = []
    for item in source:
        if isinstance(item, Mapping):
            name = str(item.get('name') or '').strip()
            if not name:
                continue
            result.append({
                'name': name,
                'type': _enum_value(item.get('type') or item.get('inferred_type')),
                'role': _enum_value(item.get('role')),
            })
            continue
        name = str(getattr(item, 'name', '') or '').strip()
        if name:
            result.append({
                'name': name,
                'type': _enum_value(getattr(item, 'type', None) or getattr(item, 'inferred_type', None)),
                'role': _enum_value(getattr(item, 'role', None)),
            })
    return tuple(result)


def _field_names(rows: Sequence[Mapping[str, Any]], schema: Any = None) -> tuple[str, ...]:
    schema_names = tuple(item['name'] for item in _schema_items(schema))
    row_names = tuple(dict.fromkeys(str(key) for row in rows for key in row))
    return tuple(dict.fromkeys((*schema_names, *row_names)))


def _looks_like_identifier(name: str) -> bool:
    folded = name.casefold().replace('-', '_').replace(' ', '_')
    tokens = {folded, *[token for token in folded.split('_') if token]}
    return bool(tokens & _IDENTIFIER_TOKENS) or folded.endswith(('_id', '_key', '_uuid', '_code'))


def _looks_like_category(name: str) -> bool:
    folded = name.casefold().replace('-', '_').replace(' ', '_')
    tokens = {folded, *[token for token in folded.split('_') if token]}
    return bool(tokens & _CATEGORY_TOKENS)


def _measurement_number(raw: Any, field: str, index: int) -> float | None:
    if raw is None or raw == '':
        return None
    if isinstance(raw, bool):
        raise ValueError(f'Measurement field {field!r} contains boolean data at row {index + 1}; choose a numeric field.')
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Measurement field {field!r} contains non-numeric data at row {index + 1}.') from exc
    if not math.isfinite(number):
        raise ValueError(f'Measurement field {field!r} contains a non-finite number at row {index + 1}.')
    return number


def _validated_values(rows: Sequence[Mapping[str, Any]], field: str) -> tuple[float | None, ...]:
    values = tuple(_measurement_number(row.get(field), field, index) for index, row in enumerate(rows))
    if not any(value is not None for value in values):
        raise ValueError(f'Measurement field {field!r} has no populated numeric values.')
    return values


def _candidate_fields(rows: Sequence[Mapping[str, Any]], schema: Any = None) -> tuple[str, ...]:
    metadata = {item['name']: item for item in _schema_items(schema)}
    candidates: list[str] = []
    for name in _field_names(rows, schema):
        item = metadata.get(name, {})
        role = item.get('role', '')
        type_name = item.get('type', '')
        # Confirmed identifiers/categories are never inferred as measurements. A
        # numeric field explicitly marked as an attribute remains eligible only when
        # it is the sole unambiguous numeric field.
        if role in _NON_MEASUREMENT_ROLES or type_name in {'boolean', 'date', 'datetime', 'category', 'json', 'string'}:
            continue
        # Metadata can be partial after a rename or an imported schema update.
        # Apply the identifier/category guard to every unconfirmed field so a
        # numeric record id can never become the inferred measurement.
        if _looks_like_identifier(name) or _looks_like_category(name):
            continue
        try:
            values = _validated_values(rows, name)
        except ValueError:
            continue
        if any(value is not None for value in values):
            candidates.append(name)
    return tuple(candidates)


def resolve_measurement_field(
    rows: Sequence[Mapping[str, Any]],
    *,
    schema: Any = None,
    field: str | None = None,
    measurement_field: str | None = None,
    required: bool = True,
) -> str | None:
    """Resolve one safe measurement field without guessing from identifiers.

    ``field`` is the explicit per-capability override and therefore has priority over
    the generated contract mapping. ``measurement_field`` is the confirmed mapping
    emitted by the data handoff. With neither, exactly one eligible numeric field is
    required; ambiguity is surfaced so the caller can present a choice/error.
    """
    names = _field_names(rows, schema)
    explicit = str(field).strip() if field is not None and str(field).strip() else None
    confirmed = str(measurement_field).strip() if measurement_field is not None and str(measurement_field).strip() else None
    selected = explicit or confirmed
    if selected:
        if selected not in names:
            kind = 'explicit measurement field' if explicit else 'confirmed measurement field'
            raise ValueError(f'{kind} {selected!r} does not exist in the dataset.')
        _validated_values(rows, selected)
        return selected

    metadata = {item['name']: item for item in _schema_items(schema)}
    confirmed_candidates = tuple(
        item['name'] for item in _schema_items(schema)
        if item.get('role') == 'measurement' and item.get('type') not in {'boolean', 'date', 'datetime', 'category', 'json', 'string'}
    )
    if len(confirmed_candidates) > 1:
        raise ValueError('ambiguous measurement mapping. Choose one measurement field: ' + ', '.join(confirmed_candidates) + '.')
    if len(confirmed_candidates) == 1:
        _validated_values(rows, confirmed_candidates[0])
        return confirmed_candidates[0]

    candidates = _candidate_fields(rows, schema)
    if len(candidates) > 1:
        raise ValueError('ambiguous measurement mapping. Choose one measurement field: ' + ', '.join(candidates) + '.')
    if len(candidates) == 1:
        return candidates[0]
    if required:
        raise ValueError('No eligible numeric measurement field was found. Choose a populated numeric measurement column.')
    return None


def resolve_category_field(
    rows: Sequence[Mapping[str, Any]],
    *,
    schema: Any = None,
    field: str | None = None,
    category_field: str | None = None,
    required: bool = False,
) -> str | None:
    """Resolve the confirmed category/entity label field for chart axes."""
    names = _field_names(rows, schema)
    explicit = str(field).strip() if field is not None and str(field).strip() else None
    confirmed = str(category_field).strip() if category_field is not None and str(category_field).strip() else None
    selected = explicit or confirmed
    if selected:
        if selected not in names:
            raise ValueError(f'Explicit category field {selected!r} does not exist in the dataset.')
        return selected
    candidates = tuple(
        item['name'] for item in _schema_items(schema)
        if item.get('role') in {'dimension', 'entity'}
    )
    if len(candidates) > 1:
        # A label axis can safely fall back to the confirmed row key when several
        # dimensions are available. Unlike measurement selection this does not
        # change numeric meaning or cause a value column to be guessed.
        return None
    if candidates:
        return candidates[0]
    if required:
        raise ValueError('No category field is available for chart labels.')
    return next((name for name in names if _looks_like_identifier(name)), None)


def numeric_data(
    rows: Sequence[Mapping[str, Any]],
    field: str | None = None,
    *,
    schema: Any = None,
    measurement_field: str | None = None,
) -> tuple[str, tuple[float | None, ...]]:
    selected = resolve_measurement_field(rows, schema=schema, field=field, measurement_field=measurement_field)
    assert selected is not None
    return selected, _validated_values(rows, selected)


__all__ = [
    'MAX_PROJECT_BYTES', 'MAX_PROJECT_COLUMNS', 'MAX_PROJECT_ROWS', 'MAX_VALUE_DEPTH',
    'checked_rows', 'numeric_data', 'resolve_category_field', 'resolve_measurement_field',
]
