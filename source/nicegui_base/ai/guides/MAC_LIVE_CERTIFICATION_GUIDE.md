# NiceGUI Base v1.6 — Legacy Mac Compatibility Certification Guide

This bundle exists to prove the **actual NiceGUI 3.15.0 browser experience**, not a static HTML approximation.

## Acceptance target

The target is not "NiceGUI with nicer CSS." NiceGUI/Quasar are runtime implementation details only. A successful review should look and behave like a polished NiceGUI Base product with no recognizable stock NiceGUI/Quasar personality.

The live lab contains **22 routes** and all ten canonical application patterns. Public visual integration coverage is **183/183**: **157 classes are directly instantiated by live route builders** and **26 are explicitly documented composite internals** (for example ChartPanel's toolbar/zoom/export helpers and DataTable's cell formatters/accessories). A new public visual class without direct use or an explicit composite ledger entry fails certification.

## Requirements on the Mac

- macOS on Apple Silicon or Intel
- Python **3.11, 3.12, or 3.13**
- Google Chrome installed in `/Applications/Google Chrome.app`
- Internet/package-index access for first-time Python dependency installation
- Microsoft Edge is optional unless you choose to require it

The bundle pins:

- `nicegui-base==1.7.2` — bundled wheel
- `nicegui==3.15.0`
- `playwright==1.62.0`
- `Pillow==12.3.0`

Playwright uses your installed Chrome/Edge channels; the setup does not download a separate Chromium browser.

## 1. First-time setup

From Terminal:

```bash
cd /path/to/nicegui_base_v1.7.2_live_certification
./setup_mac.sh
```

The setup script:

1. detects Intel vs Apple Silicon;
2. finds a supported Python;
3. creates an isolated `.venv`;
4. installs the bundled NiceGUI Base wheel plus exact Mac-certification dependencies;
5. verifies the exact NiceGUI version;
6. checks Chrome/optional Edge, assets, component coverage, compatibility metadata, disk space and port availability.

If dependency installation fails because the Mac cannot reach the Python package index, nothing is partially promoted; restore package-index access or use an approved internal Python mirror and rerun setup.

## 2. Run the real reference application

```bash
./run_lab.sh
```

The real NiceGUI application starts at:

```text
http://127.0.0.1:8080
```

Chrome opens automatically when installed.

### Review every route

The lab includes:

- Overview
- Foundation
- Standalone Shell Primitives
- Controls
- Forms & Overlays
- Enterprise DataTable
- Charts
- Content & Workflow
- Engineering & RCA
- State & Failure Lab
- Performance Lab
- Certification
- Dashboard reference app
- Data Explorer reference app
- Master/Detail reference app
- CRUD reference app
- Monitoring reference app
- Search reference app
- Settings reference app
- Wizard reference app
- Comparison reference app
- Analysis Workspace reference app

Use the global controls to change light/dark/system theme, comfortable/compact/dense density and reduced motion. Resize the real browser window as part of manual review.

### Visual acceptance checklist

Reject the build if you see any meaningful stock NiceGUI/Quasar styling, including default-looking:

- buttons, fields, selects, chips or choice controls;
- tabs, toggles, sliders, steppers, tree controls or expansion panels;
- dialogs, drawers, menus, tooltips or notifications;
- uploader, progress or spinner surfaces;
- AG Grid headers, rows, selection, menus, pagination or editors;
- Material iconography where Company SVG icons should appear.

Also inspect:

- typography hierarchy and long labels;
- surface hierarchy, borders, radius and elevation;
- focus-visible behavior and keyboard navigation;
- dark-mode parity;
- phone/tablet transformations;
- tables in selection/editing/server/master-detail states;
- chart toolbars, fullscreen/data/export actions and spatial charts;
- empty/loading/error/offline/permission/not-found states;
- deliberately ugly data, long identifiers and missing values.

## 3. Automated Mac certification

Stop a manually running lab, then execute:

```bash
./certify_mac.sh
```

For the larger browser/theme/viewport matrix:

```bash
./certify_mac.sh --exhaustive
```

The certification command launches a **temporary lab from the wheel installed in `.venv` from a neutral working directory**. The bundled source tree is used only for offline/static checks, preventing accidental source-tree imports from masquerading as wheel certification.

The suite checks:

- exact framework and NiceGUI versions;
- source/offline framework certification;
- HTTP and security headers;
- `/healthz` and `/readyz`;
- actual NiceGUI Socket.IO/WebSocket upgrade;
- bounded concurrent HTTP probes;
- all 22 live routes in the primary Chrome scenarios;
- Edge compatibility scenarios when available;
- console errors and page errors;
- horizontal overflow;
- main landmark presence;
- duplicate IDs;
- accessible names and image alt text;
- keyboard focus smoke;
- rendered-DOM stock NiceGUI/Quasar leakage;
- unapproved Material icons;
- route-specific interaction smoke tests;
- deterministic screenshots;
- approved visual-baseline drift once a baseline exists.

Evidence is written to `certification_output/`.

## 4. Human visual approval

The first certification intentionally has no approved visual baseline. Inspect the live app and every screenshot under:

```text
certification_output/screenshots/
```

Only if you approve the result:

```bash
./approve_visual_baseline.sh
```

You must type exactly:

```text
APPROVE
```

The approved screenshot set is copied to `visual_baseline/`, SHA-256 hashed and bound to browser-version evidence.

Then rerun:

```bash
./certify_mac.sh
```

With an approved baseline present, baseline verification becomes required. Missing, tampered or meaningfully drifted screenshots fail certification.

## 5. Resetting evidence

Clear only generated evidence:

```bash
./reset_lab.sh
```

Remove the approved baseline as well only when intentionally starting a new visual approval cycle:

```bash
./reset_lab.sh --including-baseline
```

## Promotion meaning

A technical browser PASS plus your explicit screenshot approval establishes **Mac Live Certification** for the exact NiceGUI Base wheel, NiceGUI version and browser baseline.

It does not substitute for company-environment certification of SSO, reverse proxy/base path, corporate CSP, Redis/session affinity, internal APIs/databases or representative production load. Those remain the final company Gold promotion gates.
