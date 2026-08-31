# NiceGUI Base 3.0.0a2 — Coding-Agent Platform

## Goal

Make OpenCode/Gemma-style coding agents fast by removing avoidable architectural choice while preserving the certified v2/v3 renderer and UI/UX contracts.

## Added in 3.0.0a2

- `nicegui-base agent-init .` installs versioned agent guidance, machine-readable catalogs and four canonical golden examples.
- `nicegui-base agent-context "<task>"` produces a compact deterministic context pack with a dominant page pattern, construction categories, inspection paths and golden examples.
- `nicegui-base agent-check .` fails closed on a stale framework scaffold or any NiceGUI Base validator warning/error.
- Golden dashboard, data-explorer, CRUD and analysis-workspace examples use real public APIs and themselves validate at zero warnings.
- Validator rules now catch unowned `asyncio` task creation, raw renderer `.props(...)`, and direct application imports from `nicegui_base.integrations.nicegui_*`.
- The v3 runtime/data/workspace layers remain opt-in. Existing rendered screens are not migrated or restyled by this release.

## Agent construction loop

```text
business task
  -> nicegui-base agent-context
  -> closest golden example
  -> framework catalog/public API
  -> application code
  -> nicegui-base agent-check
  -> tests + browser review when visual
```

## Compatibility rule

This wave is additive above the public framework surface. No design tokens, component CSS, chart renderer, DataTable renderer, overlay renderer or shell geometry were changed.
