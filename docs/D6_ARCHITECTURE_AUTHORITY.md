# NiceGUI Base D6B — Architecture Authority

Status: **D6B PASS**. This document records the D5 implementation map and the
implemented Reference Explorer/scaffolding ownership boundary. The D5 artifact
remains immutable; D6B changes are source-tree product reorientation only.

## Frozen baseline

| Fact | Authority |
|---|---|
| Team package | `NGB-20260905-D5`, `/private/tmp/ngb_d5_team/NGB-20260905-D5_TEAM.zip`, SHA-256 `ec2ff78216aab07fbc57c6840e609b6b1ae170e3155aa81e16d08c1a4830a16d` |
| Immutable RC | `NGB-20260905-D4`, D4 bundle SHA-256 `e05042d4332f0211c997e2028fa12eb3663bfa8ae3875e56c2d53382ec359021` |
| Framework/runtime | NiceGUI Base `3.0.0a8`; `nicegui==3.15.0`; Python `3.11–3.13` |
| Wheel | `nicegui_base-3.0.0a8-py3-none-any.whl`, SHA-256 `00db44ba89cfbfaad5933266c0c378f6ae29df6bd77860b18106415f982c5c17` |
| Packaged source authority | 551 files; source-state SHA-256 `7b693a506746a315670c59c1b27051a57cdc15a5c821ddf2033e5ffda2c1c785` |

## Authority rules

1. Public application code imports from `nicegui_base`; the root exports and
   typed registries are the framework boundary.
2. A registry defines capability identity and metadata. A NiceGUI integration
   renders that capability. Workbench catalog entries are a read-only index of
   those registries, not a second definition.
3. `DataSource`, `DataSchema`, `Query`, `AnalysisContext`, `SelectionBus`, and
   `DataSourceTable` own data semantics and linked state. Page callbacks and
   specimens do not create competing filter/population models.
4. A semiconductor recipe composes existing data, workspace, analysis and
   visualization authorities. It does not fork a page pattern or renderer.
5. A generated application depends on public framework APIs plus app-owned
   services/adapters. Workbench authoring helpers remain compatibility
   implementation details and are not imported by generated projects.
6. `docs/` and the packaged `source/docs/` copy are currently byte-identical;
   documentation changes must preserve that governed mirror relationship.

## KEEP / REFACTOR / RETIRE / MERGE / ADD matrix

| Product family | Current modules | D6B disposition | Single intended authority |
|---|---|---|---|
| Design, theme, tokens and assets | `source/nicegui_base/design/*`, `integrations/nicegui_theme.py`, `visual/*`, `integrations/nicegui_visual_assets.py` | **KEEP** | Design tokens, constitution CSS, theme adapter and local visual registries |
| Reusable controls | `components/*`, `integrations/nicegui_components.py` | **KEEP** | `COMPONENT_REGISTRY` + typed component specs + Company integrations |
| Content/viewers/workflow | `content/*`, `integrations/nicegui_content.py` | **KEEP** | `CONTENT_REGISTRY` + content integrations |
| Forms, filters, overlays and feedback | `forms/*`, `filters/*`, `overlays/*`, `feedback/*`, `interaction_registry.py`, integrations | **KEEP** | `INTERACTION_REGISTRY` and the typed interaction specs |
| State, services, async and jobs | `state/*`, `async_tools/*`, `services/*`, `performance/*`, `jobs/*` | **KEEP** | Page/workspace lifecycle primitives, `AnalysisContext`, `CancelableTask`, `Debouncer`, `StaleResponseGuard`, `ApplicationServices`, and job adapters |
| Navigation and application shell | `navigation/*`, `integrations/nicegui_layout.py`, `integrations/nicegui_runtime.py` | **KEEP** | `NavigationModel`, `AppShell`, `PageHeader`, responsive navigation and runtime-owned shell offsets |
| Extension and provenance boundaries | `extensions/*`, `convenience_registry.py`, `supply_chain.py` | **KEEP** | Explicit extension registration, convenience registry and provenance metadata; no route-local plugin system |
| Tables and data interaction | `data_sources/*`, `data_engine/*`, `data_table/*`, `analysis/table.py`, `integrations/nicegui_data_table.py` | **KEEP** | `DataSource`/`DataSchema`/`Query` plus `TABLE_REGISTRY`, `DataTable`, `ServerDataTable`, and `DataSourceTable` |
| Visualization and analytics | `visualization/*`, `analysis/*`, `integrations/nicegui_visualization.py`, `integrations/nicegui_analysis.py` | **KEEP** | `VISUALIZATION_REGISTRY`, semantic chart plans, `AnalysisContext`/`SelectionBus`, and Company chart integrations |
| Layouts | `layouts/*`, `integrations/nicegui_layout.py` | **KEEP** | Semantic layout primitives and responsive geometry tokens |
| Application patterns | `patterns/*`, `integrations/nicegui_layout.py`, `docs/APP_PATTERNS.md` | **KEEP** | `PATTERN_REGISTRY`, `PatternPage`/`PatternSurface`, and the registered ten patterns |
| Semiconductor calculations/entities | `engineering/*`, `semiconductor/{entities,spc,fdc,rca,yield_doe,spatial,visualization}.py` | **KEEP** | Rendering-independent engineering and semiconductor domain APIs/registries |
| Semiconductor recipes and full-app composition | `semiconductor/{recipes,context,onboarding,setup_workflow,runtime,runtime_experience,variants,surfaces,provider_sdk}.py` | **KEEP** | `SEMICONDUCTOR_RECIPE_REGISTRY`, `SEMICONDUCTOR_SURFACE_REGISTRY`, `SemiconductorAnalysisContext`, and `SemiconductorRecipeRuntime` |
| Provider onboarding/conformance | `data_sources/providers.py`, `semiconductor/provider_sdk.py`, `semiconductor/conformance.py`, certification provider modules | **KEEP** | Provider adapter contract returning the existing `DataSource`; no provider-owned query semantics |
| Catalog, registry projection and search | `workbench/registry_adapters.py`, `workbench/catalog.py`, `workbench/search.py`, `workbench/models.py` | **MERGE / REFACTOR** | Framework registries remain truth; Workbench becomes a typed read-only projection/search index with generated links |
| Catalog preview rendering | `workbench/catalog_runtime.py`, `workbench/provider_preview.py`, `workbench/preview_data.py` | **REFACTOR** | Preview adapters consume public registries, schemas, contexts and integrations; preview fixtures never become production data or renderer authority |
| Demo/specimen implementations | `workbench/{component,framework,visual,analytic,domain,pattern}_specimens.py`, `specimen_css.py`, related `_render_*` helpers in `workbench/app.py` | **RETIRE / DEMOTE** | Keep only as bounded catalog demonstrations; remove duplicated business/rendering logic when equivalent governed integration exists |
| Workbench shell and routes | `workbench/app.py`, `workbench/home.py`, `workbench/workbench_css.py` | **KEEP / REFACTOR** | Workbench is the discoverability/reference shell; shell uses public theme/layout/content APIs and does not own reusable component behavior |
| Manual Builder/project authoring | `workbench/builder.py`, `capability_studio.py`, `layout_studio.py`, `data_dock.py`, `state_matrix.py` | **RETIRE / DEMOTE** | `/build` is an explicit compatibility route only; reference Studio/Data/layout pages are authoring-free |
| Reusable recommendation/scaffolding | `workbench/builder.py` (`BuilderStage`, `PatternRecommendation`), `recipe_mapping.py`, `app_blueprints.py`, `interaction_contract.py` | **REFACTOR / KEEP** | Extract deterministic intent-to-pattern/recipe/scaffold decisions as framework authoring services used by CLI, AI and any future UI |
| Public developer/agent authoring facade | `ai/project.py`, `ai_cli.py`, `cli.py` | **KEEP / REFACTOR** | `create_pattern_application`/`create_recipe_application` and `create-pattern`/`create-recipe` consume governed pattern/recipe decisions without a second registry |
| Project state/history/audit | `workbench/project_state.py`, `project_history.py`, `project_audit.py`, `portable_project.py` | **KEEP / REFACTOR** | Schema-aware project persistence, stale-write protection, audit and portable bundle contracts; no new state store |
| Code generation/scaffolding | `workbench/codegen.py`, `project_codegen.py`, `app_blueprint_codegen.py`, `export_bootstrap.py`, `runtime_bundle.py`, `generated_smoke.py` | **KEEP / REFACTOR** | Deterministic generators and export bootstrap; generated source targets public framework APIs, with Workbench imports removed in a later boundary migration |
| CLI and agent workspace setup | `cli.py`, `ai_cli.py`, `ai_init.py`, `ai/project.py`, `ai/preflight.py` | **KEEP** | Public CLI commands: `create`, `create-pattern`, `create-recipe`, `recipes`, `provider-init/check`, `agent-*`, runtime and release gates |
| AI guidance and docs | `ai/manifest.py`, `ai/registry.py`, `ai/context.py`, `ai/templates/*`, `docs/*`, `source/docs/*` | **MERGE / KEEP** | `construction_manifest.json`, AI construction registry, public API index, application-pattern/component/recipe guides; one synchronized docs authority |
| Validation, runtime and security | `validate.py`, `runtime/*`, `diagnostics/*`, `security/*`, `integrations/nicegui_runtime.py`, `certification/*` | **KEEP** | Runtime contract, health/readiness, security, validation and certification authorities; evidence status is never inferred |
| Release/package governance | `governance/*`, `release_authority.json`, `certification/*`, D4/D5 tooling under `tools/` | **KEEP** | Hash-bound release identity, manifests, package builders and evidence verifiers |
| Reference applications/examples | `certification/mac_lab.py`, `examples/nicegui_base/*`, `examples/phase61-*` through `phase66-*` | **MERGE / REFACTOR** | Reference apps exercise the same public registries/integrations; examples document composition and do not become alternate framework implementations |

## Current surface inventory

The Workbench exposes `/`, direct compatibility `/build`, `/catalog`,
`/components`, `/patterns`, `/layouts`, `/studio/{entry}`, component/catalog
detail routes, `/analytics` and analytics detail, `/recipes` and recipe detail,
`/applications`, `/workbench/data`, `/quality`, `/ai-guide`, and the ten
canonical `/patterns/*` reference routes. D6B browser evidence covers the
Reference Explorer navigation at desktop/tablet/phone and light/dark; D5
evidence covers the compatibility Builder and generated apps. Each surface is
classified in the matrix above: primary shell/reference surfaces stay
Workbench-owned, while visible controls, tables, charts, state, recipes and
runtime are framework or domain authorities. Builder is not in primary
navigation or the normal reference journey.

## Duplication and boundary findings

- `workbench/registry_adapters.py` correctly derives catalog records from the
  canonical registries, but the preview renderer family still has hand-written
  fixtures and renderer selection. It must remain a projection, not a source of
  capability metadata or production behavior.
- `component_specimens.py` and `framework_specimens.py` demonstrate public
  integrations; their constants, sample values and CSS are demo-only. They are
  the clearest current duplication risk if copied into applications.
- `visual_specimens.py`, `analytic_specimens.py`, `domain_specimens.py`, and
  `app.py` preview helpers should call semantic chart/engineering renderers
  rather than grow parallel calculations or visualization grammar.
- `catalog_runtime.py` and `provider_preview.py` are useful compatibility
  adapters today. Generated apps currently reference the latter; the target
  boundary moves that adapter behind public data/analysis APIs without changing
  D5 exports in D6B.
- `app.py` installs reference-preview chrome by bridging a private certification
  shell method. A future public reference-shell/preview bridge should replace
  that coupling; no private bridge expansion is authorized in D6B.
- `workbench/builder.py` mixes a valuable intent/recommendation contract with
  manual GUI/project-authoring presentation. The former is preserved and
  extracted; the latter is demoted, not allowed to define the framework.

## D6B boundary

D6B intentionally preserves D2–D5 persistence, export, runtime and data
contracts. It adds the public deterministic pattern/recipe scaffolding facade,
removes manual Builder handoffs from primary/reference UX, and labels Data
Dock as an example-data contract playground. Any future artifact/runtime
change requires a new candidate identity and focused regressions.
