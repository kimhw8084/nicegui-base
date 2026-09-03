# NiceGUI Base Workbench Iteration 2.11 — Access & Action Policy Closure

Baseline: `kimhw8084/nicegui-base main @ d8cb3672e38781ac84b295cf06e7f6a875c9e668`  
Framework: `nicegui-base 3.0.0a8`  
Production NiceGUI dependency: `nicegui==3.15.0`

## Why this iteration exists

Iteration 2.10 closed production data-provider/configuration/readiness integration. The next canonical gap was not another provider framework: NiceGUI Base already contains security and runtime authorities (`Principal`, `AccessPolicy`, `AuthorizationModel`, trusted-proxy/header authentication, `NiceGUIRuntimeAdapter.require_http()`, health checks, and permission-aware navigation), but Workbench-generated applications did not yet carry an explicit generated access/action policy contract or wire page routes through those authorities.

Iteration 2.11 closes that gap without inventing company identity infrastructure, roles, permissions, or write semantics.

## Implemented scope

- Added `nicegui_base.workbench.access_policy` as a Workbench generation layer over the existing canonical security/runtime authorities.
- Generated a signed `.nicegui_base/access_contract.json` alongside the existing data/interaction contracts.
- Generated `services/app_access.py` as the single generated access-policy binding surface.
- Preserved an open local-development path while making production access fail-closed/authenticated.
- Generated only the authentication adapter the framework truthfully supports today: trusted upstream identity headers through `HeaderAuthenticationAdapter` + `TrustedProxyPolicy`.
- Did **not** invent OIDC, SAML, company SSO, database roles, permission names, cloud identity, proxy topology, or vendor-specific auth behavior.
- Bound root and secondary generated pages through the same server-side `guarded_page(...)` / `NiceGUIRuntimeAdapter.require_http()` boundary.
- Added `require_action_access(...)` as the generated action-policy handoff point. Current generated actions remain local/view-state actions and inherit page access.
- Preserved the Iteration 2.9/2.10 production mutation rule: `provider_mutation_policy = none`.
- Added provider-neutral environment configuration for access mode, header names, and trusted proxy networks.
- Added `.env.example` references without serializing assertion-secret values.
- Added a critical `access-policy` runtime health check so invalid production access configuration makes readiness unhealthy rather than silently opening the application.
- Added safe access diagnostics: mode, provider, production-auth requirement, trusted-proxy count, whether an assertion secret is configured, permission-model boundary, and mutation policy. Secret values are not emitted.
- Surfaced the generated access/action policy in Builder Review, explicitly stating that company roles/permissions remain application configuration rather than generated guesses.
- Extended generated-project contract tests so generated ZIPs self-test their access contract and route guards.

## Security behavior

### Development

Default generated configuration is `NICEGUI_BASE_ACCESS_MODE=development`. Anonymous access remains allowed to preserve zero-friction local iteration and generated-app smoke testing.

### Production

`NICEGUI_BASE_ACCESS_MODE=production` makes page policies authenticated/fail-closed. The generated project configures the existing NiceGUI Base runtime authentication adapter and applies HTTP authorization before invoking the page builder.

The generated working provider is `header`, backed by the canonical trusted-proxy/header authentication adapter. Upstream identity infrastructure remains outside generated source and must be configured by the application/deployment owner.

### Roles, permissions, and writes

Iteration 2.11 intentionally does not manufacture company roles or permission names. `AuthorizationModel` remains the canonical authority and `require_action_access(...)` is the generated extension point for application-defined permissions. Current generated actions do not mutate the production provider and therefore inherit the page access policy.

## Regression fix found during implementation

A targeted runtime test found that an explicitly configured production access policy could be attached to a runtime while page guards still fell back to the generated module's development-default config. That would have made direct guard calls inconsistent with the configured runtime.

The fix binds the resolved `AccessConfig` to the runtime during `configure_runtime_access(...)`; page/action guards resolve that runtime-bound configuration when no explicit config is passed. The regression is covered by Iteration 2.11 tests.

## Verification in the ChatGPT sandbox

Dedicated Iteration 2.11 tests:

```text
6 passed
```

Focused cumulative regression surface (Iterations 2.8–2.11 plus security/runtime/diagnostics/data/performance/async authorities):

```text
103 passed
```

Generated project contract tests:

```text
single-page generated project: 4 passed
multi-page generated project:  5 passed
```

Generated static smoke:

```text
single-page: PASS, 19 Python files / 67 total files
multi-page:  PASS, 23 Python files / 72 total files
```

Behavior exercised by those checks includes:

- signed access-contract generation and tamper detection;
- interaction-action/access-contract alignment;
- no production-provider mutations;
- secret-sentinel exclusion from generated ZIP bytes;
- development anonymous behavior;
- production authenticated/fail-closed behavior;
- real trusted-header principal authentication from an allowed proxy;
- HTTP guard rejection of an anonymous production request;
- invalid production auth configuration -> unhealthy critical readiness result;
- safe diagnostics with assertion-secret values excluded;
- every generated multi-page route guarded by the same access authority.

## Broad-suite evidence boundary

A broad repository run reaches a pre-existing failure in:

`source/tests/test_nicegui_base_identity_migration.py::test_primary_identity_is_nicegui_base`

The test looks for `nicegui_base/release_authority.json` from the repository root rather than the repository's `source/` package root and raises `FileNotFoundError`. The same isolated test fails identically against the exact reconstructed Iteration 2.10 baseline `d8cb3672...`; therefore it is not attributed to Iteration 2.11.

The 103-test security/runtime/data/Workbench regression surface relevant to 2.11 is green. A full-suite PASS is not claimed.

## Runtime/browser evidence boundary

This sandbox validates generated source, contract behavior, canonical runtime/security behavior, generated project tests, and static generated ZIP smoke. It does not claim a live NiceGUI browser/HTTP PASS here when the local NiceGUI runtime/browser environment is unavailable. The apply guide contains the user-local `.venv` live generated-app smoke command, using absolute paths so the temporary generated project can launch the correct interpreter.

## Transactional package contract

The package helper:

1. verifies NiceGUI Base identity/version and the exact `nicegui==3.15.0` dependency;
2. requires Git HEAD `d8cb3672e38781ac84b295cf06e7f6a875c9e668` and a clean worktree when `.git` is present;
3. verifies SHA-256 anchors for every replaced baseline source authority;
4. verifies the patch's own manifest before copying any payload;
5. applies only the Iteration 2.11 source/test overlay;
6. rebuilds all three committed wheel mirrors offline from source and verifies wheel/source parity;
7. regenerates source/package SHA-256 manifests;
8. runs the focused regression gate when pytest is available;
9. performs generated ZIP smoke;
10. writes `WORKBENCH_ITERATION2_11_APPLY_RESULT.json` only after successful verification;
11. restores every managed file byte-for-byte if any apply/build/manifest/test stage raises an error.

GitHub is not modified by this package or by ChatGPT.
