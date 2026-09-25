# CHG-100 current-main machine/browser review summary

- **Machine result:** `CURRENT_MAIN_MACHINE_BROWSER_PRODUCT_FAIL`
- **Project/change/request/job:** nicegui-base / CHG-100 / `stable3-browser-ui-current-main-refresh-3` / `CF-16d31d92c36bf4edd1cc6d79`
- **Exact source/base:** `8024c21adad310881d6f3bbc04b00da1f4f03d31`, tree `fcc6294ba8f7c36b68b88a217e65b7efb3050393`
- **Runtime/browser:** NiceGUI Base 3.0.0a8, `nicegui==3.15.0`, Python 3.11.7, installed Google Chrome 153.0.8010.54 through Playwright; 1440×900 desktop and 390×844 mobile contexts, DPR 1, reduced motion.
- **Scenario result:** scenarios 1–6, 8, and 9 PASS. Scenario 7 `CURRENT_MAIN_BREAKPOINT_FOCUS_RECOVERY` FAILS its extra disabled-Family fallback viewport-containment assertion. Scenario 10 aggregate FAIL. See `scenario-matrix.json` for machine detail.

## Three repaired CHG-100 failure classes

1. **Components no-match Search — PASS on exact current main.** `zzzz-no-such-component-2026` yields zero governed cards and one visible `role=status` / `aria-live=polite` no-results message. Search text, persisted ExplorerState query, and result projection agree on desktop and mobile; known match, clear, Family, Favorites, and return-context flows pass.
2. **Select popup viewport geometry — PASS on exact current main.** Keyboard/pointer interactions pass. Popup remains inside the viewport, adjacent to the controlling field, and without material opener overlap at 1440×900, 1440×700, 1024×768, 390×844, and the top-edge sanity state; listbox internal scrolling keeps the last option reachable. Per-state rects, max-height, scrolling, and hit test are in the scenario matrix.
3. **Explorer breakpoint focus continuity — PARTIAL / acceptance FAIL.** Three desktop→mobile→desktop cycles pass: mobile focus goes to the visible operable Refine summary, desktop restoration returns to Family in-frame with visible focus, and external Search focus/scroll is preserved. In the additional disabled-Family fallback, focus moves to Favorites and its focus ring and center hit test are visible, but the active button rectangle ends at `y=900.484375` in a `1440×900` CSS viewport. This is a 0.484375 CSS-pixel bottom-edge miss. The explicit current-main acceptance requires the active target rect inside the viewport; the machine scenario therefore fails. The evidence does not show a blocked action or justify a P0/P1 classification.

## Objective findings and separate checks

- Browser routes had no decisive page/console errors or failed essential requests; route-level document overflow checks passed.
- No unresolved P0/P1 browser/UI defect was established. One precise focus-containment acceptance miss is recorded above; no material task-blocking consequence was observed.
- Focused tests: see `checks/focused-tests.xml`; 138 pass and one test-only theme source-string assertion fails (`test_wave35_theme_persistence.py::test_workbench_preserves_browser_theme_while_server_is_neutral`).
- `runtime-contract`, launcher preflight, `git diff --check`, and `runtime-smoke --port 0`: PASS. The runtime smoke is local package evidence and does not qualify CHG-59.
- `agent-check` / application `gate`: FAIL separately on missing application scaffold/dependency metadata and existing syntax error `tools/verify_development_D6H2_browser.py:154`; the gate path also reports a pytest `collections.Sequence` import failure. Full outputs are attached in `checks/`. These repository validation failures are not browser regressions.

## Claim boundary

This package contains current-main E1 machine/browser evidence and supporting screenshots only. It is not accountable human review, authentic Chrome 200% zoom/reflow, CHG-59 work-computer runtime/server qualification, company-provider/data or scale qualification, deployment/operations qualification, stable 3.0.0 readiness, or publication readiness. Human files are unfilled templates. Authentic browser zoom and accountable E3 visual acceptance remain PENDING.
