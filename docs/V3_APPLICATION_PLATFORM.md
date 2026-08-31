# NiceGUI Base v3 Application Platform

## North-star contract

V3 turns NiceGUI Base from a governed component framework into an application platform while preserving the established UI/UX compatibility floor. Existing screens remain valid and are not globally rewritten. V3 services are opt-in ownership layers.

## Platform layers

1. **Runtime** owns typed state, atomic transactions, lifecycle, commands, diagnostics and undo/redo.
2. **Data** owns immutable datasets, semantic queries, shared filter sessions and reactive bindings.
3. **Workspace** owns responsive panel geometry, collision rules, persistence and restoration.
4. **Visualization** translates semantic intent into the existing governed visual renderer stack.
5. **Extensions** provide an explicit registration boundary for product-specific capabilities.

## Compatibility law

- Do not replace established renderer anatomy merely to use v3.
- Do not introduce a parallel chart/design system.
- Do not mutate runtime state through untracked mutable references.
- Do not let component-local filters diverge when the component participates in a shared `DataSession`.
- Do not persist workspace state without schema-aware, deterministic restoration.
- Breaking public API changes require a separately governed major-version decision; `3.0.0a8` additions are additive to the inherited root surface.

## Validation boundary

Build-environment completion proves the Python/static/inherited regression contracts plus the Chromium UI/UX constitution. The exact installed NiceGUI runtime, real 21-route live server/WebSocket application, and supported company browsers must still be exercised in the target deployment environment before stable `3.0.0` promotion.
