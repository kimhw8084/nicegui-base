from __future__ import annotations
import json, statistics, time
from pathlib import Path
from company_ui import TableQuery, SortSpec, SortDirection, FilterSpec, FilterOperator, TableQueryEngine
from company_ui.data_table.engine import apply_query
from company_ui.integrations.nicegui_theme import build_framework_css

N=100_000
ROWS=tuple({'id':i,'tool':f'TOOL-{i%250:03d}','status':'Critical' if i%31==0 else ('Watch' if i%13==0 else 'Normal'),'value':None if i%997==0 else (i%10000)/100} for i in range(N))

def legacy_apply(rows, query, searchable_columns=None):
    def norm(v): return '' if v is None else v
    def match(value,spec):
        op=spec.operator; a=norm(value); b=spec.value
        if op is FilterOperator.IS_EMPTY:return value is None or value==''
        if op is FilterOperator.IS_NOT_EMPTY:return not(value is None or value=='')
        if op is FilterOperator.CONTAINS:return str(b).lower() in str(a).lower()
        if op is FilterOperator.STARTS_WITH:return str(a).lower().startswith(str(b).lower())
        if op is FilterOperator.ENDS_WITH:return str(a).lower().endswith(str(b).lower())
        if op is FilterOperator.EQUALS:return a==b
        if op is FilterOperator.NOT_EQUALS:return a!=b
        if op is FilterOperator.IN:return a in set(b or ())
        try:
            if op is FilterOperator.GT:return a>b
            if op is FilterOperator.GTE:return a>=b
            if op is FilterOperator.LT:return a<b
            if op is FilterOperator.LTE:return a<=b
            if op is FilterOperator.BETWEEN:return b<=a<=spec.value2
        except TypeError:return False
        return True
    data=list(rows)
    if query.search:
        needle=query.search.lower().strip(); data=[r for r in data if any(needle in str(v).lower() for k,v in r.items() if searchable_columns is None or k in searchable_columns)]
    for f in query.filters:data=[r for r in data if match(r.get(f.key),f)]
    for s in reversed(query.sorts):data.sort(key=lambda r:(r.get(s.key) is None,norm(r.get(s.key))),reverse=s.direction is SortDirection.DESC)
    total=len(data); start=(query.page-1)*query.page_size
    return data[start:start+query.page_size],total

def med(fn,runs=5):
    vals=[]
    for _ in range(runs):
        t=time.perf_counter(); fn(); vals.append((time.perf_counter()-t)*1000)
    return statistics.median(vals)

search_q=TableQuery(search='TOOL-117',page_size=50)
filter_q=TableQuery(filters=(FilterSpec('status',FilterOperator.EQUALS,'Critical'),),sorts=(SortSpec('value',SortDirection.DESC),),page_size=100)
results={}
results['rows']=N
results['legacy_search_ms_median']=med(lambda:legacy_apply(ROWS,search_q,('tool','status')))
results['hardened_search_ms_median']=med(lambda:apply_query(ROWS,search_q,searchable_columns=('tool','status')))
results['legacy_filter_sort_ms_median']=med(lambda:legacy_apply(ROWS,filter_q,('tool','status')))
results['hardened_filter_sort_ms_median']=med(lambda:apply_query(ROWS,filter_q,searchable_columns=('tool','status')))
t=time.perf_counter(); engine=TableQueryEngine(ROWS,searchable_columns=('tool','status')); results['search_index_build_ms']=(time.perf_counter()-t)*1000
# measure uncached indexed search using distinct keys, then cached page switching
indexed=[]
for token in ('TOOL-218','TOOL-219','TOOL-220','TOOL-221','TOOL-222'):
    q=TableQuery(search=token,page_size=50); t=time.perf_counter(); engine.query(q); indexed.append((time.perf_counter()-t)*1000)
results['indexed_new_search_ms_median']=statistics.median(indexed)
base_q=TableQuery(search='TOOL-218',page_size=50); engine.query(base_q)
page_q=TableQuery(search='TOOL-218',page=2,page_size=50)
results['cached_page_switch_ms_median']=med(lambda:engine.query(page_q),runs=20)
build_framework_css.cache_clear(); t=time.perf_counter(); css=build_framework_css(); results['css_first_build_ms']=(time.perf_counter()-t)*1000; results['css_bytes']=len(css)
results['css_cached_ms_median']=med(build_framework_css,runs=50)
results['search_improvement_pct']=(1-results['hardened_search_ms_median']/results['legacy_search_ms_median'])*100
results['filter_sort_improvement_pct']=(1-results['hardened_filter_sort_ms_median']/results['legacy_filter_sort_ms_median'])*100
results['indexed_vs_legacy_search_improvement_pct']=(1-results['indexed_new_search_ms_median']/results['legacy_search_ms_median'])*100
Path('BENCHMARK_REPORT.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
print(json.dumps(results,indent=2,sort_keys=True))
