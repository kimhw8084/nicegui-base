from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import erf, exp, gamma, isfinite, log, pi, sqrt
from statistics import NormalDist, fmean, stdev
from typing import Iterable, Mapping, Sequence


class SPCInputError(ValueError): pass
class ControlChartFamily(str,Enum):
    I_MR='i_mr'; XBAR_R='xbar_r'; XBAR_S='xbar_s'; P='p'; NP='np'; C='c'; U='u'; EWMA='ewma'; CUSUM='cusum'

@dataclass(frozen=True,slots=True)
class RuleViolation:
    rule_set:str; rule:str; indices:tuple[int,...]; message:str
@dataclass(frozen=True,slots=True)
class ControlChartResult:
    family:ControlChartFamily; values:tuple[float,...]; center:tuple[float,...]; ucl:tuple[float,...]; lcl:tuple[float,...]
    secondary_values:tuple[float,...]=(); secondary_center:tuple[float,...]=(); secondary_ucl:tuple[float,...]=(); secondary_lcl:tuple[float,...]=()
    sigma:float|None=None; violations:tuple[RuleViolation,...]=(); excluded_indices:tuple[int,...]=(); metadata:dict=field(default_factory=dict)
    # CUSUM has two independent signed accumulators.  These fields were added
    # after the original result contract so positional construction of the
    # other chart families remains backwards compatible.
    positive_values:tuple[float,...]=(); negative_values:tuple[float,...]=()

    @property
    def c_plus(self)->tuple[float,...]:
        return self.positive_values

    @property
    def c_minus(self)->tuple[float,...]:
        return self.negative_values
@dataclass(frozen=True,slots=True)
class CapabilityResult:
    count:int; mean:float; within_sigma:float|None; overall_sigma:float|None; cp:float|None; cpk:float|None; pp:float|None; ppk:float|None; lsl:float|None; usl:float|None; target:float|None
    within_method:str='moving_range'; overall_method:str='sample_stdev'
@dataclass(frozen=True,slots=True)
class BoxSummary:
    count:int; minimum:float; q1:float; median:float; q3:float; maximum:float
@dataclass(frozen=True,slots=True)
class DensityPoint:
    value:float; density:float


def _clean(values:Iterable[float|None])->tuple[tuple[float,...],tuple[int,...]]:
    out=[]; excluded=[]
    for i,v in enumerate(values):
        if v is None or isinstance(v,bool): excluded.append(i); continue
        try: x=float(v)
        except (TypeError,ValueError): excluded.append(i); continue
        if not isfinite(x): excluded.append(i); continue
        out.append(x)
    return tuple(out),tuple(excluded)
def _need(values:Sequence[float],n:int,label:str):
    if len(values)<n: raise SPCInputError(f'{label} requires at least {n} finite observations')
def _repeat(v:float,n:int)->tuple[float,...]: return tuple(v for _ in range(n))
def _sample_sigma(values:Sequence[float])->float|None:
    if len(values)<2:return None
    s=stdev(values); return s if s>0 and isfinite(s) else None


def detect_western_electric(values:Sequence[float], center:float, sigma:float)->tuple[RuleViolation,...]:
    if sigma<=0 or not isfinite(sigma): return ()
    z=[(float(v)-center)/sigma for v in values]; out=[]
    for i,a in enumerate(z):
        if abs(a)>3: out.append(RuleViolation('western_electric','WE1',(i,),'1 point beyond 3σ'))
    for i in range(len(z)-2):
        w=z[i:i+3]
        for sign in (1,-1):
            idx=tuple(i+j for j,a in enumerate(w) if sign*a>2)
            if len(idx)>=2: out.append(RuleViolation('western_electric','WE2',idx,'2 of 3 points beyond 2σ on one side'))
    for i in range(len(z)-4):
        w=z[i:i+5]
        for sign in (1,-1):
            idx=tuple(i+j for j,a in enumerate(w) if sign*a>1)
            if len(idx)>=4: out.append(RuleViolation('western_electric','WE3',idx,'4 of 5 points beyond 1σ on one side'))
    for i in range(len(z)-7):
        w=z[i:i+8]
        if all(a>0 for a in w) or all(a<0 for a in w): out.append(RuleViolation('western_electric','WE4',tuple(range(i,i+8)),'8 points on one side'))
    return tuple(out)


def detect_nelson(values:Sequence[float], center:float, sigma:float)->tuple[RuleViolation,...]:
    if sigma<=0 or not isfinite(sigma): return ()
    z=[(float(v)-center)/sigma for v in values]; out=[]
    for i,a in enumerate(z):
        if abs(a)>3: out.append(RuleViolation('nelson','N1',(i,),'1 point beyond 3σ'))
    for i in range(len(z)-8):
        w=z[i:i+9]
        if all(a>0 for a in w) or all(a<0 for a in w): out.append(RuleViolation('nelson','N2',tuple(range(i,i+9)),'9 points on one side'))
    for i in range(len(z)-5):
        w=z[i:i+6]; d=[w[j+1]-w[j] for j in range(5)]
        if all(a>0 for a in d) or all(a<0 for a in d): out.append(RuleViolation('nelson','N3',tuple(range(i,i+6)),'6 points continuously increasing/decreasing'))
    for i in range(len(z)-13):
        w=z[i:i+14]; d=[w[j+1]-w[j] for j in range(13)]
        if all(d[j]*d[j+1]<0 for j in range(12)): out.append(RuleViolation('nelson','N4',tuple(range(i,i+14)),'14 points alternating'))
    for i in range(len(z)-2):
        w=z[i:i+3]
        for sign in (1,-1):
            idx=tuple(i+j for j,a in enumerate(w) if sign*a>2)
            if len(idx)>=2: out.append(RuleViolation('nelson','N5',idx,'2 of 3 beyond 2σ'))
    for i in range(len(z)-4):
        w=z[i:i+5]
        for sign in (1,-1):
            idx=tuple(i+j for j,a in enumerate(w) if sign*a>1)
            if len(idx)>=4: out.append(RuleViolation('nelson','N6',idx,'4 of 5 beyond 1σ'))
    for i in range(len(z)-14):
        w=z[i:i+15]
        if all(abs(a)<1 for a in w): out.append(RuleViolation('nelson','N7',tuple(range(i,i+15)),'15 points within 1σ'))
    for i in range(len(z)-7):
        w=z[i:i+8]
        if all(abs(a)>1 for a in w) and any(a>0 for a in w) and any(a<0 for a in w): out.append(RuleViolation('nelson','N8',tuple(range(i,i+8)),'8 points outside 1σ on both sides'))
    return tuple(out)


def _violations(values,center,sigma): return detect_western_electric(values,center,sigma)+detect_nelson(values,center,sigma)
def _violations_z(z:Sequence[float]): return detect_western_electric(z,0.0,1.0)+detect_nelson(z,0.0,1.0)

def i_mr(values:Iterable[float|None])->ControlChartResult:
    x,excluded=_clean(values); _need(x,2,'I-MR')
    mr=tuple(abs(x[i]-x[i-1]) for i in range(1,len(x))); mrbar=fmean(mr); sigma=mrbar/1.128 if mrbar>0 else 0.0; center=fmean(x)
    u=center+3*sigma; l=center-3*sigma
    return ControlChartResult(ControlChartFamily.I_MR,x,_repeat(center,len(x)),_repeat(u,len(x)),_repeat(l,len(x)),mr,_repeat(mrbar,len(mr)),_repeat(3.267*mrbar,len(mr)),_repeat(0.0,len(mr)),sigma,_violations(x,center,sigma),excluded)

_A2={2:1.880,3:1.023,4:.729,5:.577,6:.483,7:.419,8:.373,9:.337,10:.308}
_D3={2:0,3:0,4:0,5:0,6:0,7:.076,8:.136,9:.184,10:.223}; _D4={2:3.267,3:2.574,4:2.282,5:2.114,6:2.004,7:1.924,8:1.864,9:1.816,10:1.777}
_A3={2:2.659,3:1.954,4:1.628,5:1.427,6:1.287,7:1.182,8:1.099,9:1.032,10:.975}
_B3={2:0,3:0,4:0,5:0,6:.030,7:.118,8:.185,9:.239,10:.284}; _B4={2:3.267,3:2.568,4:2.266,5:2.089,6:1.970,7:1.882,8:1.815,9:1.761,10:1.716}
_D2={2:1.128,3:1.693,4:2.059,5:2.326,6:2.534,7:2.704,8:2.847,9:2.970,10:3.078}

def _subgroups(groups:Iterable[Iterable[float]])->tuple[tuple[float,...],...]:
    normalized=[]
    for group_index,group in enumerate(groups):
        values=[]
        for value_index,value in enumerate(group):
            if value is None or isinstance(value,bool):
                raise SPCInputError(f'subgroup {group_index} contains missing/non-numeric value at index {value_index}')
            try: numeric=float(value)
            except (TypeError,ValueError) as exc:
                raise SPCInputError(f'subgroup {group_index} contains non-numeric value at index {value_index}') from exc
            if not isfinite(numeric):
                raise SPCInputError(f'subgroup {group_index} contains nonfinite value at index {value_index}')
            values.append(numeric)
        normalized.append(tuple(values))
    out=tuple(normalized)
    if len(out)<2: raise SPCInputError('subgroup chart requires at least 2 subgroups')
    n=len(out[0]) if out else 0
    if n not in _A2 or any(len(g)!=n for g in out): raise SPCInputError('subgroups must have equal finite size from 2 through 10')
    return out

def _counts(values:Sequence[int], label:str)->tuple[int,...]:
    out=[]
    for index,value in enumerate(values):
        if isinstance(value,bool): raise SPCInputError(f'{label} count at index {index} must be a nonnegative integer')
        try: numeric=float(value)
        except (TypeError,ValueError) as exc: raise SPCInputError(f'{label} count at index {index} must be numeric') from exc
        if not isfinite(numeric) or numeric<0 or not numeric.is_integer(): raise SPCInputError(f'{label} count at index {index} must be a nonnegative integer')
        out.append(int(numeric))
    return tuple(out)

def xbar_r(groups:Iterable[Iterable[float]])->ControlChartResult:
    gs=_subgroups(groups); n=len(gs[0]); means=tuple(fmean(g) for g in gs); ranges=tuple(max(g)-min(g) for g in gs); xb=fmean(means); rb=fmean(ranges); sigma=rb/_D2[n] if rb>0 else 0
    mean_sigma=sigma/sqrt(n) if sigma>0 else 0
    return ControlChartResult(ControlChartFamily.XBAR_R,means,_repeat(xb,len(means)),_repeat(xb+_A2[n]*rb,len(means)),_repeat(xb-_A2[n]*rb,len(means)),ranges,_repeat(rb,len(ranges)),_repeat(_D4[n]*rb,len(ranges)),_repeat(_D3[n]*rb,len(ranges)),sigma,_violations(means,xb,mean_sigma),metadata={'subgroup_size':n,'mean_standard_error':mean_sigma,'sigma_method':'Rbar/d2'})
def xbar_s(groups:Iterable[Iterable[float]])->ControlChartResult:
    gs=_subgroups(groups); n=len(gs[0]); means=tuple(fmean(g) for g in gs); ss=tuple(stdev(g) for g in gs); xb=fmean(means); sb=fmean(ss)
    c4=sqrt(2/(n-1))*gamma(n/2)/gamma((n-1)/2); sigma=sb/c4 if sb>0 else 0; mean_sigma=sigma/sqrt(n) if sigma>0 else 0
    return ControlChartResult(ControlChartFamily.XBAR_S,means,_repeat(xb,len(means)),_repeat(xb+_A3[n]*sb,len(means)),_repeat(xb-_A3[n]*sb,len(means)),ss,_repeat(sb,len(ss)),_repeat(_B4[n]*sb,len(ss)),_repeat(_B3[n]*sb,len(ss)),sigma,_violations(means,xb,mean_sigma),metadata={'subgroup_size':n,'c4':c4,'mean_standard_error':mean_sigma,'sigma_method':'Sbar/c4'})

def p_chart(defects:Sequence[int], inspected:Sequence[int])->ControlChartResult:
    if len(defects)!=len(inspected) or len(defects)<2: raise SPCInputError('p chart requires equal defect/inspected sequences with at least 2 points')
    defects=_counts(defects,'defect'); inspected=_counts(inspected,'inspected')
    if any(n<=0 or d>n for d,n in zip(defects,inspected)): raise SPCInputError('p chart requires 0 <= defects <= inspected and inspected > 0')
    p=tuple(d/n for d,n in zip(defects,inspected)); pb=sum(defects)/sum(inspected); u=[];l=[]
    for n in inspected:
        s=sqrt(pb*(1-pb)/n); u.append(min(1,pb+3*s)); l.append(max(0,pb-3*s))
    sigma=sqrt(pb*(1-pb)/fmean(inspected)) if 0<pb<1 else 0
    z=tuple((value-pb)/sqrt(pb*(1-pb)/n) for value,n in zip(p,inspected)) if 0<pb<1 else ()
    return ControlChartResult(ControlChartFamily.P,p,_repeat(pb,len(p)),tuple(u),tuple(l),sigma=sigma,violations=_violations_z(z) if z else (),metadata={'standardized_rule_evaluation':True})
def np_chart(defects:Sequence[int], inspected:int|Sequence[int])->ControlChartResult:
    ns=(tuple(inspected) if not isinstance(inspected,int) else tuple(inspected for _ in defects))
    ns=_counts(ns,'inspected')
    if len(set(ns))!=1: raise SPCInputError('np chart requires constant sample size')
    p=p_chart(defects,ns); n=ns[0]; vals=tuple(float(d) for d in defects); center=n*p.center[0]; sigma=sqrt(n*(center/n)*(1-center/n)) if 0<center<n else 0
    return ControlChartResult(ControlChartFamily.NP,vals,_repeat(center,len(vals)),_repeat(min(n,center+3*sigma),len(vals)),_repeat(max(0,center-3*sigma),len(vals)),sigma=sigma,violations=_violations(vals,center,sigma))
def c_chart(counts:Sequence[int])->ControlChartResult:
    counts=_counts(counts,'defect')
    if len(counts)<2: raise SPCInputError('c chart requires at least 2 nonnegative counts')
    c=fmean(counts); s=sqrt(c); vals=tuple(float(v) for v in counts)
    return ControlChartResult(ControlChartFamily.C,vals,_repeat(c,len(vals)),_repeat(c+3*s,len(vals)),_repeat(max(0,c-3*s),len(vals)),sigma=s,violations=_violations(vals,c,s))
def u_chart(counts:Sequence[int], units:Sequence[float])->ControlChartResult:
    counts=_counts(counts,'defect')
    try: units=tuple(float(n) for n in units)
    except (TypeError,ValueError) as exc: raise SPCInputError('u chart units must be numeric') from exc
    if len(counts)!=len(units) or len(counts)<2 or any(not isfinite(n) or n<=0 for n in units): raise SPCInputError('u chart requires equal nonnegative counts and positive finite units')
    ub=sum(counts)/sum(units); vals=tuple(c/n for c,n in zip(counts,units)); u=[];l=[]
    for n in units:
        s=sqrt(ub/n); u.append(ub+3*s); l.append(max(0,ub-3*s))
    sigma=sqrt(ub/fmean(units)) if ub>0 else 0
    z=tuple((value-ub)/sqrt(ub/n) for value,n in zip(vals,units)) if ub>0 else ()
    return ControlChartResult(ControlChartFamily.U,vals,_repeat(ub,len(vals)),tuple(u),tuple(l),sigma=sigma,violations=_violations_z(z) if z else (),metadata={'standardized_rule_evaluation':True})
def ewma(values:Iterable[float|None], *, lambda_:float=.2, L:float=3.0, target:float|None=None)->ControlChartResult:
    x,excluded=_clean(values); _need(x,2,'EWMA')
    if not 0<lambda_<=1 or L<=0: raise SPCInputError('EWMA requires 0 < lambda <= 1 and L > 0')
    try: center=fmean(x) if target is None else float(target)
    except (TypeError,ValueError) as exc: raise SPCInputError('EWMA target must be numeric') from exc
    if not isfinite(center): raise SPCInputError('EWMA target must be finite')
    sigma=_sample_sigma(x)
    if sigma is None: sigma=0
    z=[]; u=[];l=[]; violations=[]; prev=center
    for i,v in enumerate(x,1):
        prev=lambda_*v+(1-lambda_)*prev; z.append(prev); s=sigma*sqrt(lambda_/(2-lambda_)*(1-(1-lambda_)**(2*i))); u.append(center+L*s);l.append(center-L*s)
        if prev>u[-1] or prev<l[-1]: violations.append(RuleViolation('ewma','EWMA',(i-1,),'EWMA control limit exceeded'))
    return ControlChartResult(ControlChartFamily.EWMA,tuple(z),_repeat(center,len(z)),tuple(u),tuple(l),sigma=sigma,violations=tuple(violations),excluded_indices=excluded,metadata={'lambda':lambda_,'L':L,'target':center})
def cusum(values:Iterable[float|None], *, target:float|None=None, k:float=.5, h:float=5.0)->ControlChartResult:
    x,excluded=_clean(values); _need(x,2,'CUSUM')
    if k<0 or h<=0: raise SPCInputError('CUSUM requires k >= 0 and h > 0')
    try: center=fmean(x) if target is None else float(target)
    except (TypeError,ValueError) as exc: raise SPCInputError('CUSUM target must be numeric') from exc
    if not isfinite(center): raise SPCInputError('CUSUM target must be finite')
    sigma=_sample_sigma(x)
    if sigma is None: raise SPCInputError('CUSUM requires non-degenerate variance')
    cp=cm=0.0; plus=[]; minus=[]; vals=[]; violations=[]
    for i,v in enumerate(x):
        z=(v-center)/sigma; cp=max(0,cp+z-k); cm=min(0,cm+z+k); plus.append(cp); minus.append(cm)
        # ``values`` remains the historical dominant-side projection for
        # consumers that only draw one line. New consumers must use c_plus and
        # c_minus, which preserve both declared CUSUM paths.
        vals.append(cp if abs(cp)>=abs(cm) else cm)
        if cp>h or cm<-h: violations.append(RuleViolation('cusum','CUSUM',(i,),'CUSUM decision interval exceeded'))
    plus_values=tuple(plus); minus_values=tuple(minus)
    return ControlChartResult(ControlChartFamily.CUSUM,tuple(vals),_repeat(0,len(vals)),_repeat(h,len(vals)),_repeat(-h,len(vals)),sigma=sigma,violations=tuple(violations),excluded_indices=excluded,metadata={'k':k,'h':h,'target':center,'c_plus':plus_values,'c_minus':minus_values,'positive_limit':h,'negative_limit':-h},positive_values=plus_values,negative_values=minus_values)


def capability_indices(values:Iterable[float|None], *, lsl:float|None=None, usl:float|None=None, target:float|None=None, within_sigma:float|None=None)->CapabilityResult:
    x,_=_clean(values); _need(x,2,'capability')
    if lsl is None and usl is None: raise SPCInputError('capability requires LSL and/or USL')
    try:
        lsl=None if lsl is None else float(lsl); usl=None if usl is None else float(usl); target=None if target is None else float(target)
    except (TypeError,ValueError) as exc: raise SPCInputError('capability limits and target must be numeric') from exc
    if any(v is not None and not isfinite(v) for v in (lsl,usl,target)): raise SPCInputError('capability limits and target must be finite')
    if lsl is not None and usl is not None and lsl>=usl: raise SPCInputError('LSL must be less than USL')
    mean=fmean(x); overall=_sample_sigma(x)
    if within_sigma is None:
        moving_ranges=tuple(abs(x[i]-x[i-1]) for i in range(1,len(x)))
        mrbar=fmean(moving_ranges) if moving_ranges else 0.0
        within=mrbar/1.128 if mrbar>0 else None
        within_method='moving_range'
    else:
        try: within=float(within_sigma)
        except (TypeError,ValueError) as exc: raise SPCInputError('within_sigma must be numeric') from exc
        within_method='provided'
    if within is not None and (within<=0 or not isfinite(within)): within=None
    def idx(sig):
        if sig is None:return None,None
        cp=((usl-lsl)/(6*sig)) if lsl is not None and usl is not None else None
        sides=[]
        if usl is not None:sides.append((usl-mean)/(3*sig))
        if lsl is not None:sides.append((mean-lsl)/(3*sig))
        return cp,min(sides) if sides else None
    cp,cpk=idx(within); pp,ppk=idx(overall)
    return CapabilityResult(len(x),mean,within,overall,cp,cpk,pp,ppk,lsl,usl,target,within_method,'sample_stdev')

def _percentile(sorted_values:Sequence[float], q:float)->float:
    if not sorted_values: raise SPCInputError('percentile requires data')
    position=(len(sorted_values)-1)*q; lo=int(position); hi=min(len(sorted_values)-1,lo+1); fraction=position-lo
    return sorted_values[lo]*(1-fraction)+sorted_values[hi]*fraction

def box_distribution(values:Iterable[float|None])->BoxSummary:
    x,_=_clean(values); _need(x,1,'box distribution'); xs=sorted(x)
    return BoxSummary(len(xs),xs[0],_percentile(xs,.25),_percentile(xs,.5),_percentile(xs,.75),xs[-1])

def density_estimate(values:Iterable[float|None], *, points:int=64, bandwidth:float|None=None)->tuple[DensityPoint,...]:
    x,_=_clean(values); _need(x,2,'density estimate')
    if points<8: raise SPCInputError('density estimate requires at least 8 evaluation points')
    sigma=_sample_sigma(x)
    if sigma is None: raise SPCInputError('density estimate requires non-degenerate variance')
    n=len(x); bw=float(bandwidth) if bandwidth is not None else 1.06*sigma*(n**(-.2))
    if not isfinite(bw) or bw<=0: raise SPCInputError('density bandwidth must be positive and finite')
    lo=min(x)-3*bw; hi=max(x)+3*bw; step=(hi-lo)/(points-1); norm=1/(n*bw*sqrt(2*pi))
    out=[]
    for i in range(points):
        value=lo+i*step; density=norm*sum(exp(-.5*((value-observation)/bw)**2) for observation in x); out.append(DensityPoint(value,density))
    return tuple(out)

def ridge_distributions(groups:Mapping[str,Iterable[float|None]], *, points:int=64, bandwidth:float|None=None)->dict[str,tuple[DensityPoint,...]]:
    if not groups: return {}
    return {str(label):density_estimate(values,points=points,bandwidth=bandwidth) for label,values in groups.items()}

def ecdf(values:Iterable[float|None])->tuple[tuple[float,float],...]:
    x,_=_clean(values); _need(x,1,'ECDF'); xs=sorted(x); n=len(xs); return tuple((v,(i+1)/n) for i,v in enumerate(xs))
def qq_points(values:Iterable[float|None])->tuple[tuple[float,float],...]:
    x,_=_clean(values); _need(x,2,'QQ plot'); xs=sorted(x); n=len(xs); nd=NormalDist(); return tuple((nd.inv_cdf((i-.375)/(n+.25)),v) for i,v in enumerate(xs,1))
def capability_histogram(values:Iterable[float|None], bins:int=10)->tuple[tuple[float,float,int],...]:
    x,_=_clean(values); _need(x,1,'histogram')
    if bins<1: raise SPCInputError('bins must be >= 1')
    lo=min(x);hi=max(x)
    if lo==hi:return ((lo,hi,len(x)),)
    w=(hi-lo)/bins; counts=[0]*bins
    for v in x: counts[min(bins-1,int((v-lo)/w))]+=1
    return tuple((lo+i*w,lo+(i+1)*w,counts[i]) for i in range(bins))

__all__=['SPCInputError','ControlChartFamily','RuleViolation','ControlChartResult','CapabilityResult','BoxSummary','DensityPoint','detect_western_electric','detect_nelson','i_mr','xbar_r','xbar_s','p_chart','np_chart','c_chart','u_chart','ewma','cusum','capability_indices','box_distribution','density_estimate','ridge_distributions','ecdf','qq_points','capability_histogram']
