# Phase 4 Interaction Laws

These laws are authoritative for forms, filters, overlays, messaging, and durable UI states.

## Surface selection

1. **Use a drawer for contextual work.** A drawer preserves the underlying page while the user inspects or edits an entity.
2. **Use a dedicated page for deep workflows.** A drawer is not a replacement for a long, multi-step application route.
3. **Use a dialog for a focused blocking decision.** Confirmations and short tasks fit; entire dashboards do not.
4. **Use a destructive confirmation only when the action is meaningfully risky or irreversible.** Prefer undo when reversal is cheap.
5. **Use popovers and menus for lightweight secondary actions.** They must not hide critical primary actions.
6. **Use the smallest surface that preserves comprehension.** Tooltip < popover/menu < dialog < drawer < dedicated page.

## Forms

7. Every form uses the framework `Form` contract and standardized field anatomy.
8. Validation timing defaults to `hybrid`: early enough to help, not so early that untouched fields immediately show errors.
9. Field errors appear beside the field; complex forms additionally use `ValidationSummary`.
10. Required state, description, error, disabled, and read-only behavior come from component contracts rather than app styling.
11. Unsaved changes use `DirtyStateGuard` for meaningful edits.
12. Form actions use the standard action hierarchy: destructive (if present), secondary cancel, primary submit.
13. On phone, action areas maintain touch targets and remain reachable without excessive scrolling.

## Filters

14. Analytical filtering uses `FilterBar`; do not manually scatter unrelated selectors around the page.
15. Frequently used filters remain visible; complex or secondary filters move into `AdvancedFilterDrawer`.
16. Active filters are represented with removable `FilterChip` elements.
17. Filter presets use semantic named views, not duplicated hard-coded layouts.
18. Mobile filtering transforms to a drawer rather than compressing every desktop field into an unusable row.
19. Filter persistence is explicit: none, session, user, or URL.

## Feedback

20. Use **toast** for short nonblocking operation results.
21. Use **alert** for persistent region-level conditions.
22. Use **banner** for page/application-wide conditions.
23. Use **state view** for durable empty, no-results, error, permission, not-found, or offline states.
24. Never show raw Python exceptions to normal users. Durable failures use a safe message plus optional correlation/error ID.
25. Loading behavior is contextual: skeleton for content, spinner for a short action, progress when measurable.
26. Refreshing should preserve existing usable content whenever possible rather than blanking the page.

## Overlay behavior

27. Escape closes dismissible transient overlays.
28. Focus must be trapped inside modal dialogs and restored to the originating control on close where the underlying component supports it.
29. Overlay stacking and z-index are framework-owned.
30. Drawers/dialogs transform to larger/full-screen surfaces on phone where needed.
31. Overlay animations use the approved semantic motion tokens and respect reduced-motion preferences.
32. No app-specific overlay width in raw pixels; use semantic sizes: small, medium, large, x-large, full.

## Gemma/OpenCode rules

33. Search `INTERACTION_REGISTRY` before inventing a new interaction surface.
34. Do not create a custom drawer, dialog, toast, empty state, or filter layout if an approved pattern exists.
35. Do not use NiceGUI/Quasar overlay APIs directly unless the framework cannot satisfy the requirement.
36. When a gap is legitimate, implement it as a framework extension using the existing tokens and lifecycle rules.
