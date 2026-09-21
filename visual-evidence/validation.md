# CHG-163 targeted visual evidence

- Candidate: `955b90e80a1a675d2bb7c014620ed0697d573450`; tree `815d26a6755d54ff790686ea118a8a2a94f7fa55`; base `65f17e55ed3622cafcd603c925a98db9f55ff602`.
- Branch: `codex/nicegui-base-stable3-visualize-dark-theme-preservation-fix-1`; target: `/workbench/data`; browser: Chromium via Playwright.
- Canonical Workbench launch: `python run_nicegui_base.py --host 127.0.0.1 --port <ephemeral> --no-show`.

## Results

- Focused dark viewports: 4/4 PASS.
- Data & Tables matrix: 64/64 PASS.
- Copy code accessibility records: 64/64 PASS.
- Interaction smoke: PASS; issues=[]; console_errors=[]; page_errors=[].
- Focused checks require root `dataset.theme`, Quasar `q-dark`, page `body--dark`, chart `data-chart-theme`, settled table/chart readiness, and no visible white chart surface.
- Desktop and phone include dark→light→dark round-trip screenshots with final dark synchronization.

## Candidate scope

- Source change: shared visualization theme resolver and explicit renderer theme authority only.
- No generated evidence is present in the product work tree.
- This is target evidence, not a human visual-acceptance or atlas-promotion claim.
