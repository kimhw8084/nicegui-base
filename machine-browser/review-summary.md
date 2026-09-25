# CHG-100 current-main browser/UI verification — machine review summary

**Run:** `stable3-browser-ui-current-main-refresh-2` · Fabric job `CF-a25508c618dbb510eb6c7d1f`  
**Candidate:** `7b126d431215e8aac038bd5935d39d118a1ea68b` · tree `d8b510a85f7767bb8d67dba3f0e2b1d44f8fc87b`  
**Aggregate:** `CURRENT_MAIN_MACHINE_BROWSER_PRODUCT_FAIL`  
**Scope:** fresh E1 machine/browser evidence for this exact current-main tree, plus E2-ready screenshots. This run establishes no accountable-human acceptance, no authentic browser-chrome 200% zoom, no CHG-59 work-computer runtime qualification, and no stable-release or publication readiness.

## Scenario results

| Scenario | Result | Evidence summary |
|---|---|---|
| `CURRENT_MAIN_SHARED_GALLERIES` | PASS | `/components`, `/analytics`, `/recipes`; desktop 1440×900 and mobile 390×844; one Search/refinement authority and responsive disclosure contract; no overflow or decisive browser/network errors. |
| `CURRENT_MAIN_PATTERNS_IDENTITY` | PASS | `/patterns` retains its distinct unified chooser, selected-pattern and live-example controls; no shared-gallery Search/refinement markers; no overflow or decisive errors. |
| `CURRENT_MAIN_COMPONENTS_WORKFLOW` | FAIL | Known match, Family, Favorites, return context and clear-to-all work on desktop/mobile. The visible query `zzzz-no-such-component-2026` leaves all 34 cards visible on both sizes and produces no truthful empty state. |
| `CURRENT_MAIN_DATA_EXPLORER` | PASS | Selected record and detail stay coherent when retained by a filter; removing it clears selection/detail without substitution; clearing filters recovers valid state; keyboard focus path is visible and unobscured. |
| `CURRENT_MAIN_SELECT_OVERLAY` | FAIL | Keyboard open, arrow navigation/selection, Escape close and focus return work on desktop/mobile. Mobile popup fits. On desktop its box is y=775.578…909.578 in a 900 px viewport (9.578 px past the bottom) and overlaps the opener. The focused control has a visible 3 px wrapper outline and focus shadow; focus center remains unobscured. |
| `CURRENT_MAIN_MOBILE_SHELL` | PASS | `/components` and `/analytics`: one named visible opener; dialog/layer state, Escape and Close navigation return behavior pass. |
| `CURRENT_MAIN_BREAKPOINT_FOCUS_RECOVERY` | FAIL | Starting with keyboard focus on Family, resize to mobile moves focus to the operable Refine summary. Returning to desktop opens the refinement but drops focus to `BODY`. |
| `CURRENT_MAIN_THEME_MOTION_SMOKE` | PASS | Fresh explicit Light, explicit Dark and System-dark (where configured), with reduced motion, on `/analytics/spc_i_mr`, `/analytics/capability_histogram`, `/components` and `/patterns`. Chart figure/title/description/axis/theme metadata is present and coherent; dark chart pixels have no white/mixed canvas. Captured SPC pixels visibly contain readable UCL, Center and LCL labels and axis captions. |
| `CURRENT_MAIN_BUTTON_ACCESSIBILITY_ENVELOPE` | PASS | No unnamed visible button/action across six routes at desktop/mobile; route authority counts and overflow checks pass. |

All executed browser samples had zero console errors, zero page errors, zero failed requests, zero bad HTTP responses and zero failed essential requests. Screenshot count: **55**. See `scenario-matrix.json`, `console-network.json`, `focus-accessibility.json` and `screenshots/` for route evidence.

## Objective findings for triage

- **P0: none established.**
- **P1 — gallery search stale results:** on both desktop and mobile the Search input contains the no-match query, but all 34 cards remain and no empty state appears. This blocks the expected no-match discovery task and reports stale content as current results.
- **P2 — desktop Select popup clipping/overlap:** the real popup extends 9.578 px below the viewport and covers the lower portion of its controlling field. Keyboard selection and Escape recovery still operate; mobile placement passes.
- **P2 — breakpoint focus restoration:** returning from the mobile breakpoint leaves keyboard focus on `BODY` rather than restoring an operable desktop refinement control.

No Product source was changed and no fix was attempted in this VERIFY.

## Regression and repository checks

- `git diff --check`: PASS.
- Cleanup: terminated only job-owned PID `98628` after matching its exact argv; confirmed PID absent and `127.0.0.1:63420` closed. Final work branch remains clean at the exact current-main SHA/tree, 0 ahead / 0 behind `origin/main`.
- `python run_nicegui_base.py --check`: PASS; NiceGUI Base `3.0.0a8`, `nicegui==3.15.0`, Python `3.11.7`.
- Focused Explorer/overlay/theme/visualization/accessibility tests: **105 passed**, 0 failed, 0 skipped.
- `nicegui-base runtime-contract`: PASS; 48 factories / 1172 direct calls checked.
- The additional `tests/test_wave35_theme_persistence.py` source-text assertion fails because it expects the exact substring `requested==='system'`. The real browser Light/Dark/System-dark theme smoke passed. No source was changed.
- `nicegui-base agent-check .`: FAIL on this unchanged candidate: missing local agent scaffold/version metadata, one Python syntax error in `tools/verify_development_D6H2_browser.py:154`, and 56 warnings.
- `nicegui-base gate .`: FAIL on this unchanged candidate: missing `nicegui_base.toml`, self dependency pin and entrypoint/build page; same Python syntax error and theme source-text test failure. See `checks/` for logs. These repo setup/gate failures are separate from the browser findings.
- R3 canonical framework evidence `9120663ae2bfbd0d4f78805785ce22b7e6cfce10` is reused only because its accepted CHG-203 tree equals this exact current-main tree. It was not rerun. CHG-203 artifact `cfb4ffaf90df47bb830ceb358e79a1fefe798d3c` is sole-parented to `072252a637ca201baf911696a2eb22044ae0a6f0`; 32/32 declared image hashes verified. It supports Dark-theme breadth only.

## Remaining gates

1. Authentic browser-chrome 200% zoom/reflow: **PENDING / NOT EXECUTED**. This ordinary Fabric run did not invoke or simulate zoom.
2. Accountable E3 human visual acceptance: **PENDING**. `../human-review/` contains unfilled instructions and a receipt template only.
3. CHG-59 work-computer runtime/server qualification: **DOWNSTREAM** and not performed here.

The result is limited to current-main E1 browser evidence and supporting screenshots. It does not establish company data/provider, scale, deployment/operations, stable 3.0.0, or publication readiness.
