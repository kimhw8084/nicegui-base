# Phase 57 — Canonical Switch Endpoint Correction

Phase 56's zero-horizontal-inset experiment is superseded. The golden switch now uses one deterministic Company-owned DOM/CSS contract: a 51×31 track, a 27×27 real thumb, 2px containment on every edge, and 20px horizontal travel. OFF and disabled-OFF seat at the left endpoint; ON and disabled-ON seat at the right endpoint. Disabling a switch changes appearance only, never geometry.

The implementation no longer uses a switch pseudo-element or legacy Quasar `q-toggle` styling. `Switch` renders `.cui-switch-track > .cui-switch-thumb`; the only authoritative geometry block lives in `nicegui_base/design/hardening_css.py`. Raw NiceGUI switch/toggle construction is now covered by the application validator.

Verification completed in this build environment: 713/713 pytest regressions pass, governance reports zero findings, compileall passes, and Chromium static geometry measurements at DPR 1 and 2 exactly match OFF `[2,22,2,2]` and ON `[22,2,2,2]` left/right/top/bottom gaps. See `evidence/browser_uiux/a8_switch_endpoint_fix.png`.
