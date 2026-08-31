# Phase 2 Layout Laws

These rules are normative for application code and coding agents.

1. Use an approved `PagePattern` whenever one matches the requirement.
2. Application code never sets page padding, page max-width, sidebar width, or framework breakpoints.
3. Use `Page`, `Section`, `Stack`, `Grid`, `SplitPane`, or a page pattern before raw NiceGUI layout primitives.
4. Use semantic grid presets (`METRICS`, `CONTENT_INSPECTOR`, etc.), not arbitrary CSS grid definitions.
5. Use `PanelSize` and `ContentWidth` semantic values instead of raw pixel widths.
6. `DataTable`-class content will normally occupy the full available data region; do not place it in metric slots.
7. Quick contextual inspection belongs in a detail/inspector surface; extensive editing belongs on a dedicated form route or approved form surface.
8. Mobile behavior is owned by the framework. Do not build a second independent mobile page for normal responsive transformations.
9. Split panes are for regions that need simultaneous visibility, not for decorative subdivision.
10. Do not nest visually dominant surfaces without a semantic reason.
11. Keep the page hierarchy predictable: context → controls → signal → records → drilldown.
12. Raw NiceGUI layout/CSS is an exception and should be treated as evidence of a potential framework gap.
