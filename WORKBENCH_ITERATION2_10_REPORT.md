# NiceGUI Base Workbench Iteration 2.10 — Production Integration & Runtime Readiness

Baseline authority: `main @ 5c0a1ddfe19d2bc6d8e6d09b1921073591f1915f`  
Framework version remains: `3.0.0a8`  
GitHub usage: read-only; this package performs no remote writes.

## Implemented scope

- Reuses the canonical `DataSource`, `HealthRegistry`, `RetryPolicy`, `LatestRequestController`, `ServerDataTableSpec`, and generated `services/app_data.py::build_source()` authorities rather than introducing a parallel provider/runtime framework.
- Generated apps now support environment-driven development/production switching without page-code changes.
- Truthfully generated production adapters are limited to base-package constructible providers: CSV and SQLite. Optional provider-pack declarations (REST, SQLAlchemy, ODBC, Arrow, Excel) are not falsely presented as configured adapters.
- Generated `.nicegui_base/provider_contract.json` is signed and cross-checked by generated ZIP smoke validation.
- Generated `services/provider_config.py` binds non-secret environment configuration with bounded timeout/cache/retry/staleness values.
- Generated `.env.example` contains non-secret examples only; generated `.gitignore` explicitly excludes `.env`.
- Missing/broken production configuration preserves application import/startup and exposes an unavailable canonical `DataSource`; provider diagnostics redact sensitive values.
- Generated runtime registration adds a critical `data-source` check to the existing `NiceGUIRuntimeAdapter.health` registry, so readiness reflects provider state without a duplicate health system.
- Generated server-side tables use a shared bounded `ServerDataTableSpec`; canonical `ServerDataTable` now surfaces loading, empty, stale, and error footer states while preserving prior rows as stale on failed refresh.
- Provider mutation policy remains `none`; Iteration 2.9 local-draft semantics remain intact.
- Project state schema advances to v6 only to persist the non-secret provider choice (`none`, `csv`, `sqlite`).
- Generated projects carry provider/config/readiness regression tests.

## Verification in the ChatGPT sandbox

PASS:
- Python compilation for modified source and Iteration 2.10 tests.
- Dedicated Iteration 2.10 suite: 9/9 passed.
- Focused cumulative 2.8/2.9/2.10 + data-source/diagnostics/performance/async suite: 75/75 passed.
- Generated single-page ZIP static smoke.
- Generated multi-page blueprint ZIP static smoke.
- Generated-project contract tests: 3/3 passed in an extracted generated project.
- Real generated CSV provider query, health, and diagnostics regression.
- Real generated SQLite provider query and diagnostics regression.
- Broken/missing provider configuration remains importable, not-ready, actionable, and redacted.
- Provider contract tamper detection.
- Bounded provider numeric configuration and no infinite retry contract.

PENDING in this sandbox:
- Real NiceGUI HTTP/WebSocket/browser runtime proof because the execution environment does not have the `nicegui` dependency installed. The attempted generated-app startup failed explicitly with `RuntimeError: NiceGUI is required for NiceGUIRuntimeAdapter.` No browser/runtime PASS is claimed.

Baseline debt observed and kept separate from 2.10:
- Several older Workbench tests already fail at the exact baseline because their assertions predate later iterations (for example old state-version pins, six-tab Capability Studio expectations, and older generated table code strings).
- The broad repository run therefore is not represented as globally green. Baseline-vs-overlay comparison confirmed the sampled historical Workbench failures exist before this patch.

The transactional apply helper rebuilds all three bundled wheel mirrors offline, regenerates `RECORD`, validates wheel/source byte representation, extracts the wheel to filesystem-backed `site-packages` for import, regenerates source/package checksum manifests, and runs the focused regression suite when pytest is available.

## Transactional package verification

PASS on a fresh copy of the exact baseline:
- injected failure after wheel synchronization returned non-zero and restored every managed source/wheel/checksum byte exactly;
- both new 2.10 files were removed by rollback;
- normal apply completed with status PASS;
- 12 payload files applied;
- 3 wheel mirrors were rebuilt byte-identically;
- rebuilt wheel SHA-256 in the verification run: `04a62b84f86d43d2d032e08e61eac5d46894f656f5823ae1e66df4ebe6ee270e`;
- rebuilt wheel bytes: `1,145,857`;
- source checksum manifest: 1,042 tracked entries;
- package checksum manifest: 1,385 tracked entries;
- extracted-filesystem wheel import verification passed;
- generated ZIP smoke executed during apply.

These verification values describe the sandbox baseline-copy apply run. The apply helper recomputes and records the corresponding values in `WORKBENCH_ITERATION2_10_APPLY_RESULT.json` on the user's checkout.
