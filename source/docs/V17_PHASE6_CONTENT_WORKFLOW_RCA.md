# NiceGUI Base v1.7 — Phase 6 Content, Workflow & RCA

Phase 6 turns content/workflow/RCA surfaces into deliberate investigation tools rather than generic information cards.

## Workflow progress

`ProgressSteps` now separates the connector rail from marker and copy. Each stage owns a fixed 30×30 marker on a dedicated rail, with the connector rendered behind it and labels below. Browser certification measures marker/glyph center deviation instead of relying only on screenshots.

## Evidence Image Viewer

`ImageViewer` is an inspection workspace, not a decorative image container. It exposes observable pan/zoom state through `data-cui-spatial-*` attributes and a visible percentage readout. Wheel zoom, button zoom, drag pan, double-click/reset, and Fit all share `CompanyUISpatial` state. The live lab uses a deterministic local wafer-residual SVG with a wafer clip path so the image is immediately testable without external assets.

## RCA identity and containment

`EngineeringEntityCard` now owns strict inner containment: the identity/header grid cannot overflow, property cells use bounded `minmax(0,1fr)` columns, every property cell contains layout/paint, and narrow cards collapse the metadata grid through container queries rather than leaking content across the rounded surface.

`InvestigationContextBar` is a new public RCA primitive. It keeps the investigation ID/hypothesis, owner, stage, and freshness visible above the detailed evidence hierarchy so users retain orientation while investigating.

## Release gates

Phase 6 browser acceptance fails if:

- workflow marker content is not optically centered;
- Image Viewer zoom does not change scale/readout;
- drag does not pan zoomed evidence;
- Fit does not restore 100%;
- the RCA context strip is missing;
- any engineering metadata cell escapes its containing entity card.
