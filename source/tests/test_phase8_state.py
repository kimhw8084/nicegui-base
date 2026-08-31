from dataclasses import FrozenInstanceError
import pytest

from nicegui_base.state import PageState, PageStatus, SidebarPreference, StateStore, UrlField, UrlState, UserPreferences


def test_page_state_error_requires_context():
    with pytest.raises(ValueError): PageState(PageStatus.ERROR)
    assert PageState.ready().status is PageStatus.READY


def test_user_preferences_round_trip():
    p = UserPreferences(theme='dark', density='dense', sidebar=SidebarPreference.COMPACT,
                        table_states={'tools': {'density':'dense'}}, favorites=('T1',))
    p2 = UserPreferences.from_mapping(p.to_dict())
    assert p2.theme == 'dark' and p2.sidebar is SidebarPreference.COMPACT
    assert p2.table_states['tools']['density'] == 'dense'


def test_user_preferences_are_validated():
    with pytest.raises(ValueError): UserPreferences(theme='purple')
    with pytest.raises(ValueError): UserPreferences(density='tiny')


def test_state_store_observes_changes_and_batches():
    store = StateStore({'a':1}); events=[]; store.watch(lambda k,o,n: events.append((k,o,n)))
    store['a']=2
    with store.batch():
        store['a']=3; store['a']=4; store['b']=1
    assert events == [('a',1,2),('a',2,4),('b',None,1)]


def test_state_store_ignores_same_value():
    store=StateStore({'x':1}); events=[]; store.watch(lambda *a: events.append(a)); store['x']=1
    assert not events


def test_url_state_round_trip_typed():
    codec=UrlState([UrlField('page', int, default=1), UrlField('critical', bool), UrlField('tool', str, multiple=True)])
    q=codec.encode({'tool':['T2','T1'],'critical':True,'page':3})
    decoded=codec.decode(q)
    assert decoded['page']==3 and decoded['critical'] is True and decoded['tool']==['T2','T1']


def test_url_state_stable_key_order():
    assert UrlState().encode({'z':1,'a':2}).startswith('a=2')
