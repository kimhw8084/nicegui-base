from __future__ import annotations

from typing import Any, MutableMapping

from nicegui_base.design import ThemeMode
from nicegui_base.services import (
    ClipboardService, DownloadService, NavigationService, NavigationTarget, NotificationService,
    KeyboardShortcutRegistry, PreferenceService, ThemeService, normalize_shortcut,
)
from nicegui_base.state import BrowserState, SessionState, TabState
from nicegui_base.integrations.nicegui_feedback_runtime import show_company_toast


def _nicegui():
    try:
        from nicegui import app, ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required for NiceGUIStateServices.') from exc
    return app, ui


class NiceGUIStateServices:
    """Runtime adapters around NiceGUI 3.15 storage and browser services.

    `user_preferences()` intentionally uses app.storage.user. Current NiceGUI docs
    describe app.storage.browser as read-only after the initial response, while
    app.storage.user remains mutable and shared across browser tabs.
    """

    @staticmethod
    def user_store() -> MutableMapping[str, Any]:
        app, _ = _nicegui(); return app.storage.user

    @staticmethod
    def tab_store() -> MutableMapping[str, Any]:
        app, _ = _nicegui(); return app.storage.tab

    @staticmethod
    def client_store() -> MutableMapping[str, Any]:
        app, _ = _nicegui(); return app.storage.client

    @classmethod
    def user_preferences(cls, *, key: str = 'nicegui_base_preferences') -> PreferenceService:
        return PreferenceService(cls.user_store(), key=key)

    @classmethod
    def session_state(cls) -> SessionState:
        return SessionState(backing=cls.client_store())

    @classmethod
    def tab_state(cls) -> TabState:
        return TabState(backing=cls.tab_store())

    @staticmethod
    def notification_service() -> NotificationService:
        _, ui = _nicegui()
        def sink(spec):
            show_company_toast(ui, spec.message, intent=spec.intent.value, duration_ms=spec.duration_ms)
        return NotificationService(sink)

    @staticmethod
    def navigation_service() -> NavigationService:
        _, ui = _nicegui()
        def sink(target: NavigationTarget):
            path = target.path
            if target.query:
                from urllib.parse import urlencode
                path += '?' + urlencode(target.query, doseq=True)
            ui.navigate.to(path)
        return NavigationService(sink)

    @staticmethod
    def clipboard_service() -> ClipboardService:
        _, ui = _nicegui(); return ClipboardService(lambda text: ui.clipboard.write(text))

    @staticmethod
    def download_service() -> DownloadService:
        _, ui = _nicegui(); return DownloadService(lambda req: ui.download(req.content, filename=req.filename, media_type=req.media_type))


    @staticmethod
    def install_keyboard_shortcuts(registry: KeyboardShortcutRegistry, *, ignore: list[str] | None = None):
        _, ui = _nicegui()
        ignored = ['input', 'select', 'button', 'textarea'] if ignore is None else ignore
        def handle(event):
            if not event.action.keydown or event.action.repeat:
                return
            parts = []
            if event.modifiers.ctrl: parts.append('ctrl')
            if event.modifiers.alt: parts.append('alt')
            if event.modifiers.shift: parts.append('shift')
            if event.modifiers.meta: parts.append('meta')
            parts.append(str(event.key.name).lower())
            registry.trigger(normalize_shortcut('+'.join(parts)))
        return ui.keyboard(on_key=handle, repeating=False, ignore=ignored)

    @staticmethod
    def theme_service(dark_element: Any, *, mode: ThemeMode = ThemeMode.SYSTEM, density: str = 'compact') -> ThemeService:
        _, ui = _nicegui()
        def sink(next_mode: ThemeMode, next_density: str):
            if next_mode is ThemeMode.DARK: dark_element.enable()
            elif next_mode is ThemeMode.LIGHT: dark_element.disable()
            else: dark_element.set_value(None)
            ui.run_javascript(f"document.documentElement.dataset.theme='{next_mode.value}';document.documentElement.dataset.density='{next_density}'")
        return ThemeService(mode, density, sink)
