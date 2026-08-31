# Phase 8 — State, Async, Persistence & Convenience Laws

## State ownership
1. Component-local state stays local; page state belongs to the page/controller; user preferences use the preference service.
2. Application code must not directly scatter storage reads/writes through UI callbacks.
3. Persistent mutable NiceGUI preferences use `app.storage.user`, not `app.storage.browser` after response construction.
4. Tab state is reserved for state that must be independent across browser tabs.
5. Client/session state is volatile and must not be used for durable preferences.
6. URL state contains shareable analytical/navigation context only. Secrets, credentials, large payloads, and private data do not belong in URLs.
7. Persist semantic preferences, not DOM implementation details.

## User preferences
8. Theme, density, sidebar mode, table layouts, saved filters, favorites, and recent entities are represented by `UserPreferences`.
9. Preferences must use typed defaults so a missing preference never breaks application startup.
10. Unknown application-specific preference blobs should live under a namespaced application key rather than changing framework internals.

## Async execution
11. UI callbacks must not perform long blocking work directly.
12. Use `AsyncAction` for user-triggered service operations.
13. Duplicate button actions are suppressed by default; the second caller joins the in-flight result rather than invoking duplicate work.
14. Use `CancelableTask` for latest-request-wins behavior such as search/filter/query changes.
15. Use `StaleResponseGuard` when multiple independent requests can resolve out of order.
16. Use `Debouncer` for bursty search/filter inputs and `Throttler` for intentionally rate-limited actions.
17. Timeouts belong at service/action boundaries; do not leave user actions indefinitely pending without an explicit reason.
18. Cancellation is a normal state and must not be presented as a generic system error.

## Refresh
19. Monitoring/analytical auto-refresh uses `AutoRefreshController`; applications must not create uncontrolled refresh loops.
20. The framework minimum interval is one second; production intervals should be chosen based on actual data freshness and backend load.
21. During refresh, preserve useful existing content where practical and expose refreshing/stale state instead of blanking the page.
22. Refresh failures should preserve last-known-good content when safe and surface the error separately.
23. `RefreshStatus` is the canonical source for last attempt, last success, last error, age, refreshing, and stale state.

## Services
24. Notifications go through `NotificationService`.
25. Navigation goes through `NavigationService` when application logic initiates navigation.
26. Theme/density changes go through `ThemeService` and preference persistence.
27. Clipboard/download operations go through their services, keeping NiceGUI/browser APIs out of business logic.
28. Dialog intent is represented by `DialogService`; actual visual surfaces continue to use the approved Phase 4 overlay components.
29. User-facing technical failures go through `ErrorService`, which produces a safe message and correlation/error ID.
30. Logging goes through `LoggingService` or the future company logging adapter rather than ad-hoc print statements.

## Keyboard
31. Shortcuts use `KeyboardShortcutRegistry`; applications do not implement scattered raw key handlers.
32. Shortcut strings are normalized (`cmd`→`meta`, `control`→`ctrl`) and duplicates fail loudly.
33. Global shortcuts ignore form controls by default so normal typing and selection remain predictable.
34. Shortcut help must be discoverable to users when keyboard-first behavior becomes important.

## NiceGUI boundary
35. NiceGUI storage, keyboard, navigation, clipboard, download, and dark-mode calls remain in `NiceGUIStateServices` rather than business/page code.
36. `app.storage.tab` access requires an established NiceGUI client connection; callers must respect the NiceGUI lifecycle.
37. System theme mode maps to NiceGUI dark-mode value `None`.
38. The framework remains usable/testable without importing NiceGUI until a NiceGUI adapter is actually invoked.
