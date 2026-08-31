# NiceGUI Base 1.7.1 — Visual & Interaction Correction Contract

NiceGUI Base 1.7.1 is the screenshot-backed correction release following the v1.7 redesign. It does not add a new application pattern; it tightens the visible and behavioral contracts that production applications inherit.

## Release laws

1. **Environment metadata is Company-owned.** Environment badges must not render through `q-badge`. Development, staging, production, and neutral environments use distinct semantic surfaces and readable primary text.
2. **Compact navigation is icon-only.** The collapsed desktop rail never lays out Support, Feedback, Documentation, or owner text. Those actions remain fixed-size icon targets with accessible names/tooltips.
3. **Navigation callbacks are awaited.** Sidebar/mobile toggles and route navigation use async event handlers when JavaScript or async navigation is involved. No handler may merely return an un-awaited `ui.run_javascript(...)` awaitable.
4. **Switch/range/progress anatomy is Company-owned.** Canonical surfaces do not use raw `ui.range` or `ui.linear_progress`. Dual-range controls use two native range inputs over one Company track. Progress has one track/bar contract, visible external value text, and one indeterminate animation.
5. **Inspection surfaces are side sheets.** Detail, inspector, activity, filter, and form drawers remain viewport-edge slide-outs. Centered dialogs are reserved for confirmation, review, and short modal tasks.
6. **Analytical categories remain distinguishable.** Donut categories are assigned ordered categorical palette slots. Stacked bars round only the outer silhouette; touching internal segments remain square at their seam.
7. **Workflow has one connector system.** `ProgressSteps` uses the dedicated rail only; the historical step pseudo-connector is disabled.
8. **Command palette is an actionable command surface.** It uses a native Company search field, left-aligned command rows, separate shortcut geometry, and closes before invoking navigation/actions.
9. **Engineering metadata stays inside its owner surface.** Entity metadata cells use bounded grids, `min-width:0`, governed radii, and responsive 4→2→1 column collapse. No nested decorative frame may create conflicting edge radii.
10. **Header identity is legible.** Application title is a primary hierarchy anchor; greeting and role/name are intentionally different in contrast and weight.

## Browser release gates

The macOS/browser acceptance harness explicitly checks the screenshot-backed regressions above: environment color differentiation, collapsed-footer containment, mobile navigation operation, native range geometry, side-sheet anchoring, progress animation/value placement, categorical donut colors, stacked-bar seam geometry, workflow connector ownership, command-palette anatomy/navigation, EngineeringEntity containment, and title/profile hierarchy.

These checks supplement rather than replace human visual review. A baseline should only be approved after the rendered 1.7.1 application is visually accepted in the target environment.
