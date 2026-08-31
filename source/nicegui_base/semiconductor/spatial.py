from __future__ import annotations
from dataclasses import dataclass, field
from math import atan2, degrees, hypot, isfinite
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

@dataclass(frozen=True,slots=True)
class WaferSample:
    x:float; y:float; value:float|None=None; wafer_id:str|None=None; category:str|None=None; defect_class:str|None=None; metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not isfinite(float(self.x)) or not isfinite(float(self.y)): raise ValueError('wafer coordinates must be finite')
        if self.value is not None and not isfinite(float(self.value)): raise ValueError('wafer value must be finite or None')
        object.__setattr__(self,'metadata',dict(self.metadata))

def _valued(points:Iterable[WaferSample])->tuple[WaferSample,...]: return tuple(p for p in points if p.value is not None)
def delta_wafer(affected:Sequence[WaferSample], control:Sequence[WaferSample], *, precision:int=6)->tuple[WaferSample,...]:
    c={(round(p.x,precision),round(p.y,precision)):p for p in control if p.value is not None}; out=[]
    for p in affected:
        q=c.get((round(p.x,precision),round(p.y,precision)))
        if p.value is not None and q is not None and q.value is not None: out.append(WaferSample(p.x,p.y,float(p.value)-float(q.value),p.wafer_id,metadata={'affected':p.value,'control':q.value}))
    return tuple(out)
def radial_profile(points:Iterable[WaferSample], *, bins:int=10)->tuple[dict,...]:
    pts=_valued(points)
    if bins<1: raise ValueError('bins must be >= 1')
    if not pts:return ()
    r=[hypot(p.x,p.y) for p in pts]; maxr=max(r) or 1.0; groups=[[] for _ in range(bins)]
    for p,rv in zip(pts,r): groups[min(bins-1,int(rv/maxr*bins))].append(float(p.value))
    return tuple({'ring':i,'r0':i*maxr/bins,'r1':(i+1)*maxr/bins,'mean':fmean(g) if g else None,'count':len(g)} for i,g in enumerate(groups))
def center_edge_decomposition(points:Iterable[WaferSample], *, center_fraction:float=.5)->dict[str,Any]:
    pts=_valued(points)
    if not 0<center_fraction<1: raise ValueError('center_fraction must be between 0 and 1')
    if not pts:return {'center_mean':None,'edge_mean':None,'delta':None,'center_count':0,'edge_count':0}
    maxr=max(hypot(p.x,p.y) for p in pts) or 1; c=[float(p.value) for p in pts if hypot(p.x,p.y)<=maxr*center_fraction]; e=[float(p.value) for p in pts if hypot(p.x,p.y)>maxr*center_fraction]
    cm=fmean(c) if c else None; em=fmean(e) if e else None
    return {'center_mean':cm,'edge_mean':em,'delta':None if cm is None or em is None else em-cm,'center_count':len(c),'edge_count':len(e)}
def ring_analysis(points:Iterable[WaferSample], *, rings:int=5)->tuple[dict,...]: return radial_profile(points,bins=rings)
def sector_analysis(points:Iterable[WaferSample], *, sectors:int=8)->tuple[dict,...]:
    pts=_valued(points)
    if sectors<1: raise ValueError('sectors must be >= 1')
    groups=[[] for _ in range(sectors)]
    for p in pts:
        a=(degrees(atan2(p.y,p.x))+360)%360; groups[min(sectors-1,int(a/360*sectors))].append(float(p.value))
    return tuple({'sector':i,'start_deg':i*360/sectors,'end_deg':(i+1)*360/sectors,'mean':fmean(g) if g else None,'count':len(g)} for i,g in enumerate(groups))
def lot_wafer_strip(points:Iterable[WaferSample])->dict[str,tuple[WaferSample,...]]:
    out={}
    for p in points: out.setdefault(p.wafer_id or 'unknown',[]).append(p)
    return {k:tuple(v) for k,v in out.items()}
def defect_clusters(points:Iterable[WaferSample], *, radius:float=2.0, min_points:int=2, same_class:bool=True)->tuple[tuple[int,...],...]:
    if radius<=0 or min_points<1: raise ValueError('defect clustering requires radius > 0 and min_points >= 1')
    pts=tuple(points); seen=set(); clusters=[]
    for i,p in enumerate(pts):
        if i in seen or not p.defect_class: continue
        stack=[i]; cluster=[]; seen.add(i)
        while stack:
            j=stack.pop(); cluster.append(j); q=pts[j]
            for k,r in enumerate(pts):
                if k not in seen and r.defect_class and (not same_class or r.defect_class==q.defect_class) and hypot(q.x-r.x,q.y-r.y)<=radius: seen.add(k); stack.append(k)
        if len(cluster)>=min_points: clusters.append(tuple(cluster))
    return tuple(clusters)
def contour_grid(points:Iterable[WaferSample], *, cells:int=20)->tuple[tuple[float|None,...],...]:
    pts=_valued(points)
    if cells<2: raise ValueError('cells must be >= 2')
    if not pts:return ()
    minx,maxx=min(p.x for p in pts),max(p.x for p in pts); miny,maxy=min(p.y for p in pts),max(p.y for p in pts); dx=(maxx-minx or 1)/cells;dy=(maxy-miny or 1)/cells
    grid=[[[] for _ in range(cells)] for _ in range(cells)]
    for p in pts:
        ix=min(cells-1,int((p.x-minx)/dx));iy=min(cells-1,int((p.y-miny)/dy));grid[iy][ix].append(float(p.value))
    return tuple(tuple(fmean(c) if c else None for c in row) for row in grid)
def wafer_comparison(affected:Iterable[WaferSample],control:Iterable[WaferSample])->dict[str,Any]:
    a=_valued(affected);c=_valued(control); av=fmean(float(p.value) for p in a) if a else None;cv=fmean(float(p.value) for p in c) if c else None
    return {'affected_mean':av,'control_mean':cv,'delta':None if av is None or cv is None else av-cv,'affected_count':len(a),'control_count':len(c)}

__all__=['WaferSample','delta_wafer','radial_profile','center_edge_decomposition','ring_analysis','sector_analysis','lot_wafer_strip','defect_clusters','contour_grid','wafer_comparison']
