# NiceGUI Base Workbench Iteration 2.4 — Zero-Decision Golden Starters

Baseline: `c6205faafdd05747e647c74999aea602c5ffbc8f`

## Objective
Reduce team-member decision time and application assembly TAT by converting the existing canonical patterns, analytics, tables, visualizations and controls into deterministic complete-app starting points without creating a second component/layout authority.

## Delivered
- 16 one-click Golden Starters: 8 engineering/semiconductor and 8 generic application shapes.
- Golden Starters resolve against the current Workbench/catalog adapters and canonical pattern registry at runtime; they do not hard-code duplicate component implementations.
- Schema-aware deterministic capability ranking uses the existing Workbench search contract plus Data Dock semantic roles/types.
- Builder `Auto-compose` fills empty slots or replaces the page with the current deterministic recommendation.
- Current-vs-recommended composition diff identifies add/remove/move decisions before generation.
- Project audit separates BLOCKING structural defects from non-blocking usability recommendations.
- Generation blocks duplicate capability placement, unknown catalog entries, invalid pattern slots and non-composable entries.
- Required-slot fallback remains supported, but is now visible as an audit warning rather than silently hidden.
- Generated applications now include `.nicegui_base/browser_acceptance.json` with canonical desktop/tablet/phone viewports and explicit browser-only proof requirements.
- Browser acceptance evidence starts as `PENDING_BROWSER_EXECUTION`; source/runtime validation is never mislabeled as browser PASS.
- Existing `smoke_generated_zip` remains backward compatible for older hand-built fixtures; the new browser contract is required specifically by the current Workbench generator.

## Golden Starters
### Engineering / semiconductor
1. SPC Defense Line
2. FDC Tool Health
3. Lot / Wafer Explorer
4. Yield Loss Investigation
5. PM Effect Analysis
6. Chamber Matching
7. RCA Cockpit
8. Process Capability Review

### Generic
9. Operations Dashboard
10. Data Explorer
11. Record Manager
12. Master / Detail Inspector
13. Configuration Center
14. Guided Workflow
15. Comparison Workbench
16. Engineering Analysis Workspace

## Release gates
- Exact committed baseline and clean worktree.
- Overlay manifest/hash verification.
- Python compile of every changed file.
- Workbench registration smoke when NiceGUI is available.
- All 16 Golden Starters resolve against the real canonical catalog with no unresolved required intent.
- All 16 starters pass Project Audit with zero blocking findings.
- All 16 starters generate valid governed ZIPs and valid browser-acceptance contracts.
- Auto-composition is deterministic for every canonical page pattern.
- Public-constructor signature matrix covers every currently composable catalog entry.
- Live startup proof executes one semiconductor analytical starter and one generic CRUD starter.
- Workbench live HTTP proof covers Home, Build, Layouts, Data, Capability Studio and Quality.
- Iteration 1 through 2.4 pytest regression suite runs when pytest/NiceGUI are available.
- Wheel mirrors and checksum manifests are rebuilt only after all gates pass.
- Any failure restores only touched Iteration 2.4 files/wheels/manifests transactionally.

## Methodology carried forward
Each future iteration uses the latest committed GitHub HEAD as the sole baseline, avoids duplicate truth sources, turns every discovered failure into a permanent validation class, executes the closest available real target workflow before packaging, and distinguishes source/runtime/browser/human evidence instead of promoting unexecuted checks to PASS.


## Post-gate correction — framework reference composition authority
The first target-machine 2.4 gate correctly failed on `lot-wafer-explorer` because its required records-table intent could not resolve. Root cause was not the phrase itself: `is_composable_entry()` rejected every canonical framework-catalog table and visualization because those records are intentionally represented as Workbench `REFERENCE` entries, while the generator admitted only `COMPONENT` entries.

Corrected contract:
- canonical `REFERENCE` authorities are composable only when `project_codegen` has a governed rendering adapter for that registry/key;
- all `tables` and `visualizations` framework-catalog entries are admitted through their existing canonical identities;
- governed content/interaction references such as `metric_card` and `alert` are admitted explicitly;
- richer component entries remain canonical for search/select/text/action controls;
- no duplicate component registry or starter-specific table implementation was introduced.

Release gates now explicitly require the real catalog identities `framework:tables:data_table`, `framework:visualizations:LineChart`, `framework:content:metric_card`, `framework:interactions:alert`, and the richer component controls to be both present and composable before any Golden Starter matrix runs. A dedicated regression also asserts `lot-wafer-explorer` resolves a canonical framework table.
