# NiceGUI Base Workbench Iteration 2.9 — Interaction Contracts & Workflow Assembly

Baseline: `53eb982f8c6ed0da4ae29e69c95ddafc6ee91221`

- Every canonical page pattern receives deterministic, governed workflow actions with no extra Builder configuration step.
- Generated services/app_workflow.py composes existing AnalysisContext, SelectionBus, NiceGUIStateServices tab storage and NotificationService authorities.
- Multi-page applications share tab-scoped workflow state; storage adapters are resolved lazily from connected-client action callbacks so initial page construction remains storage-secret independent.
- Generated action strips wire refresh/reset/selection/saved-view/acknowledgement/draft/wizard/comparison behavior according to the page pattern.
- Provider mutation policy is explicitly none. CRUD-shaped pages use local draft state only until an approved write service is connected.
- .nicegui_base/interaction_contract.json is signed, canonical-pattern validated, route-cross-checked and embedded into the Workbench project manifest.
- Generated projects include interaction contract regression tests and README handoff guidance.
- Source/ZIP smoke verifies every generated page is wired to the shared workflow service; live proof starts both single-page and six-route generated applications.
- Wheel synchronization remains offline and validates the extracted installation shape including package data.
