from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import fmean, stdev
from typing import Iterable, Mapping, Sequence

@dataclass(frozen=True,slots=True)
class TraceSample:
    time:float; value:float; sensor:str; step:str|None=None; tool:str|None=None; chamber:str|None=None
    def __post_init__(self):
        if not isfinite(float(self.time)) or not isfinite(float(self.value)): raise ValueError('trace sample time/value must be finite')
        if not str(self.sensor).strip(): raise ValueError('trace sample sensor is required')
@dataclass(frozen=True,slots=True)
class GoldenEnvelopePoint:
    position:int; mean:float; lower:float; upper:float; count:int
@dataclass(frozen=True,slots=True)
class PCAResult:
    means:tuple[float,...]; scales:tuple[float,...]; loadings:tuple[tuple[float,...],...]; scores:tuple[tuple[float,...],...]; eigenvalues:tuple[float,...]; t2:tuple[float,...]; spe:tuple[float,...]
@dataclass(frozen=True,slots=True)
class TraceEvent:
    time:float; label:str; kind:str='event'; tool:str|None=None; chamber:str|None=None
    def __post_init__(self):
        if not isfinite(float(self.time)): raise ValueError('trace event time must be finite')
        if not str(self.label).strip(): raise ValueError('trace event label is required')
        if not str(self.kind).strip(): raise ValueError('trace event kind is required')
@dataclass(frozen=True,slots=True)
class AlignedTraceEvent:
    sample_index:int; sample_time:float; event:TraceEvent; offset:float

def multi_sensor_panel(samples:Sequence[TraceSample])->dict[str,tuple[TraceSample,...]]:
    groups={}
    for sample in samples:
        if not isfinite(float(sample.time)) or not isfinite(float(sample.value)): raise ValueError('trace samples must contain finite time/value')
        groups.setdefault(sample.sensor,[]).append(sample)
    return {sensor:tuple(sorted(items,key=lambda item:item.time)) for sensor,items in groups.items()}

def align_trace_events(samples:Sequence[TraceSample],events:Sequence[TraceEvent], *, max_offset:float|None=None)->tuple[AlignedTraceEvent,...]:
    if max_offset is not None and max_offset<0: raise ValueError('max_offset must be >= 0')
    if not samples:return ()
    ordered=tuple(sorted(samples,key=lambda s:s.time)); out=[]
    for event in events:
        if not isfinite(float(event.time)): raise ValueError('event time must be finite')
        idx=min(range(len(ordered)),key=lambda i:abs(ordered[i].time-event.time)); offset=ordered[idx].time-event.time
        if max_offset is None or abs(offset)<=max_offset: out.append(AlignedTraceEvent(idx,ordered[idx].time,event,offset))
    return tuple(out)

def align_recipe_steps(traces:Mapping[str,Sequence[TraceSample]])->dict[str,dict[str,tuple[TraceSample,...]]]:
    out={}
    for trace_id,samples in traces.items():
        steps={}
        for s in sorted(samples,key=lambda x:x.time): steps.setdefault(s.step or 'unlabeled',[]).append(s)
        out[trace_id]={k:tuple(v) for k,v in steps.items()}
    return out

def golden_trace_envelope(traces:Sequence[Sequence[float]], *, sigma:float=3.0)->tuple[GoldenEnvelopePoint,...]:
    if sigma<=0 or not isfinite(float(sigma)): raise ValueError('sigma must be positive and finite')
    if not traces:return ()
    width=len(traces[0])
    if width<1 or any(len(trace)!=width for trace in traces): raise ValueError('golden trace envelope requires equal-length aligned traces')
    out=[]
    for i in range(width):
        vals=[]
        for trace_index,trace in enumerate(traces):
            try:value=float(trace[i])
            except (TypeError,ValueError) as exc: raise ValueError(f'trace {trace_index} contains non-numeric value at position {i}') from exc
            if not isfinite(value): raise ValueError(f'trace {trace_index} contains nonfinite value at position {i}')
            vals.append(value)
        m=fmean(vals); s=stdev(vals) if len(vals)>1 else 0.0; out.append(GoldenEnvelopePoint(i,m,m-sigma*s,m+sigma*s,len(vals)))
    return tuple(out)
def _feature_matrix(rows:Sequence[Mapping[str,float|str]], features:Sequence[str])->tuple[tuple[float,...],...]:
    if not features: raise ValueError('at least one feature is required')
    out=[]
    for row_index,row in enumerate(rows):
        values=[]
        for feature in features:
            if feature not in row: raise ValueError(f'missing feature {feature!r} in row {row_index}')
            try:value=float(row[feature])
            except (TypeError,ValueError) as exc: raise ValueError(f'feature {feature!r} must be numeric') from exc
            if not isfinite(value): raise ValueError(f'feature {feature!r} must contain only finite values')
            values.append(value)
        out.append(tuple(values))
    return tuple(out)

def normalized_fingerprint(rows:Sequence[Mapping[str,float]], features:Sequence[str])->tuple[dict[str,float],...]:
    if not rows:return ()
    matrix=_feature_matrix(rows,features)
    means={feature:fmean(row[index] for row in matrix) for index,feature in enumerate(features)}
    scales={feature:(stdev(row[index] for row in matrix) if len(matrix)>1 else 0) for index,feature in enumerate(features)}
    return tuple({feature:0.0 if scales[feature]==0 else (row[index]-means[feature])/scales[feature] for index,feature in enumerate(features)} for row in matrix)

def compare_groups(rows:Sequence[Mapping[str,float|str]], *, group_field:str, features:Sequence[str])->dict[str,dict[str,float]]:
    if not features: raise ValueError('at least one feature is required')
    matrix=_feature_matrix(rows,features) if rows else ()
    groups:dict[str,list[tuple[float,...]]]={}
    for row_index,(row,values) in enumerate(zip(rows,matrix)):
        if group_field not in row or row[group_field] is None or not str(row[group_field]).strip(): raise ValueError(f'missing group field {group_field!r} in row {row_index}')
        groups.setdefault(str(row[group_field]),[]).append(values)
    return {group:{feature:fmean(values[index] for values in group_rows) for index,feature in enumerate(features)} for group,group_rows in groups.items()}

def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _norm(a):return sqrt(_dot(a,a))
def _mat_vec(m,v):return [_dot(row,v) for row in m]
def _power_eigen(cov, *, iterations=100, tol=1e-10):
    n=len(cov); v=[1/sqrt(n)]*n; last=0.0
    for _ in range(iterations):
        w=_mat_vec(cov,v); norm=_norm(w)
        if norm==0:return 0.0,[0.0]*n
        v=[x/norm for x in w]; eig=_dot(v,_mat_vec(cov,v))
        if abs(eig-last)<tol:break
        last=eig
    return eig,v

def pca(matrix:Sequence[Sequence[float]], *, components:int=2, standardize:bool=True)->PCAResult:
    rows=[tuple(float(v) for v in r) for r in matrix]
    if len(rows)<2: raise ValueError('PCA requires at least 2 rows')
    p=len(rows[0])
    if p<1 or any(len(r)!=p for r in rows): raise ValueError('PCA matrix must be rectangular and non-empty')
    if any(not isfinite(v) for r in rows for v in r): raise ValueError('PCA matrix must contain only finite values')
    components=max(1,min(int(components),p))
    means=tuple(fmean(r[j] for r in rows) for j in range(p)); scales=[]
    for j in range(p):
        s=stdev(r[j] for r in rows) if len(rows)>1 else 1.0; scales.append(s if standardize and s>0 else 1.0)
    z=[[ (r[j]-means[j])/scales[j] for j in range(p)] for r in rows]
    cov=[[sum(r[a]*r[b] for r in z)/(len(z)-1) for b in range(p)] for a in range(p)]
    work=[row[:] for row in cov]; eigs=[]; loads=[]
    for _ in range(components):
        eig,v=_power_eigen(work); eig=max(0.0,eig); eigs.append(eig); loads.append(tuple(v))
        for i in range(p):
            for j in range(p): work[i][j]-=eig*v[i]*v[j]
    scores=tuple(tuple(_dot(r,v) for v in loads) for r in z)
    recon=[]; spe=[]; t2=[]
    for r,score in zip(z,scores):
        rr=[sum(score[k]*loads[k][j] for k in range(len(loads))) for j in range(p)]; recon.append(rr); spe.append(sum((r[j]-rr[j])**2 for j in range(p)))
        t2.append(sum((score[k]**2/eigs[k]) if eigs[k]>1e-12 else 0 for k in range(len(eigs))))
    return PCAResult(means,tuple(scales),tuple(loads),scores,tuple(eigs),tuple(t2),tuple(spe))
def hotelling_t2(result:PCAResult)->tuple[float,...]: return result.t2
def spe_q(result:PCAResult)->tuple[float,...]: return result.spe

def chamber_fingerprint(rows:Sequence[Mapping[str,float|str]],features:Sequence[str], *, chamber_field:str='chamber')->dict[str,dict[str,float]]: return compare_groups(rows,group_field=chamber_field,features=features)
def sensor_fingerprint(rows:Sequence[Mapping[str,float|str]],features:Sequence[str], *, sensor_field:str='sensor')->dict[str,dict[str,float]]: return compare_groups(rows,group_field=sensor_field,features=features)
def tool_chamber_comparison(rows:Sequence[Mapping[str,float|str]],features:Sequence[str], *, field:str='chamber')->dict[str,dict[str,float]]: return compare_groups(rows,group_field=field,features=features)

__all__=['TraceSample','GoldenEnvelopePoint','PCAResult','TraceEvent','AlignedTraceEvent','multi_sensor_panel','align_trace_events','align_recipe_steps','golden_trace_envelope','normalized_fingerprint','compare_groups','pca','hotelling_t2','spe_q','chamber_fingerprint','sensor_fingerprint','tool_chamber_comparison']
