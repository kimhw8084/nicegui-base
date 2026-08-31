# Phase 14 — v1.2.0 Production Completion Report

## Release status

**Production Gold Candidate.** The framework is code/package hardened and clean-install certified. Final **Company Production Gold** status remains contingent on live NiceGUI 3.15.0 browser, accessibility, reverse-proxy/WebSocket and company authentication certification.

## Production gaps closed from the v1.1 source audit

- DataTable toolbar, density, column management, selection/bulk actions, context actions, server query lifecycle, editing validation/rollback, status/conditional/sparkline behavior are runtime implementations rather than placeholders.
- Confirm/danger dialogs own their action footer and typed-confirmation lifecycle.
- Dirty forms protect browser unload and internal navigation.
- Menus/context actions execute callbacks.
- `AsyncContent` renders lifecycle states; state views render recovery actions.
- Desktop/sidebar/mobile navigation uses one functional route renderer.
- Core form controls expose ARIA label/description/required/error semantics and the shell exposes skip-to-main-content.
- Remaining core Material-icon assumptions were replaced with the packaged semantic SVG vocabulary.
- Chart tooltip/selection/zoom/brush/data/fullscreen/export controls are runtime-functional wrappers.
- Added 21 high-value content primitives covering metrics, detail/property presentation, trees, viewers, search results, workflow, comparison, command palette, background tasks, notification history and activity.
- Added `DurableJobAdapter` plus the explicitly non-durable `InProcessJobAdapter` reference implementation.
- Added SPDX SBOM/build provenance generation and removed the unused development artifact.
- Fixed a production-validator false positive: a single-file target now scans that file instead of silently reporting zero scanned files.

## Automated evidence

- 415/415 tests pass.
- Full Python compile passes.
- Strict static validation: certification app 0 errors / 0 warnings; component gallery 0 errors / 0 warnings.
- Offline source certification: 8 PASS / 1 intentional live-NiceGUI warning / 0 FAIL.
- Clean-installed wheel certification against canonical examples: 8 PASS / 1 intentional live-NiceGUI warning / 0 FAIL.
- Combined framework CSS: 70,707 bytes with balanced structure and no remote CSS resources.
- Semantic registries: 314 total entries excluding icon aliases; 143 icons; 12 illustrations.
- Public root API: 663 exported symbols.
- Wheel contains all production-completion modules, embedded AI guides/catalogs and 166 SVG resources.

## Remaining external certification boundary

The sandbox does not provide the actual NiceGUI 3.15.0 company runtime/browser topology. Therefore live Edge/Chrome visual equivalence, DOM accessibility, reverse-proxy/WebSocket behavior, company SSO/RBAC integration and production load/failover behavior must be certified using `docs/COMPANY_CERTIFICATION_CHECKLIST.md` in the company environment.
