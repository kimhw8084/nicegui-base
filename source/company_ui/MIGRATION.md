# Deprecated `company_ui` compatibility alias

The framework was renamed to **NiceGUI Base**. New code must use `nicegui_base` and the `nicegui-base` CLI. The root-level `company_ui` import remains temporarily available as a deprecated compatibility alias. Deep private-module imports under `company_ui.*` are not part of the compatibility guarantee; migrate them to `nicegui_base.*`.
