# CHG-163 validation

- Candidate: `f86d201372c405e43359c8fde8d0106f9c7401c0`
- Tree: `16afc20436f98937c4d8481c0e23fa12a9578f12`
- Base: `65f17e55ed3622cafcd603c925a98db9f55ff602`
- R1 predecessor preserved as an ancestor: `955b90e80a1a675d2bb7c014620ed0697d573450`
- Browser capture: Chromium with four independent Playwright browser contexts; `browser-result.json` records all client/context roles and transitions.

## Source and runtime validation

- Targeted NiceGUI Base suite covering CHG-163, visualization lifecycle/options, analytical/Data Lab contracts, and Workbench regressions — PASS, 107 tests.
- `python run_nicegui_base.py --check` — PASS.
- `nicegui-base runtime-contract` — PASS.
- `nicegui-base runtime-smoke --port 0` — PASS.

## Browser validation

- Explicit client isolation — PASS. Client A remained Dark while Client B independently toggled Light → Dark → Light; A was remounted after B changes and remained Dark. A then toggled Dark → Light → Dark while B remained Light.
- System resolution — PASS. An independent System client with `prefers-color-scheme: dark` resolved page/body/chart to dark; the light-media System client resolved all three to light.
- Live media transition — PASS. Chromium emulation changed the dark System client dark → light → dark while the independent light System client remained light.
- Browser transitions — PASS, 17/17. Every record includes candidate/tree, client ID/role, requested and expected resolved theme, root/body/chart theme, viewport, readiness, and console/page/request error counts.
- All four browser clients — PASS, 0 console errors, 0 page errors, 0 failed requests.
- R1 dark viewport regressions — PASS: 1440x1000, 1024x900, 768x900, 390x844.
- Data & Tables matrix — PASS: 64/64.
- Copy-code accessibility — PASS: 64/64.
- Interaction smoke — PASS.

## Gate classification

`nicegui-base agent-check .` and `nicegui-base gate .` reported pre-existing repository/environment failures unrelated to this change: missing agent scaffold/version metadata, missing `nicegui_base.toml`/entrypoint, a pre-existing syntax error in `tools/verify_development_D6H2_browser.py`, and the gate's environment-level pytest import mismatch. No source certification/release artifacts were changed to silence those historical gates. The canonical launcher check, runtime contract, runtime smoke, targeted tests, and browser validation above are the executed evidence for this candidate.
