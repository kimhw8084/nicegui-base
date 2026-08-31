from __future__ import annotations
from dataclasses import dataclass
from math import exp,isfinite,log
from statistics import fmean
from typing import Any,Mapping,Sequence

@dataclass(frozen=True,slots=True)
class WeibullResult:
    count:int; beta:float; eta:float; r2:float; failures:int; censored:int; method:str='median_rank_regression'
    def reliability(self,time:float)->float:
        t=float(time)
        if t<0: raise ValueError('reliability time must be >= 0')
        return exp(-((t/self.eta)**self.beta))
    def cdf(self,time:float)->float:return 1.0-self.reliability(time)
@dataclass(frozen=True,slots=True)
class ResponseSurfaceResult:
    terms:tuple[str,...]; coefficients:tuple[float,...]; factor_a:str; factor_b:str
    def predict(self,a:float,b:float)->float:
        c=self.coefficients; a=_finite_number(a,self.factor_a); b=_finite_number(b,self.factor_b)
        return c[0]+c[1]*a+c[2]*b+c[3]*a*b+c[4]*a*a+c[5]*b*b

def _finite_number(value:Any,label:str)->float:
    try: numeric=float(value)
    except (TypeError,ValueError) as exc: raise ValueError(f'{label} must be numeric') from exc
    if not isfinite(numeric): raise ValueError(f'{label} must be finite')
    return numeric

def yield_pareto(rows:Sequence[Mapping[str,Any]], *, category:str='bin', value:str='count')->tuple[dict[str,Any],...]:
    agg={}
    for index,row in enumerate(rows):
        if category not in row: raise ValueError(f'missing yield category {category!r} in row {index}')
        if value not in row: raise ValueError(f'missing yield value {value!r} in row {index}')
        amount=_finite_number(row[value],f'{value} at row {index}')
        if amount<0: raise ValueError('Pareto contribution values must be nonnegative')
        agg[row[category]]=agg.get(row[category],0)+amount
    total=sum(agg.values());running=0;out=[]
    for k,v in sorted(agg.items(),key=lambda kv:kv[1],reverse=True):running+=v;out.append({'category':k,'value':v,'cumulative':running/total if total else 0})
    return tuple(out)
def bin_pareto(rows:Sequence[Mapping[str,Any]], **kwargs): return yield_pareto(rows,**kwargs)
def yield_waterfall(steps:Sequence[tuple[str,float]], *, start:float=100.0)->tuple[dict[str,float|str],...]:
    cur=_finite_number(start,'waterfall start');out=[]
    for index,(label,delta) in enumerate(steps):
        if not str(label).strip(): raise ValueError(f'waterfall step {index} requires a label')
        numeric=_finite_number(delta,f'waterfall delta at step {index}'); before=cur; cur+=numeric
        out.append({'label':label,'start':before,'delta':numeric,'end':cur})
    return tuple(out)
def weibull_analysis(times:Sequence[float], *, failures:Sequence[bool]|None=None)->WeibullResult:
    if failures is not None and len(failures)!=len(times): raise ValueError('failures must match times length')
    records=[]
    for i,t in enumerate(times):
        value=float(t)
        if not isfinite(value) or value<=0: raise ValueError('Weibull times must be positive finite values')
        records.append((value,True if failures is None else bool(failures[i])))
    records.sort(key=lambda item:item[0]); failure_count=sum(flag for _,flag in records); censored=len(records)-failure_count
    if failure_count<2:raise ValueError('Weibull analysis requires at least 2 positive failures')
    # Johnson adjusted ranks preserve right-censored observations in the risk set
    # while retaining the dependency-free median-rank probability-plot estimator.
    n=len(records); adjusted=0.0; points=[]
    for position,(time,event) in enumerate(records,1):
        if not event: continue
        reverse_rank=n-position+1
        adjusted=adjusted+(n+1-adjusted)/(reverse_rank+1)
        f=(adjusted-.3)/(n+.4)
        f=min(1-1e-12,max(1e-12,f));points.append((time,f))
    xs=[log(t) for t,_ in points];ys=[log(-log(1-f)) for _,f in points]
    mx=fmean(xs);my=fmean(ys);den=sum((x-mx)**2 for x in xs)
    if den==0:raise ValueError('Weibull times are degenerate')
    beta=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den
    if not isfinite(beta) or beta<=0: raise ValueError('Weibull shape estimate is not positive')
    intercept=my-beta*mx;eta=exp(-intercept/beta)
    pred=[intercept+beta*x for x in xs];ssr=sum((y-p)**2 for y,p in zip(ys,pred));sst=sum((y-my)**2 for y in ys);r2=1-ssr/sst if sst else 1.0
    return WeibullResult(n,beta,eta,r2,failure_count,censored,'johnson_adjusted_rank_regression' if censored else 'median_rank_regression')
def doe_main_effects(rows:Sequence[Mapping[str,Any]], factors:Sequence[str], response:str)->dict[str,dict[Any,float]]:
    if not factors: raise ValueError('DOE main effects require at least one factor')
    out={}
    for factor in factors:
        levels={}
        for index,row in enumerate(rows):
            if factor not in row or response not in row: raise ValueError(f'DOE row {index} is missing factor/response fields')
            levels.setdefault(row[factor],[]).append(_finite_number(row[response],f'{response} at row {index}'))
        out[factor]={level:fmean(values) for level,values in levels.items()}
    return out
def doe_interactions(rows:Sequence[Mapping[str,Any]], factor_a:str,factor_b:str,response:str)->dict[Any,dict[Any,float]]:
    groups={}
    for index,row in enumerate(rows):
        if factor_a not in row or factor_b not in row or response not in row: raise ValueError(f'DOE row {index} is missing factor/response fields')
        groups.setdefault(row[factor_a],{}).setdefault(row[factor_b],[]).append(_finite_number(row[response],f'{response} at row {index}'))
    return {a:{b:fmean(values) for b,values in bs.items()} for a,bs in groups.items()}
def _solve(a,b):
    n=len(b);m=[list(map(float,a[i]))+[float(b[i])] for i in range(n)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(m[r][col]))
        if abs(m[pivot][col])<1e-12:raise ValueError('response-surface design matrix is singular')
        m[col],m[pivot]=m[pivot],m[col];p=m[col][col];m[col]=[x/p for x in m[col]]
        for r in range(n):
            if r==col:continue
            f=m[r][col];m[r]=[m[r][c]-f*m[col][c] for c in range(n+1)]
    return tuple(m[i][-1] for i in range(n))
def response_surface(rows:Sequence[Mapping[str,Any]], factor_a:str,factor_b:str,response:str)->ResponseSurfaceResult:
    if len(rows)<6:raise ValueError('quadratic response surface requires at least 6 runs')
    x=[];y=[]
    for index,row in enumerate(rows):
        if factor_a not in row or factor_b not in row or response not in row: raise ValueError(f'response-surface row {index} is missing factor/response fields')
        a=_finite_number(row[factor_a],f'{factor_a} at row {index}'); b=_finite_number(row[factor_b],f'{factor_b} at row {index}'); response_value=_finite_number(row[response],f'{response} at row {index}')
        x.append((1,a,b,a*b,a*a,b*b));y.append(response_value)
    p=6;xtx=[[sum(row[i]*row[j] for row in x) for j in range(p)] for i in range(p)];xty=[sum(row[i]*yy for row,yy in zip(x,y)) for i in range(p)];coef=_solve(xtx,xty)
    return ResponseSurfaceResult(('intercept',factor_a,factor_b,f'{factor_a}:{factor_b}',f'{factor_a}^2',f'{factor_b}^2'),coef,factor_a,factor_b)

__all__=['WeibullResult','ResponseSurfaceResult','yield_pareto','bin_pareto','yield_waterfall','weibull_analysis','doe_main_effects','doe_interactions','response_surface']
