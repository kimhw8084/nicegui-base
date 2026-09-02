# NiceGUI Base Workbench Iteration 2.5 — Project Memory & One-Click Release

Baseline: `95d92461c9b377ac3500adee8f02f236d3c312e2`

## Objective
Reduce the remaining engineering TAT between choosing a Golden Starter and carrying a reusable, recoverable, browser-testable project to another machine.

## Delivered
- Project storage schema v2 with in-place migration from the existing v1 state key.
- Bounded structural revision history (24 entries) that ignores revision-counter noise and deduplicates identical snapshots.
- Project diff summaries for field changes, capability add/remove/move, and development-row count changes.
- Named project presets (16 max) with save/apply/delete controls in Builder.
- Revision restore from Builder without introducing another project-state authority.
- One-click `Build & prove ZIP` on every Golden Starter: resolve canonical capabilities → audit → generate → static/signature smoke → fresh-process live startup → download.
- Generated `tools/browser_acceptance.py` in every current Workbench-generated app.
- Browser acceptance contract schema v2 with separate automated and manual checks plus the executable runner command.
- Playwright-based browser evidence runner for desktop/tablet/phone when a browser backend exists.
- Explicit `SKIPPED_BROWSER_BACKEND_UNAVAILABLE` evidence when Playwright or its browser executable is absent; backend absence never becomes a false PASS or a crash.
- Generated smoke validation requires the runner whenever a schema-v2 browser contract is present.

## Browser evidence policy
Runtime/HTTP proof remains distinct from browser proof. The generated browser runner records keyboard reachability, focus indication, document overflow, console/page errors, root-route response, primary-action keyboard reachability, and theme persistence. Pattern-specific visual judgments remain manual-pending rather than being promoted to automated PASS.

## Release gates
The Iteration 2.5 apply script requires the exact committed baseline and a clean worktree, compiles every overlay Python file, validates state migration/history/preset contracts, resolves and generates all 16 Golden Starters, verifies browser runner/contract presence in every generated ZIP, runs public-constructor signature checks through generation, executes the one-click release pipeline with real live startup for representative engineering and generic starters, live-probes the Workbench, runs Workbench regression tests when pytest is available, rebuilds all three wheel mirrors, and regenerates checksum manifests.

## Prior failure classes retained
- Runtime call-signature failures are caught by fresh-process registration and generated signature binding.
- Generated project shape follows the canonical generator rather than a duplicated hand-maintained project model.
- macOS `/var` vs `/private/var` path aliases are canonicalized before containment checks.
- Golden Starter capability selection uses canonical preferred identities and truthful generator adapters.
- Browser dependency partial-install state (Playwright importable but Chromium missing) returns an explicit unavailable status instead of raising.
