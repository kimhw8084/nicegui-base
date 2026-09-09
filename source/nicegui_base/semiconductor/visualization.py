from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from statistics import fmean, stdev

from nicegui_base.visualization import (
    AnnotationIntent, AxisSpec, AxisType, ChartAnnotation, ChartKind, ChartPanelSpec,
    ChartToolbarSpec, LegendPosition, LineStyle, SelectionMode, SeriesSpec, SpecLimits, ThresholdSpec, WaferPoint,
)
from .fdc import AlignedTraceEvent, GoldenEnvelopePoint, PCAResult, TraceSample, multi_sensor_panel
from .rca import EnrichmentResult
from .spatial import WaferSample
from .spc import ControlChartResult, box_distribution, capability_histogram, ecdf, qq_points, ridge_distributions

@dataclass(frozen=True,slots=True)
class SemiconductorVisualPlan:
    spec:ChartPanelSpec
    series:tuple[SeriesSpec,...]
    thresholds:tuple[ThresholdSpec,...]=()
    spec_limits:SpecLimits|None=None
    annotations:tuple[ChartAnnotation,...]=()
    metadata:Mapping[str,Any]=field(default_factory=dict)


def control_chart_visual(result:ControlChartResult, *, title:str='SPC control chart', labels:Sequence[str]|None=None, lsl:float|None=None, usl:float|None=None, target:float|None=None, event_overlays:Sequence[tuple[int,str]] = (), limit_version:str|None=None, baseline_period:str|None=None)->SemiconductorVisualPlan:
    n=len(result.values); categories=tuple(labels) if labels is not None else tuple(str(i+1) for i in range(n))
    if len(categories)!=n: raise ValueError('control-chart labels must match values')
    if result.family.value == 'cusum' and result.c_plus and result.c_minus:
        series=(SeriesSpec('c_plus','C+',result.c_plus,kind=ChartKind.CONTROL,line_style=LineStyle.SOLID,semantic_color='danger'),SeriesSpec('c_minus','C−',result.c_minus,kind=ChartKind.CONTROL,line_style=LineStyle.SOLID,semantic_color='info'),SeriesSpec('center','Center',result.center,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='neutral'),SeriesSpec('positive_limit','Positive decision limit',result.ucl,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='danger'),SeriesSpec('negative_limit','Negative decision limit',result.lcl,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='danger'))
    else:
        series=(SeriesSpec('value','Value',result.values,kind=ChartKind.CONTROL,line_style=LineStyle.SOLID),SeriesSpec('ucl','UCL',result.ucl,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='danger'),SeriesSpec('center','Center',result.center,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='neutral'),SeriesSpec('lcl','LCL',result.lcl,kind=ChartKind.CONTROL,line_style=LineStyle.DASHED,semantic_color='danger'))
    annotations=[ChartAnnotation(i,label,intent=AnnotationIntent.INFO) for i,label in event_overlays]
    for violation in result.violations:
        for idx in violation.indices[:1]:
            annotations.append(ChartAnnotation(categories[idx],f'{violation.rule}: {violation.message}',y=result.values[idx],intent=AnnotationIntent.DANGER))
    for idx in result.excluded_indices:
        annotations.append(ChartAnnotation(str(idx+1),'Excluded nonfinite/missing point',intent=AnnotationIntent.WARNING))
    spec=ChartPanelSpec(title=title,kind=ChartKind.CONTROL,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=categories),y_axis=AxisSpec(kind=AxisType.VALUE),toolbar=ChartToolbarSpec())
    return SemiconductorVisualPlan(spec,series,spec_limits=SpecLimits(lsl,usl,target) if any(v is not None for v in (lsl,usl,target)) else None,annotations=tuple(annotations),metadata={'family':result.family.value,'limit_version':limit_version,'baseline_period':baseline_period,'excluded_indices':result.excluded_indices})


def wafer_points(samples:Sequence[WaferSample])->tuple[WaferPoint,...]:
    return tuple(WaferPoint(p.x,p.y,p.value,metadata={'wafer_id':p.wafer_id,'category':p.category,'defect_class':p.defect_class,**dict(p.metadata)}) for p in samples)


def affected_control_visual(affected:Sequence[float],control:Sequence[float], *, title:str='Affected vs control')->SemiconductorVisualPlan:
    spec=ChartPanelSpec(title=title,kind=ChartKind.BOX_PLOT,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Affected','Control')),y_axis=AxisSpec(kind=AxisType.VALUE))
    return SemiconductorVisualPlan(spec,(SeriesSpec('affected','Affected',tuple(affected),kind=ChartKind.BOX_PLOT),SeriesSpec('control','Control',tuple(control),kind=ChartKind.BOX_PLOT)),metadata={'population_roles':('affected','control')})



def capability_histogram_visual(values:Sequence[float], *, title:str='Capability distribution', bins:int=20, lsl:float|None=None, usl:float|None=None, target:float|None=None)->SemiconductorVisualPlan:
    histogram=capability_histogram(values,bins)
    # Histogram bars use numeric bin centers. This keeps specification markers
    # in the same coordinate system as the measurement axis.
    points=tuple({'measurement': (lo + hi) / 2 if hi != lo else lo, 'count': count, 'start': lo, 'end': hi} for lo,hi,count in histogram)
    spec=ChartPanelSpec(title=title,kind=ChartKind.HISTOGRAM,x_axis=AxisSpec(label='Measurement',unit='nm',kind=AxisType.VALUE),y_axis=AxisSpec(label='Count',kind=AxisType.VALUE),legend=LegendPosition.HIDDEN)
    limits=SpecLimits(lsl,usl,target) if any(v is not None for v in (lsl,usl,target)) else None
    return SemiconductorVisualPlan(spec,(SeriesSpec('count','Count',points,kind=ChartKind.HISTOGRAM,x_key='measurement',y_key='count'),),spec_limits=limits,metadata={'bins':bins,'distribution':'histogram','numeric_x':True})

def qq_probability_visual(values:Sequence[float], *, title:str='Normal probability plot')->SemiconductorVisualPlan:
    points=tuple({'theoretical':x,'observed':y} for x,y in qq_points(values))
    observed=tuple(point['observed'] for point in points)
    mean=fmean(observed); sigma=stdev(observed) if len(observed)>1 else 1.0
    reference=tuple({'theoretical':point['theoretical'],'observed':mean + sigma * point['theoretical']} for point in points)
    spec=ChartPanelSpec(title=title,kind=ChartKind.SCATTER,x_axis=AxisSpec(label='Theoretical quantile',kind=AxisType.VALUE),y_axis=AxisSpec(label='Observed value',kind=AxisType.VALUE),selection=SelectionMode.BRUSH)
    return SemiconductorVisualPlan(spec,(SeriesSpec('qq','Observed',points,kind=ChartKind.SCATTER,x_key='theoretical',y_key='observed'),SeriesSpec('reference','Expected reference',reference,kind=ChartKind.LINE,x_key='theoretical',y_key='observed',marker=__import__('nicegui_base.visualization',fromlist=['MarkerShape']).MarkerShape.NONE,line_style=LineStyle.DASHED,semantic_color='neutral')),metadata={'distribution':'qq','reference':'location-scale fitted line'})

def ecdf_visual(values:Sequence[float], *, title:str='Empirical cumulative distribution')->SemiconductorVisualPlan:
    points=tuple({'value':x,'probability':p} for x,p in ecdf(values))
    spec=ChartPanelSpec(title=title,kind=ChartKind.LINE,x_axis=AxisSpec(label='Value',kind=AxisType.VALUE),y_axis=AxisSpec(label='Cumulative probability',kind=AxisType.VALUE,min_value=0,max_value=1),selection=SelectionMode.BRUSH)
    return SemiconductorVisualPlan(spec,(SeriesSpec('ecdf','ECDF',points,kind=ChartKind.LINE,x_key='value',y_key='probability',marker=__import__('nicegui_base.visualization',fromlist=['MarkerShape']).MarkerShape.NONE),),metadata={'distribution':'ecdf','step':'end'})

def box_distribution_visual(groups:Mapping[str,Sequence[float]], *, title:str='Distribution comparison')->SemiconductorVisualPlan:
    labels=tuple(str(label) for label in groups)
    summaries=tuple(box_distribution(groups[label]) for label in groups)
    data=tuple((summary.minimum,summary.q1,summary.median,summary.q3,summary.maximum) for summary in summaries)
    spec=ChartPanelSpec(title=title,kind=ChartKind.BOX_PLOT,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=labels),y_axis=AxisSpec(kind=AxisType.VALUE),selection=SelectionMode.SINGLE)
    return SemiconductorVisualPlan(spec,(SeriesSpec('box','Distribution',data,kind=ChartKind.BOX_PLOT),),metadata={'groups':labels,'counts':tuple(summary.count for summary in summaries)})

def distribution_density_visual(groups:Mapping[str,Sequence[float]], *, title:str='Distribution density', mode:str='violin', points:int=64)->SemiconductorVisualPlan:
    if mode not in {'violin','ridge','overlay'}: raise ValueError("mode must be 'violin', 'ridge', or 'overlay'")
    densities=ridge_distributions(groups,points=points)
    series=[]
    for label,density in densities.items():
        data=tuple({'value':point.value,'density':point.density} for point in density)
        series.append(SeriesSpec(str(label),str(label),data,kind=ChartKind.LINE,x_key='value',y_key='density',smooth=True))
    spec=ChartPanelSpec(title=title,kind=ChartKind.LINE,x_axis=AxisSpec(label='Value',kind=AxisType.VALUE),y_axis=AxisSpec(label='Density',kind=AxisType.VALUE),selection=SelectionMode.BRUSH)
    return SemiconductorVisualPlan(spec,tuple(series),metadata={'distribution':mode,'density_points':points,'renderer_hint':f'{mode}_density'})

def fdc_trace_visual(samples:Sequence[TraceSample], *, title:str='FDC trace', envelope:Sequence[GoldenEnvelopePoint]=(), events:Sequence[AlignedTraceEvent]=())->SemiconductorVisualPlan:
    groups=multi_sensor_panel(samples); series=[]
    for sensor,items in groups.items():
        data=tuple({'time':item.time,'value':item.value} for item in items)
        series.append(SeriesSpec(sensor,sensor,data,kind=ChartKind.LINE,x_key='time',y_key='value',marker=__import__('nicegui_base.visualization',fromlist=['MarkerShape']).MarkerShape.NONE))
    if envelope:
        for key,label,values in (('golden_mean','Golden mean',[p.mean for p in envelope]),('golden_lower','Golden lower',[p.lower for p in envelope]),('golden_upper','Golden upper',[p.upper for p in envelope])):
            data=tuple({'time':float(i),'value':float(v)} for i,v in enumerate(values)); series.append(SeriesSpec(key,label,data,kind=ChartKind.LINE,x_key='time',y_key='value',line_style=LineStyle.DASHED,semantic_color='neutral'))
    annotations=tuple(ChartAnnotation(event.sample_time,f'{event.event.kind}: {event.event.label}',intent=AnnotationIntent.WARNING if event.event.kind=='alarm' else AnnotationIntent.INFO) for event in events)
    spec=ChartPanelSpec(title=title,kind=ChartKind.LINE,x_axis=AxisSpec(label='Trace position / time',kind=AxisType.VALUE),y_axis=AxisSpec(label='Sensor value',kind=AxisType.VALUE),selection=SelectionMode.BRUSH)
    return SemiconductorVisualPlan(spec,tuple(series),annotations=annotations,metadata={'sensors':tuple(groups),'linked_hover':True,'event_count':len(events)})

def pca_scores_visual(result:PCAResult, *, labels:Sequence[str]|None=None,title:str='PCA scores')->SemiconductorVisualPlan:
    if len(result.loadings)<2: raise ValueError('PCA score plot requires at least two components')
    labels=tuple(labels) if labels is not None else tuple(str(i+1) for i in range(len(result.scores)))
    if len(labels)!=len(result.scores): raise ValueError('PCA labels must match score rows')
    data=tuple({'pc1':score[0],'pc2':score[1],'label':label} for score,label in zip(result.scores,labels))
    spec=ChartPanelSpec(title=title,kind=ChartKind.SCATTER,x_axis=AxisSpec(label='PC1',kind=AxisType.VALUE),y_axis=AxisSpec(label='PC2',kind=AxisType.VALUE),selection=SelectionMode.BRUSH)
    return SemiconductorVisualPlan(spec,(SeriesSpec('scores','Scores',data,kind=ChartKind.SCATTER,x_key='pc1',y_key='pc2'),),metadata={'labels':labels,'t2':result.t2,'spe':result.spe})

def pca_loadings_visual(result:PCAResult, *, feature_names:Sequence[str]|None=None,title:str='PCA loadings')->SemiconductorVisualPlan:
    count=len(result.means); names=tuple(feature_names) if feature_names is not None else tuple(f'F{i+1}' for i in range(count))
    if len(names)!=count: raise ValueError('feature_names must match PCA feature count')
    spec=ChartPanelSpec(title=title,kind=ChartKind.BAR,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=names),y_axis=AxisSpec(label='Loading',kind=AxisType.VALUE))
    series=tuple(SeriesSpec(f'pc{i+1}',f'PC{i+1}',loading,kind=ChartKind.BAR) for i,loading in enumerate(result.loadings))
    return SemiconductorVisualPlan(spec,series,metadata={'eigenvalues':result.eigenvalues})

def commonality_ranking_visual(items:Sequence[EnrichmentResult], *, title:str='Commonality ranking',top:int=12)->SemiconductorVisualPlan:
    ranked=tuple(sorted(items,key=lambda item:abs(item.score),reverse=True)[:top]); labels=tuple(f'{item.factor}={item.value}' for item in ranked)
    spec=ChartPanelSpec(title=title,kind=ChartKind.BAR,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=labels),y_axis=AxisSpec(label='Log odds enrichment',kind=AxisType.VALUE),selection=SelectionMode.SINGLE)
    return SemiconductorVisualPlan(spec,(SeriesSpec('enrichment','Enrichment',tuple(item.score for item in ranked),kind=ChartKind.BAR),),metadata={'items':ranked})

def matrix_visual(matrix:Mapping[str,Mapping[Any,float|None]], *, title:str='Commonality matrix')->SemiconductorVisualPlan:
    rows=tuple(matrix); columns=[]
    for values in matrix.values():
        for key in values:
            if key not in columns: columns.append(key)
    data=[]
    for y,row in enumerate(rows):
        for x,column in enumerate(columns):
            value=matrix[row].get(column)
            if value is not None: data.append((x,y,float(value)))
    spec=ChartPanelSpec(title=title,kind=ChartKind.HEATMAP,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(c) for c in columns)),y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=rows),selection=SelectionMode.SINGLE)
    return SemiconductorVisualPlan(spec,(SeriesSpec('matrix','Score',tuple(data),kind=ChartKind.HEATMAP),),metadata={'rows':rows,'columns':tuple(columns)})

def pareto_visual(items:Sequence[Mapping[str,Any]], *, title:str='Pareto',category_key:str='category',value_key:str='value',cumulative_key:str='cumulative')->SemiconductorVisualPlan:
    labels=tuple(str(item[category_key]) for item in items); values=tuple(float(item[value_key]) for item in items); cumulative=tuple(float(item[cumulative_key])*100 for item in items)
    spec=ChartPanelSpec(title=title,kind=ChartKind.PARETO,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=labels),y_axis=AxisSpec(label='Contribution',kind=AxisType.VALUE),selection=SelectionMode.SINGLE)
    series=(SeriesSpec('value','Contribution',values,kind=ChartKind.PARETO),SeriesSpec('cumulative','Cumulative %',cumulative,kind=ChartKind.LINE,y_axis_index=1,semantic_color='info'))
    return SemiconductorVisualPlan(spec,series,metadata={'categories':labels})

__all__=['SemiconductorVisualPlan','affected_control_visual','control_chart_visual','wafer_points','capability_histogram_visual','qq_probability_visual','ecdf_visual','box_distribution_visual','distribution_density_visual','fdc_trace_visual','pca_scores_visual','pca_loadings_visual','commonality_ranking_visual','matrix_visual','pareto_visual']
