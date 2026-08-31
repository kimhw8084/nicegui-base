from nicegui_base import ApplicationServices, Command, CommandRegistry, StateStore, WorkspacePreferenceService

def test_watch_key_only():
    s=StateStore(); seen=[]; s.watch_key('a',lambda *x:seen.append(x)); s['b']=1; s['a']=2; assert len(seen)==1

def test_watch_key_unsubscribe():
    s=StateStore(); seen=[]; off=s.watch_key('a',lambda *x:seen.append(x)); off(); s['a']=1; assert not seen

def test_workspace_roundtrip():
    b={}; w=WorkspacePreferenceService(b); w.save_workspace('main',{'tab':'x'}); assert w.load_workspace('main')=={'tab':'x'}; assert w.list_workspaces()==('main',)

def test_workspace_delete():
    b={}; w=WorkspacePreferenceService(b); w.save_workspace('a',{}); assert w.delete_workspace('a'); assert not w.delete_workspace('a')

def test_favorites_recent():
    b={}; w=WorkspacePreferenceService(b,max_recent=2); w.add_favorite('A'); w.add_favorite('A'); assert w.add_favorite('B').favorites==('A','B'); w.touch_recent('A'); p=w.touch_recent('B'); assert p.recent_entities==('B','A')

def test_command_registry():
    r=CommandRegistry(); r.register(Command('refresh','Refresh Data',lambda:7,keywords=('reload',))); assert r.execute('refresh')==7; assert r.search('reload')[0].key=='refresh'

def test_application_services_bundle():
    s=ApplicationServices.with_preferences({}); assert s.preferences is not None and s.workspaces is not None and s.errors is not None

def test_histories_bounded():
    s=ApplicationServices(); s.notifications.history.clear();
    for i in range(150):s.notifications.notify(str(i))
    assert len(s.notifications.history)==100
