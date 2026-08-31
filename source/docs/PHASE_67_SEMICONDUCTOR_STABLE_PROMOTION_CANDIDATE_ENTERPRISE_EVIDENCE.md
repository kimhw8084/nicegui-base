# Wave 67 — Semiconductor Stable Promotion Candidate & Enterprise Target Evidence Assimilation

Wave 67 is an additive release-channel layer above the Wave 66 qualification and stable-promotion authorities. It does **not** create a second target-certification system and it never upgrades missing target evidence to PASS.

## Added contracts

- `EnterpriseTargetEvidenceSet` assimilates existing Wave 65 target-evidence bundles, Wave 66 provider qualification, operational-readiness reports, and the Wave 66 fail-closed promotion decision into one deterministic evidence-set identity.
- `StablePromotionCandidate` binds that evidence set to the stable release channel, target version, current framework identity, exact required NiceGUI runtime, and recorded operational rehearsals.
- `PromotionRehearsalReport` records promotion, rollback, incident, and evidence-capture rehearsal progress strictly against the canonical Wave 66 semiconductor operational runbook. Rehearsal status never changes target gate status.
- `PromotionCandidateGap` exposes actionable evidence, runtime-identity, traceability, operational-readiness, and rehearsal gaps.
- `package_stable_promotion_candidate(...)` creates a deterministic ZIP with candidate/evidence/qualification/decision/runbook/rehearsal/diagnostic JSON, a SHA-256 manifest, and only artifact bytes that still match their captured hashes.
- Archive entry names are sanitized so target-supplied artifact keys and paths cannot create unsafe traversal names.
- `nicegui-base promotion-candidate` assembles and optionally packages a candidate from actual target evidence.
- `nicegui-base promotion-rehearse` records provider-neutral runbook rehearsal state without claiming deployment or certification PASS.
- Generated semiconductor applications gain additive candidate assembly/package helpers in `services/release_evidence.py` while the existing `evaluate_stable_promotion(...)` helper remains intact.
- `SemiconductorPromotionCandidatePanel` exposes candidate status, evidence status, rehearsal count, gaps, and next actions without mutating evidence.

## Release-channel rule

A Wave 67 stable-channel candidate is `READY` only when:

1. the underlying Wave 66 promotion decision is `PROMOTABLE`; and
2. all required promotion/rollback/incident/evidence-capture rehearsals are recorded PASS for every qualified recipe.

A failed target gate or failed rehearsal makes the candidate `BLOCKED`. Missing/stale/untraced target evidence or missing/incomplete rehearsals makes it `PENDING`. Packaging is allowed for all three states so teams can hand off diagnostics, but packaging never changes the state.

## Authority stack

1. Wave 59 `DataSource` / query authority
2. Wave 60 `AnalysisContext` / `SelectionBus` / workspace persistence
3. Wave 61 semiconductor semantics and analytics
4. Wave 62 recipes
5. Wave 63 onboarding/variants/runtime
6. Wave 64 conformance/performance/runtime experience
7. Wave 65 provider SDK/benchmark/portable target evidence
8. Wave 66 qualification/traceability/operational readiness/stable-promotion decision
9. **Wave 67 enterprise evidence assimilation, release-channel candidate packaging, diagnostics, and operational rehearsal recording**

## Certification boundary

Current-source tests and package integrity can be certified in the build environment. Installed target NiceGUI 3.15.0, real server/WebSocket execution, approved company provider qualification, representative fab-scale company data, supported corporate browser/publisher path, human visual baseline, and stable 3.0.0 promotion remain PENDING unless actual target evidence is supplied and verified.
