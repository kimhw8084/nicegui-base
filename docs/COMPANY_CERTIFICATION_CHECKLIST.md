# Company Runtime Certification Checklist — NiceGUI Base v3.0.0a8

Use this checklist after moving the production-gold-candidate wheel into the company environment. Do not modify framework internals during certification; record environment-specific adapters/configuration separately.

## 1. Install and seed OpenCode guidance

```bash
python -m pip install nicegui_base-3.0.0a8-py3-none-any.whl
nicegui-base-ai-init .
```

Confirm `nicegui_base.FRAMEWORK_VERSION == "3.0.0a8"` and the installed NiceGUI version is exactly `3.15.0`.

## 2. Offline/runtime doctor

```bash
nicegui-base-certify .
```

The NiceGUI runtime check must PASS in the company environment. Resolve every FAIL before application rollout.

## 3. Run the certification app and gallery

```bash
nicegui-base-cert-app
nicegui-base-gallery
```

Verify both Microsoft Edge and Google Chrome using the company-supported versions.

## 4. Visual and interaction matrix

Test light, dark and system theme modes; comfortable, compact and dense modes; desktop/laptop/tablet/phone widths; keyboard-only navigation; focus states; dialogs/drawers; filters; DataTable; charts; forms; state views; command palette; tree/viewers; and engineering compositions.

Check browser console/network logs for unexpected errors, failed assets, WebSocket reconnect loops or blocked resources.

## 5. Accessibility

Verify label/control relationships, `aria-describedby`, validation/error announcements, skip-to-main-content, visible focus, keyboard operation, dialog focus behavior, non-color state cues and adequate contrast. Run the company's preferred automated accessibility scanner if available.

## 6. Reverse proxy / base path / WebSocket

Certify the exact production topology:

- root-path or subpath routing;
- forwarded-header trust boundary;
- WebSocket upgrade and reconnect behavior;
- static SVG/CSS asset paths;
- session affinity if multiple NiceGUI instances are used;
- Redis/shared persistence when cross-instance state requires it.

Use one Uvicorn worker per NiceGUI process.

## 7. Authentication and authorization

Integrate the company identity adapter and verify:

- unauthenticated requests fail closed;
- identity headers cannot be spoofed outside the trusted proxy/assertion contract;
- role/permission checks happen server-side before protected data/content renders;
- logout/session expiry behavior;
- secure production cookie behavior;
- no secrets/tokens appear in logs or client-visible errors.

## 8. Production-data stress checks

Exercise representative large tables, server-side queries, linked charts, wafer/spatial maps, rapid filter changes, cancellation/stale-response handling, auto-refresh, file upload limits and long-running jobs.

For restart-survivable work, provide a company implementation of `DurableJobAdapter`; do not rely on `InProcessJobAdapter`.

## 9. Final signoff evidence

Capture:

- `nicegui-base-certify` output;
- browser/version matrix;
- visual regression/screenshots;
- accessibility report;
- proxy/WebSocket result;
- authentication/RBAC result;
- load/stress result;
- approved configuration values;
- deployed wheel SHA-256.

Only after these company-specific gates pass should the release be labeled **Company Production Gold**.


## Executable Gold promotion gate
After deploying through the real company proxy/auth path, run:

```bash
nicegui-base-gold-certify https://<company-host>/<base-path> \
  --root . \
  --auth-path /protected \
  --require-browser \
  --browser-name chrome --browser-name msedge \
  --screenshots ./cert-evidence/screenshots \
  --load --load-requests 500 --load-concurrency 25 \
  --evidence ./cert-evidence/GOLD_CERTIFICATION_EVIDENCE.json
```

Do not promote when the command exits nonzero or reports `Gold eligible: False`. Preserve the evidence JSON and SHA-256 sidecar with the release record.
