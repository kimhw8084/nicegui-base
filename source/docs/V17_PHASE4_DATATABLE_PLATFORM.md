# NiceGUI Base v1.7 — Phase 4 DataTable Platform

Phase 4 turns the table from an AG Grid surface with accessory controls into a governed engineering data workspace.

## Interaction constitution

- AG Grid remains the rendering/virtualization engine; NiceGUI Base owns all visible toolbar/search/preset/action anatomy.
- Search, density, refresh and row replacement must use live Grid API calls and must not remount the grid root.
- Comfortable / Compact / Dense are exactly 44 / 38 / 34 px rows. Headers are 46 / 40 / 36 px.
- Quick filter must provide visible filtered/total record feedback and has a 900 ms browser-certification budget.
- Density switching has a 700 ms browser-certification budget and must preserve the existing grid DOM root.
- Row actions are visible action pills, while row double-click remains the direct detail-inspection gesture.
- Low-priority columns must hide as complete columns, including headers, at responsive breakpoints.

## Toolbar

The toolbar is one Company-owned composition: native search on the left, then Columns, Density, Export and Refresh in one 34 px action grammar. Search no longer uses a Quasar input wrapper. Column selection uses Company checkbox anatomy. Density shows the active named density and each menu option states its row height.

## Data semantics

Numeric kinds get deterministic formatting. Percent uses `%`; units remain explicit. Status values remain semantic Company pills. Sparkline values render as lightweight inline SVG line profiles with an endpoint marker rather than text-block glyphs.

## Update/performance path

DataTable no longer calls `element.update()` for search, density, refresh, row replacement, server data replacement or edit rollback. `setGridOption`, `refreshCells`, `resetRowHeights`, `refreshHeader`, column state APIs and filter APIs are used instead. The grid keeps row virtualization, caches quick-filter text, uses AG Grid's 10-row pre-render buffer, explicitly disables vertical-scroll debouncing, disables row and column-move animation, and preserves scroll position during data replacement.

## Saved views

Saved views are Company menu surfaces instead of stock selects. A view can apply visible columns, density, pinning, sort state and supported filters through Grid API transactions. The Columns menu is synchronized after a view changes visibility.

## Certification

The `/data` browser smoke now checks filtered result feedback, quick-filter latency, density latency, row-height change, grid-root identity preservation, Inspect action behavior, row double-click detail, and modal ownership above the table toolbar.
