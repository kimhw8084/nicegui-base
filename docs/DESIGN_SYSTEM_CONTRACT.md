# NiceGUI Base Design System Contract

## Authority

`source/nicegui_base/design/tokens.py` is the single programmatic token authority. Import token roles or `build_design_system()` from `nicegui_base.design`; do not create app-local token registries. `build_css()` emits the same authority for the browser, and `install_framework_css()` installs it once per process.

The governed families are spacing, semantic gaps, radius, typography, surfaces/colors, borders, elevation, density, breakpoints, motion, z-index, interactive states, and light/dark palette mappings. `ThemePalette` owns color and shadow values; semantic aliases resolve through the active palette.

## Usage rules

1. Choose the page pattern and semantic layout first.
2. Use framework components and classes such as `cui-layout-stack`, `cui-layout-cluster`, `cui-layout-grid`, `cui-surface-token`, and `cui-focus-ring`.
3. Use token variables (`var(--cui-...)`) in framework CSS. Outer application canvases remain full width; inner reading width belongs to `ContentColumn`.
4. Use control/surface/overlay radii (10/14/18px) and the governed comfortable/compact/dense table density (44/38/34px).
5. Use canonical breakpoints and responsive framework slots. Never add local z-index, arbitrary margins, colors, shadows, or stock NiceGUI/Quasar visual anatomy.
6. A missing primitive is a framework extension request. A last-resort exception must be isolated in an allowlisted implementation/token file or carry `# nicegui-base: allow-<rule-id>` immediately above the line with a reason in the review.

Run `nicegui-base validate <app-root>` for design-value validation; AI018 identifies arbitrary visual values outside the declared implementation boundary while preserving existing validator rules. The live reference is `/design` in the Workbench and is rendered from the same Python token object.
