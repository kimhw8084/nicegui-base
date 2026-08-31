# Phase 20 — Runtime Compatibility Hotfix Report

## Trigger

A real Linux work-environment run exposed `AttributeError: LeftDrawer object has no attribute close`. This proved that the previous release gate relied too heavily on static/synthetic construction and did not sufficiently verify the real pinned NiceGUI runtime API.

## Runtime defects corrected

- Mobile navigation now maps Company `open/close/toggle` to NiceGUI 3.15 `LeftDrawer.show/hide/toggle`.
- ECharts updates no longer assign to the read-only `EChart.options` property; NiceGUI Base mutates the existing options dictionary and calls `update()`.
- Native NiceGUI fullscreen `enter/toggle` calls are no longer incorrectly awaited.

## New mandatory gates

- tagged-source adapter contract scan;
- installed NiceGUI 3.15 reflection/signature contract;
- real browserless server smoke of `/healthz`, `/readyz`, and all 22 live routes;
- traceback/AttributeError/TypeError/RuntimeError/import/ASGI log scan.

Linux setup does not report `SETUP COMPLETE` until all three runtime layers pass.

## Source verification target

- 478 automated tests;
- 22 live routes;
- 180/180 public visual integrations;
- exact `nicegui==3.15.0` pin;
- 0 known-invalid adapter patterns.

Actual target-machine runtime smoke remains deliberately executed during setup because the build sandbox does not contain the NiceGUI dependency.
