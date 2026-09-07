from __future__ import annotations

import csv
import io
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .preview_data import checked_rows, MAX_PROJECT_BYTES, MAX_PROJECT_ROWS, MAX_PROJECT_COLUMNS


class DataDockFormat(str, Enum):
    SAMPLE = 'sample'
    TSV = 'tsv'
    CSV = 'csv'
    JSON = 'json'


class DataDockSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass(frozen=True, slots=True)
class DataDockIssue:
    code: str
    message: str
    severity: DataDockSeverity = DataDockSeverity.WARNING
    column: str | None = None
    row: int | None = None


@dataclass(frozen=True, slots=True)
class DataDockColumn:
    name: str
    inferred_type: str
    role: str
    nullable: bool
    confidence: float = 1.0
    original_name: str | None = None


@dataclass(frozen=True, slots=True)
class DataDockQuality:
    rows: int
    columns: int
    missing_cells: int
    duplicate_rows: int
    issues: tuple[DataDockIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not any(issue.severity is DataDockSeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class DataDockSnapshot:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[DataDockColumn, ...]
    source_format: DataDockFormat
    quality: DataDockQuality
    source_name: str = ''
    revision: int = 0

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


@dataclass(frozen=True, slots=True)
class DataDockParseResult:
    snapshot: DataDockSnapshot | None
    issues: tuple[DataDockIssue, ...]
    detected_format: DataDockFormat | None = None

    @property
    def ok(self) -> bool:
        return self.snapshot is not None and not any(issue.severity is DataDockSeverity.ERROR for issue in self.issues)


_ROLE_TOKENS = {
    'timestamp': ('time', 'timestamp', 'datetime', 'date', 'event_time', 'measured_at', 'sample_time'),
    'identifier': ('id', 'uuid', 'key', 'record_id', 'measurement_id', 'trace_id'),
    'entity': ('wafer', 'wafer_id', 'lot', 'lot_id', 'batch', 'tool', 'tool_id', 'chamber', 'chamber_id', 'sensor', 'sensor_id', 'recipe', 'recipe_version', 'product', 'operation', 'route', 'fab', 'area'),
    'measurement': ('value', 'measurement', 'metric', 'reading', 'count', 'yield', 'yield_pct', 'cd', 'sensor_value', 'loss', 'output', 'throughput'),
    'dimension': ('category', 'bin', 'yield_bin', 'defect_class', 'status', 'state', 'group', 'type', 'class'),
}

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_DATETIME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[T ][0-2]\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d)?$')
_INT_RE = re.compile(r'^[+-]?\d+$')
_FLOAT_RE = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')


def _normalize_header(value: Any, index: int) -> str:
    text = str(value or '').strip()
    return text or f'column_{index + 1}'


def _parse_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, date, datetime, dict, list, tuple)):
        return value
    text = str(value).strip()
    if text == '':
        return None
    low = text.casefold()
    if low in {'true', 'yes'}:
        return True
    if low in {'false', 'no'}:
        return False
    if _INT_RE.fullmatch(text):
        if len(text.lstrip('+-')) > 1 and text.lstrip('+-').startswith('0'):
            return text  # Preserve zero-padded identifiers from CSV/TSV.
        try:
            return int(text)
        except ValueError:
            pass
    if _FLOAT_RE.fullmatch(text):
        try:
            value = float(text)
            return value if math.isfinite(value) else text
        except ValueError:
            pass
    if _DATETIME_RE.fullmatch(text):
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            pass
    if _DATE_RE.fullmatch(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
    return text


def _type_name(values: Sequence[Any]) -> str:
    present = [value for value in values if value is not None]
    if not present:
        return 'unknown'
    if all(isinstance(value, bool) for value in present):
        return 'boolean'
    if all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        return 'integer'
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present):
        return 'float'
    if all(isinstance(value, datetime) for value in present):
        return 'datetime'
    if all(isinstance(value, date) and not isinstance(value, datetime) for value in present):
        return 'date'
    if all(isinstance(value, (dict, list, tuple)) for value in present):
        return 'json'
    return 'string'


def suggest_semantic_role(name: str, inferred_type: str) -> tuple[str, float]:
    folded = name.casefold().strip().replace('-', '_').replace(' ', '_')
    tokens = {folded, *[token for token in folded.split('_') if token]}
    for role, aliases in _ROLE_TOKENS.items():
        if folded in aliases or any(alias in tokens for alias in aliases):
            return role, 0.98 if folded in aliases else 0.9
    if inferred_type in {'datetime', 'date'}:
        return 'timestamp', 0.9
    if inferred_type in {'integer', 'float'}:
        if folded.endswith('_id'):
            return 'identifier', 0.9
        return 'measurement', 0.72
    if folded.endswith('_id'):
        return 'entity', 0.82
    return 'attribute', 0.55


def _coerce_for_type(value: Any, type_name: str) -> Any:
    if value is None or type_name == 'unknown':
        return value
    raw = _parse_scalar(value)
    if raw is None:
        return None
    if type_name == 'string' or type_name == 'category':
        return str(value)
    if type_name == 'integer':
        if isinstance(raw, bool):
            raise ValueError('boolean is not an integer value')
        converted = int(raw)
        if isinstance(raw, float) and raw != converted:
            raise ValueError('fractional values cannot be converted to integers without data loss')
        return converted
    if type_name == 'float':
        if isinstance(raw, bool):
            raise ValueError('boolean is not a numeric value')
        result = float(raw)
        if not math.isfinite(result):
            raise ValueError('number must be finite')
        return result
    if type_name == 'boolean':
        if isinstance(raw, bool):
            return raw
        raise ValueError(f'{value!r} is not boolean')
    if type_name == 'date':
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(value))
    if type_name == 'datetime':
        if isinstance(raw, datetime):
            return raw
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if type_name == 'json':
        if isinstance(raw, (dict, list, tuple)):
            return raw
        return json.loads(str(value))
    return raw


def _dedupe_headers(headers: Sequence[str]) -> tuple[tuple[str, ...], tuple[DataDockIssue, ...]]:
    used: set[str] = set()
    output: list[str] = []
    issues: list[DataDockIssue] = []
    for index, header in enumerate(headers):
        base = _normalize_header(header, index)
        name = base
        suffix = 2
        while name in used:
            name = f'{base}_{suffix}'
            suffix += 1
        if name != base:
            issues.append(DataDockIssue('duplicate_header', f'Duplicate column {base!r} was renamed to {name!r}.', DataDockSeverity.WARNING, column=name))
        used.add(name)
        output.append(name)
    return tuple(output), tuple(issues)


def _quality(rows: Sequence[Mapping[str, Any]], columns: Sequence[DataDockColumn], base_issues: Iterable[DataDockIssue] = ()) -> DataDockQuality:
    names = tuple(column.name for column in columns)
    missing = sum(row.get(name) is None for row in rows for name in names)
    frozen_rows = [tuple(repr(row.get(name)) for name in names) for row in rows]
    duplicates = len(frozen_rows) - len(set(frozen_rows))
    issues = list(base_issues)
    if not rows:
        issues.append(DataDockIssue('empty_dataset', 'No data rows are available.', DataDockSeverity.WARNING))
    if not columns:
        issues.append(DataDockIssue('no_columns', 'No columns were detected.', DataDockSeverity.ERROR))
    uncertain = [column for column in columns if column.confidence < 0.7]
    for column in uncertain:
        issues.append(DataDockIssue('uncertain_role', f'Semantic role for {column.name!r} is uncertain; confirm before recipe mapping.', DataDockSeverity.WARNING, column=column.name))
    return DataDockQuality(len(rows), len(columns), missing, duplicates, tuple(issues))


def _infer_columns(rows: Sequence[Mapping[str, Any]], names: Sequence[str]) -> tuple[DataDockColumn, ...]:
    columns: list[DataDockColumn] = []
    for name in names:
        values = tuple(row.get(name) for row in rows)
        inferred = _type_name(values)
        role, confidence = suggest_semantic_role(name, inferred)
        columns.append(DataDockColumn(name, inferred, role, any(value is None for value in values), confidence, name))
    return tuple(columns)


def _rows_from_delimited(text: str, delimiter: str) -> tuple[list[dict[str, Any]], tuple[DataDockIssue, ...]]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
    records = list(reader)
    if not records:
        return [], (DataDockIssue('empty_input', 'Paste or upload at least a header row and one data row.', DataDockSeverity.ERROR),)
    headers, issues = _dedupe_headers(records[0])
    rows: list[dict[str, Any]] = []
    extra_issues = list(issues)
    for row_index, values in enumerate(records[1:], start=2):
        if not any(str(value).strip() for value in values):
            continue
        if len(values) > len(headers):
            extra_issues.append(DataDockIssue('extra_cells', f'Row {row_index} contains {len(values) - len(headers)} extra cell(s). Correct the header or row before importing; no data was replaced.', DataDockSeverity.ERROR, row=row_index))
        if len(values) < len(headers):
            values = [*values, *([''] * (len(headers) - len(values)))]
        rows.append({name: _parse_scalar(value) for name, value in zip(headers, values[:len(headers)])})
    return rows, tuple(extra_issues)


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key {key!r}; no data was replaced.')
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError(f'Non-finite JSON number {value!r} is not accepted.')


def _rows_from_json(text: str) -> tuple[list[dict[str, Any]], tuple[DataDockIssue, ...]]:
    try:
        payload = json.loads(text, object_pairs_hook=_unique_json_object, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as exc:
        return [], (DataDockIssue('invalid_json', f'JSON parse error at line {exc.lineno}, column {exc.colno}: {exc.msg}', DataDockSeverity.ERROR, row=exc.lineno),)
    except (ValueError, RecursionError) as exc:
        return [], (DataDockIssue('invalid_json', str(exc), DataDockSeverity.ERROR),)
    if not isinstance(payload, list):
        return [], (DataDockIssue('json_not_array', 'JSON input must be an array of objects.', DataDockSeverity.ERROR),)
    if not payload:
        return [], (DataDockIssue('empty_json', 'JSON array is empty.', DataDockSeverity.WARNING),)
    if any(not isinstance(item, Mapping) for item in payload):
        return [], (DataDockIssue('json_row_type', 'Every JSON array item must be an object.', DataDockSeverity.ERROR),)
    names = tuple(dict.fromkeys(str(key) for item in payload for key in item))
    rows = [{name: _parse_scalar(item.get(name)) for name in names} for item in payload]
    return rows, ()


def detect_format(text: str, *, filename: str | None = None) -> DataDockFormat:
    stripped = text.lstrip('\ufeff \t\r\n')
    suffix = (filename or '').casefold().rsplit('.', 1)[-1] if '.' in (filename or '') else ''
    if suffix == 'json' or stripped.startswith('['):
        return DataDockFormat.JSON
    if suffix in {'tsv', 'tab'}:
        return DataDockFormat.TSV
    if suffix == 'csv':
        return DataDockFormat.CSV
    first_line = stripped.splitlines()[0] if stripped else ''
    if '\t' in first_line:
        return DataDockFormat.TSV
    return DataDockFormat.CSV


def parse_data(text: str, *, filename: str | None = None, format_hint: DataDockFormat | str | None = None, source_name: str = '') -> DataDockParseResult:
    if not isinstance(text, str):
        return DataDockParseResult(None, (DataDockIssue('invalid_input_type', 'Data input must be text.', DataDockSeverity.ERROR),))
    if not text.strip():
        return DataDockParseResult(None, (DataDockIssue('empty_input', 'Paste or upload data before analyzing it.', DataDockSeverity.ERROR),))
    try:
        detected = DataDockFormat(format_hint) if format_hint is not None else detect_format(text, filename=filename)
    except ValueError:
        return DataDockParseResult(None, (DataDockIssue('unsupported_format', f'Unsupported data format: {format_hint!r}.', DataDockSeverity.ERROR),))
    text = text.lstrip('\ufeff')
    if len(text.encode('utf-8')) > MAX_PROJECT_BYTES:
        return DataDockParseResult(None, (DataDockIssue('data_limit', 'Input exceeds the 2 MiB development limit. Existing data was not changed.', DataDockSeverity.ERROR),), detected)
    try:
        if detected is DataDockFormat.JSON:
            rows, issues = _rows_from_json(text)
        else:
            rows, issues = _rows_from_delimited(text, '\t' if detected is DataDockFormat.TSV else ',')
        if any(issue.severity is DataDockSeverity.ERROR for issue in issues):
            return DataDockParseResult(None, issues, detected)
        checked_rows(rows)
        names = tuple(dict.fromkeys(key for row in rows for key in row))
        if not names and detected is not DataDockFormat.JSON:
            header = next(csv.reader(io.StringIO(text), delimiter='\t' if detected is DataDockFormat.TSV else ',', strict=True), ())
            names, _ = _dedupe_headers(header)
        if len(names) > MAX_PROJECT_COLUMNS or any(len(n) > 160 for n in names):
            raise ValueError('Use at most 128 columns with names of at most 160 characters.')
    except (ValueError, TypeError, csv.Error, RecursionError) as exc:
        return DataDockParseResult(None, (DataDockIssue('invalid_data', str(exc), DataDockSeverity.ERROR),), detected)
    columns = _infer_columns(rows, names)
    quality = _quality(rows, columns, issues)
    snapshot = DataDockSnapshot(tuple(deepcopy(rows)), columns, detected, quality, source_name=source_name or filename or detected.value)
    return DataDockParseResult(snapshot, quality.issues, detected)


class DataDockModel:
    """Example-data playground backed by canonical NiceGUI Base schema/source types.

    The model owns bounded example editing history. It does not replace DataSource: use
    :meth:`to_data_source` when a framework capability needs queryable data.
    """

    def __init__(self, sample_rows: Sequence[Mapping[str, Any]] = (), *, sample_name: str = 'Sample data', history_limit: int = 50):
        if history_limit < 1:
            raise ValueError('history_limit must be positive')
        checked_rows(sample_rows)
        self.history_limit = history_limit
        self._sample_rows = tuple(deepcopy(dict(row)) for row in sample_rows)
        self.sample_name = sample_name
        self._undo: list[DataDockSnapshot] = []
        self._redo: list[DataDockSnapshot] = []
        self._revision = 0
        self._snapshot = self._from_rows(self._sample_rows, DataDockFormat.SAMPLE, sample_name)

    @property
    def snapshot(self) -> DataDockSnapshot:
        return self._snapshot

    @property
    def rows(self) -> tuple[dict[str, Any], ...]:
        return self._snapshot.rows

    @property
    def columns(self) -> tuple[DataDockColumn, ...]:
        return self._snapshot.columns

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def _from_rows(self, rows: Sequence[Mapping[str, Any]], source_format: DataDockFormat, source_name: str, *, columns: Sequence[DataDockColumn] | None = None, issues: Iterable[DataDockIssue] = ()) -> DataDockSnapshot:
        checked_rows(rows)
        copied = tuple(deepcopy(dict(row)) for row in rows)
        names = tuple(dict.fromkeys(key for row in copied for key in row))
        inferred = tuple(columns) if columns is not None else _infer_columns(copied, names)
        column_names = [column.name for column in inferred]
        if (len(column_names) > MAX_PROJECT_COLUMNS or len(set(column_names)) != len(column_names)
                or any(not isinstance(name, str) or not name.strip() or len(name) > 160 for name in column_names)):
            raise ValueError('Schema must contain at most 128 distinct, nonempty field names of at most 160 characters.')
        return DataDockSnapshot(copied, inferred, source_format, _quality(copied, inferred, issues), source_name, self._revision)

    def _commit(self, snapshot: DataDockSnapshot) -> DataDockSnapshot:
        checked_rows(snapshot.rows)
        self._undo.append(self._snapshot)
        if len(self._undo) > self.history_limit:
            del self._undo[: len(self._undo) - self.history_limit]
        while len(self._undo) > 1 and sum(len(json.dumps(x.rows, default=str).encode('utf-8')) for x in self._undo) > 8 * MAX_PROJECT_BYTES:
            self._undo.pop(0)
        self._redo.clear()
        self._revision += 1
        self._snapshot = replace(snapshot, revision=self._revision)
        return self._snapshot

    def load_text(self, text: str, *, filename: str | None = None, format_hint: DataDockFormat | str | None = None, source_name: str = '') -> DataDockParseResult:
        result = parse_data(text, filename=filename, format_hint=format_hint, source_name=source_name)
        if result.ok:
            self._commit(result.snapshot)
            result = DataDockParseResult(self._snapshot, self._snapshot.quality.issues, result.detected_format)
        return result

    def load_bytes(self, content: bytes, *, filename: str) -> DataDockParseResult:
        if len(content) > MAX_PROJECT_BYTES:
            return DataDockParseResult(None, (DataDockIssue('data_limit', 'Upload exceeds 2 MiB. Existing data was not changed.', DataDockSeverity.ERROR),))
        try:
            text = bytes(content).decode('utf-8-sig')
        except UnicodeDecodeError:
            return DataDockParseResult(None, (DataDockIssue('encoding', 'CSV/JSON uploads must be UTF-8 encoded.', DataDockSeverity.ERROR),))
        return self.load_text(text, filename=filename, source_name=filename)

    def reset_sample(self) -> DataDockSnapshot:
        return self._commit(self._from_rows(self._sample_rows, DataDockFormat.SAMPLE, self.sample_name))

    def replace_rows(self, rows: Sequence[Mapping[str, Any]], *, source_name: str | None = None) -> DataDockSnapshot:
        columns_by_name = {column.name: column for column in self.columns}
        names = tuple(dict.fromkeys(key for row in rows for key in row))
        columns = []
        inferred = {column.name: column for column in _infer_columns(rows, names)}
        for name in names:
            prior = columns_by_name.get(name)
            latest = inferred[name]
            columns.append(replace(latest, role=prior.role, confidence=prior.confidence) if prior else latest)
        return self._commit(self._from_rows(rows, self.snapshot.source_format, source_name or self.snapshot.source_name, columns=columns))

    def edit_cell(self, row_index: int, column: str, value: Any) -> DataDockSnapshot:
        if not 0 <= row_index < len(self.rows):
            raise IndexError(row_index)
        target = next((item for item in self.columns if item.name == column), None)
        if target is None:
            raise KeyError(column)
        rows = [dict(row) for row in self.rows]
        rows[row_index][column] = _coerce_for_type(value, target.inferred_type)
        return self._commit(self._from_rows(rows, self.snapshot.source_format, self.snapshot.source_name, columns=self.columns))

    def add_row(self, values: Mapping[str, Any] | None = None) -> DataDockSnapshot:
        row = {column.name: None for column in self.columns}
        for key, value in dict(values or {}).items():
            if key not in row:
                raise KeyError(key)
            target = next(column for column in self.columns if column.name == key)
            row[key] = _coerce_for_type(value, target.inferred_type)
        return self._commit(self._from_rows((*self.rows, row), self.snapshot.source_format, self.snapshot.source_name, columns=self.columns))

    def delete_row(self, row_index: int) -> DataDockSnapshot:
        if not 0 <= row_index < len(self.rows):
            raise IndexError(row_index)
        rows = [dict(row) for index, row in enumerate(self.rows) if index != row_index]
        # Preserve columns when the last row is removed.
        if not rows:
            return self._commit(self._from_rows((), self.snapshot.source_format, self.snapshot.source_name, columns=self.columns))
        return self._commit(self._from_rows(rows, self.snapshot.source_format, self.snapshot.source_name, columns=self.columns))

    def rename_column(self, old: str, new: str) -> DataDockSnapshot:
        new = str(new).strip()
        if not new:
            raise ValueError('column name must not be empty')
        if old not in self.snapshot.column_names:
            raise KeyError(old)
        if new != old and new in self.snapshot.column_names:
            raise ValueError(f'column {new!r} already exists')
        rows = []
        for row in self.rows:
            updated = {}
            for key, value in row.items():
                updated[new if key == old else key] = value
            rows.append(updated)
        columns = tuple(replace(column, name=new, original_name=column.original_name or old) if column.name == old else column for column in self.columns)
        return self._commit(self._from_rows(rows, self.snapshot.source_format, self.snapshot.source_name, columns=columns))

    def configure_column(self, old: str, *, name: str, type_name: str, role: str) -> DataDockSnapshot:
        """Apply rename/type/role together, or leave the original state and history intact."""
        staged = DataDockModel(self.rows, sample_name=self.snapshot.source_name)
        staged.restore_schema_metadata(self.schema_metadata())
        if name != old:
            staged.rename_column(old, name)
        staged.set_column_type(name, type_name)
        staged.set_semantic_role(name, role)
        return self._commit(self._from_rows(staged.rows, self.snapshot.source_format, self.snapshot.source_name, columns=staged.columns))

    def to_payload(self) -> dict[str, Any]:
        return {'rows': checked_rows(self.serializable_rows()), 'columns': list(self.schema_metadata()),
                'source_name': self.snapshot.source_name, 'source_format': self.snapshot.source_format.value}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> 'DataDockModel':
        rows = checked_rows(payload.get('rows', []))
        columns = payload.get('columns', ())
        if not isinstance(columns, (list, tuple)) or len(columns) > MAX_PROJECT_COLUMNS:
            raise ValueError('Saved data schema is invalid.')
        result = cls(rows, sample_name=str(payload.get('source_name') or 'Restored data')[:160])
        result.restore_schema_metadata(columns)
        # Rehydrate serialized date/datetime values with the persisted field contract.
        converted = []
        for row in rows:
            converted.append({col.name: _coerce_for_type(row.get(col.name), col.inferred_type) for col in result.columns})
        fmt = DataDockFormat(payload.get('source_format', 'sample'))
        result._snapshot = result._from_rows(converted, fmt, result.sample_name, columns=result.columns)
        return result

    def set_column_type(self, column: str, type_name: str) -> DataDockSnapshot:
        allowed = {'string','integer','float','boolean','date','datetime','category','json','unknown'}
        if type_name not in allowed:
            raise ValueError(f'unsupported field type: {type_name!r}')
        target = next((item for item in self.columns if item.name == column), None)
        if target is None:
            raise KeyError(column)
        issues: list[DataDockIssue] = []
        rows = []
        for index, row in enumerate(self.rows, start=1):
            updated = dict(row)
            try:
                updated[column] = _coerce_for_type(row.get(column), type_name)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                issues.append(DataDockIssue('type_conversion', f'Row {index}, {column}: {exc}', DataDockSeverity.ERROR, column=column, row=index))
            rows.append(updated)
        if issues:
            raise ValueError('; '.join(issue.message for issue in issues[:3]))
        columns = tuple(replace(item, inferred_type=type_name) if item.name == column else item for item in self.columns)
        return self._commit(self._from_rows(rows, self.snapshot.source_format, self.snapshot.source_name, columns=columns))

    def set_semantic_role(self, column: str, role: str) -> DataDockSnapshot:
        allowed = {'dimension','measurement','identifier','timestamp','entity','attribute'}
        if role not in allowed:
            raise ValueError(f'unsupported semantic role: {role!r}')
        if column not in self.snapshot.column_names:
            raise KeyError(column)
        columns = tuple(replace(item, role=role, confidence=1.0) if item.name == column else item for item in self.columns)
        return self._commit(self._from_rows(self.rows, self.snapshot.source_format, self.snapshot.source_name, columns=columns))

    def rectangular_paste(self, start_row: int, start_column: str | int, text: str) -> DataDockSnapshot:
        if start_row >= MAX_PROJECT_ROWS:
            raise ValueError(f'Paste exceeds the {MAX_PROJECT_ROWS:,}-row development limit.')
        if len(text.encode('utf-8')) > MAX_PROJECT_BYTES:
            raise ValueError('Paste exceeds the 2 MiB development limit.')
        if start_row < 0:
            raise ValueError('start_row must be >= 0')
        if isinstance(start_column, str):
            try:
                start_col = self.snapshot.column_names.index(start_column)
            except ValueError as exc:
                raise KeyError(start_column) from exc
        else:
            start_col = int(start_column)
        if start_col < 0 or start_col >= len(self.columns):
            raise IndexError(start_col)
        matrix = [row for row in csv.reader(io.StringIO(text), delimiter='\t') if row]
        if not matrix:
            return self.snapshot
        if start_row + len(matrix) > MAX_PROJECT_ROWS:
            raise ValueError('Paste exceeds the development row limit; existing data was not changed.')
        if any(start_col + len(row) > len(self.columns) for row in matrix):
            raise ValueError('Paste is wider than the remaining columns; no cells were discarded or changed.')
        rows = [dict(row) for row in self.rows]
        while len(rows) < start_row + len(matrix):
            rows.append({column.name: None for column in self.columns})
        for r_offset, cells in enumerate(matrix):
            for c_offset, cell in enumerate(cells):
                c_index = start_col + c_offset
                if c_index >= len(self.columns):
                    break
                column = self.columns[c_index]
                rows[start_row + r_offset][column.name] = _coerce_for_type(cell, column.inferred_type)
        return self._commit(self._from_rows(rows, self.snapshot.source_format, self.snapshot.source_name, columns=self.columns))

    def undo(self) -> DataDockSnapshot:
        if not self._undo:
            return self.snapshot
        self._redo.append(self._snapshot)
        self._revision += 1
        self._snapshot = replace(self._undo.pop(), revision=self._revision)
        return self._snapshot

    def redo(self) -> DataDockSnapshot:
        if not self._redo:
            return self.snapshot
        self._undo.append(self._snapshot)
        self._revision += 1
        self._snapshot = replace(self._redo.pop(), revision=self._revision)
        return self._snapshot

    def schema_metadata(self) -> tuple[dict[str, Any], ...]:
        """Return serializable Workbench schema decisions without data values."""
        return tuple({
            'name': column.name,
            'inferred_type': column.inferred_type,
            'role': column.role,
            'nullable': column.nullable,
            'confidence': float(column.confidence),
            'original_name': column.original_name,
        } for column in self.columns)

    def restore_schema_metadata(self, value: Sequence[Mapping[str, Any]] | None) -> DataDockSnapshot:
        """Restore user-confirmed schema semantics without creating edit-history noise."""
        source = value if isinstance(value, (list, tuple)) else ()
        by_name = {
            str(item.get('name')): item
            for item in source if isinstance(item, Mapping) and str(item.get('name') or '').strip()
        }
        allowed_types = {'string','integer','float','boolean','date','datetime','category','json','unknown'}
        allowed_roles = {'dimension','measurement','identifier','timestamp','entity','attribute'}
        columns: list[DataDockColumn] = []
        existing: set[str] = set()
        for column in self.columns:
            existing.add(column.name)
            item = by_name.get(column.name)
            if item is None:
                columns.append(column); continue
            inferred = str(item.get('inferred_type') or column.inferred_type)
            role = str(item.get('role') or column.role)
            try:
                confidence = max(0.0, min(1.0, float(item.get('confidence', column.confidence))))
            except (TypeError, ValueError, OverflowError):
                confidence = column.confidence
            columns.append(replace(
                column,
                inferred_type=inferred if inferred in allowed_types else column.inferred_type,
                role=role if role in allowed_roles else column.role,
                nullable=bool(item.get('nullable')) if 'nullable' in item else column.nullable,
                confidence=confidence,
                original_name=str(item.get('original_name')) if item.get('original_name') else column.original_name,
            ))
        # A persisted schema is authoritative even when the user intentionally has zero rows.
        for item in source:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get('name') or '').strip()
            if not name or name in existing:
                continue
            inferred = str(item.get('inferred_type') or item.get('type') or 'unknown')
            role = str(item.get('role') or 'attribute')
            try:
                confidence = max(0.0, min(1.0, float(item.get('confidence', 1.0))))
            except (TypeError, ValueError, OverflowError):
                confidence = 1.0
            columns.append(DataDockColumn(
                name,
                inferred if inferred in allowed_types else 'unknown',
                role if role in allowed_roles else 'attribute',
                bool(item.get('nullable', True)),
                confidence,
                str(item.get('original_name')) if item.get('original_name') else None,
            ))
            existing.add(name)
        self._snapshot = self._from_rows(
            self.rows, self.snapshot.source_format, self.snapshot.source_name, columns=tuple(columns),
        )
        return self._snapshot

    def to_schema(self, *, key: str = 'workbench'):
        from nicegui_base.data_sources.models import DataSchema, FieldRole, FieldType, SemanticField
        type_map = {
            'string': FieldType.STRING, 'integer': FieldType.INTEGER, 'float': FieldType.FLOAT,
            'boolean': FieldType.BOOLEAN, 'date': FieldType.DATE, 'datetime': FieldType.DATETIME,
            'category': FieldType.CATEGORY, 'json': FieldType.JSON, 'unknown': FieldType.UNKNOWN,
        }
        role_map = {
            'dimension': FieldRole.DIMENSION, 'measurement': FieldRole.MEASUREMENT,
            'identifier': FieldRole.IDENTIFIER, 'timestamp': FieldRole.TIMESTAMP,
            'entity': FieldRole.ENTITY, 'attribute': FieldRole.ATTRIBUTE,
        }
        fields = tuple(SemanticField(column.name, type=type_map[column.inferred_type], role=role_map[column.role], nullable=column.nullable) for column in self.columns)
        return DataSchema(fields, key=key, revision=f'workbench-{self.snapshot.revision}')

    def to_data_source(self, *, key: str = 'workbench'):
        from nicegui_base.data_sources.memory import InMemoryDataSource
        return InMemoryDataSource(key, self.rows, schema=self.to_schema(key=key))

    def serializable_rows(self) -> tuple[dict[str, Any], ...]:
        def encode(value: Any) -> Any:
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            if isinstance(value, tuple):
                return [encode(item) for item in value]
            if isinstance(value, list):
                return [encode(item) for item in value]
            if isinstance(value, dict):
                return {str(key): encode(item) for key, item in value.items()}
            return value
        return tuple({key: encode(value) for key, value in row.items()} for row in self.rows)


DEFAULT_ENGINEERING_SAMPLE = (
    {'id':'M-001','timestamp':'2026-08-31T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'ETCH-01','chamber':'A','lot':'L100','wafer':'W01','x':-1,'y':0,'value':10.2,'sensor':'pressure','sensor_value':1.02,'bin':'PASS','count':95,'yield_pct':99.1,'category':'PASS','defect_class':'none','status':'normal'},
    {'id':'M-002','timestamp':'2026-08-31T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'ETCH-01','chamber':'A','lot':'L100','wafer':'W01','x':0,'y':0,'value':10.5,'sensor':'pressure','sensor_value':1.20,'bin':'B1','count':3,'yield_pct':98.7,'category':'B1','defect_class':'particle','status':'watch'},
    {'id':'M-003','timestamp':'2026-08-31T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'ETCH-01','chamber':'B','lot':'L101','wafer':'W02','x':1,'y':0,'value':9.9,'sensor':'pressure','sensor_value':1.10,'bin':'B2','count':2,'yield_pct':99.0,'category':'B2','defect_class':'scratch','status':'normal'},
)



def default_data_dock() -> DataDockModel:
    return DataDockModel(DEFAULT_ENGINEERING_SAMPLE, sample_name='Engineering sample')


__all__ = [
    'DEFAULT_ENGINEERING_SAMPLE','DataDockColumn','DataDockFormat','DataDockIssue','DataDockModel','DataDockParseResult',
    'DataDockQuality','DataDockSeverity','DataDockSnapshot','default_data_dock','detect_format','parse_data','suggest_semantic_role',
]
