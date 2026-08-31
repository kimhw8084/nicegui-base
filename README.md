# NiceGUI Base 3.0.0a8 — Source-Complete Application Platform Alpha

NiceGUI Base is the company-standard NiceGUI base template and application framework for rapidly building production-quality internal web applications. It provides the golden starting point, reusable UI/data/application primitives, engineering examples, validation, packaging, and release guardrails so teams can focus on their application logic instead of rebuilding infrastructure. `3.0.0a8` is the first v3 architecture line: it keeps the certified v2 rendering/design contracts as the compatibility floor while adding governed application runtime, data, workspace, interaction and extension layers above them.


## NiceGUI Base identity refactor status

The active framework identity is fully refactored to **NiceGUI Base**. The distribution and wheel are `nicegui-base`, Python imports are `nicegui_base`, primary commands are `nicegui-base*`, generated apps use the `.nicegui_base` metadata directory and `NICEGUI_BASE_*` variables, and current release/certification authorities use the new identity. Compatibility aliases exist only for migration and are explicitly deprecated.

## Rename from Company UI

The project identity is now **NiceGUI Base**. New code uses the `nicegui_base` Python package, the `nicegui-base` distribution, `nicegui-base ...` CLI commands, and `NICEGUI_BASE_*` environment variables. A deprecated `company_ui` root import, former `company-ui*` console-script aliases, and `COMPANY_UI_*` environment-variable fallback remain only for migration. Historical release evidence keeps the former name when necessary to preserve provenance. Internal `cui-*` CSS/DOM tokens are intentionally retained as a stable compatibility namespace and are not user-facing branding.

## Release status

`3.0.0a8` is **source-complete alpha**, not stable `3.0.0`. Source-level non-regression is green across the complete inherited estate; live target/runtime/browser/human certification remains deliberately PENDING because NiceGUI and the supported browser matrix are unavailable in this build sandbox.

The authoritative parent is frozen `3.0.0a8`. Existing v2 routes do **not** need to migrate to the v3 workspace/runtime model, and the established renderer, shell, control anatomy, DataTable behavior, chart stack, geometry and accessibility contracts remain the compatibility floor.

## What makes v3 a major architecture

- **Application runtime kernel** — `ApplicationRuntime` and `WorkspaceRuntime` own lifecycle scopes, typed state, commands, diagnostics and workspace resources.
- **Governed state + interaction history** — namespaced typed keys, atomic transactions, defensive reads, revision history, exact rollback, transaction-level undo/redo and stale-redo invalidation.
- **Unified data engine** — immutable datasets and shared data sessions drive table-like rows, grouped chart series and KPIs from one semantic filter authority.
- **Large-data query hardening** — exact row identity plus lazy equality/IN indexes accelerate repeated cross-filtering without changing data semantics.
- **Adaptive workspace engine** — deterministic collision-free panel placement, constrained move/resize, responsive derivation, compaction and exact snapshot restoration.
- **Whole-workspace persistence** — application/workspace snapshots serialize runtime state, panel geometry and shared data-session filters to JSON and rehydrate deterministically.
- **Semantic visualization planning** — visualization intent is mapped onto the existing certified chart renderers; v3 does not create an ungoverned second chart stack.
- **Governed extension API** — explicit registrations for components, data sources, commands, visualizations and workspace panels replace ad-hoc patching.
- **Runtime diagnostics** — lifecycle/task, command-performance, workspace-panel and extension ownership are inspectable as platform state.
- **Provider-neutral production data** — typed semantic schemas, query ASTs, provider capabilities, provenance and server-side pushdown keep page composition independent of the backing store.
- **Unified analytical context** — filters, time ranges, affected/control/baseline populations, entity focus, freshness and typed selections are shared across analytical surfaces.
- **Interactive analytical workspaces** — governed move/resize/collapse/hide/lock/dock/split/duplicate/reset/undo/redo behavior is runtime-owned and persistable.

## Zero-regression UI/UX rule

V3 capability is additive and opt-in. Existing v2 pages continue through the established renderer and design laws unless a page is explicitly migrated to a v3 workspace. A new v3 primitive must preserve the established visual constitution or provide a tested, measurably stronger contract; local route CSS, raw visual anatomy forks and ungoverned z-index/layout fixes remain forbidden.

RC4/RC5 performance and correctness fixes remain authoritative: one-primary-grid DataTable mounting, immediate-scroll behavior, lifecycle-scoped cleanup, async race/cancellation contracts, schema-aware table persistence, exact typed row identity, overlay focus/Escape/scroll ownership, stale-last-good refresh behavior, revision-owned editable saves, hidden-chart update coalescing, accessibility alternatives and pathological-data regressions are retained.

## Runtime contract

Production dependency:

```text
nicegui==3.15.0
```

Optional browser-certification dependencies:

```text
playwright==1.62.0
Pillow==12.3.0
```

Setup validates production runtime only and must not require browser-certification packages or a free fixed port. `run_lab` owns its configured lab port. Full browser certification remains strict.

## 3.0.0a8 Wave 77 source evidence

- Python/source regression estate: **1,581/1,581 PASS across 137 test files**
- dedicated Wave 77 behavioral regressions: **36/36 PASS**
- governance: **0 errors / 0 warnings**
- shipped examples: **41 files / 0 errors / 0 warnings**
- static certification: **12 PASS / 1 expected NiceGUI-unavailable environment warning / 0 FAIL**
- visual integration coverage: **183/183**
- public root API entries: **1,525** (**+0 / 0 removals / 0 changed Wave 76 frozen signatures**)
- stable `3.0.0` publication: **NOT PERFORMED**; target runtime/browser/company/human/reviewer/operations evidence remains **PENDING** until genuinely executed and verified.

## Stable 3.0.0 promotion blockers

1. Install the v3 wheel in a supported target/company environment and pass the exact NiceGUI 3.15.0 runtime contract.
2. Pass real server smoke for all 21 canonical current routes with no runtime error patterns.
3. Pass supported Chrome/Edge certification across the canonical responsive matrix, including console, geometry, interaction, overlay, table, chart and screenshot-regression gates.
4. Review and approve the hash-locked human visual baseline.
5. Capture required macOS/Linux company-target evidence and regenerate the stable `3.0.0` manifest/SBOM/provenance against the final wheel.

See `docs/V3_APPLICATION_PLATFORM.md`, `docs/V3_MIGRATION_GUIDE.md`, `PHASE_46_V300A1_APPLICATION_PLATFORM_REPORT.json`, `TEST_REPORT.json`, `CERTIFICATION_REPORT.json` and `LIVE_CERTIFICATION_READINESS.json`.


## Wave 61 — Semiconductor Semantic Platform + Engineering Analytics Library

Wave 61 adds the canonical semiconductor entity/genealogy model, shared manufacturing context and dependent DataSource filters, SPC/capability, wafer/spatial, FDC/PCA, RCA/commonality, yield/reliability/DOE analytics, 58 machine-readable semiconductor surfaces, and three integrated golden workflows. It reuses Wave 59 DataSource and Wave 60 AnalysisContext/SelectionBus/AnalyticalPanel authorities and adds no mandatory numerical dependency. See `docs/PHASE_61_SEMICONDUCTOR_SEMANTIC_ANALYTICS.md` and `PHASE_61_V300A8_SEMICONDUCTOR_SEMANTIC_ANALYTICS_REPORT.json`. Current target NiceGUI/browser certification remains pending.

## Wave 62 semiconductor application recipe factory

Use `nicegui-base recipes "<engineering intent>"` to select among eight governed semiconductor complete-app recipes, then generate with `nicegui-base create ... --template analysis-workspace --recipe <recipe>`. See `docs/SEMICONDUCTOR_APPLICATION_RECIPES.md` and `PHASE_62_V300A8_SEMICONDUCTOR_APPLICATION_RECIPE_FACTORY_REPORT.json`. Recipes reuse the Wave 59–61 data/state/analysis authorities and do not create a parallel runtime.


## Wave 63 semiconductor recipe production runtime + smart onboarding

Wave 63 adds conservative explainable schema onboarding, provider-neutral `SemiconductorSourceAdapter`, eight governed focused recipe variants, non-forking recipe customization, and `SemiconductorRecipeRuntime` for bounded refresh/records and shared stale/error/empty/readiness behavior. Generate a focused starter with `nicegui-base create ... --recipe <recipe> --variant <variant>`. See `docs/SEMICONDUCTOR_RUNTIME_ONBOARDING.md` and `PHASE_63_V300A8_SEMICONDUCTOR_RECIPE_PRODUCTION_RUNTIME_REPORT.json`. The runtime continues to reuse Wave 59–62 authorities; target NiceGUI/browser/company adapter certification remains pending.

## Wave 64 semiconductor production adapter conformance + runtime experience hardening

Wave 64 adds bounded provider conformance that verifies advertised pushdown through observed `QueryStats`, UI-ready onboarding/setup contracts, a shared ready/loading/stale/empty/partial/error runtime experience model for all eight semiconductor recipes, safe recipe runtime presets backed by the existing Wave 60 workspace snapshot authority, bounded runtime performance probes, and explicit target-environment certification state. A missing installed NiceGUI/server/browser/company-adapter/human gate remains **PENDING**, never inferred as PASS. See `docs/SEMICONDUCTOR_PRODUCTION_RUNTIME.md` and `docs/PHASE_64_SEMICONDUCTOR_PRODUCTION_ADAPTER_RUNTIME_HARDENING.md`.

## Wave 65 semiconductor provider SDK + guided RC operationalization

Wave 65 adds provider-author tooling around the existing Wave 59 `DataSource`/Wave 64 conformance authorities: `SemiconductorProviderAdapterBase`, governed development/production conformance fixtures, remediation guidance, provider-init/provider-check CLI flows, a guided setup workflow and `SemiconductorSetupWizard`, recipe operational guardrails, bounded development/provider-RC benchmark profiles, and portable target-evidence bundles. Development fixtures may make an app runnable, but representative provider, installed NiceGUI/server, supported browser, company-environment and human visual evidence remain separate release gates and stay **PENDING** when absent. See `docs/SEMICONDUCTOR_PROVIDER_SDK_RC.md` and `docs/PHASE_65_SEMICONDUCTOR_PROVIDER_SDK_ONBOARDING_RC.md`.

## Wave 66 semiconductor target certification + operational deployment readiness

Wave 66 adds fail-closed qualification and promotion orchestration over the existing Wave 59–65 authorities: deterministic provider qualification packs, evidence freshness and SHA-256 traceability, exact framework/NiceGUI evidence identity, operational readiness and provider-neutral runbooks for all eight semiconductor recipes, stable-promotion decisions, deployment-readiness UI, and a `nicegui-base target-qualify` CLI. Runtime usability and stable release promotion remain separate: missing/stale/untraced or legacy identity evidence is **PENDING**, failed/corrupt/provider-source/version-mismatched evidence is **BLOCKED**, and unavailable installed NiceGUI/server/browser/company/human evidence is never synthesized as PASS. See `docs/SEMICONDUCTOR_TARGET_CERTIFICATION_OPERATIONAL_READINESS.md` and `docs/PHASE_66_SEMICONDUCTOR_TARGET_CERTIFICATION_OPERATIONAL_READINESS.md`.

## Wave 67 semiconductor stable-promotion candidate + enterprise evidence assimilation

Wave 67 layers deterministic enterprise evidence assimilation, stable-promotion candidates, governed release channels, promotion/rollback/incident/evidence-capture rehearsals and self-contained candidate packaging over the canonical Wave 66 qualification/promotion decision. Missing company/runtime/browser/human evidence remains PENDING.

## Wave 68 enterprise target-execution intake + operational handoff

Wave 68 adds fail-closed target-execution intake for the existing external gates, independent candidate-archive reverification, deterministic operational handoff packages and runbook-bound operation evidence. Operation records never change candidate or target-gate truth and the generic framework performs no company deployment.

## Wave 69 promotion execution-adapter qualification + release audit closure

Wave 69 adds artifact-backed external execution-adapter qualification and deterministic release-audit closure/package contracts. Audit `CLOSED` means evidence completeness only; it never means deployment, publication or stable-promotion approval.

## Wave 70 stable release evidence acceptance + promotion closure

Wave 70 independently reverifies immutable Wave 69 audit archives, binds external release acceptance to exact artifacts/framework/NiceGUI/audit identity, and produces fail-closed documentary promotion closure plus deterministic self-contained closure packages. `CLOSED` does not deploy or publish stable `3.0.0`, does not alter canonical Wave 66/67 truth, and cannot synthesize missing company/runtime/browser/human evidence. See `docs/SEMICONDUCTOR_STABLE_RELEASE_EVIDENCE_ACCEPTANCE_PROMOTION_CLOSURE.md` and `PHASE_70_V300A8_ENTERPRISE_STABLE_RELEASE_EVIDENCE_ACCEPTANCE_PROMOTION_CLOSURE_REPORT.json`.


## Wave 71 enterprise release publication evidence + post-promotion verification

Wave 71 independently reverifies the immutable Wave 70 closure package, binds external stable-publication evidence to exact closure/candidate/archive/framework/NiceGUI identity, and verifies generic publication-integrity plus post-release runtime-smoke evidence. `PUBLISHED`/`VERIFIED` are evidence states only; the generic framework performs no deployment, publication or continuous production monitoring.

## Wave 72 enterprise post-release stability evidence + rollback readiness

Wave 72 independently reverifies the Wave 71 post-promotion package, assimilates artifact-backed production-health/incident evidence, and verifies rollback readiness against exact Wave 71/Wave 72 identities. The stable policy requires `production-health-window` and `incident-summary`; rollback readiness requires `rollback-plan-validation`, `rollback-artifact-integrity` and `rollback-rehearsal`. Optional externally captured rollback-execution evidence is preserved as evidence only. `STABLE`/`READY` never mean NiceGUI Base monitored production, responded to an incident, executed a rollback, deployed, or published the release. See `docs/SEMICONDUCTOR_POST_RELEASE_STABILITY_ROLLBACK_READINESS.md` and `docs/PHASE_72_ENTERPRISE_POST_RELEASE_STABILITY_ROLLBACK_READINESS.md`.


## Wave 73 enterprise sustained-operations evidence acceptance + incident/rollback audit closure

Wave 73 independently reverifies the Wave 72 rollback-readiness package, binds external `sustained-operations-window` and `incident-audit-summary` evidence to exact Wave 72/framework/NiceGUI identities, and closes an incident/rollback audit only with artifact-backed `incident-audit-closure` and `rollback-audit-closure` evidence plus an accepted sustained-operations record. `ACCEPTED`/`CLOSED` are documentary evidence states only: NiceGUI Base does not continuously monitor production, handle incidents, execute rollback, deploy, publish, or approve stable `3.0.0`. Missing evidence stays PENDING; changed, corrupt, unsafe, or identity-mismatched evidence is BLOCKED. See `docs/SEMICONDUCTOR_SUSTAINED_OPERATIONS_INCIDENT_ROLLBACK_AUDIT.md` and `docs/PHASE_73_ENTERPRISE_SUSTAINED_OPERATIONS_INCIDENT_ROLLBACK_AUDIT.md`.


## Wave 74 enterprise sustained-operations renewal + continuity

Wave 74 independently reverifies the Wave 73 incident/rollback audit package, classifies external renewal evidence as current/expiring/expired/missing/contradictory under bounded framework policy, and builds deterministic operational-assurance continuity dossiers without changing historical Wave 73 truth. Missing/expired evidence stays `PENDING`; contradictory/tampered/identity-mismatched evidence is `BLOCKED`.

## Wave 75 enterprise operational-assurance renewal ledger + longitudinal evidence governance

Wave 75 independently reverifies immutable Wave 74 continuity packages, binds their outer SHA-256 identities, and composes multiple verified periods into a deterministic longitudinal ledger. Bounded framework policy diagnoses uncovered gaps, tolerated gaps, overlaps, stale active windows, historical stale intervals renewed in time, duplicate identities, future timestamps, identity drift and post-binding archive mutation. `ASSURED` and `EXPIRING` are documentary evidence states only; missing/stale history remains `PENDING`, corrupt/unsafe/changed/identity-mismatched or contradictory history is `BLOCKED`, and NiceGUI Base performs no continuous monitoring, incident response, rollback, deployment, publication or company approval. See `docs/SEMICONDUCTOR_OPERATIONAL_ASSURANCE_RENEWAL_LEDGER.md` and `PHASE_75_V300A8_ENTERPRISE_OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_LONGITUDINAL_EVIDENCE_GOVERNANCE_REPORT.json`.


## Wave 76 enterprise longitudinal assurance review + evidence exception governance

Wave 76 independently reverifies the immutable Wave 75 longitudinal assurance ZIP and every nested Wave 74 period, then binds external reviewer/authority/reference artifacts to the exact Wave 75 dossier/package identity. Bounded exception decisions may document a review obligation but never change the underlying Wave 75 `ASSURED`/`EXPIRING`/`PENDING`/`BLOCKED` evidence state or create a synthetic PASS. Missing, expired, or revoked review authority remains `PENDING`; tampered, contradictory, unsafe, identity-mismatched, or default-policy non-waivable blocked evidence is `BLOCKED`. NiceGUI Base performs no monitoring, incident response, rollback, deployment, publication, or company approval through these records. See `docs/PHASE_76_ENTERPRISE_LONGITUDINAL_ASSURANCE_REVIEW_EVIDENCE_EXCEPTION_GOVERNANCE.md`.

## Wave 77 final release-candidate consolidation + stable qualification handoff

Wave 77 adds no new evidence authority. It consolidates release identity, source-certification phase ownership, public API/release mirrors, generated-project guidance, wheel/source/package representation, checksum/archive verification, executable-mode preservation and historical-evidence classification. `nicegui-base final-audit` produces a diagnostic source release-candidate audit; `nicegui-base stable-qualification-handoff` identifies the remaining real target/company qualification gates. Source completion never manufactures stable `3.0.0` publication or missing runtime/browser/provider/data/human/reviewer/operations evidence. See `docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md`.
# nicegui-base
