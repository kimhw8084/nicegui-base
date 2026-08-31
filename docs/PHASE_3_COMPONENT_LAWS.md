# Phase 3 Component Laws

These rules are part of the public UI contract and are intended for both human developers and coding agents.

1. Use framework components before raw NiceGUI/Quasar controls.
2. Application code chooses semantic intent, size and state; it does not choose visual color, radius, spacing, shadow or transition values.
3. `ActionButton` is the preferred control for primary asynchronous or stateful actions; full async lifecycle behavior is hardened in Phase 8.
4. Icon-only controls require an accessible label. Final canonical icons arrive in Phase 7; applications must not introduce external icon dependencies.
5. A field owns its label, required marker, description, error, disabled/read-only state and focus treatment as one visual anatomy.
6. Disabled and read-only are distinct states and must not be combined.
7. Use `Select` for known single-choice values, `MultiSelect` for multiple known values, `Autocomplete` for large searchable sets, and `Combobox` only when custom values are explicitly allowed.
8. Use switches for immediate binary settings, checkboxes for independent selections, and radio groups for mutually exclusive choices.
9. Use `Panel` for routine enterprise containment; reserve `Card` for content needing stronger visual grouping/elevation.
10. Avoid nested cards. Prefer sections, panels, wells and dividers for hierarchy.
11. `InteractiveCard` and `Chip` expose selection semantically through `selected`; applications must not hand-style selected states.
12. Status intent is one of neutral/info/success/warning/danger. Status must include readable text, not color alone.
13. Data quality uses the canonical complete/partial/delayed/estimated/unavailable vocabulary.
14. Use `CollapsiblePanel` or `Accordion` for progressive disclosure rather than inventing hide/show behavior.
15. All controls inherit light/dark/system theme, density and reduced-motion rules from the design kernel.
16. On coarse-pointer devices, interactive targets maintain a 44px effective minimum target.
17. Application-specific raw CSS for standard component appearance is considered a framework-gap signal and should be escalated rather than copied between apps.
18. Final table and chart visual internals are outside Phase 3 and must not be inferred from showcase placeholders.
