# NiceGUI Base Iteration 2.1 — Developer Velocity

Target baseline: `bebbeae8a7d97fdd6800646a4612e2348207cf71`
Framework version remains `3.0.0a8` with exact `nicegui==3.15.0` dependency.

## Implemented

- First-paint theme bootstrap from non-sensitive client display preference, eliminating the light-before-dark navigation flash.
- Theme/density/motion selections mirror to localStorage for correct first paint on subsequent routes.
- Capability Studio preview theme/density is scoped to the preview host instead of mutating the whole Workbench.
- AppShell receives a universal debugger trigger in the application header.
- Universal debugger captures bounded/redacted Python logs, browser errors, unhandled rejections, safe fetch metadata, client events, runtime/package information, optional health information, and sanitized diagnostic bundle export.
- Sidebar footer adds NiceGUI Base version, NiceGUI version and environment context.
- Mobile navigation toggle now writes the single DOM navigation state directly.
- Visible `REF APP` environment treatment is removed; the reference app is platform-neutral.
- DataTable reference page is rewritten into five distinct real-world table patterns: measurement population, recipe/configuration editor, equipment maintenance planner, incident/alarm queue, and change/reconciliation review. Four heavyweight secondary examples retain lazy Load behavior.
- Visualization reference page becomes a dense recipe gallery with 40+ reusable typed/specialist recipes spanning trends, markings, comparison, distributions, multivariate analysis, hierarchy/flow, DOE and engineering spatial analysis.
- Builder exposes Edit Goal / Edit Data / Change Recommendation navigation and removes the public arbitrary numeric score while preserving deterministic internal ranking.
- Workbench no longer advertises the legacy Reference Lab as a competing front door.
- Repository hygiene removes `__pycache__`, `*.pyc`, `.nicegui`, `.DS_Store` residue and adds ignore rules.
- Existing offline wheel builder is reused to rebuild all three wheel mirrors and regenerate source/package checksum manifests.

## Diagnostic privacy contract

The in-app debugger does not collect HTTP bodies, cookies, authorization headers, form values, or localStorage values. Existing `nicegui_base.security.redact` remains the redaction boundary for captured server/log context and exported diagnostic data.

## Delivery

Run `apply_iteration2_1.py ~/home/development/nicegui-base` from the extracted patch directory. The helper refuses a different Git baseline or unrelated local edits.
