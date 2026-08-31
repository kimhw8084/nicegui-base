# Phase 6 — Visualization Laws

1. ECharts is the default analytical rendering engine. Plotly is an explicit specialist escape hatch.
2. Application code supplies semantic chart meaning and data; it does not hand-style axes, tooltips, legends, colors, grids, or toolbox controls.
3. Chart canvas colors are resolved from NiceGUI Base light/dark design palettes. Do not pass CSS variables as ECharts canvas colors.
4. Stable series keys produce deterministic colors across charts and pages.
5. Use semantic status colors only for semantic meaning; categorical data uses the categorical palette.
6. Every analytical chart is hosted in `ChartPanel` anatomy with title, optional description, lifecycle state, toolbar, responsive sizing, and theme support.
7. Prefer linked filtering through `CrossFilterEngine` / `LinkedAnalysisController`; do not directly couple a chart implementation to a table implementation.
8. Chart selection changes analytical context. Entity inspection belongs in the approved detail surface rather than inside chart callback UI code.
9. Use `SpecLimits` and `ThresholdSpec` for engineering limits. Do not draw ad-hoc limit lines.
10. Pareto uses contributor bars plus a cumulative-percentage secondary axis.
11. Control/process trend charts use standardized limit/target annotation semantics.
12. Donut charts are permitted only for small-part composition. They are not the default categorical comparison chart.
13. Wafer/spatial charts use framework spatial models and axis-free analytical presentation.
14. Large line series automatically disable point symbols and use LTTB sampling; large scatter/bar series request ECharts large/progressive paths.
15. Full visual-performance profiling remains a Phase 13 responsibility; Phase 6 provides safe defaults, not benchmark claims.
16. Standard toolbar affordances are zoom/reset/fullscreen/export/data-view when appropriate; app code may disable irrelevant affordances semantically.
17. Chart light/dark mode is changed through the adapter's theme path, not by app-specific option mutations.
18. Raw `ui.echart` is an escape hatch only when the framework lacks the required visualization grammar.
19. Raw Plotly usage is wrapped in `PlotlyPanel` so framework surface anatomy remains consistent.
20. New reusable chart grammar discovered in applications should be promoted into this subsystem instead of duplicated.
