# NiceGUI Base Data Source Guide

Wave 59 introduces one provider-neutral analytical data boundary. Application pages should consume `DataSource` rather than opening database connections or reading production files directly.

## Default choice

- Use `InMemoryDataSource` for tests, examples and genuinely small static datasets.
- Use `SQLiteDataSource` as the dependency-free SQL reference provider and for local analytical stores.
- Use `DBAPIDataSource` when the company-approved database driver already exposes Python DB-API 2.0 and the semantic schema is known.
- Use `CSVDataSource` only for small/local CSV workflows; it intentionally materializes the file in memory.
- Keep enterprise provider packages optional. Do not add SQLAlchemy, ODBC, Arrow, Excel or REST dependencies to core merely because one application needs them.

## Semantic schema first

Describe fields with `SemanticField` and `DataSchema`. Include measurement units, identifier/dimension/entity roles, nullability and precision whenever known. UI and recipe layers should use these semantics instead of guessing from labels.

## Query contract

Use the typed query AST (`Query`, `Comparison`, `And`, `Or`, `Between`, `In`, `TextMatch`, `QuerySort`) and `AggregateQuery`. Never concatenate user values into SQL. Provider implementations must validate referenced fields against `schema()` before execution.

## Scale rule

If the underlying source can become fab-scale, prefer a provider that declares filter/sort/pagination/aggregation pushdown. Do not call `rows()` or build a pandas-style full materialization merely to render a table page or metric.

## Portability rule

A page/recipe should not branch on `source.provider`. If provider-specific behavior is necessary, put it behind a provider capability or adapter. The same analytical composition should run unchanged against in-memory fixtures and the production provider.

## Provenance and freshness

Preserve `QueryResult.provenance`, source health and freshness metadata through reporting and saved-view layers. An exported engineering conclusion must be traceable to its source and query time.
