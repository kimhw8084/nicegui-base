# NiceGUI Base v1.7 — Phase 7 Reference Applications

Phase 7 converts the ten canonical patterns from component demonstrations into production-composition references. The reference routes intentionally omit the certification Theme/Density/Motion toolbar so page geometry matches a real product.

## Composition law

All canonical patterns use one 12-column Company grid. Optional slots flow naturally; an absent slot must never create a phantom empty area.

- Dashboard / Monitoring / Data Explorer: 8-column primary analysis + 4-column secondary analysis.
- Master / Detail: 7-column master + 5-column sticky detail inspector.
- CRUD: 8-column filter region + 4-column action region, followed by full-width managed data.
- Search: 3-column sticky refinement rail + 9-column results/detail region.
- Settings: 3-column local-navigation rail + 9-column configuration region.
- Wizard: centered 8-column guided workflow.
- Comparison: full-width aligned population identity, spatial evidence and difference table.
- Analysis Workspace: 8-column analytical workspace + 4-column sticky investigation inspector.

Below the tablet breakpoint every canonical slot becomes one ordered full-width column and local sticky regions become static.

## Pattern surfaces

`PatternSurface` is a public pattern primitive with four sanctioned slot surfaces:

- `plain`: no additional chrome;
- `subtle`: low-emphasis filter/navigation context;
- `surface`: contained decision/form surface;
- `inspector`: persistent contextual detail surface.

`PatternPage.slot()` also forbids rendering the same semantic slot twice and emits machine-readable `data-cui-slot` / `data-cui-slot-surface` attributes.

## Reference application behavior

The ten routes must demonstrate real product behavior, not toast-only placeholders:

- CRUD creates a saved-view configuration in a real FormDrawer.
- Search results open a contextual InspectorDrawer.
- Wizard review opens a real review dialog before entering analysis.
- Comparison includes synchronized affected/control wafer evidence.
- Analysis includes Investigation Context, Commonality Matrix, full analytical charting and a sticky RCA inspector.
- Settings uses governed local navigation and the real shell settings/profile surfaces.

## Browser release gates

Desktop, tablet and phone certification verifies all ten routes. It fails if a certification toolbar leaks into a reference app, a semantic slot escapes the page canvas, a desktop split collapses unexpectedly, a mobile composition remains side-by-side, or the core CRUD/Search/Wizard/Comparison/Analysis behaviors are absent.
