# Phase 15 Completion Report — v1.2.1 Gold Promotion Harness

## Purpose

Phase 15 does not redesign NiceGUI Base. It converts the remaining company-specific Production Gold boundary into an executable, auditable promotion gate.

## Added

- `nicegui-base-gold-certify` CLI.
- Live HTTP availability probe.
- Reverse-proxy/base-path preservation probe.
- Required response-security-header probe.
- `/healthz` liveness and `/readyz` readiness probes.
- Raw RFC WebSocket upgrade verification against the configurable NiceGUI Socket.IO path.
- Fail-closed unauthenticated protected-route probe.
- Authenticated protected-route probe when ephemeral request headers are supplied.
- Optional Playwright browser certification with explicit Chrome and Microsoft Edge channels.
- Desktop/tablet/phone browser viewports.
- Browser console error, uncaught page error, WebSocket creation and horizontal-overflow checks.
- Basic DOM accessibility smoke checks: main landmark, accessible interactive names, duplicate IDs, image alt text and keyboard focus.
- Optional screenshot evidence.
- Optional SSO Playwright storage-state injection without embedding storage contents into evidence.
- Bounded HTTP concurrency/load probe with success-rate, p50, p95 and maximum latency.
- Redacted JSON certification evidence plus SHA-256 sidecar.
- Fail-closed Gold eligibility rule: any required failure or required skip prevents promotion.
- `GOLD_PROMOTION_HARNESS.md` embedded in the wheel and AI workspace scaffold.
- Gemma/OpenCode certification construction guidance and Gold-promotion laws.

## Verification

- 420/420 automated tests pass.
- New certification probes are unit-tested against controlled local HTTP and WebSocket servers.
- Full Python compilation passes.
- Certification app and component gallery retain 0 static validator errors / 0 warnings.
- Offline framework certification remains 8 PASS / 1 expected live-runtime warning / 0 FAIL in this sandbox.
- Exact live NiceGUI/browser/company infrastructure certification remains intentionally external and is now executable through the new harness.

## Promotion rule

Do not relabel the package as Company Production Gold until the real deployed company URL is tested with required browser and authentication probes and the harness reports `Gold eligible: True`.
