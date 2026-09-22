# Application Pattern Decision Guide

| Requirement signal | Pattern | Typical anatomy |
|---|---|---|
| KPIs + trend overview | `DashboardPage` | Header → optional filters → metrics → primary/secondary visuals → summary data |
| Filters + analytics + records | `DataExplorerPage` | Header → filters → metrics → charts → DataTable → DetailDrawer |
| Browse list and inspect entity | `MasterDetailPage` | Header → master data → selected detail → actions |
| Manage records | `CrudPage` | Header → filters/search → DataTable → create/edit drawer/page |
| Operational health/live status | `MonitoringPage` | Header/status → alerts → metrics → trends → affected records |
| Search heterogeneous entities | `SearchPage` | Header → facets/filtering → results → contextual preview |
| App/user configuration | `SettingsPage` | Header → local settings navigation → form content → actions |
| Guided multi-step task | `WizardPage` | Header → progress/navigation → constrained content → safe actions |
| Baseline/current comparison | `ComparisonPage` | Header → filters → comparative metrics/visuals → delta/evidence |
| Maximum-density analysis | `AnalysisWorkspacePage` | Compact header/filtering → resizable primary workspace → optional inspector |

If two patterns seem plausible, choose the pattern that best matches the **user's dominant task**, not the one that merely resembles the requested widgets.

## MasterDetail responsive contract

`MasterDetailPage` keeps the `DATA` and `DETAILS` slots simultaneously visible on desktop and tablet. On phone, the framework hides the inactive details slot and promotes the same selected detail surface to a full-screen contextual surface. The page adds an accessible **Back to master list** control, focus containment, Escape handling, body-scroll locking, and focus restoration without changing the table selection or query state.

Selection callbacks may call `page.open_detail()` after rendering the selected detail and `page.close_detail()` to return to the preserved master context. Governed selectable `DataTable` rows also open the contextual surface automatically. Applications should keep detail content in the public `LayoutSlot.DETAILS`; route-local responsive CSS or duplicate mobile drawers are not required.
