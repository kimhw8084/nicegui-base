# Phase 58 — Correctness, Lifecycle, and Trust

Wave 58 converts the audit's highest-risk findings into executable framework contracts rather than adding new product surface area.

## Correctness guarantees

- `DataSession.transaction()` is atomic and rolls back nested mutations correctly.
- Closed sessions reject reads, writes, bindings, snapshots, and transactions.
- Unknown dataset fields and invalid collection-filter operands fail loudly.
- Numeric aggregation rejects non-finite/non-numeric values instead of returning plausible-but-wrong results.
- Generated starters are imported and their `build_page()` functions are actually executed by the application gate.
- Compound table filters preserve AND/OR semantics, asynchronous row replacement is owned, and browser CSV export uses the governed formula-safe serializer.

## Lifecycle and security guarantees

- Protected navigation is fail-closed without an explicit permission resolver.
- `FileUpload` enforces `UploadPolicy` before application callbacks.
- Cancellation is never retried. Refreshed lazy resources dispose the previous resource, while failed refreshes preserve the last good resource.
- Validator implementation errors are not mistaken for signature mismatch. Browser listener bridges install cleanup ownership.

## Visualization and state guarantees

- Wafer/spatial values are finite numeric values or explicit missing values.
- Chart annotations and record-based `x_key`/`y_key` series mapping are executable.
- Clearing a cross-filter emits an explicit REMOVE mutation.
- Accordion, scoped state, and async loader abstractions now have distinct behavior instead of decorative aliases.

## Verification

- **734/734** tests pass across **118** test files.
- **21** Wave 58 behavioral regressions directly cover the audit fixes.
- Governance: **0 errors / 0 warnings**.
- Shipped examples validator: **0 errors / 0 warnings**.
- Static certification: **12 PASS / 1 expected environment WARNING / 0 FAIL**.
- Visual component mapping: **183/183**.

The current browser matrix is intentionally **PENDING** because Wave 58 changes source beyond the previously recorded browser run. The Phase 57 switch proof remains historical switch evidence, not a current Wave 58 browser-certification claim.
