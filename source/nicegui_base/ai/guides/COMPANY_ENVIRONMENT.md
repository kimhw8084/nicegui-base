# Company Environment Contract

## Certified intent

- Python: `>=3.11,<3.14` until company certification narrows this further.
- NiceGUI: exactly `3.15.0` for this framework milestone.
- Mandatory runtime assets: local package resources; no CDN dependency.
- Browser target: modern Chromium-family corporate browsers unless internal certification specifies more.
- NiceGUI process: one Uvicorn worker per process.
- Horizontal scale: multiple application instances, session-affinity/sticky routing, and shared persistence such as Redis when cross-instance state is required.
- Reverse proxy/base path: configure through Phase 10 `RuntimeConfig`; do not improvise forwarded-header trust.
- Authentication: use a framework authentication adapter; proxy identity requires the configured trust/assertion mechanism.
- Secrets: environment/secure runtime configuration, never source code.
- Data access: service/repository adapters; UI components do not depend on database technology.

## Workstation integration sequence

1. Install the supplied wheel into the approved Python environment.
2. Run the runtime doctor.
3. Confirm NiceGUI version and packaged visual assets.
4. Confirm reverse-proxy/WebSocket/base-path behavior in the actual company gateway.
5. Configure authentication adapter and permissions.
6. Wire application services/repositories.
7. Run `python -m nicegui_base.validate <app-root>`.
8. Run application tests/startup smoke test.
9. Run the later Certification App before declaring the environment certified.
