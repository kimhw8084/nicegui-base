# Phase 11 — Gemma/OpenCode Construction Laws

1. **Pattern before layout; layout before component; component before customization.**
2. **Inspect before invent.** Registered APIs/source are authoritative; generated names or parameters are forbidden.
3. **Framework internals are stable application dependencies.** Normal app work does not modify `nicegui_base/`.
4. **Raw NiceGUI is an escape hatch.** Normal page/control/layout code uses NiceGUI Base public APIs.
5. **Raw AG Grid and ECharts are prohibited in application code.** Use the Phase 5/6 abstractions.
6. **Visual decisions are semantic.** App code does not choose arbitrary colors, pixel spacing, radius, shadows, icon files or motion.
7. **Canonical assets only.** Use `Icons.*`/`Illustrations.*`; standard UI resources remain local/offline.
8. **Data access is layered.** SQL/API integration belongs in repositories/services, not UI pages.
9. **State and async behavior use framework primitives.** Direct storage, ad-hoc debounce/cancellation and custom refresh loops are prohibited by default.
10. **Security remains server-side and fail closed.** UI visibility is never authorization.
11. **Engineering evidence semantics are preserved.** Commonality is not causality; confidence is not a probability unless calibrated.
12. **Generated code must pass `nicegui-base-validate`.** Errors require correction; warnings require correction or a narrow documented exemption.
13. **Escape hatches are local and evidence-based.** `# nicegui-base: allow-aiNNN` applies only to the intentional line/rule.
14. **Reusable gaps become framework candidates.** Do not copy a custom workaround into multiple apps.
15. **Agent materials travel with the wheel.** New workspaces can be initialized with `nicegui-base-ai-init` so OpenCode always has the governing contract.
