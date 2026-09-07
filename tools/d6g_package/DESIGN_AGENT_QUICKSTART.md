# Design and agent quick start

This candidate is the department reference system. Start with the installed
catalog and registered application authorities; do not begin with manual
Builder composition.

```bash
nicegui-base agent-context "<short business and data requirement>" --format json
nicegui-base catalog-search "<intent>" --format json
nicegui-base recommend-pattern "<requirement>" --format json
nicegui-base recommend-visualization "<intent>" --schema timestamp --schema measurement --format json
nicegui-base scaffold-plan "<requirement>" --format json
nicegui-base create-pattern ./my-app --name "My App" --pattern monitoring
nicegui-base create-recipe ./my-spc --name "SPC Monitor" --recipe spc-monitor
nicegui-base agent-check ./my-app
nicegui-base gate ./my-app
```

Use the returned pattern, reusable components/tables, visualization contract,
canonical loading/empty/error states, and design tokens. Keep business/data
access in services. Generated applications import the installed
`nicegui_base` package; they do not copy Workbench or demo implementations.
