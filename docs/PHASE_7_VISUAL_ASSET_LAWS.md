# Phase 7 Visual Asset Laws

1. Application code uses semantic icon keys through `ICON_REGISTRY`, `get_icon()`, `SvgIcon`, or approved higher-level component parameters.
2. Runtime UI icons must not use emoji, arbitrary inline SVG, remote icon services, or remote images.
3. All mandatory assets are packaged locally and referenced through machine-readable manifests.
4. Generic and semiconductor icons share the same 24×24, rounded-line visual grammar and semantic `currentColor` theming.
5. Icon-only actions require an accessible label; the renderer emits `aria-hidden` only for decorative icons.
6. Aliases resolve AI vocabulary variance (`reload` → `refresh`, `equipment` → `tool`, `out-of-spec` → `oos`) without producing different visuals.
7. State illustrations are restrained system illustrations, not decorative stock artwork.
8. SVG files may not contain scripts, `foreignObject`, JavaScript URLs, HTTP(S) references, CSS `url(...)`, or missing `viewBox`.
9. Dataviz markers/patterns are package assets and must remain distinguishable without relying only on color.
10. Every asset has explicit source/provenance metadata. Phase 7 runtime assets are project-authored.
11. Third-party libraries may be evaluated as future sources only after license/version review and explicit vendoring; no hidden runtime dependency is allowed.
12. Asset keys are versioned API. Renames require aliases/deprecation rather than silent breakage.
