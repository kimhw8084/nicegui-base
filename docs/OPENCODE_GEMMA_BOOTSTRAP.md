# OpenCode / Gemma Bootstrap Prompt

Use the following as the first instruction for a coding agent working in an application built on NiceGUI Base.

> Treat NiceGUI Base as the application platform and `nicegui_base/` as stable framework code unless the task explicitly requests framework development. Read `AGENTS.md` first. Before coding, run `nicegui-base agent-context "<current task>"` and inspect the recommended golden example plus `.nicegui_base/framework_catalog.json`. Use only real NiceGUI Base public APIs; do not invent symbols or parameters. Keep page modules limited to composition and event delegation, with business logic in services and data access in repositories. Do not import NiceGUI directly, create raw AG Grid/ECharts, add arbitrary CSS/geometry/colors, or create parallel state/filter/layout/overlay systems. Use v3 `ApplicationRuntime`/`WorkspaceRuntime`, `DataSession`, workspace layout, and semantic visualization layers when they remove duplicate ownership. Preserve existing UI/UX unless the task explicitly improves it. After meaningful changes run `nicegui-base agent-check .`, application tests, and browser/runtime checks for visual work. Do not declare completion with validator warnings, failing tests, or unreviewed visual changes.

For a new workspace, bootstrap once with:

```bash
nicegui-base agent-init .
```

For every substantive task:

```bash
nicegui-base agent-context "<task>"
nicegui-base agent-check .
```
