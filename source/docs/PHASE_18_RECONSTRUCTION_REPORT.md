# Phase 18 — v1.5 Design-System Reconstruction Report

## Why reconstruction was necessary

Real browser review of v1.4 exposed systemic rendered defects: inconsistent radii, missing gaps/padding, text/container overflow, shell overlap, weak control alignment, nonfunctional density, insufficiently testable motion, default-looking buttons/fields, unusable DataTable examples, dated/broken charts, weak spatial visualization, compressed content/RCA layouts and a performance lab that did not visibly prove work.

The root cause was not missing component breadth. It was insufficiently strict composition and visual laws.

## Root causes found in source

- Reference-lab context helpers were entering NiceGUI containers incorrectly, corrupting parent composition.
- The lab stylesheet referenced nonexistent Company tokens, so browser CSS declarations silently dropped.
- Radius/spacing/control dimensions had drifted across multiple historical layers.
- Complex controls still carried local geometry rather than consuming one density/control contract.
- The previous browser audit checked stock visual leakage but not enough computed geometry.

## Reconstruction completed

- New design constitution: 10px controls, 14px surfaces, 18px overlays.
- New Apple-like neutral light/dark palettes with WCAG-safe tertiary text.
- Mandatory page gutters, surface padding, stack/cluster/section gaps and overflow containment.
- New public composition primitives for actions, forms, alerts, content and surface grids.
- Modern filled/soft/ghost/destructive button hierarchy with optical SVG centering.
- Unified field/control vertical alignment.
- Real Comfortable/Compact/Dense geometry.
- Testable motion/reduced-motion laboratory.
- Header/sidebar ownership of title, subtitle, greeting, settings, user menu and collapse geometry.
- DataTable fixes and density synchronization.
- Modern ECharts options, donut/heatmap repair and visible zoom/reset/fullscreen/export/data-view controls.
- Purpose-built SVG wafer and residual-field renderers with die cells, legends, hover and pan/zoom.
- Engineering/RCA investigation-cockpit composition.
- Visible 10k/100k performance generation, mounting, query timing and cancellation states.
- Browser geometry certification for overlap, overflow, gaps, clipping, icon centering, radius and density.
- Linux-first platform-neutral `doctor/lab/certify/approve-baseline` tooling.
- Framework + live-lab CSS token audit so showcase-only CSS can no longer bypass certification.

## Release philosophy

Phase 18 does not claim Production Gold from source evidence alone. Source/offline and clean-installed-wheel gates are necessary, while actual NiceGUI 3.15.0 browser execution and explicit visual-baseline approval remain required in the target Linux work environment.

## Final offline verification

- 453/453 automated tests pass.
- Python compilation passes.
- Certification app and component gallery static validation: 0 errors / 0 warnings.
- Source/offline certification: 11 PASS / 1 intentional missing-live-runtime warning / 0 FAIL.
- Combined NiceGUI Base CSS: 133,259 bytes with balanced braces.
- Framework + live-lab CSS: zero unresolved Company custom properties.
- Stock NiceGUI visual source paths: zero.
- 22 live routes, 10 canonical page patterns and 178/178 visual integration coverage.
- Stable public API index: 671 documented classes/functions/constants.
