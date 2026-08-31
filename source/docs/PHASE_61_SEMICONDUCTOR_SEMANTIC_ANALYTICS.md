# Phase 61 — Semiconductor Semantic Platform + Engineering Analytics Library

Wave 61 extends the Wave 59 production-data platform and Wave 60 unified-analysis authority with a typed semiconductor domain model, governed manufacturing context, rendering-independent engineering calculations, reusable visualization plans, and machine-readable workflow guidance. It does **not** add a parallel state, filtering, population, selection, persistence, or layout architecture, and it adds no mandatory numerical dependency.

## Delivered scope

### 61A — Canonical semiconductor semantics

`nicegui_base.semiconductor` now exposes 37 typed entity kinds covering fab/equipment, technology/product/process, lot/wafer/die, metrology/inspection/yield, SPC, FDC, maintenance/change, and excursion/investigation. Important genealogy is explicit through typed identifier fields instead of opaque metadata. Required relationships and finite numerical fields fail fast when invalid.

### 61B — Shared manufacturing context

`SemiconductorAnalysisContext` is a facade over the existing Wave 60 `AnalysisContext`. Product → Route → Operation, Area → Tool → Chamber, Lot → Wafer, and Recipe → RecipeVersion dependencies are governed atomically. `ManufacturingFilterController` resolves options through Wave 59 `DataSource.distinct()` while preserving unrelated AnalysisContext filters, search, and time context. `set_many()` is dependency-order independent. Affected/control/baseline populations remain Wave 60 `PopulationDefinition` authorities.

### 61C — SPC and capability

Implemented rendering-independent I-MR, Xbar-R, Xbar-S, p, np, c, u, EWMA, and CUSUM calculations. I-MR includes its moving-range companion, covering the requested ten chart surfaces. Western Electric and Nelson rule detectors are directly testable. Control limits, excluded points, baseline/limit-version metadata, event overlays, dynamic EWMA violations, and variable-opportunity p/u standardization are supported. Capability includes Cp/Cpk/Pp/Ppk, histogram, QQ, ECDF, box summary, density/violin/ridge-ready distributions, and affected/control comparison. Malformed subgroup/count/specification and nonfinite inputs fail explicitly.

### 61D — Wafer/spatial

Thirteen registered wafer surfaces cover continuous, categorical/bin, defect, delta, comparison, lot strip, synchronized small multiples, contour/surface, radial, center-edge, ring, sector, and defect-cluster analysis. Numerical transforms reuse existing certified wafer renderer contracts and shared selection/context behavior.

### 61E — FDC/equipment

Twelve registered FDC surfaces cover recipe-step trace alignment, golden envelopes, multi-sensor views, tool/chamber comparison, chamber/sensor fingerprints, alarm/event overlays, PCA scores/loadings, Hotelling T², and SPE/Q. Numerical analytics are independent of rendering and validate trace alignment and finite feature matrices explicitly.

### 61F — RCA/commonality

Eleven registered RCA surfaces cover affected/control comparison, enrichment, commonality ranking/matrix, contribution waterfall, correlation/evidence matrices, genealogy graph, cause tree, logical fault tree, and Sankey/process flow. Sankey weights preserve repeated genealogy paths; commonality remains prioritization evidence rather than causal proof.

### 61G — Yield/reliability/DOE

Seven registered surfaces cover yield/bin Pareto, yield decomposition waterfall, right-censored Weibull analysis, DOE main effects, interaction plots, and serializable quadratic response-surface results. Invalid/nonfinite observational inputs and singular response-surface designs fail explicitly.

### 61H — Unified visualization contract

`SemiconductorAnalyticalSurface` binds every registered domain surface to the existing `AnalysisContext`, `SelectionBus`, and `AnalyticalPanelController` lifecycle. `SemiconductorAnalyticalPanel` is the NiceGUI shell adapter over the existing Wave 60 `AnalyticalPanel`; it supports that panel's standard actions when callbacks are supplied rather than creating a semiconductor-only toolbar. Semiconductor visual-plan helpers reuse the certified chart grammar for SPC, capability/distributions, FDC, PCA, RCA/commonality, and Pareto work. Existing chart export now includes copy-CSV support.

### 61I — Framework intelligence and examples

The framework catalog contains 58 semiconductor surface definitions with positive `use_when` and non-empty `avoid_when` guidance. Agent routing recognizes semiconductor drift, wafer-change, PM/FDC, and RCA/commonality intents. Three executable integrated examples use one shared AnalysisContext/SelectionBus across calculations, surfaces, visual plans, records, and populations:

- `examples/phase61_spc_wafer_investigation.py`
- `examples/phase61_fdc_tool_health.py`
- `examples/phase61_rca_commonality.py`

## Verified source gates

The final Wave 61 evidence is generated from the current source, not copied from Wave 60:

- 825 collected tests across 121 test files: PASS in eight independently launched fresh pytest batches.
- Dedicated Wave 61 behavioral tests: 40/40 PASS.
- Governance: 0 errors / 0 warnings.
- Shipped examples validator: 0 errors / 0 warnings across 25 example files.
- Compile/static source certification: 12 PASS / 1 expected NiceGUI-unavailable warning / 0 FAIL.
- Existing visual integration coverage: 183/183.
- Public root API: 1,043 entries versus Wave 60's 902, with zero removals.
- Semiconductor registry: 58 surfaces — 9 SPC, 6 capability, 13 wafer, 12 FDC, 11 RCA, 3 yield, 1 reliability, 3 DOE.

Target NiceGUI runtime, real server/WebSocket, supported corporate-browser, company data-source adapter, and human visual-baseline certification remain **PENDING** because this environment cannot genuinely execute those gates. Historical browser artifacts are retained only as historical/stale evidence and are not a Wave 61 PASS claim.

## Wave 62 continuation

The approved next phase is the semiconductor application recipe factory: compose complete applications such as `SPCMonitor`, `ExcursionDefenseLine`, `FdcToolHealth`, `LotWaferExplorer`, `YieldLoss`, `PMEffectAnalysis`, `ChamberMatching`, and `RcaCockpit` from the Wave 59–61 authorities, with intelligent default layouts, components, filters, interactions, and semantic data bindings rather than new parallel application infrastructure.
