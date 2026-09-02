# NiceGUI Base Workbench Iteration 2.2 — Fastest App Assembly

Baseline: `e31fee28d22c5395708773224f6566b113c5c076`

## Delivered
- Persistent Workbench project state with current project, favorites, recents, queued Studio capabilities, and bounded development-data resume.
- Builder v2: Goal → Data → App Pattern → Page Composition → Review → Generate.
- Canonical 10-pattern selection directly from `PATTERN_REGISTRY`; real required/optional slots and responsive behavior are shown before component selection.
- Slot-based composition for analytics, tables, visualization primitives, and high-value common controls.
- “Add to current project” + Favorite on every Capability Studio.
- Direct command-palette “Add to Project” actions.
- Layout & Shell Studio using canonical pattern contracts and one-click “Use in Builder”.
- Home Resume/Favorites/Recents surfaces.
- Developer-readiness coverage matrix on Quality.
- Multi-capability generated starter with `.nicegui_base/workbench_project.json` composition manifest.
- Generated-app smoke gate before download: ZIP CRC, generator-owned required files, manifest contract, AST parse for every Python file, canonical import policy, `build_page`, and `LayoutSlot` proof.
- Regression suite `test_workbench_iteration2_2.py`.

## Design rule
Iteration 2.2 does not introduce a second layout/component truth source. Page structure comes from `nicegui_base.patterns.registry`; capability identity comes from the Workbench adapters over canonical registries; generated projects delegate the surrounding scaffold to `create_application`.

## Runtime gates added because static compile is insufficient
- Fresh-process Workbench route-registration smoke executes `register_workbench_pages(include_reference=False)` against the installed NiceGUI runtime.
- Fresh-process generated-app import smoke creates a real project with `create_application`, runs the generated ZIP contract, extracts `pages/home.py`, imports it against the public `nicegui_base` surface, and asserts `build_page`, generated `runtime`, and generated `main` are callable.
- Public-constructor signature matrix generates a page for every currently composable catalog entry and binds every direct `nicegui_base` constructor call with `inspect.signature`. This blocks syntactically valid but runtime-invalid call shapes.
- The patch is baseline-guarded to `e31fee28d22c5395708773224f6566b113c5c076` and restores touched source, wheel mirrors, and checksum manifests on failure.

## Corrections after failed pre-release packages
### Generator-owned project shape
An earlier package incorrectly required `pyproject.toml` in generated applications. The canonical `nicegui_base.ai.project.create_application(...)` generator does not emit that file. Required generated files are now derived from `CreatedApplication.written`, with only the Workbench-owned composition manifest added separately.

### macOS canonical temporary paths
macOS can expose the same temporary directory as both `/var/folders/...` and `/private/var/folders/...`. `Path.relative_to()` is lexical and therefore rejected a valid generated file. Iteration 2.2 now resolves both the generated application root and every `CreatedApplication.written` path before containment/relative-path calculation. A symlink-alias regression test reproduces the same class of path mismatch on non-macOS systems, and an escape test verifies that files outside the generated application root are still rejected.

### Persisted-state hardening
Malformed or stale persisted `revision`, theme, or density values now normalize safely instead of crashing Builder resume.

## Package-side verification performed before delivery
- Python compile of every Iteration 2.2 module, regression test, and apply helper.
- Synthetic end-to-end project generation using generator-owned resolved paths.
- Symlink/canonical-path alias regression: PASS.
- Generated-root escape rejection: PASS.
- Constructor signature validator accepts valid calls and rejects deliberately invalid calls.
- Malformed persisted Builder state normalization: PASS.
- ZIP CRC, duplicate-entry, path-safety, overlay-manifest integrity, and no-`__pycache__` checks are run on the final extracted archive.

Target-machine NiceGUI runtime, pytest, wheel rebuild, Workbench registration, generated-project import, and constructor-signature matrix are executed again by `apply_iteration2_2.py` before it can return PASS.
