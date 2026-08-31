# Phase 5 — Enterprise DataTable Laws

These laws are normative for humans and coding agents.

## T01 — Framework table first
Use `DataTable` for normal interactive tabular data. Do not instantiate raw `ui.aggrid` in application code unless a documented framework gap exists.

## T02 — Server mode for large source populations
Use `ServerDataTable` when the source is large enough that sort/filter/page operations belong in SQL or an API. Do not send an entire large source population to the browser.

## T03 — Semantic columns
Describe columns with `TableColumn`: data kind, units, precision, status semantics, editability and business validation. Do not style individual cells with arbitrary CSS.

## T04 — Stable row identity
Every interactive table has a stable `row_key`. Selection, expansion, refresh reconciliation and persistence must never depend on visual row position.

## T05 — Density is semantic
Use `comfortable`, `compact` or `dense`. Application code does not invent row heights.

## T06 — Numeric readability
Numeric columns align right and use tabular numerals. Precision and units are explicit in the column definition.

## T07 — Selection reveals actions
Bulk actions appear in `TableSelectionBar` only when selection exists. Destructive actions retain Phase 4 confirmation rules.

## T08 — Progressive detail
Use expandable/master-detail rows for compact contextual information. Use `DetailDrawer` or a dedicated route for deeper workflows.

## T09 — Editing is opt-in
Read-only is the default. Inline edit is used for bounded, low-complexity fields and must validate before commit. Complex edits use Phase 4 forms/drawers.

## T10 — Preferences persist, transient state does not
Persist column visibility/order/width, pinning, density, sort/filter presets and page size. Do not persist ephemeral row selection by default.

## T11 — Mobile prioritizes rather than compresses blindly
Critical identifier/status/value/action columns remain. Low-priority context can hide or move to row detail. Horizontal scrolling remains available when needed.

## T12 — Lifecycle states are first class
Loading, empty, no-results and error states preserve the table region and use standardized framework feedback rather than raw exceptions.

## T13 — Export follows displayed semantics
CSV/clipboard exports use column labels, units/format rules and visible business columns. Action columns are excluded.

## T14 — Conditional formatting communicates meaning
Use semantic warning/danger/success rules. Never depend on color alone; retain text/value/status context.

## T15 — Table chrome is standardized
Search, filters, columns, density, export and refresh belong to the canonical toolbar. Do not create a bespoke toolbar for each app.

## T16 — Raw AG Grid options are an escape hatch
Advanced AG Grid capability may be exposed by the framework when reusable. Repeated raw-grid configuration is evidence of a missing framework primitive.

## T17 — Refresh preserves user context
When possible, refresh must retain sort/filter/column preferences, reconcile selection by stable row key, and avoid disruptive scroll jumps.

## T18 — Performance before decoration
Virtualization/server query modes and efficient updates take priority over decorative cell rendering for large tables.
