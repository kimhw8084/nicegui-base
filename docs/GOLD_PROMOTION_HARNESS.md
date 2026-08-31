# NiceGUI Base Gold Promotion Harness

This guide converts the final company-environment certification boundary into an executable, evidence-producing release gate.

## Goal

A release is **Gold-eligible** only when every required gate passes. Optional probes may be skipped without promotion failure; required probes may not.

## Canonical command

```bash
nicegui-base-gold-certify https://internal.example.com/my-app \
  --root . \
  --browser --require-browser \
  --browser-name chrome --browser-name msedge \
  --auth-path /protected \
  --screenshots ./cert-evidence/screenshots \
  --load --load-requests 500 --load-concurrency 25 \
  --load-max-p95-ms 750 \
  --evidence ./cert-evidence/GOLD_CERTIFICATION_EVIDENCE.json
```

If company authentication requires a trusted header for the certification account, inject it at runtime:

```bash
nicegui-base-gold-certify https://internal.example.com/my-app \
  --header 'Authorization=Bearer <ephemeral-token>' \
  --require-browser
```

Header **names** are recorded in evidence; header **values are never intentionally written**. Evidence is recursively secret-redacted before persistence and receives a SHA-256 sidecar.

## Required company gates

The harness verifies:

1. Offline NiceGUI Base framework certification.
2. Exact local NiceGUI runtime version unless explicitly waived.
3. Live application HTTP availability.
4. Reverse-proxy/base-path preservation.
5. Required security response headers.
6. `/healthz` liveness.
7. `/readyz` readiness.
8. Actual RFC WebSocket upgrade through the configured NiceGUI Socket.IO path.
9. Fail-closed unauthenticated protected-route behavior when `--auth-path` is configured.
10. Authenticated protected-route access when request headers are supplied.
11. Browser probes when `--require-browser` is used.
12. Optional bounded HTTP concurrency/load probe with success-rate and p95 thresholds.

NiceGUI 3.15 mounts Socket.IO under `/_nicegui_ws/socket.io`. When the application is served beneath a reverse-proxy prefix, the harness automatically prefixes the configured target URL path. Override `--websocket-path` only when the company gateway rewrites it differently.

## Browser probe

Browser automation is intentionally optional at package runtime. For final company Gold promotion, use `--require-browser` and explicitly certify the installed `chrome` and `msedge` channels. When Playwright is present, the harness tests configured browsers and desktop/tablet/phone viewports, recording:

- page-load status;
- browser console errors;
- uncaught page errors;
- detected WebSocket creation;
- horizontal overflow;
- presence of a main landmark;
- missing accessible names on interactive controls;
- duplicate DOM IDs;
- images missing `alt`;
- keyboard focus after a Tab-key smoke test;
- optional screenshots.

For browser-based SSO, `--browser-storage-state <path>` can use an ephemeral Playwright storage state. The storage-state contents are never embedded into certification evidence.

`--require-browser` turns missing browser automation or any browser failure into a promotion failure.

## Load probe

The built-in load probe is a bounded HTTP concurrency smoke/load gate, not a substitute for the company's full production performance system. It measures success rate, p50, p95 and maximum latency. Use a representative read-only endpoint or readiness-safe route.

## Promotion rule

Only promote **Production Gold Candidate → Company Production Gold** when:

```text
Gold eligible: True
```

and the resulting evidence JSON and SHA-256 sidecar are stored with the release artifacts/change record.
