from nicegui_base.data_table import ColumnKind, FilterOperator, FilterSpec, SortDirection, SortSpec, TableColumn, TableQuery, apply_query, export_csv, format_cell

ROWS=[
 {'id':1,'tool':'ETCH-01','yield':97.2,'status':'Watch'},
 {'id':2,'tool':'ETCH-02','yield':99.1,'status':'Normal'},
 {'id':3,'tool':'CMP-04','yield':95.4,'status':'Critical'},
]

def test_search():
    r=apply_query(ROWS,TableQuery(search='etch'))
    assert r.total==2

def test_filter_equals():
    r=apply_query(ROWS,TableQuery(filters=(FilterSpec('status',FilterOperator.EQUALS,'Critical'),)))
    assert [x['id'] for x in r.rows]==[3]

def test_numeric_filter():
    r=apply_query(ROWS,TableQuery(filters=(FilterSpec('yield',FilterOperator.LT,98),)))
    assert r.total==2

def test_sort_desc():
    r=apply_query(ROWS,TableQuery(sorts=(SortSpec('yield',SortDirection.DESC),)))
    assert [x['id'] for x in r.rows]==[2,1,3]

def test_pagination():
    r=apply_query(ROWS,TableQuery(page=2,page_size=2))
    assert r.total==3 and [x['id'] for x in r.rows]==[3] and r.page_count==2

def test_percent_formatting():
    c=TableColumn('yield','Yield',ColumnKind.PERCENT,decimals=1)
    assert format_cell(97.24,c)=='97.2%'

def test_float_unit_formatting():
    c=TableColumn('x','X',ColumnKind.FLOAT,decimals=2,unit='nm')
    assert format_cell(1.2,c)=='1.20 nm'

def test_null_formatting():
    assert format_cell(None,TableColumn('x','X'))=='—'

def test_csv_export_uses_labels_and_formatting():
    c=(TableColumn('tool','Tool'),TableColumn('yield','Yield',ColumnKind.PERCENT,decimals=1))
    csv=export_csv(ROWS[:1],c)
    assert 'Tool,Yield' in csv and 'ETCH-01,97.2%' in csv
