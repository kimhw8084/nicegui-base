# Phase 19 — v1.6 Rendered Product Hardening

## Why Phase 19 exists

Real Linux browser review showed that broad component coverage was not enough. Remaining defects were concentrated in shell geometry, page-canvas width, element spacing/alignment, overlay behavior, select internals, DataTable interaction/performance, analytical zoom and composed reference-app layout.

Phase 19 therefore changes the quality definition from **component exists** to **component renders, aligns, spaces and behaves correctly**.

## Structural corrections

- Desktop sidebar no longer depends on Quasar drawer geometry. NiceGUI Base owns a fixed `<aside>` with actual expanded/collapsed widths.
- Only one desktop collapse control exists.
- A frozen sidebar footer exposes owner/support/documentation/VOC actions.
- Main content uses real width math: `viewport - sidebar width`; collapsed state recomputes both offset and width.
- Outer pages always consume the full main canvas and use symmetric framework gutters.
- Reading-width modes constrain inner content only.
- Canonical `.cui-pattern` pages explicitly preserve grid display instead of being overridden by generic page flex rules.

## Interaction corrections

- Select-family double transformation of NiceGUI option models was removed.
- Company-owned SVG select arrows remain contained in the field.
- Operator Note is genuinely editable.
- ContextMenu is a true right-click pointer-position menu.
- Analytical drawers remain open during internal interaction.
- Command Palette destinations perform actual navigation.
- Attachment surface supports clipboard paste in addition to browse/drag-drop.
- DataTable supports real inspector interaction and in-place row/density updates.
- Chart zoom targets the actual dataZoom model and works through direct pointer interaction where appropriate.
- Chart export is one clear surface; heatmap legend occupies a non-axis collision region.

## Semiconductor visualization expansion

In addition to custom wafer and residual-field renderers, Phase 19 adds:

- synchronized affected-vs-control wafer comparison using one quantitative scale;
- radial center-to-edge profile visualization for center/edge/ring signature analysis;
- a meaningful zoomable/pannable engineering evidence image in the Content/Workflow lab.

## Browser certification expansion

The browser harness now reports failures for conditions including:

- `MAIN_CANVAS_WIDTH_MISMATCH`
- `PAGE_CANVAS_NOT_FULL_WIDTH`
- `PAGE_GUTTER_MISSING`
- `PAGE_TOP_GUTTER_MISMATCH`
- `CONTENT_OVERLAPS_HEADER`
- `CONTENT_OVERLAPS_SIDEBAR`
- `VERTICAL_GAP_TOO_SMALL`
- `GRID_GAP_TOO_SMALL`
- `SURFACE_PADDING_MISSING`
- `OVERLAY_OUTSIDE_VIEWPORT`
- `TOAST_HEADER_COLLISION`
- `DIALOG_HEADER_ALIGNMENT`
- `FIELD_APPEND_OUTSIDE_CONTROL`

Behavior smoke also verifies sidebar collapse, textarea editing, persistent drawer behavior, row double-click inspection, Command Palette navigation, density geometry and chart zoom state.

## Linux workflow

Manual setup/lab launch no longer requires Chrome/Chromium. Browser availability is required only for automated live certification. This prevents browser-discovery failure from blocking ordinary visual/manual review.

## Release boundary

Phase 19 source/offline tests and isolated-wheel checks remain distinct from target Linux browser certification. Linux Live Certification still requires the actual target browser matrix plus explicit human approval of its screenshot baseline.
