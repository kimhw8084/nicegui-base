# NiceGUI Base v3 Migration Guide

## Default: do not migrate a working v2 page

A v2 page remains supported as-is. Adopt v3 only where runtime ownership, shared data state, workspace persistence, semantic visualization or extension governance creates material value.

## Safe adoption sequence

1. Keep the existing page renderer and Company primitives unchanged.
2. Create an `ApplicationRuntime` and one `WorkspaceRuntime` for the application/workspace boundary.
3. Move shared application/session/workspace values into governed typed runtime state; keep component-local presentation state local.
4. Introduce a `Dataset`/`DataSession` only when multiple tables/charts/KPIs must share one filter/query authority.
5. Introduce `WorkspaceLayoutEngine` only for panels that need responsive placement, move/resize or persistence.
6. Use `SemanticVisualizationPlanner` to select existing governed visual renderers; do not build a parallel ECharts wrapper.
7. Register product-specific integrations through `ExtensionRegistry` rather than monkey-patching core modules.
8. Run the complete inherited regression and target browser certification gates before treating a migrated page as production-equivalent.

## Rollback rule

Because v3 is additive, a page can remain on or return to the inherited v2 rendering path without forcing a global application downgrade. Persisted v3 workspace/state payloads should be treated as governed application data, not as replacement visual markup.
