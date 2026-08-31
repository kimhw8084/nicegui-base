# Semiconductor Analytics Guide — Wave 61

Wave 61 is the specialist semiconductor layer over the Wave 59/60 platform. It is intentionally **not** a parallel application architecture: production data remains behind `DataSource`; shared analytical state remains in `AnalysisContext`; cross-filter/drill selection remains in `SelectionBus`; affected/control/baseline populations remain `PopulationDefinition`; analytical lifecycle remains in `AnalyticalPanelController`/`AnalyticalPanel`; and layout/persistence remain owned by the workspace runtime.

## Canonical semantic entities

`nicegui_base.semiconductor` provides typed fab/equipment, product/process, lot/wafer, metrology/inspection, SPC/FDC, maintenance/change, and excursion/investigation entities. Genealogy uses explicit identifiers such as `Area.fab_id`, `Chamber.tool_id`, `Operation.route_id`, `RecipeVersion.recipe_id`, `Wafer.lot_id`, `Measurement.wafer_id/tool_id/chamber_id/recipe_version_id`, and investigation/evidence links. Use `relationship_fields()` when tooling needs to discover relationships programmatically. Required genealogy and finite numerical values reject incomplete or nonfinite records instead of silently degrading to arbitrary strings.

## Shared manufacturing context and filters

Use `SemiconductorAnalysisContext(existing_analysis_context)`. Its selected dimensions are persisted in the existing AnalysisContext snapshot metadata and mirrored as ordinary query filters; restoring a Wave 60 workspace therefore restores semiconductor context without a second state store.

`ManufacturingFilterController` resolves dependent values through Wave 59 `DataSource.distinct()` with Product → Route → Operation, Area → Tool → Chamber, Lot → Wafer, and Recipe → RecipeVersion dependencies. Parent updates clear omitted descendants atomically, `set_many()` is keyword-order independent, and option queries preserve unrelated AnalysisContext filters, search, and time ranges. Filters owned by other controllers are not stolen even when they use the same field/value.

Affected, control, and baseline populations remain Wave 60 `PopulationDefinition` fields. Reuse these for capability comparisons, PM-effect analysis, RCA/commonality, and defense-line applications.

## SPC and capability

Rendering-independent functions are directly testable: `i_mr`, `xbar_r`, `xbar_s`, `p_chart`, `np_chart`, `c_chart`, `u_chart`, `ewma`, and `cusum`. I-MR includes its MR companion. Western Electric and Nelson rules are available through `detect_western_electric` and `detect_nelson`. Xbar rule evaluation uses subgroup-mean standard error, and p/u rules standardize against each point's sample size/opportunity. EWMA emits its own dynamic-limit violation markers.

Malformed subgroup members, unequal subgroup sizes, non-integer count data, invalid denominators, nonfinite targets/specifications, insufficient observations, and degenerate variance fail explicitly through `SPCInputError` rather than returning plausible-looking values.

`capability_indices` reports Cp/Cpk and Pp/Ppk. `capability_histogram`, `qq_points`, `ecdf`, `box_distribution`, `density_estimate`, and `ridge_distributions` provide numerical inputs for capability/distribution surfaces. Show the specification source/version and baseline period beside capability claims.

## Wafer and spatial

The spatial layer complements the existing certified `WaferMap`, `WaferComparisonMap`, and `RadialProfilePlot` renderers. It provides transforms for continuous/categorical/defect maps, delta wafers, comparisons, lot strips, synchronized small multiples, contour grids, radial profiles, center-edge decomposition, rings, sectors, and defect clusters. `WaferSample` is renderer-neutral. Emit wafer/die/spatial selections through the shared `SelectionBus` so records, SPC, FDC, and RCA cross-filter together.

## FDC and equipment

`align_recipe_steps`, `multi_sensor_panel`, `align_trace_events`, `golden_trace_envelope`, chamber/sensor fingerprints, group comparison, PCA scores/loadings, Hotelling T², and SPE/Q are numerical primitives. Trace/envelope alignment and feature matrices reject malformed or nonfinite inputs explicitly. The dependency-free PCA implementation suits framework-level small/medium analytical payloads; fab-scale/advanced computation can be supplied behind adapters without changing the UI/state contract.

## RCA and commonality

Use the same affected/control populations from AnalysisContext. `enrichment`, `commonality_ranking`, `commonality_matrix`, `contribution_waterfall`, `correlation_matrix`, `evidence_matrix`, `genealogy_graph`, `cause_tree`, `fault_tree`, and `sankey_process_flow` are reusable primitives. The fault tree preserves AND/OR gate nodes; Sankey flow weights count repeated genealogy paths. Commonality/enrichment are prioritization evidence, not proof of causality.

## Yield, reliability, and DOE

Wave 61 includes yield/bin Pareto, yield decomposition waterfall, Weibull reliability with right-censor support, DOE main effects/interactions, and a serializable two-factor quadratic `ResponseSurfaceResult`. Yield contributions and DOE responses reject nonfinite values; response surfaces fail on singular designs instead of silently regularizing invalid experiments.

## Unified analytical surfaces and visualization plans

`SEMICONDUCTOR_SURFACE_REGISTRY` is the machine-readable inventory. Every registered surface is instantiated as `SemiconductorAnalyticalSurface(key, context, selections)` and shares loading, error, empty, partial, stale, selection, and cross-filter behavior. `SemiconductorAnalyticalPanel` binds the same controller to the existing NiceGUI `AnalyticalPanel` shell and therefore supports the standard panel actions when the corresponding callbacks are provided.

Rendering stays separate from calculations. `control_chart_visual`, `capability_histogram_visual`, `qq_probability_visual`, `ecdf_visual`, `box_distribution_visual`, `distribution_density_visual`, `fdc_trace_visual`, `pca_scores_visual`, `pca_loadings_visual`, `commonality_ranking_visual`, `matrix_visual`, `pareto_visual`, and `wafer_points` convert analytical results into existing NiceGUI Base visualization contracts. Do not build independent SPC/FDC/RCA/wafer page frameworks.

## Machine guidance

Each of the 58 catalog surfaces contains both `use_when` and `avoid_when` guidance. Examples of intended composition:

- “compare chambers after PM” → FDC tool/chamber comparison + affected/control + event overlay.
- “is chamber B drifting?” → SPC + affected/control + chamber fingerprint/FDC.
- “where on wafer did the process change?” → delta wafer + radial/ring/sector/center-edge analysis.
- “what is common across affected lots?” → commonality ranking/matrix + genealogy/process flow + evidence matrix.

## Integrated golden examples

- `examples/phase61_spc_wafer_investigation.py` — SPC + capability + affected/control + wafer delta/radial + record source + shared surfaces/visual plans.
- `examples/phase61_fdc_tool_health.py` — recipe-step traces + golden envelope + PM event + chamber fingerprint + PCA + shared FDC surfaces/visual plans.
- `examples/phase61_rca_commonality.py` — shared populations + commonality ranking/matrix + genealogy/Sankey + affected/control visual plans.

These are executable composition references, not hard-coded fab schemas. Map company fields with `SemiconductorFieldMap`, keep vendor/database/environment details behind `DataSource` providers, and preserve server-side/pushdown execution for fab-scale data.

## Wave 62 complete application recipes

Wave 62 adds `SEMICONDUCTOR_RECIPE_REGISTRY` and `assemble_semiconductor_application()` above this analytical surface library. Use a recipe when the request describes a complete monitoring, excursion, FDC, wafer, yield, PM, chamber-matching or RCA application. The recipe selects and lays out registered surfaces while retaining the same Wave 59–61 data/state/selection authorities. See `SEMICONDUCTOR_APPLICATION_RECIPES.md`.

