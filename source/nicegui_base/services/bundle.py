from __future__ import annotations
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, MutableMapping
from .core import ClipboardService, DownloadService, NavigationService, NotificationService, ThemeService
from .keyboard import KeyboardShortcutRegistry
from .operations import DialogService, ErrorService, LoggingService
from .preferences import PreferenceService, WorkspacePreferenceService
from .commands import CommandRegistry
from nicegui_base.performance import LifecycleScope, PerformanceMonitor
@dataclass(slots=True)
class ApplicationServices:
    notifications:NotificationService=field(default_factory=NotificationService)
    navigation:NavigationService=field(default_factory=NavigationService)
    theme:ThemeService=field(default_factory=ThemeService)
    clipboard:ClipboardService=field(default_factory=ClipboardService)
    downloads:DownloadService=field(default_factory=DownloadService)
    dialogs:DialogService=field(default_factory=DialogService)
    logging:LoggingService=field(default_factory=LoggingService)
    errors:ErrorService|None=None
    shortcuts:KeyboardShortcutRegistry=field(default_factory=KeyboardShortcutRegistry)
    commands:CommandRegistry=field(default_factory=CommandRegistry)
    performance:PerformanceMonitor=field(default_factory=PerformanceMonitor)
    lifecycle:LifecycleScope=field(default_factory=LifecycleScope)
    preferences:PreferenceService|None=None
    workspaces:WorkspacePreferenceService|None=None
    def __post_init__(self):
        if self.errors is None:self.errors=ErrorService(self.logging)
    @classmethod
    def with_preferences(cls,backing:MutableMapping[str,Any],**overrides:Any):
        return cls(preferences=PreferenceService(backing),workspaces=WorkspacePreferenceService(backing),**overrides)
    def register_cleanup(self, cleanup:Callable[[],Any|Awaitable[Any]], *, key:object|None=None):
        return self.lifecycle.register(cleanup,key=key)
    def create_task(self, awaitable:Awaitable[Any], *, name:str|None=None):
        return self.lifecycle.create_task(awaitable,name=name)
    async def aclose(self)->tuple[BaseException,...]:
        return await self.lifecycle.aclose()
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
        return False
