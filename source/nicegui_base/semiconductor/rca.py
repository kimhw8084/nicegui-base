from __future__ import annotations
from dataclasses import dataclass,field
from math import isfinite,log,sqrt
from statistics import fmean
from typing import Any,Iterable,Mapping,Sequence

@dataclass(frozen=True,slots=True)
class EnrichmentResult:
    factor:str; value:Any; affected_exposed:int; affected_total:int; control_exposed:int; control_total:int; affected_rate:float; control_rate:float; risk_ratio:float|None; odds_ratio:float|None; score:float
@dataclass(frozen=True,slots=True)
class GraphEdge:
    source:str; target:str; label:str|None=None; weight:float=1.0; metadata:Mapping[str,Any]=field(default_factory=dict)
@dataclass(frozen=True,slots=True)
class PopulationComparison:
    field:str; affected_count:int; control_count:int; affected_mean:float|None; control_mean:float|None; delta:float|None; standardized_difference:float|None

def population_comparison(affected:Sequence[Mapping[str,Any]],control:Sequence[Mapping[str,Any]],field:str)->PopulationComparison:
    def finite(rows):
        values=[]
        for row in rows:
            value=row.get(field)
            if value is None: continue
            try: numeric=float(value)
            except (TypeError,ValueError) as exc: raise ValueError(f'{field} must be numeric for population comparison') from exc
            if not isfinite(numeric): raise ValueError(f'{field} must contain only finite values')
            values.append(numeric)
        return values
    av=finite(affected); cv=finite(control); am=fmean(av) if av else None; cm=fmean(cv) if cv else None
    delta=None if am is None or cm is None else am-cm
    pooled=None
    if len(av)>1 and len(cv)>1:
        va=sum((x-am)**2 for x in av)/(len(av)-1); vc=sum((x-cm)**2 for x in cv)/(len(cv)-1); pooled=sqrt((va+vc)/2)
    standardized=None if delta is None or not pooled else delta/pooled
    return PopulationComparison(field,len(av),len(cv),am,cm,delta,standardized)

def enrichment(affected:Sequence[Mapping[str,Any]],control:Sequence[Mapping[str,Any]],factor:str)->tuple[EnrichmentResult,...]:
    vals=[]
    for row in affected+control:
        v=row.get(factor)
        if v not in vals:vals.append(v)
    out=[]; at=len(affected);ct=len(control)
    for v in vals:
        ae=sum(r.get(factor)==v for r in affected);ce=sum(r.get(factor)==v for r in control); ar=ae/at if at else 0; cr=ce/ct if ct else 0
        rr=(ar/cr if cr>0 else None); a=ae+.5;b=at-ae+.5;c=ce+.5;d=ct-ce+.5; odds=(a*d)/(b*c); score=log(odds) if odds>0 else 0
        out.append(EnrichmentResult(factor,v,ae,at,ce,ct,ar,cr,rr,odds,score))
    return tuple(sorted(out,key=lambda x:abs(x.score),reverse=True))
def commonality_ranking(affected:Sequence[Mapping[str,Any]],control:Sequence[Mapping[str,Any]],factors:Sequence[str])->tuple[EnrichmentResult,...]:
    items=[x for f in factors for x in enrichment(affected,control,f)]; return tuple(sorted(items,key=lambda x:abs(x.score),reverse=True))
def commonality_matrix(affected:Sequence[Mapping[str,Any]],control:Sequence[Mapping[str,Any]],factors:Sequence[str])->dict[str,dict[Any,float]]:
    return {f:{r.value:r.score for r in enrichment(affected,control,f)} for f in factors}
def contribution_waterfall(items:Sequence[EnrichmentResult], *, top:int=10)->tuple[dict[str,Any],...]:
    ordered=sorted(items,key=lambda r:abs(r.score),reverse=True)[:top]; running=0;out=[]
    for r in ordered:
        start=running;running+=r.score;out.append({'label':f'{r.factor}={r.value}','start':start,'delta':r.score,'end':running})
    return tuple(out)
def _pearson(x,y):
    if len(x)<2:return None
    mx=fmean(x);my=fmean(y);num=sum((a-mx)*(b-my) for a,b in zip(x,y));dx=sqrt(sum((a-mx)**2 for a in x));dy=sqrt(sum((b-my)**2 for b in y));return None if dx==0 or dy==0 else num/(dx*dy)
def correlation_matrix(rows:Sequence[Mapping[str,Any]],fields:Sequence[str])->dict[str,dict[str,float|None]]:
    out={}
    for a in fields:
        out[a]={}
        for b in fields:
            pairs=[]
            for r in rows:
                if r.get(a) is None or r.get(b) is None: continue
                try: x,y=float(r[a]),float(r[b])
                except (TypeError,ValueError) as exc: raise ValueError(f'correlation fields {a}/{b} must be numeric') from exc
                if not isfinite(x) or not isfinite(y): raise ValueError(f'correlation fields {a}/{b} must contain only finite values')
                pairs.append((x,y))
            out[a][b]=_pearson([x for x,_ in pairs],[y for _,y in pairs]) if pairs else None
    return out
def evidence_matrix(hypotheses:Sequence[str], evidence:Sequence[Mapping[str,Any]])->dict[str,dict[str,float]]:
    labels=tuple(str(h).strip() for h in hypotheses)
    if any(not label for label in labels): raise ValueError('hypothesis labels must be non-empty')
    if len(set(labels))!=len(labels): raise ValueError('hypothesis labels must be unique')
    out={label:{} for label in labels}
    for index,item in enumerate(evidence):
        if 'hypothesis' not in item: raise ValueError(f'evidence row {index} is missing hypothesis')
        hypothesis=str(item['hypothesis']).strip()
        if hypothesis not in out: raise ValueError(f'evidence row {index} references unknown hypothesis {hypothesis!r}')
        key=str(item.get('key') or item.get('evidence') or f'evidence_{index+1}').strip()
        if not key: raise ValueError(f'evidence row {index} requires a key')
        try: direction=float(item.get('direction',1)); strength=float(item.get('strength',1))
        except (TypeError,ValueError) as exc: raise ValueError(f'evidence row {index} direction/strength must be numeric') from exc
        if not isfinite(direction) or not isfinite(strength): raise ValueError(f'evidence row {index} direction/strength must be finite')
        out[hypothesis][key]=direction*strength
    return out
def genealogy_graph(rows:Sequence[Mapping[str,Any]], chain:Sequence[str])->tuple[GraphEdge,...]:
    seen=set();out=[]
    for r in rows:
        vals=[r.get(k) for k in chain]
        for a,b,la,lb in zip(vals,vals[1:],chain,chain[1:]):
            if a is None or b is None:continue
            key=(f'{la}:{a}',f'{lb}:{b}')
            if key not in seen:seen.add(key);out.append(GraphEdge(key[0],key[1],f'{la}→{lb}'))
    return tuple(out)
def cause_tree(root:str, branches:Mapping[str,Sequence[str]])->tuple[GraphEdge,...]:
    out=[]
    for branch,leaves in branches.items():out.append(GraphEdge(root,branch,'cause'));out.extend(GraphEdge(branch,str(x),'candidate') for x in leaves)
    return tuple(out)
def fault_tree(root:str, gates:Mapping[str,Sequence[str]])->tuple[GraphEdge,...]:
    root=str(root).strip()
    if not root: raise ValueError('fault-tree root is required')
    out=[]
    for gate,conditions in gates.items():
        gate_name=str(gate).strip()
        if not gate_name: raise ValueError('fault-tree gate names must be non-empty')
        gate_node=f'gate:{gate_name}'
        out.append(GraphEdge(root,gate_node,'gate',metadata={'gate':gate_name}))
        for condition in conditions:
            condition_name=str(condition).strip()
            if not condition_name: raise ValueError('fault-tree conditions must be non-empty')
            out.append(GraphEdge(gate_node,condition_name,'condition',metadata={'gate':gate_name}))
    return tuple(out)
def sankey_process_flow(rows:Sequence[Mapping[str,Any]],chain:Sequence[str])->tuple[GraphEdge,...]:
    counts={}
    for row in rows:
        values=[row.get(k) for k in chain]
        for a,b,la,lb in zip(values,values[1:],chain,chain[1:]):
            if a is None or b is None: continue
            key=(f'{la}:{a}',f'{lb}:{b}',f'{la}→{lb}')
            counts[key]=counts.get(key,0)+1
    return tuple(GraphEdge(a,b,l,float(w)) for (a,b,l),w in sorted(counts.items()))

__all__=['EnrichmentResult','GraphEdge','PopulationComparison','population_comparison','enrichment','commonality_ranking','commonality_matrix','contribution_waterfall','correlation_matrix','evidence_matrix','genealogy_graph','cause_tree','fault_tree','sankey_process_flow']
