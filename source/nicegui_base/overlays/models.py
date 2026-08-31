from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Sequence




class OverlayLayer(IntEnum):
    """Company-owned global stacking contract.

    Local component internals must stay below POPOVER. Modal backdrops and
    surfaces always dominate application chrome; toasts are the final transient
    feedback layer.
    """
    BASE = 0
    STICKY = 100
    APP_CHROME = 600
    LOCAL_POPUP = 900
    POPOVER = 2000
    BACKDROP = 3000
    MODAL = 3100
    TOOLTIP = 3200
    TOAST = 4000


class OverlaySize(str, Enum):
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'
    X_LARGE = 'x-large'
    FULL = 'full'


class DrawerSide(str, Enum):
    LEFT = 'left'
    RIGHT = 'right'


class OverlayRole(str, Enum):
    DETAIL = 'detail'
    FORM = 'form'
    FILTER = 'filter'
    INSPECTOR = 'inspector'
    ACTIVITY = 'activity'
    NAVIGATION = 'navigation'


class DialogIntent(str, Enum):
    DEFAULT = 'default'
    CONFIRM = 'confirm'
    DANGER = 'danger'


@dataclass(frozen=True, slots=True)
class DrawerSpec:
    title: str
    role: OverlayRole = OverlayRole.DETAIL
    side: DrawerSide = DrawerSide.RIGHT
    size: OverlaySize = OverlaySize.MEDIUM
    dismissible: bool = True
    resizable: bool = False
    persistent: bool = False
    full_screen_on_mobile: bool = True

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('DrawerSpec title must not be empty')

    @property
    def classes(self) -> str:
        flags = []
        if self.resizable:
            flags.append('is-resizable')
        if self.persistent:
            flags.append('is-persistent')
        if self.full_screen_on_mobile:
            flags.append('is-mobile-full')
        return ' '.join(['cui-drawer', f'cui-drawer--{self.side.value}', f'cui-drawer--{self.size.value}', *flags])


@dataclass(frozen=True, slots=True)
class DialogSpec:
    title: str
    description: str | None = None
    size: OverlaySize = OverlaySize.SMALL
    intent: DialogIntent = DialogIntent.DEFAULT
    dismissible: bool = True
    primary_label: str | None = None
    secondary_label: str | None = 'Cancel'
    destructive: bool = False
    typed_confirmation: str | None = None
    close_on_primary: bool = True
    close_on_secondary: bool = True

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('DialogSpec title must not be empty')
        if self.typed_confirmation and not self.destructive:
            raise ValueError('typed_confirmation requires destructive=True')

    @property
    def classes(self) -> str:
        return f'cui-dialog cui-dialog--{self.size.value} cui-dialog--{self.intent.value}'


MenuCallback = Callable[[Any], Any] | Callable[[], Any]


@dataclass(frozen=True, slots=True)
class MenuItemSpec:
    key: str
    label: str
    icon: str | None = None
    disabled: bool = False
    danger: bool = False
    shortcut: str | None = None
    separator_before: bool = False
    on_select: MenuCallback | None = field(default=None, compare=False, repr=False)
    close_on_select: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('MenuItemSpec requires key and label')


@dataclass(frozen=True, slots=True)
class MenuSpec:
    items: Sequence[MenuItemSpec] = field(default_factory=tuple)
    searchable: bool = False
    max_height: int | None = 360

    def __post_init__(self) -> None:
        keys = [item.key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError('Menu item keys must be unique')
        if self.max_height is not None and self.max_height < 120:
            raise ValueError('max_height must be >= 120')


@dataclass(frozen=True, slots=True)
class TooltipSpec:
    text: str
    delay_ms: int = 450
    max_width: int = 320

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError('Tooltip text must not be empty')
        if self.delay_ms < 0:
            raise ValueError('delay_ms must be >= 0')


@dataclass(frozen=True, slots=True)
class PopoverSpec:
    title: str | None = None
    dismissible: bool = True
    placement: str = 'bottom-start'
