# CHG-165 current-main validation

Identity: `nicegui-base-master-detail-mobile-context-rebase-fix-2`

## PASS

- Fresh base verified: `ca98dfbf70f9b0c3948785211a0e136b1cc01791` / tree `16afc20436f98937c4d8481c0e23fa12a9578f12`.
- Candidate is a clean sole-parent descendant of fresh base: `126b9b6185bd7a28fdbf550c079dab4011ab402d` / tree `f0ede69c117879211e793cd00852031a040151d`.
- Predecessor verified: `f8d8fbe91179dcfdfc32063c501b17f913901362` / tree `93f3d4e33f7e97313ac340aea12031b757571e0e`, sole parent old base `65f17e55ed3622cafcd603c925a98db9f55ff602`.
- R1 patch reapplied cleanly; base-to-candidate Product diff remains exactly the accepted 12-file surface.
- `python run_nicegui_base.py --check`: PASS.
- `nicegui-base runtime-contract`: PASS.
- `nicegui-base runtime-smoke --port 0`: PASS, all 23 canonical routes.
- `nicegui-base catalog-audit --format json`: PASS.
- Affected current-main scope: 128 passed, including CHG-165, CHG-163 theme isolation, overlay, table, layout, pattern, Workbench and UI/UX suites.
- Real Chromium for Testing, DPR1: desktop 1440x900, phone 390x844, narrow phone 320x800; 11 canonical screenshots captured.
- Browser contract: desktop inline composition, phone fixed full-viewport context, touch/Enter/Space selection, dialog semantics, focus trap/restoration, inert/aria-hidden background, Escape/Back close, scroll lock, zero horizontal overflow, singleton reopen, reduced-motion, forced-colors, explicit Dark/System-dark/Light and simultaneous theme isolation all PASS. Console/page/request error counts: zero.

## Pre-existing repository checks (not caused by this candidate)

- `PYTHONPATH=source python -m nicegui_base.validate .`: FAIL on historical `tools/verify_development_D6H2_browser.py:154` f-string syntax error; warnings include pre-existing direct-import/raw-task checks and the new contract test import.
- `PYTHONPATH=source python -m pytest -q tests`: 1 historical Wave35 token-string assertion failure; candidate does not touch `source/nicegui_base/workbench/app.py`.
- `cd source && PYTHONPATH=. python -m pytest -q`: 14 historical Python 3.11 StateKey/golden-template failures; no CHG-165 failure.
- `nicegui-base agent-check .` and `nicegui-base gate .`: FAIL on existing missing scaffold/config/release paths and the same historical syntax/runtime issues.

No source certification or release artifacts were changed to silence these unrelated checks.
