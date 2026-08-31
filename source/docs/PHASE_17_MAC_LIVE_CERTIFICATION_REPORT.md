# Phase 17 — Mac Live Certification Completion Report

## Outcome

NiceGUI Base v1.4.0 packages the framework as a real Mac acceptance product rather than a static showcase.

### Live laboratory

- 22 real NiceGUI routes
- 10 canonical reference applications
- deterministic synthetic semiconductor/engineering data
- 178/178 public visual integration coverage
- 156 direct route instantiations
- 22 explicit composite internals
- theme, density and motion controls
- large-data, failure, engineering/RCA and certification laboratories

### Browser certification

The Mac harness performs Chrome/optional Edge route matrices, DOM stock-style leakage detection, accessibility smoke checks, console/page-error checks, responsive-overflow checks, WebSocket/health/readiness/load probes and screenshot regression.

### Human visual approval

A technical run does not approve design automatically. The user explicitly reviews screenshots and types `APPROVE` to create a SHA-256 locked visual baseline. Subsequent runs require the baseline and fail on meaningful drift.

### Artifact integrity

Final release packaging includes the installable wheel, certified source, Mac scripts, design/certification documentation, compatibility metadata, AI/OpenCode guides, SBOM, provenance and SHA-256 inventories.

### Remaining external boundary

The final Production Gold promotion still requires the actual company SSO/proxy/CSP/internal services and representative production load environment. Those are intentionally separate from the Mac UI/runtime acceptance gate.

## Final offline verification

- 440/440 automated tests pass.
- Python compilation passes.
- Certification app and component gallery: 0 errors / 0 warnings.
- Offline certification: 10 PASS / 1 intentional missing-live-runtime warning / 0 FAIL.
- Installed-wheel certification: 8 PASS / 1 intentional missing-live-runtime warning / 0 FAIL.
- Public root API index: 721 symbols.
- Combined NiceGUI Base CSS: 103,936 bytes.
- Public visual integration coverage: 178/178 (156 direct + 22 explicit composite internals).
