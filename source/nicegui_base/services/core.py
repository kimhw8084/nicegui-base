from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nicegui_base.design import ThemeMode
from nicegui_base.feedback import FeedbackIntent, ToastSpec


@dataclass(frozen=True, slots=True)
class NavigationTarget:
    path: str
    query: dict[str, Any] | None = None
    replace: bool = False


class NotificationService:
    def __init__(self, sink: Callable[[ToastSpec], Any] | None = None, *, history_limit:int=100): self.sink = sink; self.history = deque(maxlen=history_limit)
    def notify(self, message: str, *, intent: FeedbackIntent = FeedbackIntent.INFO, duration_ms: int = 3500) -> ToastSpec:
        spec = ToastSpec(message, intent, duration_ms); self.history.append(spec)
        if self.sink: self.sink(spec)
        return spec
    def success(self, message: str): return self.notify(message, intent=FeedbackIntent.SUCCESS)
    def warning(self, message: str): return self.notify(message, intent=FeedbackIntent.WARNING)
    def error(self, message: str): return self.notify(message, intent=FeedbackIntent.DANGER)


class NavigationService:
    def __init__(self, sink: Callable[[NavigationTarget], Any] | None = None, *, history_limit:int=100): self.sink = sink; self.history = deque(maxlen=history_limit)
    def go(self, path: str, *, query: dict[str, Any] | None = None, replace: bool = False) -> NavigationTarget:
        target = NavigationTarget(path, query, replace); self.history.append(target)
        if self.sink: self.sink(target)
        return target
    def back_target(self) -> NavigationTarget | None: return self.history[-2] if len(self.history) >= 2 else None


class ThemeService:
    def __init__(self, mode: ThemeMode = ThemeMode.SYSTEM, density: str = 'compact', sink: Callable[[ThemeMode, str], Any] | None = None):
        if density not in {'comfortable','compact','dense'}: raise ValueError('Invalid density')
        self.mode = mode; self.density = density; self.sink = sink
    def set(self, *, mode: ThemeMode | None = None, density: str | None = None) -> None:
        if mode is not None: self.mode = mode
        if density is not None:
            if density not in {'comfortable','compact','dense'}: raise ValueError('Invalid density')
            self.density = density
        if self.sink: self.sink(self.mode, self.density)


class ClipboardService:
    def __init__(self, sink: Callable[[str], Any] | None = None): self.sink = sink
    def copy(self, text: str) -> str:
        if self.sink: self.sink(text)
        return text


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    filename: str
    content: bytes
    media_type: str = 'application/octet-stream'


class DownloadService:
    def __init__(self, sink: Callable[[DownloadRequest], Any] | None = None): self.sink = sink
    def download(self, filename: str, content: bytes | str, *, media_type: str = 'application/octet-stream') -> DownloadRequest:
        if not filename.strip(): raise ValueError('filename must not be empty')
        payload = content.encode() if isinstance(content, str) else content
        request = DownloadRequest(filename, payload, media_type)
        if self.sink: self.sink(request)
        return request
