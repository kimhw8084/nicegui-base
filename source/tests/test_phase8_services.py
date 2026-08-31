import logging
import pytest

from nicegui_base.design import ThemeMode
from nicegui_base.feedback import FeedbackIntent
from nicegui_base.services import (
    ClipboardService, DialogService, DownloadService, ErrorService, KeyboardShortcut,
    KeyboardShortcutRegistry, NavigationService, NotificationService, PreferenceService,
    ThemeService, normalize_shortcut,
)


def test_notification_helpers():
    seen=[]; service=NotificationService(seen.append); spec=service.success('Saved')
    assert spec.intent is FeedbackIntent.SUCCESS and seen == [spec]


def test_navigation_history():
    nav=NavigationService(); nav.go('/a'); nav.go('/b')
    assert nav.back_target().path == '/a'


def test_theme_service_validation():
    seen=[]; s=ThemeService(sink=lambda m,d: seen.append((m,d)))
    s.set(mode=ThemeMode.DARK,density='dense')
    assert seen[-1] == (ThemeMode.DARK,'dense')
    with pytest.raises(ValueError): s.set(density='micro')


def test_preference_service_persists_table_and_filter():
    backing={}; p=PreferenceService(backing)
    p.update(theme='dark'); p.save_table_state('t',{'x':1}); p.save_filter_view('critical',{'status':'critical'})
    loaded=p.load(); assert loaded.theme=='dark' and loaded.table_states['t']['x']==1 and loaded.filter_views['critical']['status']=='critical'


def test_keyboard_normalization_and_registry():
    assert normalize_shortcut('Shift+Control+K') == 'ctrl+shift+k'
    out=[]; r=KeyboardShortcutRegistry(); r.register(KeyboardShortcut('cmd+k', lambda: out.append(1), 'Open commands'))
    r.trigger('meta+k'); assert out == [1]
    with pytest.raises(ValueError): r.register(KeyboardShortcut('meta+k', lambda: None, 'Duplicate'))


def test_clipboard_download_dialog_are_sink_driven():
    copied=[]; ClipboardService(copied.append).copy('abc'); assert copied==['abc']
    downloads=[]; req=DownloadService(downloads.append).download('x.csv','a,b', media_type='text/csv'); assert req.content == b'a,b' and downloads[0] == req
    dialogs=[]; d=DialogService(dialogs.append).request('Confirm', destructive=True); assert dialogs==[d] and d.destructive


def test_error_service_returns_safe_error_id(caplog):
    caplog.set_level(logging.ERROR)
    err=ErrorService(prefix='app').capture(ValueError('secret-ish technical text'), message='Request failed', retryable=True)
    assert err.error_id.startswith('APP-') and err.message=='Request failed' and err.retryable
