from __future__ import annotations

import asyncio
import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from nicegui_base.diagnostics.debug_runtime import build_diagnostic_bundle, diagnostic_buffer, runtime_snapshot
from nicegui_base.version import FRAMEWORK_VERSION
from nicegui_base.visual import render_icon_svg


BROWSER_DIAGNOSTICS_BOOTSTRAP = r'''<script>
(() => {
  if (window.__niceguiBaseDiagnostics) return;
  const cap = 160;
  const state = {errors: [], requests: [], events: []};
  const trim = a => { if (a.length > cap) a.splice(0, a.length - cap); };
  const safeUrl = input => {
    try { const u = new URL(String(input), window.location.href); return u.pathname; }
    catch (_) { return String(input || '').split('?')[0].slice(0, 240); }
  };
  const push = (bucket, value) => { state[bucket].push(value); trim(state[bucket]); };
  window.addEventListener('error', e => push('errors', {
    time: new Date().toISOString(), type: 'error', message: String(e.message || 'Browser error'),
    source: safeUrl(e.filename || ''), line: e.lineno || null, column: e.colno || null,
    stack: String(e.error?.stack || '').slice(0, 4000),
  }));
  window.addEventListener('unhandledrejection', e => push('errors', {
    time: new Date().toISOString(), type: 'unhandledrejection',
    message: String(e.reason?.message || e.reason || 'Unhandled promise rejection').slice(0, 1000),
    stack: String(e.reason?.stack || '').slice(0, 4000),
  }));
  document.addEventListener('cui:overlay-open', e => push('events', {
    time: new Date().toISOString(), type: 'overlay-open', kind: String(e.detail?.kind || 'overlay')
  }));
  const originalFetch = window.fetch?.bind(window);
  if (originalFetch) {
    window.fetch = async (...args) => {
      const input = args[0]; const init = args[1] || {}; const started = performance.now();
      const method = String(init.method || input?.method || 'GET').toUpperCase();
      const path = safeUrl(input?.url || input);
      try {
        const response = await originalFetch(...args);
        push('requests', {time:new Date().toISOString(), method, path, status:response.status,
          ok:response.ok, duration_ms:Math.round((performance.now()-started)*10)/10});
        return response;
      } catch (err) {
        push('requests', {time:new Date().toISOString(), method, path, status:null, ok:false,
          duration_ms:Math.round((performance.now()-started)*10)/10, error:String(err?.message || err).slice(0,500)});
        throw err;
      }
    };
  }
  window.__niceguiBaseDiagnostics = {
    mark(type, detail={}) { push('events', {time:new Date().toISOString(), type:String(type), detail}); },
    clear() { state.errors.length=0; state.requests.length=0; state.events.length=0; },
    snapshot() {
      return {
        page: {path: location.pathname, hash: location.hash, title: document.title},
        browser: {user_agent:navigator.userAgent, language:navigator.language, online:navigator.onLine,
          viewport:{width:innerWidth,height:innerHeight,device_pixel_ratio:devicePixelRatio}},
        errors: state.errors.slice(), requests: state.requests.slice(), events: state.events.slice(),
      };
    }
  };
})();
</script>'''


@dataclass(frozen=True, slots=True)
class DebuggerConfig:
    app_name: str = 'NiceGUI application'
    app_version: str = ''
    environment: str = ''
    framework_version: str = FRAMEWORK_VERSION
    enabled: bool = True
    event_limit: int = 250
    health_provider: Callable[[], Mapping[str, Any] | Any] | None = None


class UniversalDebugger:
    """Reusable in-app troubleshooting console for NiceGUI Base applications.

    The debugger is intentionally observability-first rather than a remote shell:
    it exposes redacted logs, browser errors, request metadata, client events,
    environment/version information and optional health data. It never collects
    request bodies, cookies, authorization headers, form values, or local-storage values.
    """

    def __init__(self, config: DebuggerConfig | None = None):
        from nicegui import ui
        self.ui = ui
        self.config = config or DebuggerConfig()
        self.buffer = diagnostic_buffer()
        self._browser_snapshot: dict[str, Any] = {}
        self._health_snapshot: dict[str, Any] = {}
        self._trigger_badge = None
        self._summary_host = None
        self._logs_host = None
        self._errors_host = None
        self._requests_host = None
        self._events_host = None
        self._environment_host = None
        self._health_host = None
        self._trigger_task: asyncio.Task[None] | None = None
        self._trigger_disposed = False
        ui.add_head_html(BROWSER_DIAGNOSTICS_BOOTSTRAP, shared=True)
        self.dialog = ui.dialog().props('maximized transition-show=fade transition-hide=fade')
        self._build_dialog()

    @staticmethod
    def _icon(key: str, label: str, *, size: str = 'sm'):
        from nicegui import ui
        return ui.html(render_icon_svg(key, size=size, label=label), sanitize=False).classes('cui-svg-icon-host')

    def trigger(self):
        ui = self.ui
        with ui.element('div').classes('cui-debugger-trigger-wrap'):
            with ui.button(on_click=self.open).props(
                'flat round dense aria-label="Open debugger" title="Debugger"'
            ).classes('cui-icon-button cui-debugger-trigger') as button:
                self._icon('diagnostics', 'Debugger', size='sm')
            self._trigger_badge = ui.label('').classes('cui-debugger-trigger-badge')

        # Do not use NiceGUI Timer here: Timer is slot-owned and can race a
        # client/page deletion. A plain task has explicit client lifecycle.
        self._trigger_disposed = False
        self._update_trigger_badge()
        try:
            self._trigger_task = asyncio.get_running_loop().create_task(
                self._trigger_loop(),
                name='nicegui-base-debugger-badge',
            )
        except RuntimeError:
            self._trigger_task = None

        client = getattr(getattr(ui, 'context', None), 'client', None)
        on_delete = getattr(client, 'on_delete', None)
        if callable(on_delete):
            on_delete(self._dispose_trigger)
        return button

    async def _trigger_loop(self) -> None:
        try:
            while not self._trigger_disposed:
                await asyncio.sleep(1.5)
                if self._trigger_disposed:
                    return
                try:
                    self._update_trigger_badge()
                except RuntimeError as exc:
                    # A client can disappear between the sleep wake-up and the
                    # on-delete callback. Treat deleted-slot access as disposal.
                    message = str(exc).casefold()
                    if 'parent slot' in message or 'deleted' in message:
                        self._trigger_disposed = True
                        return
                    raise
        except asyncio.CancelledError:
            return

    def _dispose_trigger(self, *_args) -> None:
        if self._trigger_disposed:
            return
        self._trigger_disposed = True
        task = self._trigger_task
        self._trigger_task = None
        if task is not None and not task.done():
            task.cancel()
        self._trigger_badge = None

    def _build_dialog(self) -> None:
        ui = self.ui
        with self.dialog:
            with ui.element('section').classes('cui-debugger-shell').props(
                'role="dialog" aria-modal="true" aria-label="NiceGUI Base debugger"'
            ):
                with ui.element('header').classes('cui-debugger-header'):
                    with ui.element('div').classes('cui-debugger-header__title'):
                        self._icon('diagnostics', 'Debugger', size='sm')
                        with ui.element('div'):
                            ui.label('Debugger').classes('cui-debugger-title')
                            ui.label('Logs · errors · requests · events · performance · environment').classes('cui-debugger-subtitle')
                    with ui.element('div').classes('cui-debugger-header__actions'):
                        ui.button('Refresh', on_click=self.refresh).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
                        ui.button('Download diagnostic bundle', on_click=self.download_bundle).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
                        with ui.button(on_click=self.close).props('flat round aria-label="Close debugger" title="Close"').classes('cui-icon-button'):
                            self._icon('close', 'Close debugger', size='sm')
                self._summary_host = ui.element('div').classes('cui-debugger-summary')
                tabs = ui.tabs(value='logs').classes('cui-debugger-tabs').props('dense no-caps align=left')
                with tabs:
                    ui.tab('logs', label='Logs')
                    ui.tab('errors', label='Errors')
                    ui.tab('requests', label='Requests')
                    ui.tab('events', label='State & Events')
                    ui.tab('environment', label='Environment')
                    ui.tab('health', label='Health')
                with ui.tab_panels(tabs, value='logs').classes('cui-debugger-panels'):
                    with ui.tab_panel('logs'):
                        self._logs_host = ui.element('div').classes('cui-debugger-stream')
                    with ui.tab_panel('errors'):
                        self._errors_host = ui.element('div').classes('cui-debugger-stream')
                    with ui.tab_panel('requests'):
                        self._requests_host = ui.element('div').classes('cui-debugger-stream')
                    with ui.tab_panel('events'):
                        self._events_host = ui.element('div').classes('cui-debugger-stream')
                    with ui.tab_panel('environment'):
                        self._environment_host = ui.element('div').classes('cui-debugger-json')
                    with ui.tab_panel('health'):
                        self._health_host = ui.element('div').classes('cui-debugger-json')

    def _update_trigger_badge(self) -> None:
        if self._trigger_badge is None:
            return
        counts = self.buffer.counts()
        count = counts['ERROR'] + counts['CRITICAL']
        self._trigger_badge.set_text(str(count) if count else '')
        self._trigger_badge.set_visibility(bool(count))

    async def _browser(self) -> dict[str, Any]:
        try:
            value = await self.ui.run_javascript('window.__niceguiBaseDiagnostics?.snapshot?.() || {}')
            return dict(value or {}) if isinstance(value, Mapping) else {}
        except Exception as exc:
            return {'diagnostic_error': f'{type(exc).__name__}: {exc}'}

    async def _health(self) -> dict[str, Any]:
        provider = self.config.health_provider
        if provider is None:
            return {'status': 'not-configured', 'detail': 'No application health provider was attached to AppShell.'}
        try:
            value = provider()
            if inspect.isawaitable(value):
                value = await value
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            return dict(value or {}) if isinstance(value, Mapping) else {'value': str(value)}
        except Exception as exc:
            return {'status': 'error', 'detail': f'{type(exc).__name__}: {exc}'}

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, indent=2, sort_keys=True, default=str)

    def _render_summary(self) -> None:
        if self._summary_host is None:
            return
        counts = self.buffer.counts()
        browser_errors = len(self._browser_snapshot.get('errors', ()) or ())
        requests = self._browser_snapshot.get('requests', ()) or ()
        slow = sum(float(item.get('duration_ms') or 0) >= 750 for item in requests if isinstance(item, Mapping))
        self._summary_host.clear()
        with self._summary_host:
            for value, label in (
                (counts['ERROR'] + counts['CRITICAL'] + browser_errors, 'Errors'),
                (counts['WARNING'], 'Warnings'),
                (len(requests), 'Requests'),
                (slow, 'Slow ≥750 ms'),
            ):
                with self.ui.element('div').classes('cui-debugger-kpi'):
                    self.ui.label(str(value)).classes('cui-debugger-kpi__value')
                    self.ui.label(label).classes('cui-debugger-kpi__label')

    def _render_logs(self) -> None:
        events = self.buffer.snapshot(limit=self.config.event_limit)
        if self._logs_host is not None:
            self._logs_host.clear()
            with self._logs_host:
                if not events:
                    self.ui.label('No Python log events captured yet.').classes('cui-debugger-empty')
                for event in reversed(events):
                    with self.ui.element('article').classes(f'cui-debugger-row is-{event.level.casefold()}'):
                        self.ui.label(event.level).classes('cui-debugger-row__level')
                        with self.ui.element('div').classes('cui-debugger-row__body'):
                            self.ui.label(event.message).classes('cui-debugger-row__message')
                            self.ui.label(f'{event.timestamp} · {event.logger}').classes('cui-debugger-row__meta')
                            if event.context:
                                self.ui.label(self._json(event.context)).classes('cui-debugger-row__context')
        if self._errors_host is not None:
            self._errors_host.clear()
            with self._errors_host:
                python_errors = [event for event in events if event.level in {'ERROR', 'CRITICAL'}]
                browser_errors = list(self._browser_snapshot.get('errors', ()) or ())
                if not python_errors and not browser_errors:
                    self.ui.label('No captured errors.').classes('cui-debugger-empty')
                for event in reversed(python_errors):
                    with self.ui.element('article').classes('cui-debugger-error-card'):
                        self.ui.label(f'{event.exception_type or event.level} · {event.message}').classes('cui-debugger-row__message')
                        self.ui.label(event.timestamp).classes('cui-debugger-row__meta')
                        if event.exception:
                            self.ui.label(event.exception).classes('cui-debugger-stack')
                for item in reversed(browser_errors):
                    with self.ui.element('article').classes('cui-debugger-error-card'):
                        self.ui.label(f"Browser · {item.get('message', 'Error')}").classes('cui-debugger-row__message')
                        self.ui.label(str(item.get('time', ''))).classes('cui-debugger-row__meta')
                        if item.get('stack'):
                            self.ui.label(str(item['stack'])).classes('cui-debugger-stack')

    def _render_browser_streams(self) -> None:
        if self._requests_host is not None:
            self._requests_host.clear()
            with self._requests_host:
                requests = list(self._browser_snapshot.get('requests', ()) or ())
                if not requests:
                    self.ui.label('No browser fetch activity captured yet.').classes('cui-debugger-empty')
                for item in reversed(requests[-160:]):
                    status = item.get('status') if item.get('status') is not None else 'ERR'
                    with self.ui.element('article').classes('cui-debugger-request-row'):
                        self.ui.label(str(item.get('method', 'GET'))).classes('cui-debugger-request-row__method')
                        self.ui.label(str(status)).classes('cui-debugger-request-row__status')
                        self.ui.label(str(item.get('path', ''))).classes('cui-debugger-request-row__path')
                        self.ui.label(f"{item.get('duration_ms', 0)} ms").classes('cui-debugger-request-row__time')
        if self._events_host is not None:
            self._events_host.clear()
            with self._events_host:
                events = list(self._browser_snapshot.get('events', ()) or ())
                if not events:
                    self.ui.label('No browser state/events captured yet.').classes('cui-debugger-empty')
                for item in reversed(events[-160:]):
                    self.ui.label(self._json(item)).classes('cui-debugger-event-row')

    def _render_environment(self) -> None:
        if self._environment_host is None:
            return
        self._environment_host.clear()
        payload = runtime_snapshot(
            app_name=self.config.app_name,
            app_version=self.config.app_version,
            environment=self.config.environment,
        )
        payload['framework_version'] = self.config.framework_version
        payload['browser'] = self._browser_snapshot.get('browser', {})
        payload['page'] = self._browser_snapshot.get('page', {})
        with self._environment_host:
            self.ui.label(self._json(payload)).classes('cui-debugger-pre')

    def _render_health(self) -> None:
        if self._health_host is None:
            return
        self._health_host.clear()
        with self._health_host:
            self.ui.label(self._json(self._health_snapshot)).classes('cui-debugger-pre')

    async def refresh(self) -> None:
        self._browser_snapshot = await self._browser()
        self._health_snapshot = await self._health()
        self._render_summary()
        self._render_logs()
        self._render_browser_streams()
        self._render_environment()
        self._render_health()
        self._update_trigger_badge()

    async def open(self) -> None:
        await self.refresh()
        self.dialog.open()

    def close(self) -> None:
        self.dialog.close()

    async def download_bundle(self) -> None:
        await self.refresh()
        data = build_diagnostic_bundle(
            app_name=self.config.app_name,
            app_version=self.config.app_version,
            environment=self.config.environment,
            browser=self._browser_snapshot,
            health=self._health_snapshot,
            event_limit=max(250, self.config.event_limit),
        )
        safe_name = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in self.config.app_name.lower()).strip('-') or 'nicegui-app'
        self.ui.download.content(data, f'{safe_name}-diagnostics.json')


__all__ = ['BROWSER_DIAGNOSTICS_BOOTSTRAP', 'DebuggerConfig', 'UniversalDebugger']
