# NiceGUI Base D6B — Target Architecture

This is the target dependency map for the department-standard reference system.
It describes ownership and direction; D6B implements the first reorientation
slice while preserving D5 compatibility and export contracts.

## Canonical direction

```text
AI guidance / CLI / Workbench discovery
              │ intent, registry metadata, authoring decisions
              ▼
     application patterns + semiconductor recipes
              │ composition only
              ▼
       public framework APIs and integrations
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
  DataSource     AnalysisContext   Workspace/layout
  DataSchema     SelectionBus      PatternPage
  Query          DataSourceTable   PatternSurface
       │              │              │
       └──────────────┼──────────────┘
                      ▼
       governed tables, charts, content, controls
                      ▼
              NiceGUI runtime/theme/assets
```

The arrows are one-way. Registries describe capabilities; integrations render
them; application recipes compose them; Workbench discovers and demonstrates
them. A lower layer never imports Workbench UI or a higher-level application
recipe.

## Layer contracts

### 1. Platform foundation

`design`, `visual`, `runtime`, `security`, `diagnostics`, `services`,
`state`, `async_tools`, `performance`, and `jobs` provide tokens, lifecycle,
security, persistence, cancellation, measurement and durable execution. They
own cross-cutting behavior and are consumed through public root exports.

### 2. Semantic reusable framework

`components`, `content`, `forms`, `filters`, `overlays`, `feedback`, `layouts`,
`patterns`, `data_table`, and `visualization` define the standard vocabulary.
Their registries are the only identity source for reusable controls, content,
tables, charts and page patterns. NiceGUI/Quasar remains an implementation
detail behind `integrations/*`.

### 3. Data and analytical state

`data_sources` owns schema, provider capabilities, typed query expressions,
provenance, health and pushdown. `analysis` owns one context and selection bus
per analytical workspace, binding tables/panels to that context. The table and
chart layers consume the same query and selection state; neither maintains a
second page-local filter model.

For semiconductor applications, `SemiconductorAnalysisContext` and the
registered manufacturing filters extend the shared analysis context. Provider
adapters return the existing `DataSource`; they do not own UI callbacks or
alternate query semantics.

### 4. Semiconductor application recipes

`semiconductor/recipes.py` is the composition authority for the eight governed
recipes. `onboarding.py`, `setup_workflow.py`, `runtime.py`, `runtime_experience.py`
and `variants.py` resolve source bindings, readiness, panels, filters,
refresh, presets and operational diagnostics. `semiconductor/surfaces.py` and
`visualization.py` describe engineering surfaces and semantic visual plans.
`engineering/*` supplies rendering-independent SPC/FDC/RCA/yield/domain
calculations. Recipes select these authorities; they do not duplicate them.

### 5. Reference application

The reference UI consumes the exact public reusable implementations that a
developer imports:

```text
registry → public spec/model → public NiceGUI integration → PatternPage/recipe
```

Reference routes may add navigation, explanation and safe fixture data, but
they may not implement a second Button, DataTable, chart, filter, theme,
workspace, recipe calculation or state model. Catalog previews are explicit
specimens and must be labeled as such.

### 6. Workbench discovery and authoring

Workbench is a discoverability and compatibility shell, not the framework
source of truth.

- `registry_adapters.py` projects canonical registry metadata into searchable
  `WorkbenchEntry` records.
- `catalog.py` and `search.py` index those records and preserve routes,
  relationships and coverage checks.
- `catalog_runtime.py` is a bounded preview adapter. It may select a specimen
  and fixture, but cannot define production semantics.
- `provider_preview.py` is a transitional provider-aware preview adapter. It
  must use the page-owned `AnalysisContext`, `DataSource`, schema and governed
  renderers. Its eventual implementation belongs behind public data/analysis
  APIs, not in generated app imports.
- `app.py` owns shell routing and reference-preview chrome only.

### 7. Authoring, generation and CLI

The useful Builder contract is split deliberately:

| Preserve as reusable authoring logic | Retire/demote as primary product UX |
|---|---|
| Intent-to-pattern and intent-to-recipe recommendation | Manual six-stage widget-first composition |
| Pattern/recipe compatibility and placement validation | Builder-only preview implementations |
| Schema/data handoff, field mapping and project validation | Manual layout studio as the normal starting point |
| Project state/history/presets/stale-write protection | GUI-driven project authoring as the department standard |
| Blueprint resolution and deterministic scaffold decisions | Builder-specific business semantics |
| Code generation, export bootstrap, bundled provenance and smoke contracts | Any generated source that imports Workbench internals long term |

`codegen.py`, `project_codegen.py`, `app_blueprint_codegen.py`,
`export_bootstrap.py`, `runtime_bundle.py`, and `portable_project.py` remain the
implementation path for compatible exports. `ai_cli.py` and `cli.py` are the
preferred developer/agent entry point: `create-pattern` and `create-recipe`
select governed pattern/recipe identities and write projects that directly
consume the public framework. `/build` remains an explicit compatibility route
and is not part of the reference journey.

### 8. Guidance, validation and release

`construction_manifest.json`, `AI_CONSTRUCTION_REGISTRY`, `agent-context`,
the public API index, patterns/component/recipe guides, `validate`, runtime
contract/smoke and certification are one guidance-to-evidence chain. Release
governance binds source state, wheel, runtime, manifests and evidence. A
missing target/browser/company check remains pending or blocked; it is never
converted into a source-only PASS.

## Intended source-of-truth table

| Concern | One authority | Consumers |
|---|---|---|
| Visual language | `design/*`, `visual/*`, theme/asset integrations | Every page, reference route and generated app |
| Controls/content | component/content registries and integrations | Workbench specimens, recipes, generated apps |
| Interaction grammar | forms/filters/overlays/feedback + interaction registry | Every stateful surface |
| Rows and queries | `data_sources`, `data_engine`, `data_table` | Tables, charts, metrics and providers |
| Linked analytical state | `analysis/context.py`, `selection.py`, `bindings.py` | Analytical pages and semiconductor runtime |
| Charts | `visualization/*` + chart integrations | Reference UI, recipes and generated apps |
| Layout/pattern | `layouts/*`, `patterns/*` | Reference UI, CLI starters, generated apps |
| Semiconductor semantics | `engineering/*`, `semiconductor/*` registries/runtime | Recipes, provider adapters, reference pages |
| Discovery | canonical registries projected by `workbench/registry_adapters.py` | Catalog/search/Studio |
| Authoring | recommendation/scaffold services extracted from Workbench | CLI, AI agents, optional Builder UI |
| Documentation | synchronized `docs/` and packaged `source/docs/` | AI context, engineers, validation |
| Evidence/release | runtime/certification/governance/release tools | D4/D5/D6 release gates |

## Forbidden dependency directions

- Framework modules must not import `workbench.*` to obtain production
  components, data semantics or recipes.
- Generated application pages must not own a second registry, chart grammar,
  filter controller, theme system or workspace state model.
- Workbench specimens must not be copied into application code as examples of
  production implementation.
- A provider adapter must not bypass `DataSource` query/pushdown contracts.
- A recipe must not call raw NiceGUI visual primitives when a public Company
  integration exists.
- Documentation, AI guidance and catalog metadata must not describe an API that
  is absent from the public root surface.

## Migration order after D6B

1. Define a public preview contract so catalog specimens consume the same
   semantic renderers without owning fixtures or calculations.
2. Move generated provider rendering behind public data/analysis APIs while
   preserving D5 export compatibility and adding byte/hash regression coverage.
3. Replace the private reference-shell bridge with a governed public bridge.

Each step requires focused behavior regressions and a new release identity when
generated artifacts or runtime behavior change.
