# Phase 65 — Semiconductor Provider SDK, Onboarding Wizard & Release-Candidate Operationalization

Wave 65 extends the Wave 64 production contracts with provider-developer tooling and release-candidate workflow composition. The authoritative query/state/runtime layers remain Wave 59–64.

## Added

- provider-neutral SDK base and manifest;
- development/production conformance profiles and fixture suites;
- provider adapter starter and `provider-check` CLI;
- actionable conformance remediation guidance;
- first-class guided recipe setup workflow and NiceGUI setup wizard;
- recipe-specific operational guardrails and configuration review;
- bounded `development-smoke` and representative `provider-rc` benchmark profiles;
- portable target-evidence bundles with environment fingerprint and hashed artifacts;
- generated recipe-app provider fixtures, guided setup hooks, benchmark config and release-evidence helper.

## Non-negotiable boundaries

No provider-specific company infrastructure is assumed. No benchmark performs a full-source enumeration. Development fixtures cannot masquerade as representative production evidence. Missing target browser/runtime/human execution remains `PENDING`.
