from nicegui_base import ColumnKind, FilterOperator, FilterSpec, SortDirection, SortSpec, TableColumn, TableQuery, TableQueryEngine, apply_query, export_csv
ROWS=tuple({'id':i,'name':f'Tool {i}','value':None if i%10==0 else i} for i in range(100))

def test_engine_matches_apply_query():
    q=TableQuery(search='Tool 1',filters=(FilterSpec('id',FilterOperator.GTE,10),),sorts=(SortSpec('id',SortDirection.DESC),),page_size=10)
    assert TableQueryEngine(ROWS).query(q).rows==apply_query(ROWS,q).rows

def test_engine_pagination_cache():
    e=TableQueryEngine(ROWS); a=e.query(TableQuery(page=1,page_size=10)); b=e.query(TableQuery(page=2,page_size=10)); assert a.total==b.total==100 and a.rows!=b.rows

def test_nulls_last_asc():
    r=apply_query(ROWS,TableQuery(sorts=(SortSpec('value',SortDirection.ASC),),page_size=100)); assert r.rows[-1]['value'] is None

def test_nulls_last_desc():
    r=apply_query(ROWS,TableQuery(sorts=(SortSpec('value',SortDirection.DESC),),page_size=100)); assert r.rows[-1]['value'] is None

def test_csv_formula_injection():
    cols=(TableColumn('x','X',ColumnKind.TEXT),); text=export_csv(({'x':'=1+1'},),cols); assert "'=1+1" in text

def test_csv_numeric_not_escaped():
    cols=(TableColumn('x','X',ColumnKind.INTEGER),); text=export_csv(({'x':-3},),cols); assert "'-3" not in text
