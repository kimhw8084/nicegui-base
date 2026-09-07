# D6E Patterns, Recipes, and Full Applications

## Composition authority

`nicegui_base.patterns.composition` is the single composition facade. It delegates
to the existing `AppShell`, `PatternPage.slot`, `FilterBar`, `MetricStrip`,
`Section` plus registered chart/table renderers, `InspectorDrawer`, and `StateView`.
The page registry remains the layout authority; the facade does not introduce a
second renderer or a route-local geometry system.

## Department coverage

| Department need | Composition profile | Canonical implementation |
|---|---|---|
| Dashboard | `dashboard` | `DashboardPage` |
| Monitoring | `monitoring` | `MonitoringPage` |
| Analysis workspace | `analysis_workspace` | `AnalysisWorkspacePage` |
| Investigation | `investigation` | `AnalysisWorkspacePage` + evidence recipe |
| Comparison | `comparison` | `ComparisonPage` |
| Master-detail | `master_detail` | `MasterDetailPage` |
| CRUD/admin | `crud` | `CrudPage` |
| Settings/configuration | `settings` | `SettingsPage` |
| Upload/review | `upload_review` | `DataExplorerPage` + Data Dock contract |
| Report | `report` | `DashboardPage` + evidence-backed recipe |
| Drill-down/details | `drill_down` | `MasterDetailPage` + inspector |
| Full-screen operations | `full_screen_operations` | `MonitoringPage` + responsive workspace |

Profiles intentionally reuse the ten governed page implementations. A profile is
a task-to-composition contract, not a parallel page registry.

## Semiconductor workflow coverage

`nicegui_base.semiconductor.recipes.recipe_workflow_coverage()` is the machine
authority for the engineering-question matrix. It covers SPC, I-MR, EWMA/CUSUM,
capability/distribution comparison, chamber/tool health, lot history, yield/defect
review, recipe/tool comparison, FDC signal exploration, excursion investigation,
correlation/parameter exploration, golden-tool before/after, alarm/event timeline,
and PM effectiveness. Each row records required data, governed visualizations,
patterns, alternatives, caveats, a runnable example, and the exact scaffold command.

The eight complete recipes remain the executable application authority:
`spc-monitor`, `excursion-defense-line`, `fdc-tool-health`, `lot-wafer-explorer`,
`yield-loss`, `pm-effect-analysis`, `chamber-matching`, and `rca-cockpit`.
Their source contracts require explicit data bindings and keep control/spec limits,
association/commonality, and causal conclusions distinct.

## Full applications

The Reference Explorer exposes three runnable compositions under `/applications`:
SPC Control Center, FDC Tool Health Center, and Excursion Investigation. Each uses
the public pattern slots, filter bar, KPI strip, registered visualization/table
renderers, inspector, and explicit no-results state. Their synthetic fixtures are
reference data only; generated applications continue to use the existing CLI and
recipe runtime authorities.
