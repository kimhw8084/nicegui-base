# NiceGUI Base v1.6 — Linux-First Live Certification Guide

The live laboratory proves the actual NiceGUI 3.15.0 browser experience. It is not a static HTML showcase.

## Primary target

The primary work-environment target is Linux. The tooling is platform-neutral and also discovers Chrome/Chromium/Edge on macOS; Linux remains the parallel supported packaging path.

Requirements:

- Python 3.11, 3.12 or 3.13;
- NiceGUI 3.15.0 exactly;
- Playwright 1.62.0 exactly;
- Pillow 12.3.0 exactly;
- A normal browser for manual review; Chrome/Chromium (or supported Edge) is required only for automated browser certification;
- PyPI or an approved internal Python mirror, or a prepared wheelhouse.

## Recommended Linux workflow

```bash
./setup_linux.sh
./run_lab.sh
```

The application starts at `http://127.0.0.1:8080` by default. Setup and manual lab launch use `--no-require-browser`, so a failed Chrome/Chromium discovery does not prevent manual review.

The public CLI is:

```bash
nicegui-base doctor
nicegui-base lab
nicegui-base certify
nicegui-base approve-baseline
```

The historical `nicegui-base-mac-*` commands remain compatibility aliases only.

## What to review

The 22-route / 180-visual-integration laboratory includes Foundation, Shell Primitives, Controls, Forms/Overlays, DataTable, Charts, Content/Workflow, Engineering/RCA, State/Failure, Performance, Certification and all ten canonical reference applications.

Review light/dark/system theme, comfortable/compact/dense density, normal/reduced motion and desktop/tablet/phone widths.

## Automated certification

```bash
./certify_linux.sh
```

or directly:

```bash
nicegui-base certify --root ./source --output ./certification_output --baseline ./visual_baseline
```

The harness starts a temporary lab from the **installed wheel in a neutral working directory**, while the source tree is used only for offline/static certification. This prevents source imports from masquerading as installed-wheel evidence.

The browser matrix verifies runtime/HTTP/security headers, health/readiness, Socket.IO/WebSocket upgrade, bounded load, console/page errors, responsive overflow, accessible names, keyboard focus, stock-framework leakage, rendered geometry laws and deterministic screenshots.

## Human visual approval

The package deliberately ships with no approved baseline. After the first technical PASS, manually review the live app and every screenshot. Only if approved:

```bash
./approve_visual_baseline.sh
./certify_linux.sh
```

The approval command requires typing `APPROVE`. The exact screenshot set is SHA-256 locked. Subsequent certification fails on baseline tampering or meaningful visual drift.

## Company Gold boundary

Linux live certification proves the framework UI/runtime on that workstation/environment. Production Gold still requires the real company SSO/auth adapter, reverse proxy/base path/CSP/WebSocket behavior, shared persistence/session affinity where applicable, internal services/data and representative production load/failover.

## v1.6 rendered-product acceptance

The browser harness additionally measures full-width main-canvas/sidebar geometry, symmetric page gutters, minimum composition gaps, overlay viewport containment, field append containment and dialog alignment. Behavior smoke verifies sidebar collapse, density dimension changes, editable form fields, persistent drawer interaction, table row inspection, Command Palette navigation and chart zoom state. See `DESIGN_CONSTITUTION_V1_6.md`.
