# Phase 9 Completion Report — v0.10.0

## Scope completed

Phase 9 adds the reusable semiconductor/engineering semantic layer on top of the approved design, layout, component, table, visualization, visual-resource, and state/service foundations.

### Engineering entity system
- Typed entity vocabulary for fab, area, tool, chamber, lot, wafer, die, recipe, process step, route, parameter, measurement, defect, alarm, and investigation.
- Canonical operational status grammar: normal, watch, warning, critical, unknown, offline, maintenance, hold.
- `EngineeringEntityCardSpec` plus NiceGUI rendering adapter using packaged Phase 7 semantic SVG icons.

### Specification / process-control semantics
- `LimitBand` for lower/upper specification, target, and optional warning bands.
- `ControlLimits` for LCL/UCL/centerline.
- Canonical `evaluate_spec` returning missing, in-spec, near-limit, or OOS-low/high states.
- Reusable `SpecLimitIndicator` and `OutOfSpecIndicator` adapters.
- `ProcessTrendSpec` builds the approved Phase 6 control-chart grammar with specification and control-limit context.

### Baseline / population comparison
- `BaselineComparison` with delta, percent delta, direction, stable tolerance, and optional higher-is-better semantics.
- Population summaries with n, mean, median, stdev, min/max, p10/p90.
- Affected/control comparison with mean delta, mean ratio, and pooled standardized mean difference where valid.
- `DistributionComparisonSpec` uses common histogram bins for affected/control populations.
- `PopulationComparisonPanel` adapter.

### Commonality analysis
- Typed commonality categories and explicit interpretations (observed, routing, causal candidate, confounding, excluded).
- Affected/control exposure rate, rate difference, risk ratio, and weighted enrichment.
- Safe zero-denominator behavior.
- Ranking utility based on enrichment rather than raw affected overlap alone.
- `CommonalityTableSpec` + `CommonalityTable` using the Phase 5 DataTable.

### Evidence / RCA
- Typed evidence channels, directions, and strengths.
- Evidence items retain source, timestamp, metadata, strength, direction, and optional confidence.
- Evidence balance preserves supporting, contradicting, and neutral channels separately.
- Qualitative confidence model with percent display only when explicitly calibrated.
- `RcaHypothesis`, `RcaEvidencePanelSpec`, `RcaWorkspaceSpec`, hypothesis ranking utility, and NiceGUI `EvidenceCard` / `RcaEvidencePanel` adapters.
- `EngineeringTimeline` for chronological engineering events.

### AI discoverability
- `ENGINEERING_REGISTRY` documents 14 major engineering components/patterns with category, purpose, and when-to-use guidance.
- Public API exports make the domain layer source-discoverable to Gemma/OpenCode.
- `PHASE_9_ENGINEERING_LAWS.md` explicitly prohibits conflating commonality, evidence ranking, confidence, and causality.

## Verification
- 284/284 tests passing.
- All Phase 1–8 regression suites remain passing.
- Python source/tests/examples compile successfully.
- NiceGUI remains pinned to 3.15.0.
- No new external/CDN runtime dependency introduced.
- Phase 9 engineering CSS is installed automatically by the existing NiceGUI theme adapter.
- No Phase 9 HTML showcase generated, per approved faster review workflow.

## Runtime certification note
Exact NiceGUI/browser visual certification remains deferred to the later integrated certification phase because this sandbox does not provide the certified company NiceGUI/browser runtime.
