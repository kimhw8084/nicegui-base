from nicegui_base import AnalyticalDataController, ApplicationServices, TableQuery, TableQueryEngine

ROWS=tuple({'id':i,'tool':f'TOOL-{i%40:02d}','status':'Critical' if i%17==0 else 'Normal'} for i in range(1000))
TABLE=TableQueryEngine(ROWS, searchable_columns=('tool','status'))
services=ApplicationServices()

def visible_rows(search:str=''):
    return TABLE.query(TableQuery(search=search,page_size=50))
