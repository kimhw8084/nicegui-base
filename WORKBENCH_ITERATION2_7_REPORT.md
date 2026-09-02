# NiceGUI Base Workbench Iteration 2.7 — Application Blueprints & Multi-Page Assembly

Baseline: `47afc0446bcf298bb10f1167650be3557bfb5994`

- Six governed multi-page application blueprints; single-page generation remains the default.
- The Workbench-composed primary page remains authoritative; surrounding pages are deterministic compositions from existing pattern/catalog authorities.
- Generated applications use AppShell + NavigationModel for one consistent desktop/mobile navigation grammar.
- NiceGUIRuntimeAdapter now owns secondary-page registration so generated apps do not teach raw NiceGUI route wiring.
- Browser acceptance contracts and runtime proof cover every generated route, not only `/`.
- Generated ZIP smoke validates blueprint manifests, page modules and app route wiring.
- Project state schema v4 persists blueprint selection; portable project/history/preset flows inherit it automatically.
- Wheel synchronization remains offline and validates an extracted installation shape including package data.
