# NiceGUI Base 2.0.0rc5 — P0 Lifecycle, State, Async and Interaction Hardening

RC5 hardens the RC4 rendering baseline without changing the proven DataTable page-mount strategy. The release concentrates on ownership: tasks, requests, persisted state, overlays, edits and chart updates each have one explicit authority and deterministic cleanup/race behavior.

## Implemented contracts

- `LifecycleScope` owns async tasks and cleanup callbacks; close is idempotent, cancels owned tasks and runs cleanup once in reverse order.
- `AsyncAction` tracks concurrent work without one-handle races and only retries when the caller explicitly declares idempotency and retryable failures.
- `LatestRequestController` provides latest-request-wins cancellation, duplicate coalescing, bounded caching and governed retry for server-backed reads.
- DataTable persistence now restores and migrates column order/visibility/width/pinning, filters, sorts, density, search, pagination, exact typed selection identity and scroll position.
- Overlay ownership centralizes Escape priority, focus restoration and body-scroll locking across nested drawers/dialogs/popovers.
- Async content has a distinct `STALE` state so a failed refresh preserves the last successful content and exposes a safe retry rather than replacing useful context with an error page.
- EditableTable uses per-cell revision ownership. Obsolete save failures cannot roll back newer edits; latest failures restore the exact prior value and focused cell. Optimistic and confirmed commit modes are explicit.
- Editable pending state uses CSS class rules rather than DOM-heavy custom cell renderers; boolean text rendering uses a value formatter.
- ChartPanel observes intersection and non-zero geometry, coalesces mutations while hidden/zero-sized and flushes once with an ECharts resize when renderability returns.
- Charts expose a programmatic data alternative and explicit client-delete cleanup.
- Browser certification includes reusable frame-latency, long-task and resize probes.
- Pathological fixtures centralize empty, 1-row, 50k-row, 100-column, null/mixed numeric, extreme-string/security and timezone/DST data.
- Torture regressions repeatedly close lifecycle scopes and supersede latest-request work to prove no owned-task leakage.

## Source validation

- pytest: **630/630 PASS**
- governance: **PASS — 0 errors / 0 warnings**
- static/source certification: **12 PASS / 1 expected environment warning / 0 FAIL / 0 SKIP**
- visual component coverage: **183/183**
- canonical live routes: **22**

The expected warning is environmental: NiceGUI 3.15.0 is not installed in the build sandbox. RC5 therefore does not claim installed-runtime, real-server/browser or human visual-baseline certification.

## Promotion boundary

RC5 is a source-complete release candidate. Stable `2.0.0` remains blocked on the exact installed NiceGUI 3.15.0 runtime contract, 22-route live smoke, supported-browser console/geometry/interaction evidence, human visual-baseline approval and required company target-platform evidence.
