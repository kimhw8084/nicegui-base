from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

PROVIDER_CONTRACT_SCHEMA_VERSION = 1
GENERATED_PROVIDER_KEYS = ('csv', 'sqlite')
DEFAULT_PROVIDER_SELECTION = 'none'
_ALLOWED_PROVIDER_SELECTIONS = frozenset((DEFAULT_PROVIDER_SELECTION, *GENERATED_PROVIDER_KEYS))


def _signature_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'schema_version': int(value.get('schema_version') or 0),
        'selected_provider': str(value.get('selected_provider') or ''),
        'generated_provider_keys': list(value.get('generated_provider_keys') or ()),
        'framework_provider_authority': str(value.get('framework_provider_authority') or ''),
        'provider_boundary': str(value.get('provider_boundary') or ''),
        'config_boundary': str(value.get('config_boundary') or ''),
        'health_boundary': str(value.get('health_boundary') or ''),
        'runtime_mode_env': str(value.get('runtime_mode_env') or ''),
        'provider_env': str(value.get('provider_env') or ''),
        'configuration': value.get('configuration') if isinstance(value.get('configuration'), list) else [],
        'resilience': value.get('resilience') if isinstance(value.get('resilience'), Mapping) else {},
        'provider_mutation_policy': str(value.get('provider_mutation_policy') or ''),
    }


def provider_contract_for_project(project: Mapping[str, Any]) -> dict[str, object]:
    selected = str(project.get('production_provider') or DEFAULT_PROVIDER_SELECTION)
    if selected not in _ALLOWED_PROVIDER_SELECTIONS:
        selected = DEFAULT_PROVIDER_SELECTION
    contract: dict[str, object] = {
        'schema_version': PROVIDER_CONTRACT_SCHEMA_VERSION,
        'selected_provider': selected,
        'generated_provider_keys': list(GENERATED_PROVIDER_KEYS),
        'framework_provider_authority': 'nicegui_base.data_sources.DATA_SOURCE_PROVIDERS',
        'provider_boundary': 'services.app_data:build_source',
        'config_boundary': 'services.provider_config:ProviderConfig.from_env',
        'health_boundary': 'services.app_data:register_source_health',
        'runtime_mode_env': 'NICEGUI_BASE_DATA_MODE',
        'provider_env': 'NICEGUI_BASE_DATA_PROVIDER',
        'configuration': [
            {'name': 'NICEGUI_BASE_DATA_MODE', 'secret': False, 'required_in_production': True, 'purpose': 'development or production source selection'},
            {'name': 'NICEGUI_BASE_DATA_PROVIDER', 'secret': False, 'required_in_production': selected == DEFAULT_PROVIDER_SELECTION, 'purpose': 'csv or sqlite provider selection'},
            {'name': 'NICEGUI_BASE_DATA_CSV_PATH', 'secret': False, 'required_for': 'csv', 'purpose': 'CSV path'},
            {'name': 'NICEGUI_BASE_DATA_SQLITE_PATH', 'secret': False, 'required_for': 'sqlite', 'purpose': 'SQLite database path'},
            {'name': 'NICEGUI_BASE_DATA_SQLITE_TABLE', 'secret': False, 'required_for': 'sqlite', 'purpose': 'SQLite table name'},
            {'name': 'NICEGUI_BASE_DATA_TIMEOUT_SECONDS', 'secret': False, 'purpose': 'bounded provider request timeout'},
            {'name': 'NICEGUI_BASE_DATA_CACHE_TTL_SECONDS', 'secret': False, 'purpose': 'bounded read cache TTL'},
            {'name': 'NICEGUI_BASE_DATA_RETRY_ATTEMPTS', 'secret': False, 'purpose': 'bounded idempotent read retries'},
            {'name': 'NICEGUI_BASE_DATA_RETRY_BASE_DELAY_SECONDS', 'secret': False, 'purpose': 'bounded retry backoff base'},
            {'name': 'NICEGUI_BASE_DATA_STALE_AFTER_SECONDS', 'secret': False, 'purpose': 'stale-data threshold'},
        ],
        'resilience': {
            'timeout_seconds': {'default': 30.0, 'min': 1.0, 'max': 120.0},
            'cache_ttl_seconds': {'default': 15.0, 'min': 1.0, 'max': 300.0},
            'retry_attempts': {'default': 2, 'min': 1, 'max': 5},
            'retry_base_delay_seconds': {'default': 0.15, 'min': 0.0, 'max': 5.0},
            'stale_after_seconds': {'default': 120.0, 'min': 1.0, 'max': 3600.0},
            'retry_scope': 'idempotent reads only',
            'infinite_retry': False,
        },
        'provider_mutation_policy': 'none',
    }
    contract['contract_signature'] = hashlib.sha256(
        json.dumps(_signature_payload(contract), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    return contract


def validate_provider_contract(value: Any) -> tuple[str, ...]:
    findings: list[str] = []
    if not isinstance(value, Mapping):
        return ('provider_contract:not_object',)
    if value.get('schema_version') != PROVIDER_CONTRACT_SCHEMA_VERSION:
        findings.append('provider_contract:schema_version')
    selected = str(value.get('selected_provider') or '')
    if selected not in _ALLOWED_PROVIDER_SELECTIONS:
        findings.append('provider_contract:selected_provider')
    if tuple(value.get('generated_provider_keys') or ()) != GENERATED_PROVIDER_KEYS:
        findings.append('provider_contract:generated_provider_keys')
    expected_boundaries = {
        'framework_provider_authority': 'nicegui_base.data_sources.DATA_SOURCE_PROVIDERS',
        'provider_boundary': 'services.app_data:build_source',
        'config_boundary': 'services.provider_config:ProviderConfig.from_env',
        'health_boundary': 'services.app_data:register_source_health',
        'runtime_mode_env': 'NICEGUI_BASE_DATA_MODE',
        'provider_env': 'NICEGUI_BASE_DATA_PROVIDER',
        'provider_mutation_policy': 'none',
    }
    for key, expected in expected_boundaries.items():
        if value.get(key) != expected:
            findings.append(f'provider_contract:{key}')
    configuration = value.get('configuration')
    if not isinstance(configuration, list) or not configuration:
        findings.append('provider_contract:configuration')
    else:
        names: list[str] = []
        for item in configuration:
            if not isinstance(item, Mapping):
                findings.append('provider_contract:configuration_item')
                continue
            name = str(item.get('name') or '')
            names.append(name)
            if not name.startswith('NICEGUI_BASE_DATA_'):
                findings.append(f'provider_contract:configuration_name:{name}')
            if item.get('secret') is not False:
                findings.append(f'provider_contract:secret_configuration:{name}')
            if 'value' in item or 'default_value' in item:
                findings.append(f'provider_contract:embedded_value:{name}')
        if len(names) != len(set(names)):
            findings.append('provider_contract:duplicate_configuration')
    resilience = value.get('resilience')
    if not isinstance(resilience, Mapping):
        findings.append('provider_contract:resilience')
    else:
        if resilience.get('infinite_retry') is not False:
            findings.append('provider_contract:infinite_retry')
        if resilience.get('retry_scope') != 'idempotent reads only':
            findings.append('provider_contract:retry_scope')
    signature = str(value.get('contract_signature') or '')
    expected_signature = hashlib.sha256(
        json.dumps(_signature_payload(value), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    if signature != expected_signature:
        findings.append('provider_contract:signature_mismatch')
    return tuple(dict.fromkeys(findings))


def _provider_config_source(selected_provider: str) -> str:
    return f'''from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Mapping

DEFAULT_PRODUCTION_PROVIDER = {selected_provider!r}
SUPPORTED_PRODUCTION_PROVIDERS = ('csv', 'sqlite')


class ProviderConfigurationError(RuntimeError):
    pass


def _bounded_float(env: Mapping[str, str], name: str, default: float, minimum: float, maximum: float) -> float:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ProviderConfigurationError(f'{{name}} must be a number') from exc
    if not minimum <= value <= maximum:
        raise ProviderConfigurationError(f'{{name}} must be between {{minimum:g}} and {{maximum:g}}')
    return value


def _bounded_int(env: Mapping[str, str], name: str, default: int, minimum: int, maximum: int) -> int:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ProviderConfigurationError(f'{{name}} must be an integer') from exc
    if not minimum <= value <= maximum:
        raise ProviderConfigurationError(f'{{name}} must be between {{minimum}} and {{maximum}}')
    return value


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    mode: str = 'development'
    provider: str = DEFAULT_PRODUCTION_PROVIDER
    csv_path: str | None = None
    sqlite_path: str | None = None
    sqlite_table: str | None = None
    timeout_seconds: float = 30.0
    cache_ttl_seconds: float = 15.0
    retry_attempts: int = 2
    retry_base_delay_seconds: float = 0.15
    stale_after_seconds: float = 120.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> 'ProviderConfig':
        env = os.environ if environ is None else environ
        mode = str(env.get('NICEGUI_BASE_DATA_MODE', 'development') or 'development').strip().lower()
        if mode not in {{'development', 'production'}}:
            raise ProviderConfigurationError('NICEGUI_BASE_DATA_MODE must be development or production')
        provider = str(env.get('NICEGUI_BASE_DATA_PROVIDER', DEFAULT_PRODUCTION_PROVIDER) or DEFAULT_PRODUCTION_PROVIDER).strip().lower()
        return cls(
            mode=mode,
            provider=provider,
            csv_path=(str(env.get('NICEGUI_BASE_DATA_CSV_PATH') or '').strip() or None),
            sqlite_path=(str(env.get('NICEGUI_BASE_DATA_SQLITE_PATH') or '').strip() or None),
            sqlite_table=(str(env.get('NICEGUI_BASE_DATA_SQLITE_TABLE') or '').strip() or None),
            timeout_seconds=_bounded_float(env, 'NICEGUI_BASE_DATA_TIMEOUT_SECONDS', 30.0, 1.0, 120.0),
            cache_ttl_seconds=_bounded_float(env, 'NICEGUI_BASE_DATA_CACHE_TTL_SECONDS', 15.0, 1.0, 300.0),
            retry_attempts=_bounded_int(env, 'NICEGUI_BASE_DATA_RETRY_ATTEMPTS', 2, 1, 5),
            retry_base_delay_seconds=_bounded_float(env, 'NICEGUI_BASE_DATA_RETRY_BASE_DELAY_SECONDS', 0.15, 0.0, 5.0),
            stale_after_seconds=_bounded_float(env, 'NICEGUI_BASE_DATA_STALE_AFTER_SECONDS', 120.0, 1.0, 3600.0),
        )

    @property
    def active_provider(self) -> str:
        return 'memory' if self.mode == 'development' else self.provider

    def validation_issues(self) -> tuple[str, ...]:
        if self.mode == 'development':
            return ()
        issues: list[str] = []
        if self.provider not in SUPPORTED_PRODUCTION_PROVIDERS:
            issues.append('NICEGUI_BASE_DATA_PROVIDER must be csv or sqlite')
        elif self.provider == 'csv' and not self.csv_path:
            issues.append('missing:NICEGUI_BASE_DATA_CSV_PATH')
        elif self.provider == 'sqlite':
            if not self.sqlite_path:
                issues.append('missing:NICEGUI_BASE_DATA_SQLITE_PATH')
            if not self.sqlite_table:
                issues.append('missing:NICEGUI_BASE_DATA_SQLITE_TABLE')
        return tuple(issues)

    def public_diagnostics(self) -> dict[str, object]:
        return {{
            'mode': self.mode,
            'provider': self.active_provider,
            'timeout_seconds': self.timeout_seconds,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'retry_attempts': self.retry_attempts,
            'retry_base_delay_seconds': self.retry_base_delay_seconds,
            'stale_after_seconds': self.stale_after_seconds,
            'mutation_policy': 'none',
        }}


__all__ = ['DEFAULT_PRODUCTION_PROVIDER','ProviderConfig','ProviderConfigurationError','SUPPORTED_PRODUCTION_PROVIDERS']
'''


def _env_example(selected_provider: str) -> str:
    provider = selected_provider if selected_provider in GENERATED_PROVIDER_KEYS else 'csv'
    return '\n'.join([
        '# NiceGUI Base generated provider configuration.',
        '# This file contains non-secret examples only. Copy values into your environment; do not commit credentials.',
        'NICEGUI_BASE_DATA_MODE=development',
        f'NICEGUI_BASE_DATA_PROVIDER={provider}',
        'NICEGUI_BASE_DATA_CSV_PATH=./data/production.csv',
        'NICEGUI_BASE_DATA_SQLITE_PATH=./data/application.sqlite3',
        'NICEGUI_BASE_DATA_SQLITE_TABLE=records',
        'NICEGUI_BASE_DATA_TIMEOUT_SECONDS=30',
        'NICEGUI_BASE_DATA_CACHE_TTL_SECONDS=15',
        'NICEGUI_BASE_DATA_RETRY_ATTEMPTS=2',
        'NICEGUI_BASE_DATA_RETRY_BASE_DELAY_SECONDS=0.15',
        'NICEGUI_BASE_DATA_STALE_AFTER_SECONDS=120',
        '',
    ])


def _bind_app_runtime_source(source: str) -> str:
    if 'register_source_health' in source:
        return source
    lines = source.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            insert_at = index + 1
    lines.insert(insert_at, 'from services.app_data import register_source_health')
    source = '\n'.join(lines) + ('\n' if source.endswith('\n') else '')
    pattern = re.compile(r'(?m)^(    )return NiceGUIRuntimeAdapter\((.+)\)$')
    match = pattern.search(source)
    if not match:
        raise ValueError('generated app runtime shape is not recognized for provider health binding')
    indent, expression = match.group(1), match.group(2)
    replacement = (
        f'{indent}adapter = NiceGUIRuntimeAdapter({expression})\n'
        f'{indent}register_source_health(adapter)\n'
        f'{indent}return adapter'
    )
    return pattern.sub(replacement, source, count=1)


def materialize_production_integration(root: Path, project: Mapping[str, Any]) -> tuple[dict[str, object], tuple[Path, ...], dict[str, str]]:
    contract = provider_contract_for_project(project)
    findings = validate_provider_contract(contract)
    if findings:
        raise ValueError('generated provider contract is invalid: ' + '; '.join(findings))
    selected = str(contract['selected_provider'])
    sources = {
        'services/provider_config.py': _provider_config_source(selected),
        '.env.example': _env_example(selected),
    }
    written: list[Path] = []
    for rel, source in sources.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        written.append(path)

    meta = root / '.nicegui_base' / 'provider_contract.json'
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    written.append(meta)

    app_path = root / 'app.py'
    if not app_path.is_file():
        raise FileNotFoundError('generated app.py is required before provider runtime binding')
    app_source = _bind_app_runtime_source(app_path.read_text(encoding='utf-8'))
    app_path.write_text(app_source, encoding='utf-8')
    sources['app.py'] = app_source
    written.append(app_path)

    gitignore_path = root / '.gitignore'
    existing_ignore = gitignore_path.read_text(encoding='utf-8') if gitignore_path.is_file() else ''
    ignore_lines = existing_ignore.splitlines()
    if '.env' not in ignore_lines:
        ignore_lines.append('.env')
    gitignore_path.write_text('\n'.join(ignore_lines).rstrip() + '\n', encoding='utf-8')
    written.append(gitignore_path)

    readme_path = root / 'README.md'
    if readme_path.is_file():
        selected_text = selected if selected != DEFAULT_PROVIDER_SELECTION else 'runtime selection required for production'
        readme = readme_path.read_text(encoding='utf-8').rstrip()
        readme += (
            '\n\n## Production data provider & runtime readiness\n\n'
            f'- Generated production-provider default: `{selected_text}`.\n'
            '- Supported generated production adapters: `csv`, `sqlite`. NiceGUI Base also exposes generic DB-API and optional provider-pack authorities, but this generated project does not pretend those are configured without application-specific connection code.\n'
            '- Development/production switching is environment-driven through `NICEGUI_BASE_DATA_MODE`; page code does not change.\n'
            '- Non-secret configuration reference: `.env.example`. Do not place passwords, tokens, API keys, connection strings, cookies, private keys, or authorization headers in generated/project artifacts.\n'
            '- Runtime readiness: the canonical `NiceGUIRuntimeAdapter` health registry includes the generated `data-source` health check. A missing/broken production provider makes `/readyz` return not-ready while the app remains startable for diagnostics.\n'
            '- Provider diagnostics: `services.app_data::provider_diagnostics()` reports mode, active provider, readiness, bounded timeout/cache/retry policy, and a redacted failure reason.\n'
            '- Reads use the canonical `DataSourceTable`/`ServerDataTableSpec` bounded timeout, cache and idempotent retry path. Provider mutation remains disabled.\n\n'
            'Example local readiness check after setting environment values:\n\n'
            '```bash\npython -c "import asyncio; from services.app_data import provider_diagnostics; print(asyncio.run(provider_diagnostics()))"\n```\n'
        )
        readme_path.write_text(readme, encoding='utf-8')
        written.append(readme_path)

    return contract, tuple(dict.fromkeys(written)), dict(sources)


__all__ = [
    'DEFAULT_PROVIDER_SELECTION','GENERATED_PROVIDER_KEYS','PROVIDER_CONTRACT_SCHEMA_VERSION',
    'materialize_production_integration','provider_contract_for_project','validate_provider_contract',
]
