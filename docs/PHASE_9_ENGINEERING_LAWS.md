# Phase 9 — Engineering & RCA Laws

1. **Domain components stay reusable.** Framework objects represent engineering concepts (tool, chamber, lot, wafer, recipe, limits, evidence, commonality), not one application's database schema.
2. **Spec limits and control limits are distinct.** LSL/USL/target are product/process specification context; LCL/UCL/centerline are statistical/process-control context. The API never silently substitutes one for the other.
3. **OOS is deterministic.** `evaluate_spec` owns the canonical in-spec / watch / OOS grammar. Applications do not invent colors or alternate threshold semantics.
4. **Commonality is not causality.** A shared route/tool/chamber is an observed overlap. `CommonalityInterpretation` must be explicit when the application wants to call something routing, causal-candidate, confounding, or excluded.
5. **Affected/control comparisons are descriptive by default.** Mean shifts, ratios, standardized mean differences, exposure rates, and risk ratios summarize populations; they do not prove root cause.
6. **Zero denominators are never disguised.** If a risk ratio cannot be computed safely, the framework returns `None` rather than infinity or an arbitrary continuity correction.
7. **Contradictions remain visible.** `RcaEvidencePanelSpec.show_contradictions` defaults to true. Strong supporting evidence does not silently erase contradictory evidence.
8. **Evidence channels are explicit.** Physical, metrology, SPC, alarms, process, routing, maintenance, defect, yield, logs, model output, and user evidence remain distinguishable.
9. **Evidence balance is a ranking aid, not probability.** Weighted evidence and commonality can prioritize hypotheses but are never labeled as a probability or causal certainty.
10. **Confidence percentages require calibration.** A numeric score is rendered as a percentage only when `calibrated_probability=True`. Otherwise the UI shows a qualitative confidence level.
11. **Baseline direction is semantic.** `higher_is_better` is optional; the framework never assumes that an upward process parameter is good or bad.
12. **Population distributions use common bins.** Affected and control histograms share the same bin edges so visual comparisons remain valid.
13. **Table percentages use percentage points.** Engineering composition adapters convert internal 0–1 rates to 0–100 values expected by the framework's percent formatter.
14. **All visuals inherit existing systems.** Engineering components use Phase 1 design tokens, Phase 5 tables, Phase 6 charts, and Phase 7 icons rather than introducing a second visual language.
15. **Application data access stays outside UI components.** SQL/API/database integration belongs in services/repositories; engineering components consume typed data only.
16. **No raw NiceGUI requirement.** Standard engineering/RCA screens must be constructible from the public Phase 9 API plus existing framework primitives.
