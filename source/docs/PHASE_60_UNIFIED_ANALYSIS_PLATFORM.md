# Phase 60 — Unified Analysis and Interaction Platform

Phase 60 builds the shared analytical-state, typed selection, cross-filter, DataSource-table, analytical-panel, workspace-interaction, and durable-persistence layer required before semiconductor-specific recipes are expanded.

## Delivered

- transactional `AnalysisContext`
- affected/control/baseline population definitions
- source/as-of/freshness analytical metadata
- typed `SelectionBus` with replace/add/remove/clear and drill/back
- selection-to-context `AnalysisCoordinator`
- latest-request-wins `AnalysisBinding`
- standard `AnalyticalPanelController`
- Company-owned NiceGUI `AnalyticalPanel`
- `TableQuery` → Wave 59 query AST translation with compound filter preservation
- semantic schema → DataTable column generation
- provider-backed `DataSourceTable`
- `WorkspaceController` with move/resize/collapse/hide/lock/dock/split/duplicate/reset/undo/redo
- Company-owned `NiceGUIWorkspace` renderer with drag/drop panel movement and governed resize controls
- complete Wave 60 state in `WorkspaceRuntime` snapshots
- backward-compatible JSON persistence for Wave 59 snapshots
- persisted date/datetime/Decimal analytical values
- machine-readable `ANALYSIS_REGISTRY`
- AI construction/catalog guidance for the shared analysis architecture

## Design law

A page must not separately own filter state, selection state, provider query state, and workspace interaction state when the NiceGUI Base Wave 60 authorities can own them once.

The next implementation wave can therefore build semiconductor semantics and specialist analysis on top of one stable interaction/data foundation instead of creating a second architecture.
