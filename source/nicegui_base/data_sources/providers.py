from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DataSourceProviderDefinition:
    key: str
    implementation: str
    dependency: str
    use_when: str


DATA_SOURCE_PROVIDERS: Mapping[str, DataSourceProviderDefinition] = MappingProxyType({
    'memory': DataSourceProviderDefinition('memory', 'InMemoryDataSource', 'core', 'Tests, examples, small immutable datasets and local prototyping.'),
    'csv': DataSourceProviderDefinition('csv', 'CSVDataSource', 'core', 'Dependency-free CSV development/reference data.'),
    'dbapi': DataSourceProviderDefinition('dbapi', 'DBAPIDataSource', 'core', 'Any DB-API 2.0 connection with an explicit semantic schema.'),
    'sqlite': DataSourceProviderDefinition('sqlite', 'SQLiteDataSource', 'core', 'Reference SQL provider and local analytical persistence.'),
    'sqlalchemy': DataSourceProviderDefinition('sqlalchemy', 'optional provider pack', 'nicegui-base[data-sql]', 'Enterprise SQL engines where SQLAlchemy is approved.'),
    'odbc': DataSourceProviderDefinition('odbc', 'optional provider pack', 'nicegui-base[data-odbc]', 'Enterprise ODBC sources.'),
    'arrow': DataSourceProviderDefinition('arrow', 'optional provider pack', 'nicegui-base[data-arrow]', 'Arrow/Parquet analytical datasets.'),
    'excel': DataSourceProviderDefinition('excel', 'optional provider pack', 'nicegui-base[data-excel]', 'Excel ingestion/export workflows.'),
    'rest': DataSourceProviderDefinition('rest', 'optional provider pack', 'nicegui-base[data-rest]', 'Internal HTTP/JSON services.'),
})


__all__ = ['DATA_SOURCE_PROVIDERS', 'DataSourceProviderDefinition']
