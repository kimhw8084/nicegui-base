# NiceGUI Base v1.4 — Design and Improvement Summary

## Design target

NiceGUI Base deliberately treats NiceGUI/Quasar as runtime infrastructure. The visible product language is Company-owned: restrained big-tech internal-product styling, dense but readable information architecture, semantic hierarchy, local SVG iconography, subtle elevation, precise interactions and strict light/dark parity.

## Core visual system

- Semantic light/dark/system theme tokens
- 4/8-derived spacing hierarchy
- restrained radii and elevation
- system-native typography stack and tabular numeric treatment
- comfortable/compact/dense modes
- reduced-motion and forced-colors support
- responsive semantic layout laws
- 143 local semantic SVG icons and 12 state illustrations
- no required CDN/font/icon/image service

## Zero-stock NiceGUI layer

v1.3/v1.4 normalize the actual Quasar and AG Grid DOM rather than styling wrapper placeholders. Company styling owns buttons, fields, selects/chips, checkbox/radio/switch, sliders, tabs, segmented controls, expansions, steppers, trees, uploaders, progress/spinner, dialogs/drawers/backdrops, menus/tooltips, notifications and the complete AG Grid visual grammar.

The browser certification gate inspects the rendered DOM. Stock Quasar surfaces outside approved Company wrappers, stock notifications, unthemed AG Grid roots and unapproved Material icons are release failures.

## Application construction system

The framework contains ten canonical page patterns:

1. Dashboard
2. Data Explorer
3. Master/Detail
4. CRUD
5. Monitoring
6. Search
7. Settings
8. Wizard
9. Comparison
10. Analysis Workspace

Patterns own visual geometry and semantic slots so generated applications do not invent layout structure independently.

## Enterprise/data behavior

- enterprise DataTable with search/filter/sort/pagination
- bulk selection and row actions
- column manager, density, presets and export
- editing validation/rollback
- server-mode latest-request-wins loading
- master/detail drilldown
- conditional/status/sparkline cells
- optimized local 100k-row query/search path
- spreadsheet formula-injection protection for CSV

## Analytics and engineering

- ECharts-first semantic chart shell and Company toolbar
- line/area/bar/stacked/scatter/histogram/box/heatmap/Pareto/control/timeline/donut/gauge
- wafer and spatial maps
- specialist Plotly escape hatch inside Company panel anatomy
- specification/control-limit separation
- affected/control population comparisons
- commonality with routing-vs-causal distinction
- visible contradiction evidence
- calibrated-vs-uncalibrated confidence semantics
- reusable RCA evidence and engineering timeline components

## Resilience and performance

- cancellation and stale-response prevention
- debounce/throttle/latest-request-wins controls
- bounded TTL/LRU and single-flight cache
- analytical data controller
- lazy resources, bounded concurrency and retry policy
- background/blocking-work boundary
- runtime health/readiness
- correlation IDs and structured redacted logging
- durable-job adapter contract
- security-header/proxy/RBAC/upload hardening

## AI/OpenCode consistency

- authoritative `AGENTS.md`
- machine-readable framework catalog and construction manifest
- 721-symbol public API index generated from the live package
- validator that blocks raw NiceGUI UI construction, raw AG Grid/ECharts, arbitrary styling, remote resources, direct storage and UI-layer SQL
- embedded visual laws, performance guide, production completion guide and Mac certification guide

## v1.4 live-certification improvements

- 22-route executable NiceGUI laboratory
- all ten realistic reference applications
- 178/178 public visual integration classes accounted for
- 156 directly instantiated by route builders
- 22 explicitly justified composite internals
- standalone AppHeader/AppSidebar/MobileNavigationDrawer certification route
- expanded chart statistical/specialist coverage including Plotly
- master/detail, presets, selection/bulk/context table review
- base state, validation, metric and engineering-indicator review
- exact Playwright/Pillow certification dependency pins
- real wheel-vs-source separation in Mac orchestration
- deterministic screenshots and human-approved SHA-256 visual baseline
