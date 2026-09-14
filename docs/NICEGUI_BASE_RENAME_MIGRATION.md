# NiceGUI Base identity

The NiceGUI template/framework now ships under one supported identity:

- Display name: **NiceGUI Base**
- Distribution: `nicegui-base`
- Python package: `nicegui_base`
- Primary CLI: `nicegui-base`
- Primary environment prefix: `NICEGUI_BASE_`

## Former identity removal

There is no compatibility window for the former product identity. The root import, former console-script names, and former environment-variable prefix are removed. New and existing applications must use only the NiceGUI Base identity.

Deep private imports are not part of the compatibility guarantee; use the corresponding `nicegui_base.*` module instead.

## Stable internal selectors

Existing `cui-*` CSS classes, DOM markers, test hooks, and related internal selector tokens remain unchanged. They are compatibility identifiers, not product branding. Renaming them would break custom CSS and automation without user value.

## Historical evidence

Historical reports and archived evidence may retain former naming when rewriting would falsify provenance. Those records are not current guidance or release authority. Current release authorities, package metadata, generated starters, docs, examples, and certification output use NiceGUI Base.
