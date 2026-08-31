# Wave 66 — Semiconductor Target Certification Orchestrator & Operational Deployment Readiness

Wave 66 is an additive release-readiness layer over Waves 59–65. It does not replace `DataSource`, `AnalysisContext`, `SelectionBus`, semiconductor recipes, smart onboarding, provider conformance, benchmark profiles, or Wave 65 target-evidence bundles.

## Added contracts

- `ProviderQualificationPack` aggregates the newest evidence bundle per recipe for one provider and produces a deterministic qualification ID.
- `EvidenceFreshnessPolicy` and `EvidenceTraceabilityReport` distinguish current, stale, future/invalid, missing, and hash-mismatched evidence.
- Passed external gates (installed NiceGUI, server/WebSocket, browser, human visual baseline) must be linked to captured artifacts for stable promotion. Wave 65 bundle semantics remain unchanged.
- Newly captured target-evidence bundles record the authoritative framework version and required NiceGUI version. Stable promotion treats legacy bundles without that identity as PENDING, mismatched framework/runtime contracts as BLOCKED, and an installed-NiceGUI PASS against any version other than the exact required runtime as BLOCKED.
- `SemiconductorOperationalReadiness` separates **ready to run** from **ready for release** and consumes existing runtime, conformance, performance and benchmark authorities.
- `SemiconductorOperationalRunbook` provides provider-neutral startup, stale-data, incident preservation, provider-failure, rollback, and evidence-capture procedures for all eight recipes.
- `SemiconductorPromotionDecision` is fail-closed: failed/corrupt evidence blocks; stale/missing/untraced evidence remains pending; only complete current traceable target evidence plus operational release readiness is promotable.

## Non-negotiable promotion rule

A waiver, manual assertion, source-level static certification, development fixture, historical browser result, or evidence captured by a different framework/runtime contract is never converted into target PASS. Missing target execution or legacy evidence identity stays PENDING; contradictory version evidence is BLOCKED.

## Authority stack

1. Wave 59 `DataSource` / `QueryStats`
2. Wave 60 `AnalysisContext` / `SelectionBus` / workspace persistence
3. Wave 61 semiconductor semantics/analytics
4. Wave 62 recipes
5. Wave 63 onboarding/variants/runtime
6. Wave 64 conformance/performance/runtime experience
7. Wave 65 provider SDK/setup/benchmark/evidence bundle
8. Wave 66 evidence aggregation, traceability, operational readiness and promotion decision
