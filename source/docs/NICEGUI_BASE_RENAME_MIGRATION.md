# NiceGUI Base identity migration

The golden NiceGUI template/framework formerly shipped under the **Company UI** identity. Its current identity is:

- Display name: **NiceGUI Base**
- Distribution: `nicegui-base`
- Python package: `nicegui_base`
- Primary CLI: `nicegui-base`
- Primary environment prefix: `NICEGUI_BASE_`

## Compatibility window

The `company_ui` root import is a deprecated compatibility alias. Former `company-ui*` console scripts remain deprecated aliases to the new implementation. Runtime configuration accepts legacy `COMPANY_UI_*` variables as a fallback when the corresponding `NICEGUI_BASE_*` value is absent. New generated applications use only the NiceGUI Base identity.

Deep private imports such as `company_ui.runtime.config` are not part of the compatibility guarantee; migrate them to `nicegui_base.runtime.config`.

## Stable internal selectors

Existing `cui-*` CSS classes, DOM markers, test hooks, and related internal selector tokens remain unchanged. They are compatibility identifiers, not product branding. Renaming them would break custom CSS and automation without user value.

## Historical evidence

Historical reports and archived evidence may retain the former identity. They are provenance records and are not rewritten to imply they were produced under the new name. Current release authorities, package metadata, generated starters, docs, examples, and certification output use NiceGUI Base.
