"""Golden analytical fixtures and semantic contracts for the Reference Explorer."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .preview_data import numeric_data


@dataclass(frozen=True, slots=True)
class AnalyticSemanticContract:
    """Auditable name → data → geometry → labeling → meaning agreement."""

    key: str
    geometry: str
    x_axis: str
    y_axis: str
    legend: str
    meaning: str
    required_fields: tuple[str, ...]
    panels: tuple[str, ...] = ()
    options: tuple[str, ...] = ()


def _c(key: str, geometry: str, x_axis: str, y_axis: str, legend: str, meaning: str,
       required_fields: Sequence[str], *, panels: Sequence[str] = (), options: Sequence[str] = ()) -> AnalyticSemanticContract:
    return AnalyticSemanticContract(key, geometry, x_axis, y_axis, legend, meaning, tuple(required_fields), tuple(panels), tuple(options))


_CONTRACTS = (
    _c('spc_i_mr', 'paired_control_chart', 'sample order', 'measurement / moving range', 'Individuals; Moving Range; Center; UCL; LCL', 'Individual stability and adjacent-sample variation', ('sample', 'measurement'), panels=('individuals', 'moving_range'), options=('control_limits',)),
    _c('spc_xbar_r', 'paired_control_chart', 'rational subgroup', 'subgroup mean / range', 'Xbar; Range; Center; UCL; LCL', 'Subgroup mean and within-subgroup range stability', ('subgroup', 'observation', 'measurement'), panels=('xbar', 'range'), options=('control_limits',)),
    _c('spc_xbar_s', 'paired_control_chart', 'rational subgroup', 'subgroup mean / standard deviation', 'Xbar; Standard deviation; Center; UCL; LCL', 'Subgroup mean and within-subgroup standard-deviation stability', ('subgroup', 'observation', 'measurement'), panels=('xbar', 'standard_deviation'), options=('control_limits',)),
    _c('spc_p', 'control_chart', 'sample order', 'nonconforming proportion', 'p; Center; UCL; LCL', 'Binary nonconformance rate with varying sample sizes', ('sample', 'nonconforming', 'inspected'), options=('control_limits',)),
    _c('spc_np', 'control_chart', 'sample order', 'nonconforming count', 'np; Center; UCL; LCL', 'Binary nonconforming counts at a constant sample size', ('sample', 'nonconforming', 'inspected'), options=('control_limits',)),
    _c('spc_c', 'control_chart', 'sample order', 'defect count', 'c; Center; UCL; LCL', 'Poisson defect counts at constant opportunity', ('sample', 'defects'), options=('control_limits',)),
    _c('spc_u', 'control_chart', 'sample order', 'defects per unit', 'u; Center; UCL; LCL', 'Poisson defect rate with varying opportunity', ('sample', 'defects', 'units'), options=('control_limits',)),
    _c('spc_ewma', 'control_chart', 'sample order', 'EWMA statistic', 'EWMA; Center; UCL; LCL', 'A small sustained shift becomes visible through exponentially weighted history', ('sample', 'measurement'), options=('center_limits', 'lambda')),
    _c('spc_cusum', 'control_chart', 'sample order', 'positive / negative cumulative deviation', 'C+; C−; Decision limits', 'Persistent positive and negative mean shifts accumulate toward decisions', ('sample', 'measurement'), options=('positive_negative', 'decision_limits')),
    _c('capability_histogram', 'histogram', 'measurement bins', 'count', 'Distribution; LSL; Target; USL', 'Distribution shape and placement relative to engineering specification limits', ('measurement', 'lsl', 'target', 'usl'), options=('spec_limits',)),
    _c('qq_probability', 'qq_plot', 'theoretical quantile', 'ordered observed quantile', 'Observed quantiles; Expected line', 'Departure from the expected distribution appears as curvature away from the reference line', ('measurement',), options=('expected_line',)),
    _c('ecdf', 'step_line', 'observed value', 'empirical cumulative probability', 'ECDF', 'Monotone proportion at or below each distinct observed value', ('measurement',), options=('step', 'monotone_0_1')),
    _c('box_distribution', 'grouped_boxplot', 'population', 'measurement', 'Population', 'Quartiles, median, whiskers, and between-population shift', ('population', 'measurement'), options=('quartiles', 'median', 'whiskers')),
    _c('violin_distribution', 'violin', 'population', 'measurement density', 'Population', 'Mirrored density width teaches distribution shape and spread', ('population', 'measurement'), options=('density_silhouette',)),
    _c('ridge_distribution', 'ridge', 'measurement', 'offset density by population', 'Population', 'Offset density curves compare several chamber distributions without overlap ambiguity', ('population', 'measurement'), options=('offset_density',)),
    _c('wafer_continuous', 'wafer_map', 'wafer x', 'wafer y', 'Continuous measurement', 'Continuous spatial process response across the clipped wafer geometry', ('x', 'y', 'measurement')),
    _c('wafer_categorical', 'wafer_map', 'wafer x', 'wafer y', 'Category', 'Discrete wafer categories use named states rather than a continuous measurement scale', ('x', 'y', 'category'), options=('categorical_legend',)),
    _c('wafer_defect', 'wafer_map', 'wafer x', 'wafer y', 'Defect state', 'Inspection locations show discrete defect classes and no-defect state', ('x', 'y', 'defect_state'), options=('defect_legend',)),
    _c('wafer_delta', 'wafer_delta_map', 'wafer x', 'wafer y', 'Affected − control', 'Signed spatial change between matched wafer populations', ('x', 'y', 'control', 'affected', 'delta')),
    _c('wafer_comparison', 'paired_wafer_map', 'wafer x', 'wafer y', 'Shared measurement scale', 'Control and affected wafers remain spatially aligned on one governed scale', ('x', 'y', 'control', 'affected'), panels=('control', 'affected')),
    _c('lot_wafer_strip', 'wafer_strip', 'wafer sequence', 'spatial measurement', 'Shared measurement scale', 'Lot-level wafer-to-wafer spatial evolution', ('wafer', 'x', 'y', 'measurement')),
    _c('wafer_small_multiples', 'wafer_small_multiples', 'wafer', 'spatial measurement', 'Shared measurement scale', 'Synchronized small multiples compare signatures without changing color meaning', ('wafer', 'x', 'y', 'measurement')),
    _c('wafer_contour', 'wafer_contour', 'wafer x', 'wafer y', 'Smoothed field', 'A smooth spatial field is used only for sufficiently sampled continuous data', ('x', 'y', 'measurement'), options=('circular_clip', 'contour_isolines')),
    _c('wafer_radial', 'radial_profile', 'normalized radius', 'mean measurement', 'Affected; Control', 'Center-to-edge profile reveals radial process signatures', ('radius', 'population', 'measurement')),
    _c('wafer_center_edge', 'region_comparison', 'wafer region', 'mean measurement', 'Region', 'Center, middle, edge, and outer-edge summaries quantify spatial shift', ('region', 'measurement')),
    _c('wafer_ring', 'ring_profile', 'ring', 'mean residual', 'Ring', 'Concentric summaries expose ring-shaped signatures', ('ring', 'measurement')),
    _c('wafer_sector', 'sector_profile', 'sector', 'mean residual', 'Sector', 'Azimuthal summaries expose directional signatures', ('sector', 'measurement')),
    _c('wafer_defect_clusters', 'wafer_defect_clusters', 'wafer x', 'wafer y', 'Defect cluster state', 'Clustered inspection defects remain discrete and spatially bounded', ('x', 'y', 'defect_state', 'cluster')),
    _c('fdc_recipe_step_trace', 'step_aligned_trace', 'elapsed time / recipe step', 'sensor value', 'Sensor', 'Equipment trace behavior aligned to recipe-step boundaries', ('timestamp', 'recipe_step', 'sensor', 'value')),
    _c('fdc_golden_envelope', 'envelope_trace', 'elapsed time', 'sensor value', 'Observed; Golden upper; Golden lower', 'Observed trace deviation from a qualified baseline envelope', ('timestamp', 'observed', 'golden_lower', 'golden_upper')),
    _c('fdc_multi_sensor', 'multi_line', 'elapsed time', 'normalized sensor response', 'Sensor', 'Correlated equipment sensors retain separate governed series', ('timestamp', 'sensor', 'value')),
    _c('fdc_tool_chamber_compare', 'grouped_bar', 'tool / chamber', 'normalized deviation', 'Tool / chamber', 'Matched equipment groups expose outlying chamber behavior', ('tool', 'chamber', 'score')),
    _c('fdc_chamber_fingerprint', 'fingerprint_matrix', 'engineering feature', 'chamber', 'Normalized deviation', 'Multivariate chamber signatures remain aligned by feature', ('chamber', 'feature', 'score')),
    _c('fdc_sensor_fingerprint', 'fingerprint_matrix', 'sensor feature', 'sensor', 'Normalized deviation', 'Per-sensor signatures expose slope, noise, lag, and location differences', ('sensor', 'feature', 'score')),
    _c('fdc_alarm_overlay', 'event_overlay_trace', 'elapsed time', 'sensor value', 'Sensor; Alarm event', 'Alarm timing is aligned with the measured excursion', ('timestamp', 'value', 'event'), options=('event_marker',)),
    _c('fdc_equipment_event_overlay', 'event_overlay_trace', 'elapsed time', 'sensor value', 'Sensor; Equipment event', 'PM or equipment events are aligned with trace behavior', ('timestamp', 'value', 'event'), options=('event_marker',)),
    _c('fdc_pca_scores', 'scatter', 'PC1 score', 'PC2 score', 'Population', 'Multivariate operating-state separation in score space', ('population', 'pc1', 'pc2')),
    _c('fdc_pca_loadings', 'loading_bar', 'sensor variable', 'PC1 loading', 'Loading sign', 'Variables contributing to multivariate separation', ('sensor', 'loading')),
    _c('fdc_hotelling_t2', 'limit_chart', 'sample order', 'Hotelling T²', 'T²; Limit', 'Score-space anomaly magnitude against a governed threshold', ('sample', 'statistic', 'limit')),
    _c('fdc_spe_q', 'limit_chart', 'sample order', 'SPE / Q', 'SPE/Q; Limit', 'Residual anomaly magnitude against a governed threshold', ('sample', 'statistic', 'limit')),
    _c('rca_affected_control', 'grouped_boxplot', 'population', 'measurement', 'Affected; Control', 'Population shift is evidence, not causal proof', ('population', 'measurement'), options=('quartiles', 'median', 'whiskers')),
    _c('rca_commonality_ranking', 'ranked_bar', 'factor', 'affected overlap', 'Evidence rank', 'Shared-factor evidence ranked without implying causal probability', ('factor', 'score')),
    _c('rca_enrichment', 'ranked_bar', 'factor', 'enrichment ratio', 'Enrichment', 'Factor over-representation relative to matched controls', ('factor', 'score')),
    _c('rca_commonality_matrix', 'matrix', 'population', 'factor', 'Commonality score', 'Factor exposure patterns across affected, control, and baseline populations', ('factor', 'population', 'score')),
    _c('rca_contribution_waterfall', 'waterfall', 'factor', 'signed contribution', 'Contribution', 'Ranked positive and negative contributions accumulate to the observed shift', ('factor', 'contribution'), options=('cumulative_bridge',)),
    _c('rca_correlation_matrix', 'correlation_matrix', 'variable', 'variable', 'Correlation −1…1', 'Numeric association screening without causal overclaim', ('x_variable', 'y_variable', 'correlation')),
    _c('rca_evidence_matrix', 'evidence_matrix', 'evidence state', 'hypothesis', 'Supports; Contradicts; Unknown', 'Evidence status remains distinct from hypothesis confidence', ('hypothesis', 'evidence_state', 'score')),
    _c('rca_genealogy_graph', 'relationship_graph', 'process stage', 'entity branch', 'Entity type', 'Branching and merging lot/wafer/tool genealogy preserves directed relationships', ('source', 'target', 'quantity'), options=('branching', 'merging')),
    _c('rca_cause_tree', 'cause_tree', 'decomposition level', 'candidate branch', 'Cause family', 'Structured causal candidates remain hypotheses pending evidence', ('node', 'parent', 'level')),
    _c('rca_fault_tree', 'fault_tree', 'decomposition level', 'failure branch', 'Root; AND/OR gate; Leaf', 'Hierarchical logical failure decomposition with explicit gate semantics', ('node', 'parent', 'level', 'gate'), options=('connectors', 'and_or_gates')),
    _c('rca_sankey', 'sankey', 'process stage', 'quantity-weighted flow', 'Process node', 'Flow-band width encodes population quantity through process paths', ('source', 'target', 'quantity'), options=('weighted_bands',)),
    _c('yield_pareto', 'pareto', 'yield-loss contributor', 'count / cumulative percent', 'Contributor; Cumulative %', 'Ranked yield loss with cumulative contribution', ('category', 'count', 'cumulative_pct')),
    _c('bin_pareto', 'pareto', 'failing bin', 'count / cumulative percent', 'Bin; Cumulative %', 'Ranked failing-bin contribution', ('category', 'count', 'cumulative_pct')),
    _c('yield_waterfall', 'waterfall', 'loss / recovery source', 'yield delta', 'Signed delta', 'Signed contributions reconcile the total yield change', ('category', 'delta'), options=('cumulative_bridge',)),
    _c('weibull_reliability', 'probability_line', 'exposure time', 'cumulative failure probability', 'Failure probability', 'Time-to-failure trend for explicitly defined failure and censoring semantics', ('time', 'failure_probability')),
    _c('doe_main_effects', 'main_effect_lines', 'factor level', 'mean response', 'Factor', 'Clear slope direction and magnitude teach interpretable factor main effects', ('factor', 'level', 'response'), options=('clear_slopes',)),
    _c('doe_interactions', 'interaction_lines', 'factor A level', 'mean response', 'Factor B level', 'Materially non-parallel and crossing lines expose factor interaction', ('factor_a', 'factor_b', 'response'), options=('non_parallel', 'crossing')),
    _c('doe_response_surface', 'response_surface', 'factor A', 'factor B', 'Response', 'Bounded quadratic response over the designed factor region', ('factor_a', 'factor_b', 'response')),
)

ANALYTIC_SEMANTIC_CONTRACTS: Mapping[str, AnalyticSemanticContract] = MappingProxyType({contract.key: contract for contract in _CONTRACTS})

DATA_SURFACES = frozenset({'spc_i_mr', 'spc_ewma', 'spc_cusum', 'capability_histogram', 'qq_probability', 'ecdf', 'box_distribution'})
CANONICAL_MEASUREMENT_FIELDS = {key: 'measurement' for key in DATA_SURFACES}
SEMANTIC_CAPTIONS = {key: f'{contract.geometry.replace("_", " ").title()} · x: {contract.x_axis} · y: {contract.y_axis}' for key, contract in ANALYTIC_SEMANTIC_CONTRACTS.items()}


def _measurement_rows(values: Sequence[float], *, populations: Sequence[str] | None = None, **constant: Any) -> tuple[dict[str, object], ...]:
    return tuple({'id': f'R{index:02d}', 'sample': f'R{index:02d}', 'timestamp': f'08:{index:02d}', 'measurement': float(value), **({'population': populations[index - 1]} if populations else {}), **constant} for index, value in enumerate(values, start=1))


_I_MR = _measurement_rows((40.00, 40.30, 39.70, 40.80, 40.10, 40.60, 39.90, 40.40, 40.20, 41.00, 40.50, 40.90, 40.30, 39.80, 40.70, 41.20, 40.60, 40.10, 40.90, 41.40))
_EWMA = _measurement_rows((39.72, 39.88, 39.94, 40.05, 40.12, 40.20, 40.31, 40.42, 40.28, 40.54, 40.66, 40.81, 40.74, 40.92, 41.06, 40.98, 41.18, 41.31, 41.21, 41.42))
_CUSUM = _measurement_rows((40.10, 40.18, 40.26, 40.04, 40.22, 40.31, 40.37, 39.84, 39.72, 39.66, 39.78, 39.58, 39.48, 39.62, 39.76, 40.08, 40.16, 40.24, 40.12, 40.30))
_CAPABILITY = _measurement_rows((39.12, 39.34, 39.48, 39.61, 39.72, 39.78, 39.84, 39.91, 39.95, 40.01, 40.06, 40.10, 40.14, 40.21, 40.27, 40.33, 40.42, 40.51, 40.66, 40.82, 40.94, 41.08, 41.24, 41.46), lsl=38.5, target=40.0, usl=41.5)
_QQ = _measurement_rows((38.92, 39.21, 39.46, 39.68, 39.82, 39.96, 40.05, 40.16, 40.28, 40.43, 40.59, 40.82, 41.07, 41.39, 41.78))
_ECDF = _measurement_rows((38.4, 38.8, 39.2, 39.6, 40.0, 40.0, 40.4, 40.8, 41.2, 41.6, 42.0, 42.4))
_BOX = _measurement_rows((39.18, 39.42, 39.76, 39.92, 40.08, 40.24, 40.41, 40.58, 40.76, 40.92, 41.18, 41.34, 41.55, 41.72, 41.96), populations=('Control',) * 5 + ('Affected',) * 5 + ('Post-PM',) * 5)


def _subgroups(*, spread_scale: float) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    offsets = (-1.4, -.35, .45, 1.3)
    means = (40.00, 40.08, 39.94, 40.16, 40.25, 40.12, 40.34, 40.28, 40.46, 40.55)
    for subgroup, mean in enumerate(means, 1):
        local_spread = spread_scale * (1 + (subgroup % 3) * .13)
        for observation, offset in enumerate(offsets, 1):
            rows.append({'subgroup': f'SG-{subgroup:02d}', 'observation': observation, 'measurement': round(mean + offset * local_spread, 3)})
    return tuple(rows)


def _wafer_rows(key: str) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    coords = ((-2, 0), (-1, -1), (-1, 1), (0, -2), (0, 0), (0, 2), (1, -1), (1, 1), (2, 0))
    for index, (x, y) in enumerate(coords):
        radius = (x * x + y * y) ** .5
        measurement = round(40.0 + .22 * radius + .08 * x - .04 * y, 3)
        row: dict[str, object] = {'x': x, 'y': y, 'measurement': measurement}
        if key == 'wafer_categorical':
            row['category'] = ('Nominal', 'Watch', 'Review')[index % 3]
        elif key in {'wafer_defect', 'wafer_defect_clusters'}:
            row['defect_state'] = 'Defect' if index in ({1, 2, 6} if key == 'wafer_defect_clusters' else {2, 7}) else 'No defect'
            if key == 'wafer_defect_clusters': row['cluster'] = 'Edge cluster' if index in {1, 2, 6} else 'None'
        elif key in {'wafer_delta', 'wafer_comparison'}:
            row['control'] = round(measurement - .18, 3); row['affected'] = round(measurement + .12 + .07 * x, 3)
            if key == 'wafer_delta': row['delta'] = round(float(row['affected']) - float(row['control']), 3)
        elif key in {'lot_wafer_strip', 'wafer_small_multiples'}:
            row['wafer'] = f'W{index % 4 + 1:02d}'
        elif key == 'wafer_radial':
            row['radius'] = round(radius / 2, 3)
            row['population'] = 'Affected' if index % 2 else 'Control'
        elif key == 'wafer_center_edge':
            row['region'] = ('Center', 'Middle', 'Edge', 'Outer edge')[min(3, int(radius * 1.5))]
        elif key == 'wafer_ring':
            row['ring'] = f'R{min(4, int(radius * 2))}'
        elif key == 'wafer_sector':
            row['sector'] = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'Center')[index]
        rows.append(row)
    return tuple(rows)


def _fdc_rows(key: str) -> tuple[dict[str, object], ...]:
    if key == 'fdc_golden_envelope':
        return tuple({'timestamp': index, 'observed': value, 'golden_lower': value - .18, 'golden_upper': value + .14} for index, value in enumerate((1.0, 1.15, 1.4, 1.8, 2.05, 1.7, 1.35, 1.1)))
    if key == 'fdc_tool_chamber_compare':
        return tuple({'tool': tool, 'chamber': chamber, 'score': score} for tool, chamber, score in (('ETCH-03', 'A', .12), ('ETCH-03', 'B', .18), ('ETCH-07', 'A', .84), ('ETCH-07', 'B', .23), ('ETCH-11', 'A', .16), ('ETCH-11', 'C', .31)))
    if key in {'fdc_chamber_fingerprint', 'fdc_sensor_fingerprint'}:
        entity = 'chamber' if key == 'fdc_chamber_fingerprint' else 'sensor'
        names = ('ETCH-03/A', 'ETCH-07/B', 'ETCH-11/C') if entity == 'chamber' else ('Pressure', 'RF bias', 'Gas flow')
        return tuple({entity: name, 'feature': feature, 'score': round((i + 1) * .17 - (j % 2) * .22, 3)} for i, name in enumerate(names) for j, feature in enumerate(('Mean shift', 'Slope', 'Noise')))
    if key == 'fdc_pca_scores':
        return tuple({'population': population, 'pc1': pc1, 'pc2': pc2} for population, pc1, pc2 in (('Baseline', -1.6, -.8), ('Baseline', -1.0, .2), ('Baseline', -.3, .5), ('Affected', 1.3, .9), ('Affected', 2.0, .8), ('Affected', 2.5, 1.4)))
    if key == 'fdc_pca_loadings':
        return tuple({'sensor': sensor, 'loading': loading} for sensor, loading in (('RF bias', .72), ('Pressure', .61), ('Gas A', -.48), ('Temperature', .33), ('Endpoint', .18)))
    if key in {'fdc_hotelling_t2', 'fdc_spe_q'}:
        values = (1.1, 1.4, 1.2, 1.7, 2.4, 3.1, 4.8, 6.2) if key == 'fdc_hotelling_t2' else (.4, .5, .6, .72, 1.1, 1.4, 2.8, 3.4)
        limit = 5.0 if key == 'fdc_hotelling_t2' else 2.5
        return tuple({'sample': f'R{i:02d}', 'statistic': value, 'limit': limit} for i, value in enumerate(values, 1))
    if key in {'fdc_alarm_overlay', 'fdc_equipment_event_overlay'}:
        event_name = 'Pressure high' if key == 'fdc_alarm_overlay' else 'PM complete'
        return tuple({'timestamp': i, 'value': value, 'event': event_name if i == 6 else 'None'} for i, value in enumerate((1.0, 1.1, 1.2, 1.35, 1.62, 2.15, 1.74, 1.42), 1))
    if key == 'fdc_multi_sensor':
        return tuple({'timestamp': i, 'sensor': sensor, 'value': round(base + i * slope + (i % 3) * .03, 3)} for sensor, base, slope in (('Pressure', 1.0, .10), ('RF bias', .8, .14), ('Gas flow', 1.2, -.025)) for i in range(1, 7))
    return tuple({'timestamp': i, 'recipe_step': f'S{1 + i // 2}', 'sensor': 'Pressure', 'value': value} for i, value in enumerate((1.0, 1.1, 1.2, 1.65, 1.72, 2.10, 1.55, 1.40)))


def _rca_rows(key: str) -> tuple[dict[str, object], ...]:
    if key == 'rca_affected_control':
        return _measurement_rows((39.1, 39.5, 39.8, 40.0, 40.3, 40.6, 40.9, 41.2, 41.7, 42.1, 42.5, 42.9), populations=('Control',) * 6 + ('Affected',) * 6)
    if key in {'rca_commonality_ranking', 'rca_enrichment'}:
        values = (92, 78, 63, 42, 25) if key.endswith('ranking') else (4.8, 3.6, 2.9, 1.8, 1.2)
        return tuple({'factor': factor, 'score': score} for factor, score in zip(('CH-3', 'ETCH-021', 'Recipe R18', 'PM < 3 d', 'Material M4'), values, strict=True))
    if key == 'rca_commonality_matrix':
        return tuple({'factor': factor, 'population': population, 'score': score} for factor, values in (('CH-3', (.94, .18, .12)), ('Recipe R18', (.88, .31, .22)), ('PM < 3 d', (.76, .15, .19))) for population, score in zip(('Affected', 'Control', 'Baseline'), values, strict=True))
    if key == 'rca_contribution_waterfall':
        return tuple({'factor': factor, 'contribution': value} for factor, value in (('CH-3', 2.2), ('Recipe', -.4), ('PM age', 1.1), ('Material', .6), ('Controls', -.2)))
    if key == 'rca_correlation_matrix':
        return tuple({'x_variable': x, 'y_variable': y, 'correlation': round(value, 2)} for x, y, value in (('CD', 'Pressure', .82), ('CD', 'RF bias', -.44), ('Pressure', 'RF bias', .31), ('Flow', 'Temperature', -.58), ('CD', 'Flow', .17)))
    if key == 'rca_evidence_matrix':
        return tuple({'hypothesis': hypothesis, 'evidence_state': state, 'score': score} for hypothesis, state, score in (('CH-3 drift', 'Supports', .90), ('Recipe mismatch', 'Contradicts', .61), ('Material lot', 'Unknown', .47), ('PM recovery', 'Supports', .71)))
    if key in {'rca_genealogy_graph', 'rca_sankey'}:
        edges = (('LOT-2471', 'W08', 48), ('LOT-2471', 'W09', 36), ('W08', 'ETCH-021/CH-3', 48), ('W09', 'ETCH-021/CH-3', 31), ('W09', 'ETCH-024/CH-1', 5), ('ETCH-021/CH-3', 'Review', 61))
        return tuple({'source': source, 'target': target, 'quantity': quantity} for source, target, quantity in edges)
    if key == 'rca_fault_tree':
        return (
            {'node': 'OOS event', 'parent': '', 'level': 0, 'gate': 'ROOT'},
            {'node': 'Equipment branch', 'parent': 'OOS event', 'level': 1, 'gate': 'OR'},
            {'node': 'Pressure unstable', 'parent': 'Equipment branch', 'level': 2, 'gate': 'LEAF'},
            {'node': 'RF mismatch', 'parent': 'Equipment branch', 'level': 2, 'gate': 'LEAF'},
            {'node': 'Detection branch', 'parent': 'OOS event', 'level': 1, 'gate': 'AND'},
            {'node': 'SPC violation', 'parent': 'Detection branch', 'level': 2, 'gate': 'LEAF'},
            {'node': 'Edge signature', 'parent': 'Detection branch', 'level': 2, 'gate': 'LEAF'},
        )
    return tuple({'node': node, 'parent': parent, 'level': level} for node, parent, level in (('CD excursion', '', 0), ('Equipment', 'CD excursion', 1), ('Process', 'CD excursion', 1), ('CH-3 drift', 'Equipment', 2), ('Recipe step', 'Process', 2)))


def _build_fixtures() -> dict[str, tuple[dict[str, object], ...]]:
    fixtures: dict[str, tuple[dict[str, object], ...]] = {
        'spc_i_mr': _I_MR, 'spc_xbar_r': _subgroups(spread_scale=.24), 'spc_xbar_s': _subgroups(spread_scale=.34),
        'spc_ewma': _EWMA, 'spc_cusum': _CUSUM, 'capability_histogram': _CAPABILITY, 'qq_probability': _QQ,
        'ecdf': _ECDF, 'box_distribution': _BOX,
        'violin_distribution': _measurement_rows((39.0, 39.3, 39.7, 39.9, 40.0, 40.1, 40.3, 40.8, 41.4, 39.5, 39.8, 40.2, 40.6, 41.0, 41.5), populations=('CH-1',) * 5 + ('CH-2',) * 5 + ('CH-3',) * 5),
        'ridge_distribution': _measurement_rows((38.8, 39.2, 39.7, 40.0, 40.2, 39.4, 39.8, 40.2, 40.6, 40.9, 40.1, 40.5, 40.9, 41.2, 41.7), populations=('CH-1',) * 5 + ('CH-2',) * 5 + ('CH-3',) * 5),
        'spc_p': tuple({'sample': f'R{i:02d}', 'nonconforming': count, 'inspected': size} for i, (count, size) in enumerate(((4, 200), (3, 180), (6, 220), (5, 190), (9, 240), (11, 225), (7, 210), (13, 230)), 1)),
        'spc_np': tuple({'sample': f'R{i:02d}', 'nonconforming': count, 'inspected': 200} for i, count in enumerate((4, 3, 5, 4, 6, 8, 11, 7), 1)),
        'spc_c': tuple({'sample': f'R{i:02d}', 'defects': count} for i, count in enumerate((2, 4, 3, 5, 4, 7, 10, 6), 1)),
        'spc_u': tuple({'sample': f'R{i:02d}', 'defects': count, 'units': units} for i, (count, units) in enumerate(((9, 50), (12, 60), (8, 50), (16, 65), (13, 55), (21, 70), (18, 50), (17, 62)), 1)),
    }
    for key in ANALYTIC_SEMANTIC_CONTRACTS:
        if key.startswith('wafer_') or key == 'lot_wafer_strip': fixtures[key] = _wafer_rows(key)
        elif key.startswith('fdc_'): fixtures[key] = _fdc_rows(key)
        elif key.startswith('rca_'): fixtures[key] = _rca_rows(key)
    fixtures.update({
        'yield_pareto': tuple({'category': category, 'count': count, 'cumulative_pct': pct} for category, count, pct in zip(('CD OOS', 'Edge defect', 'Overlay', 'Scratch', 'Other'), (34, 22, 13, 8, 5), (41.5, 68.3, 84.1, 93.9, 100.0), strict=True)),
        'bin_pareto': tuple({'category': category, 'count': count, 'cumulative_pct': pct} for category, count, pct in zip(('Bin 3', 'Bin 7', 'Edge', 'Scratch', 'Other'), (31, 24, 14, 9, 6), (36.9, 65.5, 82.1, 92.9, 100.0), strict=True)),
        'yield_waterfall': tuple({'category': category, 'delta': delta} for category, delta in (('CD OOS', -1.8), ('Edge', -.9), ('Overlay', -.6), ('Recovery', .3), ('Other', -.2))),
        'weibull_reliability': tuple({'time': time, 'failure_probability': probability} for time, probability in zip(range(10, 130, 10), (.01, .02, .04, .07, .12, .19, .29, .42, .57, .71, .83, .91), strict=True)),
        'doe_main_effects': tuple({'factor': factor, 'level': level, 'response': response} for factor, values in (('RF bias', (39.4, 40.1, 41.3)), ('Pressure', (40.9, 40.2, 39.5))) for level, response in zip(('Low', 'Center', 'High'), values, strict=True)),
        'doe_interactions': tuple({'factor_a': factor_a, 'factor_b': factor_b, 'response': response} for factor_b, values in (('Pressure low', (39.4, 40.1, 41.2)), ('Pressure high', (41.0, 40.5, 39.7))) for factor_a, response in zip(('RF low', 'RF center', 'RF high'), values, strict=True)),
        'doe_response_surface': tuple({'factor_a': a, 'factor_b': b, 'response': round(39.5 + .18 * a - .12 * b + .06 * a * b - .035 * a * a, 3)} for a in range(-3, 4) for b in range(-2, 4)),
    })
    missing = set(ANALYTIC_SEMANTIC_CONTRACTS) - set(fixtures)
    if missing: raise RuntimeError(f'Missing Golden analytical fixtures: {sorted(missing)}')
    return fixtures


CANONICAL_ANALYTIC_FIXTURES: Mapping[str, tuple[dict[str, object], ...]] = MappingProxyType(_build_fixtures())


def canonical_fixture_for_surface(surface_key: str) -> tuple[dict[str, object], ...]:
    try: return CANONICAL_ANALYTIC_FIXTURES[surface_key]
    except KeyError as exc: raise KeyError(f'No canonical analytical fixture is registered as {surface_key!r}.') from exc


def analytic_plan(surface_key: str, rows: Sequence[Mapping[str, Any]], title: str, measurement: str | None = None):
    from nicegui_base.semiconductor import spc, visualization as plans
    measurement = measurement or CANONICAL_MEASUREMENT_FIELDS.get(surface_key)
    _, values = numeric_data(rows, measurement)
    values = tuple(value for value in values if value is not None)
    if surface_key in {'spc_i_mr', 'spc_ewma', 'spc_cusum'}:
        return plans.control_chart_visual({'spc_i_mr': spc.i_mr, 'spc_ewma': spc.ewma, 'spc_cusum': spc.cusum}[surface_key](values), title=title)
    if surface_key == 'capability_histogram':
        from nicegui_base.visualization import SpecLimits
        return plans.capability_histogram_visual(values, title=title, limits=SpecLimits(lower=38.5, upper=41.5, target=40.0, lower_label='LSL', upper_label='USL', target_label='Target'))
    if surface_key == 'qq_probability': return plans.qq_probability_visual(values, title=title)
    if surface_key == 'ecdf': return plans.ecdf_visual(values, title=title)
    raise ValueError(f'{surface_key} uses a different visual adapter.')


def render_analytic(surface_key: str, category: str, *, title: str, rows: Sequence[Mapping[str, Any]], options: Mapping[str, Any]):
    from nicegui import ui
    contract = ANALYTIC_SEMANTIC_CONTRACTS[surface_key]
    with ui.element('section').classes('cui-analytic-semantic-contract').props(
        f'data-analytic-key="{surface_key}" data-semantic-geometry="{contract.geometry}" data-semantic-panels="{" ".join(contract.panels)}" '
        f'data-semantic-options="{" ".join(contract.options)}" data-semantic-x="{contract.x_axis}" data-semantic-y="{contract.y_axis}"'
    ):
        if surface_key in DATA_SURFACES:
            if not rows:
                ui.label('No observations. Add data in the Data tab.').classes('cui-workbench-note'); return None
            measurement = options.get('measurement') or CANONICAL_MEASUREMENT_FIELDS.get(surface_key)
            canonical = canonical_fixture_for_surface(surface_key)
            if measurement and not any(measurement in row for row in rows): rows = canonical
            if measurement == CANONICAL_MEASUREMENT_FIELDS.get(surface_key) and tuple(rows) == tuple(canonical):
                from .app import _render_surface_preview
                return _render_surface_preview(surface_key, category, title=title)
            ui.label('Development analysis. Statistical assumptions and baseline suitability must be reviewed before operational use.').classes('cui-workbench-note')
            ui.label(SEMANTIC_CAPTIONS[surface_key]).classes('cui-workbench-preview-caption').props(f'data-visual-contract="{surface_key}"')
            if surface_key == 'box_distribution':
                from .visual_specimens import render_visualization
                return render_visualization('BoxPlot', title=title, rows=rows, options={**options, 'measurement': measurement})
            from nicegui_base.integrations.nicegui_visualization import ChartPanel
            plan = analytic_plan(surface_key, rows, title, measurement)
            return ChartPanel(plan.series, spec=plan.spec, thresholds=plan.thresholds, spec_limits=plan.spec_limits, annotations=plan.annotations)
        from .app import _render_surface_preview
        ui.label('Canonical synthetic reference fixture; engineering conclusions require validated production data.').classes('cui-workbench-note')
        return _render_surface_preview(surface_key, category, title=title)


__all__ = ['ANALYTIC_SEMANTIC_CONTRACTS', 'AnalyticSemanticContract', 'CANONICAL_ANALYTIC_FIXTURES', 'CANONICAL_MEASUREMENT_FIELDS', 'DATA_SURFACES', 'SEMANTIC_CAPTIONS', 'analytic_plan', 'canonical_fixture_for_surface', 'render_analytic']
