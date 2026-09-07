from __future__ import annotations

import hashlib
import json
import math
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_HANDOFF_MODES = ('schema_only', 'include_development_rows')
from .preview_data import (
    MAX_PROJECT_COLUMNS,
    MAX_PROJECT_ROWS,
    checked_rows,
    resolve_category_field,
    resolve_measurement_field,
)
MAX_GENERATED_DEVELOPMENT_ROWS = MAX_PROJECT_ROWS
_ALLOWED_TYPES = {'string','integer','float','boolean','date','datetime','category','json','unknown'}
_ALLOWED_ROLES = {'dimension','measurement','identifier','timestamp','entity','attribute'}


@dataclass(frozen=True, slots=True)
class HandoffField:
    name: str
    inferred_type: str
    role: str
    nullable: bool
    confidence: float = 1.0
    original_name: str | None = None
    generated: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('data handoff field name must not be empty')
        if self.inferred_type not in _ALLOWED_TYPES:
            raise ValueError(f'unsupported data handoff type: {self.inferred_type!r}')
        if self.role not in _ALLOWED_ROLES:
            raise ValueError(f'unsupported data handoff role: {self.role!r}')

    def to_dict(self) -> dict[str, object]:
        return {
            'name': self.name,
            'type': self.inferred_type,
            'role': self.role,
            'nullable': self.nullable,
            'confidence': round(float(self.confidence), 4),
            'original_name': self.original_name,
            'generated': self.generated,
        }


@dataclass(frozen=True, slots=True)
class DataHandoffPlan:
    mode: str
    source_name: str
    fields: tuple[HandoffField, ...]
    row_key: str
    measurement_field: str | None
    category_field: str | None
    fixture_rows: tuple[dict[str, Any], ...]
    original_row_count: int

    @property
    def contains_original_values(self) -> bool:
        return self.mode == 'include_development_rows'

    @property
    def contract_signature(self) -> str:
        payload = {
            'mode': self.mode,
            'source_name': self.source_name,
            'fields': [field.to_dict() for field in self.fields],
            'row_key': self.row_key,
            'measurement_field': self.measurement_field,
            'category_field': self.category_field,
            'fixture_rows': len(self.fixture_rows),
            'original_row_count': self.original_row_count,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()

    def to_manifest(self) -> dict[str, object]:
        return {
            'schema_version': 1,
            'mode': self.mode,
            'source_name': self.source_name,
            'fields': [field.to_dict() for field in self.fields],
            'row_key': self.row_key,
            'measurement_field': self.measurement_field,
            'category_field': self.category_field,
            'fixture_rows': len(self.fixture_rows),
            'original_row_count': self.original_row_count,
            'contains_original_values': self.contains_original_values,
            'contract_signature': self.contract_signature,
            'provider_boundary': 'services.app_data:build_source',
        }


def _infer_type(values: Sequence[Any]) -> str:
    present = [value for value in values if value is not None]
    if not present:
        return 'unknown'
    if all(isinstance(value, bool) for value in present):
        return 'boolean'
    if all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        return 'integer'
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present):
        return 'float'
    return 'string'


def _infer_role(name: str, inferred_type: str) -> str:
    folded = name.casefold().replace('-', '_').replace(' ', '_')
    if folded in {'id','record_id','measurement_id','uuid','key'} or folded.endswith('_id'):
        return 'identifier'
    if 'time' in folded or 'date' in folded:
        return 'timestamp'
    if folded in {'tool','chamber','wafer','lot','batch','product','recipe','operation','area','fab','sensor'}:
        return 'entity'
    if inferred_type in {'integer','float'}:
        return 'measurement'
    if folded in {'status','state','category','class','type','bin','group'}:
        return 'dimension'
    return 'attribute'


def normalize_schema(project: Mapping[str, Any]) -> tuple[HandoffField, ...]:
    rows = tuple(dict(row) for row in project.get('data_rows', ()) if isinstance(row, Mapping))
    schema = project.get('data_schema') if isinstance(project.get('data_schema'), (list, tuple)) else ()
    row_names = tuple(dict.fromkeys(str(key) for row in rows for key in row))
    by_name: dict[str, Mapping[str, Any]] = {
        str(item.get('name')): item for item in schema if isinstance(item, Mapping) and str(item.get('name') or '').strip()
    }
    names = tuple(dict.fromkeys((*row_names, *by_name.keys())))
    fields: list[HandoffField] = []
    for name in names:
        item = by_name.get(name, {})
        values = tuple(row.get(name) for row in rows)
        inferred = str(item.get('inferred_type') or item.get('type') or _infer_type(values))
        if inferred not in _ALLOWED_TYPES:
            inferred = _infer_type(values)
        role = str(item.get('role') or _infer_role(name, inferred))
        if role not in _ALLOWED_ROLES:
            role = _infer_role(name, inferred)
        nullable = bool(item.get('nullable')) if 'nullable' in item else any(value is None for value in values)
        try:
            confidence = max(0.0, min(1.0, float(item.get('confidence', 1.0))))
        except (TypeError, ValueError, OverflowError):
            confidence = 1.0
        fields.append(HandoffField(name, inferred, role, nullable, confidence, str(item.get('original_name')) if item.get('original_name') else None))
    if not fields:
        fields.append(HandoffField('__row_id', 'string', 'identifier', False, 1.0, generated=True))
    return tuple(fields)


def _unique_identifier(fields: Sequence[HandoffField], rows: Sequence[Mapping[str, Any]]) -> str | None:
    identifiers = [field for field in fields if field.role == 'identifier']
    if not rows and identifiers:
        # Preserve an explicitly confirmed identifier in schema-only/zero-row projects.
        return identifiers[0].name
    for field in identifiers:
        values = [row.get(field.name) for row in rows]
        if values and all(value is not None and value != '' for value in values) and len(values) == len({repr(value) for value in values}):
            return field.name
    return None


def _synthetic_value(field: HandoffField, index: int) -> Any:
    number = index + 1
    if field.role == 'identifier':
        if field.inferred_type == 'integer':
            return number
        if field.inferred_type == 'float':
            return float(number)
        return f'R-{number:03d}'
    if field.role == 'timestamp' or field.inferred_type == 'datetime':
        return f'2026-01-{number:02d}T08:{index:02d}:00'
    if field.inferred_type == 'date':
        return f'2026-01-{number:02d}'
    if field.inferred_type == 'boolean':
        return bool(index % 2)
    if field.inferred_type == 'integer':
        return 100 + index
    if field.inferred_type == 'float':
        return round(10.0 + index * 0.5, 3)
    if field.inferred_type == 'json':
        return {'sample': number}
    if field.role in {'entity','dimension'} or field.inferred_type == 'category':
        return f'{field.name.upper()}-{number:02d}'
    return f'Sample {number}'


def _with_generated_row_key(fields: tuple[HandoffField, ...], rows: Sequence[Mapping[str, Any]]) -> tuple[tuple[HandoffField, ...], str]:
    identifier = _unique_identifier(fields, rows)
    if identifier:
        return fields, identifier
    if len(fields) >= MAX_PROJECT_COLUMNS:
        raise ValueError('A 128-column dataset needs a confirmed unique identifier before export; no column was discarded.')
    key = '__row_id'
    suffix = 2
    while any(field.name == key for field in fields):
        key = f'__row_id_{suffix}'
        suffix += 1
    return (HandoffField(key, 'string', 'identifier', False, 1.0, generated=True), *fields), key


def _literal_safe(value: Any, *, path: str = 'value') -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f'{path} contains a non-finite number; clean the development data before inclusion')
        return value
    if isinstance(value, Mapping):
        return {str(key): _literal_safe(item, path=f'{path}.{key}') for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_literal_safe(item, path=f'{path}[{index}]') for index, item in enumerate(value)]
    isoformat = getattr(value, 'isoformat', None)
    if callable(isoformat):
        return str(isoformat())
    raise ValueError(f'{path} contains unsupported value type {type(value).__name__}; convert it before including development rows')


def _ensure_row_key(rows: Sequence[Mapping[str, Any]], row_key: str) -> tuple[dict[str, Any], ...]:
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        if item.get(row_key) is None or item.get(row_key) == '':
            item[row_key] = f'R-{index:03d}'
        output.append(item)
    return tuple(output)


def _explicit_mapping(project: Mapping[str, Any], kind: str) -> str | None:
    """Read one explicit field mapping from the project/configuration boundary."""
    aliases = {
        'measurement': ('measurement_field', 'measurement'),
        'category': ('category_field', 'label_field', 'category'),
    }[kind]
    values: list[str] = []
    for key in aliases:
        raw = project.get(key)
        if raw is not None and str(raw).strip():
            values.append(str(raw).strip())
    configurations = project.get('capability_configurations')
    if isinstance(configurations, Mapping):
        for configuration in configurations.values():
            if not isinstance(configuration, Mapping):
                continue
            options = configuration.get('options')
            if not isinstance(options, Mapping):
                continue
            for key in aliases:
                raw = options.get(key)
                if raw is not None and str(raw).strip():
                    values.append(str(raw).strip())
    unique = tuple(dict.fromkeys(values))
    if len(unique) > 1:
        label = 'measurement' if kind == 'measurement' else 'category'
        raise ValueError(f'Multiple explicit {label} mappings were provided: {", ".join(unique)}. Choose one field.')
    return unique[0] if unique else None


def build_data_handoff_plan(project: Mapping[str, Any], *, require_measurement: bool = True) -> DataHandoffPlan:
    mode = str(project.get('data_handoff_mode') or 'schema_only')
    if mode not in DATA_HANDOFF_MODES:
        raise ValueError(f'unsupported data handoff mode: {mode!r}')
    source_name = str(project.get('data_source_name') or 'Workbench development data')[:160]
    raw_rows = project.get('data_rows') if isinstance(project.get('data_rows'), (list, tuple)) else ()
    selected_rows = tuple(checked_rows(raw_rows))
    if mode == 'include_development_rows':
        original_rows = tuple(
            {str(key): _literal_safe(item, path=f'row[{index}].{key}') for key, item in row.items()}
            for index, row in enumerate(selected_rows)
        )
    else:
        # Schema-only never serializes these values; retain them only for row-key/schema reasoning.
        original_rows = selected_rows
    fields = normalize_schema(project)
    fields, row_key = _with_generated_row_key(fields, original_rows)
    if mode == 'include_development_rows':
        fixture = _ensure_row_key(original_rows, row_key)
    else:
        fixture = tuple({field.name: _synthetic_value(field, index) for field in fields} for index in range(5))
        fixture = _ensure_row_key(fixture, row_key)
    explicit_measurement = _explicit_mapping(project, 'measurement')
    try:
        measurement = resolve_measurement_field(
            original_rows,
            schema=fields,
            field=explicit_measurement,
            required=require_measurement,
        )
    except ValueError as exc:
        # Ambiguity remains visible in the generated chart and Builder review, but a
        # table-only project may still export a truthful schema-only contract. An
        # explicit invalid mapping is never swallowed.
        if not require_measurement and str(exc).startswith('ambiguous measurement mapping'):
            measurement = None
        else:
            raise
    explicit_category = _explicit_mapping(project, 'category')
    category = resolve_category_field(
        original_rows,
        schema=fields,
        field=explicit_category,
        required=False,
    ) or row_key
    return DataHandoffPlan(mode, source_name, fields, row_key, measurement, category, fixture, len(raw_rows))


def validate_data_contract_manifest(value: Any) -> tuple[str, ...]:
    findings: list[str] = []
    if not isinstance(value, Mapping):
        return ('data_contract:not_object',)
    if value.get('schema_version') != 1:
        findings.append('data_contract:schema_version')
    mode = str(value.get('mode') or '')
    if mode not in DATA_HANDOFF_MODES:
        findings.append('data_contract:mode')
    fields = value.get('fields')
    if not isinstance(fields, list) or not fields:
        findings.append('data_contract:fields')
        fields = []
    names: list[str] = []
    for item in fields:
        if not isinstance(item, Mapping):
            findings.append('data_contract:field_not_object'); continue
        name = str(item.get('name') or '')
        if not name:
            findings.append('data_contract:field_name')
        if str(item.get('type') or '') not in _ALLOWED_TYPES:
            findings.append(f'data_contract:field_type:{name}')
        if str(item.get('role') or '') not in _ALLOWED_ROLES:
            findings.append(f'data_contract:field_role:{name}')
        names.append(name)
    if len(names) != len(set(names)):
        findings.append('data_contract:duplicate_fields')
    if str(value.get('row_key') or '') not in names:
        findings.append('data_contract:row_key')
    try:
        fixture_rows = int(value.get('fixture_rows') or 0)
    except (TypeError, ValueError):
        fixture_rows = 0
    minimum_rows = 0 if mode == 'include_development_rows' else 1
    if not minimum_rows <= fixture_rows <= MAX_GENERATED_DEVELOPMENT_ROWS:
        findings.append('data_contract:fixture_rows')
    contains = bool(value.get('contains_original_values'))
    if contains != (mode == 'include_development_rows'):
        findings.append('data_contract:original_value_policy')
    signature = str(value.get('contract_signature') or '')
    if not signature:
        findings.append('data_contract:signature')
    else:
        try:
            original_row_count = max(0, int(value.get('original_row_count') or 0))
        except (TypeError, ValueError, OverflowError):
            original_row_count = 0
            findings.append('data_contract:original_row_count')
        signature_payload = {
            'mode': mode,
            'source_name': str(value.get('source_name') or ''),
            'fields': fields,
            'row_key': str(value.get('row_key') or ''),
            'measurement_field': value.get('measurement_field'),
            'category_field': value.get('category_field'),
            'fixture_rows': fixture_rows,
            'original_row_count': original_row_count,
        }
        expected_signature = hashlib.sha256(
            json.dumps(signature_payload, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')
        ).hexdigest()
        if signature != expected_signature:
            findings.append('data_contract:signature_mismatch')
    if value.get('provider_boundary') != 'services.app_data:build_source':
        findings.append('data_contract:provider_boundary')
    # The manifest must describe data shape/policy only; raw rows are forbidden here.
    forbidden = {'rows','data_rows','fixture','values','records'}
    if forbidden & {str(key) for key in value}:
        findings.append('data_contract:raw_values_in_manifest')
    return tuple(dict.fromkeys(findings))


def _schema_source(plan: DataHandoffPlan) -> str:
    lines = [
        'from __future__ import annotations',
        'from nicegui_base import DataSchema, FieldRole, FieldType, SemanticField',
        '',
        'DATA_SCHEMA = DataSchema((',
    ]
    for field in plan.fields:
        lines.append(
            f"    SemanticField({field.name!r}, type=FieldType.{field.inferred_type.upper()}, role=FieldRole.{field.role.upper()}, nullable={field.nullable!r}),"
        )
    lines.extend([
        f"), key='application', revision='workbench-{plan.contract_signature[:12]}')",
        f'ROW_KEY = {plan.row_key!r}',
        f'MEASUREMENT_FIELD = {plan.measurement_field!r}',
        f'CATEGORY_FIELD = {plan.category_field!r}',
        '',
    ])
    return '\n'.join(lines)


def _fixture_source(plan: DataHandoffPlan) -> str:
    body = pprint.pformat(tuple(plan.fixture_rows), width=110, sort_dicts=False)
    return (
        'from __future__ import annotations\n\n'
        '# Development fixture generated by NiceGUI Base Workbench.\n'
        f'# Handoff mode: {plan.mode}. '
        + ('Values were explicitly included by the Workbench user.\n' if plan.contains_original_values else 'Values are deterministic synthetic examples; original Data Dock values are not present.\n')
        + f'DEVELOPMENT_ROWS = {body}\n'
    )


def _app_data_source(plan: DataHandoffPlan) -> str:
    return r'''from __future__ import annotations
import math
from typing import Any

from nicegui_base import (
    CSVDataSource, DataSource, InMemoryDataSource, Query, ServerDataTableSpec,
    SourceCapabilities, SourceHealth, SourceHealthStatus, SQLiteDataSource,
)
from nicegui_base.analysis import columns_from_schema
from nicegui_base.diagnostics import HealthCheck, HealthResult, HealthState
from nicegui_base.security import redact_text
from .data_contract import CATEGORY_FIELD, DATA_SCHEMA, MEASUREMENT_FIELD, ROW_KEY
from .development_fixture import DEVELOPMENT_ROWS
from .provider_config import ProviderConfig, ProviderConfigurationError


class _UnavailableDataSource(DataSource):
    """Safe failure adapter which preserves the canonical DataSource boundary."""
    def __init__(self, reason: str, *, requested_provider: str = 'unknown', timeout_seconds: float = 30.0):
        super().__init__('application', timeout_seconds=timeout_seconds)
        self.reason = redact_text(str(reason))
        self.requested_provider = str(requested_provider or 'unknown')

    @property
    def provider(self) -> str:
        return 'unavailable'

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities()

    async def schema(self):
        self._ensure_open()
        return DATA_SCHEMA

    def _raise(self):
        raise ProviderConfigurationError(self.reason)

    async def query(self, query=Query()):
        self._raise()

    async def aggregate(self, query):
        self._raise()

    async def distinct(self, field: str, query=Query()):
        self._raise()

    async def health(self) -> SourceHealth:
        return SourceHealth.current(
            SourceHealthStatus.UNAVAILABLE,
            message=self.reason,
            metadata={'requested_provider': self.requested_provider},
        )


def _load_provider_config() -> tuple[ProviderConfig, str | None]:
    try:
        return ProviderConfig.from_env(), None
    except ProviderConfigurationError as exc:
        # Keep startup alive so canonical readiness can explain the failure safely.
        return ProviderConfig(mode='production', provider='invalid'), redact_text(str(exc))


PROVIDER_CONFIG, _PROVIDER_CONFIG_ERROR = _load_provider_config()


def build_source(config: ProviderConfig | None = None) -> DataSource:
    """Single generated provider boundary. Page modules never choose providers.

    Development mode is always the generated in-memory fixture. Production mode
    supports only provider adapters the base package can instantiate truthfully from
    non-secret environment configuration: CSV and SQLite. Unsupported/missing
    production configuration returns an unavailable DataSource so the application
    can start and report not-ready through the canonical runtime health registry.
    """
    cfg = PROVIDER_CONFIG if config is None else config
    if config is None and _PROVIDER_CONFIG_ERROR:
        return _UnavailableDataSource(_PROVIDER_CONFIG_ERROR, requested_provider=cfg.provider, timeout_seconds=cfg.timeout_seconds)
    if cfg.mode == 'development':
        return InMemoryDataSource('application', DEVELOPMENT_ROWS, schema=DATA_SCHEMA, timeout_seconds=cfg.timeout_seconds)
    issues = cfg.validation_issues()
    if issues:
        return _UnavailableDataSource('; '.join(issues), requested_provider=cfg.provider, timeout_seconds=cfg.timeout_seconds)
    try:
        if cfg.provider == 'csv':
            return CSVDataSource('application', cfg.csv_path or '', schema=DATA_SCHEMA, timeout_seconds=cfg.timeout_seconds)
        if cfg.provider == 'sqlite':
            return SQLiteDataSource('application', cfg.sqlite_path or '', cfg.sqlite_table or '', schema=DATA_SCHEMA, timeout_seconds=cfg.timeout_seconds)
    except Exception as exc:
        return _UnavailableDataSource(
            f'{type(exc).__name__}: {redact_text(str(exc))}',
            requested_provider=cfg.provider,
            timeout_seconds=cfg.timeout_seconds,
        )
    return _UnavailableDataSource('unsupported production provider', requested_provider=cfg.provider, timeout_seconds=cfg.timeout_seconds)


SOURCE = build_source()

DATA_TABLE_SPEC = ServerDataTableSpec(
    tuple(columns_from_schema(DATA_SCHEMA)),
    row_key=ROW_KEY,
    cache_pages=2,
    cache_ttl_seconds=PROVIDER_CONFIG.cache_ttl_seconds,
    request_timeout_seconds=PROVIDER_CONFIG.timeout_seconds,
    retry_attempts=PROVIDER_CONFIG.retry_attempts,
    retry_base_delay_seconds=PROVIDER_CONFIG.retry_base_delay_seconds,
    stale_after_seconds=PROVIDER_CONFIG.stale_after_seconds,
    empty_message='No records from the active data provider',
    error_message='Unable to load records from the active data provider',
)


async def provider_diagnostics(source: DataSource | None = None, config: ProviderConfig | None = None) -> dict[str, object]:
    cfg = PROVIDER_CONFIG if config is None else config
    active = SOURCE if source is None else source
    try:
        health = await active.health()
        status = health.status.value
        reason = redact_text(str(health.message or ''))
        ready = health.status is SourceHealthStatus.HEALTHY
        freshness_at = health.freshness_at
    except Exception as exc:
        status = SourceHealthStatus.UNAVAILABLE.value
        reason = redact_text(f'{type(exc).__name__}: {exc}')
        ready = False
        freshness_at = None
    result = cfg.public_diagnostics()
    result.update({
        'provider': active.provider,
        'ready': ready,
        'status': status,
        'reason': reason,
        'freshness_at': freshness_at,
    })
    return result


def _health_state(status: SourceHealthStatus) -> HealthState:
    if status is SourceHealthStatus.HEALTHY:
        return HealthState.HEALTHY
    if status in {SourceHealthStatus.DEGRADED, SourceHealthStatus.UNKNOWN}:
        return HealthState.DEGRADED
    return HealthState.UNHEALTHY


async def source_health_check(source: DataSource | None = None, config: ProviderConfig | None = None) -> HealthResult:
    cfg = PROVIDER_CONFIG if config is None else config
    active = SOURCE if source is None else source
    try:
        health = await active.health()
        detail = redact_text(str(health.message or 'data source health reported'))
        state = _health_state(health.status)
        metadata = {
            'mode': cfg.mode,
            'provider': active.provider,
            'requested_provider': cfg.provider if cfg.mode == 'production' else 'memory',
            'freshness_at': health.freshness_at,
            'mutation_policy': 'none',
        }
        return HealthResult('data-source', state, detail, metadata=metadata)
    except Exception as exc:
        return HealthResult(
            'data-source', HealthState.UNHEALTHY, redact_text(f'{type(exc).__name__}: {exc}'),
            metadata={'mode': cfg.mode, 'provider': active.provider, 'mutation_policy': 'none'},
        )


def register_source_health(runtime: Any, *, source: DataSource | None = None, config: ProviderConfig | None = None) -> None:
    if any(check.name == 'data-source' for check in runtime.health.checks):
        return
    cfg = PROVIDER_CONFIG if config is None else config
    active = SOURCE if source is None else source
    runtime.health.register(
        HealthCheck(
            'data-source',
            lambda: source_health_check(active, cfg),
            critical=True,
            timeout_seconds=min(10.0, max(1.0, cfg.timeout_seconds)),
        )
    )


def series_labels() -> tuple[str, ...]:
    # Generated charts retain deterministic development preview values. Provider-backed
    # data surfaces use SOURCE directly through DataSourceTable; do not query async
    # production providers during module import/page construction.
    field = CATEGORY_FIELD or ROW_KEY
    return tuple(
        str(row.get(field) if row.get(field) not in (None, '') else row.get(ROW_KEY, index + 1))
        for index, row in enumerate(DEVELOPMENT_ROWS)
    )


def series_values() -> tuple[float | None, ...]:
    if not MEASUREMENT_FIELD:
        raise ValueError('No confirmed measurement field is available for this generated chart.')
    values: list[float | None] = []
    for index, row in enumerate(DEVELOPMENT_ROWS):
        raw = row.get(MEASUREMENT_FIELD)
        if raw is None or raw == '':
            values.append(None)
            continue
        if isinstance(raw, bool):
            raise ValueError(f'Measurement field {MEASUREMENT_FIELD!r} contains boolean data at row {index + 1}.')
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Measurement field {MEASUREMENT_FIELD!r} contains non-numeric data at row {index + 1}.') from exc
        if not math.isfinite(value):
            raise ValueError(f'Measurement field {MEASUREMENT_FIELD!r} contains a non-finite number at row {index + 1}.')
        values.append(value)
    if not any(value is not None for value in values):
        raise ValueError(f'Measurement field {MEASUREMENT_FIELD!r} has no populated numeric values.')
    return tuple(values)


__all__ = [
    'CATEGORY_FIELD','DATA_SCHEMA','DATA_TABLE_SPEC','DEVELOPMENT_ROWS','MEASUREMENT_FIELD','PROVIDER_CONFIG',
    'ROW_KEY','SOURCE','build_source','provider_diagnostics','register_source_health','series_labels','series_values','source_health_check',
]
'''


def materialize_data_handoff(root: Path, project: Mapping[str, Any], *, require_measurement: bool = False) -> tuple[dict[str, object], tuple[Path, ...], dict[str, str]]:
    plan = build_data_handoff_plan(project, require_measurement=require_measurement)
    sources = {
        'services/data_contract.py': _schema_source(plan),
        'services/development_fixture.py': _fixture_source(plan),
        'services/app_data.py': _app_data_source(plan),
    }
    written: list[Path] = []
    for rel, source in sources.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        written.append(path)
    manifest = plan.to_manifest()
    meta = root / '.nicegui_base' / 'data_contract.json'
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    written.append(meta)

    test_path = root / 'tests' / 'test_project_contract.py'
    existing_test = test_path.read_text(encoding='utf-8') if test_path.is_file() else ''
    contract_test = (
        '\nfrom nicegui_base import DataSource\n'
        'from services.app_data import DATA_SCHEMA, ROW_KEY, SOURCE, build_source\n\n'
        'def test_generated_data_contract() -> None:\n'
        '    assert DATA_SCHEMA.get(ROW_KEY) is not None\n'
        '    assert isinstance(SOURCE, DataSource)\n'
        '    assert isinstance(build_source(), DataSource)\n'
    )
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(existing_test.rstrip() + '\n' + contract_test, encoding='utf-8')
    written.append(test_path)
    sources['tests/test_project_contract.py'] = test_path.read_text(encoding='utf-8')

    readme_path = root / 'README.md'
    if readme_path.is_file():
        readme = readme_path.read_text(encoding='utf-8').rstrip()
        readme += (
            '\n\n## Generated data contract\n\n'
            f'- Handoff mode: `{plan.mode}`.\n'
            f'- Schema: `{len(plan.fields)}` fields; row key `{plan.row_key}`.\n'
            '- Machine-readable contract: `.nicegui_base/data_contract.json`.\n'
            '- Canonical schema code: `services/data_contract.py`.\n'
            '- Development fixture: `services/development_fixture.py`.\n'
            '- Production provider replacement boundary: `services/app_data.py::build_source`.\n\n'
            'Keep page code provider-neutral. Replace `build_source()` with the approved NiceGUI Base `DataSource` provider rather than wiring SQL/CSV/company adapters directly into pages.\n'
        )
        readme_path.write_text(readme, encoding='utf-8')
        written.append(readme_path)
    return manifest, tuple(dict.fromkeys(written)), dict(sources)


__all__ = [
    'DATA_HANDOFF_MODES','MAX_GENERATED_DEVELOPMENT_ROWS','DataHandoffPlan','HandoffField',
    'build_data_handoff_plan','materialize_data_handoff','normalize_schema','validate_data_contract_manifest',
]
