# NiceGUI Base Wave 60 — Unified Analysis Guide

Wave 60 establishes one shared analytical-state and interaction architecture on top of the Wave 59 `DataSource` platform.

## Default architecture

For analytical pages, create one `WorkspaceRuntime` and use its owned objects:

```python
runtime = ApplicationRuntime()
workspace = runtime.open_workspace('process-analysis')

context = workspace.analysis
selections = workspace.selections
layout = workspace.workspace
```

Do not create independent filter dictionaries, page-local selection buses, or a second workspace-layout model.

## Shared context

`AnalysisContext` owns filters, free-text search, time range, affected/control/baseline populations, focused entity, source identity, as-of/freshness timestamps, and analytical metadata. Mutations are revisioned and transactional.

```python
with context.transaction():
    context.set_source('fab_dw')
    context.set_time_range(TimeRange('event_ts', start, end))
    context.set_affected(PopulationDefinition('affected', filter=...))
```

Use `context.query(base_query)` before querying a `DataSource`. This applies the shared context without forcing page code to rebuild query logic.

## Selection bus and cross-filtering

`SelectionBus` carries typed selections for rows, entities, time ranges, wafers, dies, spatial regions, chart points, series, and populations. Use `SelectionMutationMode` for replace/add/remove/clear semantics. `drill()` and `back()` provide deterministic drill history.

A `Selection` can carry a typed Wave 59 query expression under `values['filter']`. `AnalysisCoordinator` then maintains that selection-derived filter in the shared `AnalysisContext` without removing unrelated base filters.

## Async bindings

`AnalysisBinding` connects context changes to asynchronous data loading using latest-request-wins behavior. Older requests are cancelled and cannot overwrite a newer result.

Use it when a chart, metric, table, or engineering panel refreshes from `AnalysisContext`.

## Analytical panel contract

`AnalyticalPanelController` standardizes these states:

- ready
- loading
- empty
- partial
- stale
- error

`AnalyticalPanel` provides the NiceGUI shell with governed status text and optional refresh/data/export/fullscreen actions. New analytical visualizations should use this contract instead of inventing their own loading/error chrome.

## DataSource-backed tables

`table_query_to_source()` translates the existing NiceGUI Base `TableQuery`/compound filter AST into the Wave 59 provider-neutral query AST. It preserves AND/OR grouping, sorting, paging, and shared context filters.

`query_data_source_table()` is the framework-neutral bridge. `DataSourceTable` is the NiceGUI server-paged surface and should be preferred for provider-backed tables.

`columns_from_schema()` converts semantic field types to governed table column kinds.

## Interactive workspace

`WorkspaceController` layers interaction state over `WorkspaceLayoutEngine` and owns:

- move
- resize
- collapse
- hide
- runtime lock
- dock
- split-group membership
- duplicate
- reset
- undo/redo

`NiceGUIWorkspace` is the Company-owned browser renderer. Layout geometry stays in `WorkspaceLayoutEngine`; interaction state stays in `WorkspaceController`.

## Persistence

`WorkspaceRuntime.snapshot()` now includes:

- runtime state
- deterministic grid geometry
- workspace interaction state
- analysis context
- typed selection state/history
- legacy `DataSession` snapshots

The JSON serializer preserves query filters plus `date`, `datetime`, and `Decimal` values. Older Wave 59 snapshots that omit Wave 60 fields remain loadable.

## Rules for generated applications

1. Use `WorkspaceRuntime.analysis`, `WorkspaceRuntime.selections`, and `WorkspaceRuntime.workspace` rather than parallel page-local authorities.
2. Keep data access behind `DataSource`.
3. Use query pushdown for large tables and analytical panels.
4. Publish typed selections instead of wiring unrelated panels together with bespoke callbacks.
5. Use `AnalyticalPanel` for consistent loading/error/empty/stale/partial states.
6. Persist the workspace snapshot rather than separately serializing each panel's state.
