# Golden UI v3 retrospective audit — CHG-203

## Decision

`V3_MATERIAL_FINDINGS_GIT_PUBLISHED_AWAITING_AUDIT` — one bounded machine-observed Product defect is established: `V3-203-001`, a shared explicit-Dark chart canvas mismatch affecting eleven evidenced analytics and recipe routes. This is an audit handoff, not self-acceptance or a UI fix.

## Identity and immutable input

- Project/request/operation: `nicegui-base` / `golden-ui-v3-retrospective-audit-1` / `VERIFY` (`CHG-203`).
- Fabric job / work branch: `CF-bdeeabc8ee0d28a48f7f4e93` / `codex/nicegui-base-golden-ui-v3-retrospective-audit-1`.
- Exact source/base: `1bc15bbb197245e8a6367de9161dc7f63001b71a`; tree `726617815ac1b06880ead6cb2f6fa6a39279049f`. No Product source changes, commits or changed Product files.
- Pixel input: promoted R16 artifact `1fd12d6477010c58cb477dd836d984c6b99e7bbf`, evidence `04e5753c67187d105597011415fbeb6745edfbe0`; manifest, bundle, reader PDFs and reader index hashes are recorded in `audit-manifest.json`.
- Inventory: 144 surfaces and 288 canonical screenshots (144 desktop 1440x900 + 144 mobile 390x844). Every canonical desktop/mobile PNG was inspected. 51 review contact sheets contain composites only; no R16 PNG, PDF or ZIP is copied.

## What was reviewed

The current construction manifest/catalog, approved v1.6 design constitution, task pattern guide, accessibility/state authorities, Workbench gallery, chart/table/pattern/overlay source authorities, and rendered R16 pixels. The 27 canonical sheets cover all 288 images. Fourteen existing diagnostic sheets cover desktop-constrained 1366x768, mobile-narrow 360x800, holdout 414x896, explicit/system dark and resize roundtrip profiles. Chart-kind and paired-theme diagnostics were also inspected. No browser, server, Playwright, or new screenshot capture was used.

The normal product identity reads as a restrained, dense engineering reference product. Navigation and gallery discovery are intent-first; named patterns, components, charts and recipe objects keep their task context visible. Desktop and mobile both preserve useful information hierarchy. No other material static pixel/task-truth defect was established.

## Material finding

R16's existing explicit-Dark diagnostics identify the requested theme as Dark, resolved theme as dark, the chart theme attribute as dark, and the shell as dark. In eleven analytics/recipe surfaces, the plot canvas is white. Each has a paired System-dark diagnostic whose chart canvas is dark. Five other explicit-Dark diagnostic routes also match dark and are listed as controls. Exact paths and SHA-256 values are in `findings.json` and `relationship-state-review.json`.

The shared boundary is the ChartPanel/theme renderer path (`nicegui_visualization.py`, `visualization/theme.py`, `visualization/options.py`) with Workbench theme propagation. The audit establishes the rendered defect but does not claim to have isolated the frontend mechanism. Recommended next step: one separate bounded FIX at the shared chart/theme boundary, verified against all eleven affected consumers and the five dark controls.

## Evidence debt and limits

Dynamic state ownership and real loading/empty/error/disabled transitions, complete keyboard/focus/Escape/Back/overlay and selection restoration, authentic 200% browser zoom, accountable human visual acceptance, screen-reader/AT, native/physical-device, CHG-59 work-computer qualification and measured user preference remain unproven or uncaptured as itemized in `evidence-debt.json`. CHG-100 authentic zoom remains NOT_EXECUTED because a safe/exclusive browser-chrome control path was unavailable. Agent pixel review is not human acceptance.

## Publication and source boundary

This package is the complete audit deliverable; R16 and AR-62 remain unchanged. The receipt binds exact source/R16 identities, counts, reviewed-image count, finding/debt counts and package hashes. The receipt file's own SHA-256 is bound by the separate native `.codex-fabric/audit.json` on the deterministic Fabric evidence ref and by the artifact commit, avoiding a self-referential hash field.
