# NiceGUI Base Workbench Iteration 2.3 — Runtime-Proven Golden Standard

Baseline: `f122e05b3679be6c140b1b64c8db7eda533a5682`

## Objective
Move NiceGUI Base from source-valid / generator-valid to a runtime-proven development standard while continuing to optimize team-member efficiency, consistency, fastest TAT, and reuse coverage.

## Delivered
- Capability Studio Interaction Inspector derived from real public constructor signatures, canonical pattern/recipe contracts, State Matrix availability, responsive proof surfaces, project composition support, and generated-code binding.
- Browser-only evidence is explicitly PENDING until executed; source metadata is never promoted to browser PASS.
- Data Dock rectangular Excel/TSV paste now targets the currently selected grid cell and grows rows as needed.
- One-click `Paste clipboard at selected cell` using the browser Clipboard API, with a textarea fallback for restricted clipboard environments.
- Layout & Shell Studio shows Desktop / Tablet / Phone behavior simultaneously and runs structural pattern-contract checks.
- Developer readiness expands from six checks to ten: discoverability, preview, sample data, guidance, code, project composition, Interaction Inspector, State Matrix, responsive proof, and public construction contract.
- Builder generated-app download is now two-layer gated: source/ZIP smoke first, then actual live startup proof in a fresh subprocess.
- `runtime_proof.py` provides bounded, cross-platform HTTP route proof with temporary port allocation, process cleanup, route timing, and bounded stdout/stderr diagnostics.
- Release/apply validation performs a real Workbench server smoke across Home, Build, Layouts, Data, a Capability Studio route, and Quality.
- Iteration 2.3 regression suite plus Iterations 1/2/2.1/2.2 regression suites run when pytest is available.

## Methodology retained
1. Exact committed GitHub HEAD is the only patch baseline.
2. Small transactional overlay/transform package; no direct GitHub mutation.
3. Existing canonical registries/generators remain the single authorities.
4. Every discovered failure becomes a permanent validation class.
5. Compile/AST checks are necessary but never considered runtime proof.
6. Public constructor signatures are bound against the real `nicegui_base` API.
7. Generated project shape follows the canonical generator rather than a duplicate hand-maintained model.
8. macOS/symlink paths are canonicalized before containment/relative-path checks.
9. Real server startup + HTTP route rendering is executed before release PASS.
10. Any apply failure restores every touched file/wheel/checksum from an in-memory backup map.

## Proof layers
- Source: automated.
- Generated ZIP/project shape: automated.
- Public API call signatures: automated.
- Fresh-process import: automated.
- Fresh-process server startup and route render: automated.
- Browser keyboard/focus/visual collision proof: remains explicit executed-browser evidence, not inferred source evidence.
- Human visual quality: remains explicit review evidence.
