# NiceGUI Base agent contract

NiceGUI Base `3.0.0a8` is the application platform. Treat `source/nicegui_base/` as stable framework code; put normal product work in the application layer. The supported runtime is exactly `nicegui==3.15.0` on Python 3.11–3.13.

## Before coding

1. Read this contract and `nicegui_base/ai/construction_manifest.json`.
2. Resolve the business question, data shape, ownership and states before choosing UI.
3. Run `nicegui-base agent-context "<requirement>" --format json`.
4. Inspect the returned `.nicegui_base/framework_catalog.json`, registered pattern/layout, relevant component/table/visualization metadata and the named golden example. Use `nicegui-base catalog-search "<intent>" --format json` when the authority is unclear.

Use this decision order: Page pattern → semantic layout → framework component → controlled extension. Select registered application patterns, semantic composition, tables, states and visualizations before an isolated extension.

## Construction rules

- Use public `from nicegui_base import ...` APIs. Do not import `nicegui.ui` directly or `nicegui_base.integrations.nicegui_*` from application code.
- Use `nicegui-base recommend-pattern` and `nicegui-base recommend-visualization` for unfamiliar requirements; select the returned authority, data contract and alternatives rather than inventing a primitive.
- Use `DataTable` for enterprise rows and Company visualization wrappers for charts. Keep data access in services/repositories and page callbacks thin.
- Use framework design tokens for spacing, gaps, typography, surfaces, borders, radius, density, breakpoints, motion, states and light/dark behavior. Use canonical loading, empty, error, disabled, readonly and overflow panels.
- Use framework async/state/lifecycle primitives for refresh, debounce, cancellation, stale-response protection, persistence and shortcuts. Use fail-closed security/runtime primitives for auth, uploads, health and deployment.
- Preserve identifiers, schema semantics, nulls, row alignment and finite-number validation. Never infer a measurement from an identifier/category when an explicit mapping is invalid or ambiguous; surface the choice/error.
- Do not add arbitrary CSS, raw grids, raw ECharts/AG Grid, stock visual anatomy or a new registry. An extension is allowed only when no registered authority satisfies a legitimate requirement; isolate it, reuse tokens/accessibility/state/error semantics, and place `# nicegui-base: allow-<rule-id>` immediately above any intentional validator exception.
- Do not use `ui.notify`, raw `ui.icon`, raw `ui.menu_item`, local z-index/layout geometry, or undocumented renderer props in canonical code.
- Generated apps must use installed `nicegui_base` authorities, never copied Workbench/demo implementations. Use `nicegui-base create-pattern` or `nicegui-base create-recipe` for scaffolding.

## Discovery and completion

Machine-readable discovery is intentionally bounded and deterministic:

```bash
nicegui-base catalog-search "<intent>" --format json
nicegui-base recommend-pattern "<requirement>" --format json
nicegui-base recommend-visualization "<intent>" --schema timestamp --schema measurement --format json
nicegui-base scaffold-plan "<requirement>" --format json
nicegui-base catalog-audit --format json
nicegui-base agent-benchmark agent_tasks/manifest.json --format json
```

For an application workspace, finish with:

```bash
nicegui-base agent-check .
nicegui-base gate .
nicegui-base runtime-contract
nicegui-base runtime-smoke --port 0
```

For framework changes, also run from the repository root:

```bash
PYTHONPATH=source .venv/bin/python -m nicegui_base.validate .
PYTHONPATH=source .venv/bin/python -m pytest -q tests
(cd source && ../.venv/bin/python -m pytest -q)
nicegui-base runtime-contract
```

Report exact commands, PASS/FAIL/NOT_RUN, evidence paths and any pre-existing warning separately. Never claim a live/browser/runtime PASS without executing it. Do not reset, clean, stash or overwrite unrelated work.

## G2 Explorer product laws

- Prefer intent-first and gallery-first discovery. A user must not open dozens of detail pages merely to learn what capabilities look like.
- Normal reference/application canvases use the full width beside governed navigation with semantic gutters; do not add an outer narrow max-width.
- Preserve Explorer search, filters, comparison, favorites and return context. Static registry/sample/thumbnail work may be build-bound cached; never share user/provider data across authorization boundaries.
- Reuse the canonical registry and production renderer. Do not create a second catalog, preview-only component authority, or schematic that is mislabeled as the current live renderer.
- Heavy galleries use evidence-bound thumbnails/lazy rendering and bounded live mounts. Detail pages remain the current interactive authority.
- Before adding a component, visualization, pattern, or full app, prove an existing authority/variant/composition cannot cover the recurring need without semantic distortion.
- Explorer changes require click-efficiency, search-latency, state-restoration, installed-browser and human-visual evidence in addition to normal framework gates.
