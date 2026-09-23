# CHG-177 candidate validation

Candidate: 4642e004f39a23a7e4f295c929aef05caeb68967  
Tree: 726617815ac1b06880ead6cb2f6fa6a39279049f  
Parent/base: 55307c22125df3ffeefe6210677e95e332732a8d (f0ede69c117879211e793cd00852031a040151d3)  
Work branch: codex/nicegui-base-stable3-chart-threshold-label-clip-fix-1

## PASS

- rtk env PYTHONPATH=source pytest -q source/tests/test_phase6_options.py source/tests/test_phase6_adapter_contract.py source/tests/test_visualization_final_integrity.py source/tests/test_visualization_micro_closure.py source/tests/test_chg163_visualization_theme.py source/tests/test_phase61_v300a8_semiconductor_platform.py — 101 passed.
- rtk env PYTHONPATH=source pytest -q source/tests/test_phase6_theme_palette.py source/tests/test_phase16_visual_normalization.py source/tests/test_phase25_v17_phase5_analytical_visualization.py source/tests/test_phase29_v171_visual_interaction_hotfix.py source/tests/test_phase43_v3_semantic_visualization_extensions.py source/tests/test_phase47_v300a1_browser_uiux_gate.py source/tests/test_phase54_v300a6_switch_visual_integrity.py source/tests/test_workbench_d6h_visual_reference.py source/tests/test_workbench_d6h1_visual_closure.py source/tests/test_workbench_d6h2_visual_closure.py — 61 passed.
- rtk python run_nicegui_base.py --check — PASS; NiceGUI 3.15.0, Python 3.11.7.
- rtk env PYTHONPATH=source nicegui-base runtime-contract — PASS; 48 factories and 1175 direct calls checked.
- rtk env PYTHONPATH=source nicegui-base runtime-smoke --port 0 --format json — PASS; health/ready plus all normal application routes returned HTTP 200 (23 routes total).
- Fresh candidate runtime: rtk python run_nicegui_base.py --port 49173; Chromium 151.0.7922.34, Playwright 1.62.0. All 14 final screenshot captures passed.
- /charts: 1440×900, 390×844, 1366×768, 360×800, 414×896. Full LSL and Target labels stay inside chart/plot bounds, do not collide, and do not clip at the host or page edge.
- /analytics/capability_histogram: desktop/mobile; LSL, Target and USL are horizontal, fully readable and anchored to vertical x-axis specification lines.
- /analytics/spc_i_mr: desktop/mobile, Individuals and Moving Range charts; real labels LCL, UCL, Center and MR center are fully readable and anchored to horizontal y-axis lines.
- Explicit Dark and System with dark media preference both resolve to dark and retain bounded, legible labels.
- The Reset chart toolbar action retained labels. Resizing desktop to mobile and back retained label geometry; page width stayed equal to viewport width. No browser/page errors or failed essential requests occurred.
- Screenshots are lossless PNG at the requested viewport sizes; each file SHA-256 and its host/grid/markLine/page geometry is recorded in manifest.json and browser-result.json.
- rtk git diff --check — PASS.

## Baseline gate failures (proven on the exact base)

- rtk env PYTHONPATH=source nicegui-base agent-check . --format json — FAIL: app scaffold/nicegui_base.toml absent; untouched tools/verify_development_D6H2_browser.py:154 has a Python f-string syntax error; 56 existing warnings.
- rtk env PYTHONPATH=source nicegui-base gate . --format json — FAIL: absent app manifest/dependency pin/entrypoint, the same untouched syntax error, and tests/test_wave35_theme_persistence.py::test_workbench_preserves_browser_theme_while_server_is_neutral.
- rtk env PYTHONPATH=source python -m nicegui_base.validate . — FAIL on the same untouched syntax error and 56 warnings.
- Exact-base proof used a detached checkout at base SHA 55307c22125df3ffeefe6210677e95e332732a8d, tree f0ede69c117879211e793cd00852031a040151d3:
  - rtk env PYTHONPATH=/tmp/chg177-baseline/source nicegui-base agent-check /tmp/chg177-baseline --format json reproduced the missing scaffold, same syntax error, and 56 warnings.
  - rtk env PYTHONPATH=/tmp/chg177-baseline/source nicegui-base gate /tmp/chg177-baseline --format json reproduced the same manifest/dependency/entrypoint/syntax failures and theme-persistence test failure.
  - rtk env PYTHONPATH=/tmp/chg177-baseline/source pytest -q /tmp/chg177-baseline/tests/test_wave35_theme_persistence.py reproduced the same single failing assertion.
- The chart-specific focused and existing browser/visual test sets pass on the candidate; these baseline gate findings are outside the two changed files.

## Evidence map

- visual-evidence/browser-result.json: per-capture browser result, options and canvas text geometry, viewport/page overflow, toolbar, errors, theme and interaction states.
- visual-evidence/manifest.json: hashes and provenance for before/after screenshots and interaction checks.
- visual-evidence/before/: clean exact-base /charts desktop/mobile screenshots.
- visual-evidence/: final candidate screenshots for all required chart panels, viewports and themes.
