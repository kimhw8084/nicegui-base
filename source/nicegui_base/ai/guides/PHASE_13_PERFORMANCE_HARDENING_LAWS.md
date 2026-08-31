# Phase 13 Performance & Hardening Laws

1. Measure before optimizing; speculative performance abstractions are not accepted.
2. Caches must be bounded and time-limited; mutations are never cached.
3. Authorization-variant data must never share a cache key across security contexts.
4. Rapid analytical requests use latest-request-wins cancellation semantics.
5. Stale data may remain visible during refresh, but must be semantically marked stale/refreshing.
6. Expensive hidden tabs/drawers should be lazy-loaded.
7. Async fan-out must be bounded when it can overload backend services.
8. Automatic retries are reserved for idempotent transient failures.
9. Blocking work must not run directly on the NiceGUI event loop.
10. Stable repeated local tables may use TableQueryEngine; fast-changing datasets should use stateless/server-side querying instead.
11. User workspaces are persisted through framework preference abstractions, not direct browser storage.
12. Standard application services are obtained from ApplicationServices unless a test/special adapter requires an override.
13. Framework CSS is deterministic and process-cached; app code must not inject duplicate framework styles.
14. Data exports must protect spreadsheet consumers from formula injection.
15. Performance optimization must not bypass the approved NiceGUI Base component/layout/security model.
