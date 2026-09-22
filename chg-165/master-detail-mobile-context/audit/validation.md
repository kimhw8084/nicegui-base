# CHG-165 candidate validation

- Focused framework/layout/overlay/table/normalization suite: PASS, 116 passed.
- Runtime contract: PASS; NiceGUI 3.15.0; 48 factories and 1172 direct calls checked.
- Runtime smoke: PASS; health/readiness plus all 23 canonical routes returned 200.
- Catalog audit: PASS; 465 conforming catalog entries, no issues.
- Environment preflight: PASS (`python run_nicegui_base.py --check`).
- Compile and diff checks: PASS.
- Browser evidence: Chromium DPR1 at 1440x900, 390x844, and 320x800; desktop inline detail, phone dialog/context surface, keyboard/touch open, Escape/back close, focus restoration, inert background, reduced motion, forced colors, and no horizontal overflow verified.

Repository baseline notes: `nicegui-base agent-check .` and `nicegui-base gate .` remain blocked by the checkout's pre-existing missing application scaffold, missing app dependency pin/entrypoint, and the known D6H2 syntax error. The complete source suite also retains unrelated Python 3.11 `StateKey` generic-construction failures.
