# NiceGUI Base v1.7 — Phase 5 Analytical Visualization

Phase 5 defines the analytical interaction and semiconductor-native visualization contract.

## Analytical interaction

- Applicable Cartesian ECharts use two explicit `inside` dataZoom domains: X and Y.
- Wheel/trackpad zoom changes both analytical domains directly; drag pans both domains.
- The Company chart toolbar exposes `View range` with Both / X / Y zoom-out, fit and zoom-in controls. Axis-specific manipulation never depends on a hidden modifier gesture.
- Toolbar range changes read the live ECharts `getOption()` state first, so explicit controls continue from the user's current wheel/drag view instead of stale Python percentages.
- Single-series legends are suppressed. Multi-series legends remain in a reserved top-right legend zone.
- Plotly escape-hatch panels enable scroll zoom by default while keeping the Plotly mode bar hidden.

## Heatmap scale

ECharts `visualMap` still performs numeric-to-color mapping but its floating UI is hidden. NiceGUI Base renders the visible scale in a dedicated band below the plot. This isolates the scale from ECharts cursors/tooltips and prevents the color bar from landing inside the x-axis or hover region.

## Exact spatial containment

Wafer and spatial renderers now use SVG clip paths created from the exact same circle or 14px rounded rectangle used for the visible boundary. Die/cell rectangles can no longer extend beyond the boundary. The outer viewport also clips at the canonical 14px Company surface radius.

Spatial pan is bounded to the zoomed content rather than allowing the visual to be dragged away indefinitely. Double-click resets the view.

## Semiconductor-native renderers

### ChamberFingerprintMatrix
A normalized chamber/process fingerprint matrix for comparing chamber signatures across process signals such as CD delta, pressure, RF bias, PM age and OOS rate. It uses a shared quantitative scale and exact cell hover values.

### CommonalityMatrix
An RCA-specific affected/control/baseline enrichment surface. Rows represent candidate factors; columns represent populations; cell intensity and percentage encode commonality without generic dashboard chart chrome.

## Certification

The `/charts` browser smoke now verifies:

- toolbar zoom changes both X and Y domains;
- explicit Y-axis range control changes the Y domain;
- wheel interaction changes the 2D data window;
- heatmap scale band exists below, not over, the plot;
- wafer die groups have boundary clip paths;
- fingerprint and commonality renderers are present.
