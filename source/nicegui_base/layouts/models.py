from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SidebarMode(str, Enum):
    EXPANDED = 'expanded'
    COMPACT = 'compact'
    HIDDEN = 'hidden'
    AUTO = 'auto'


class ContentWidth(str, Enum):
    READING = 'reading'
    STANDARD = 'standard'
    WIDE = 'wide'
    FULL = 'full'


class PanelSize(str, Enum):
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'
    XLARGE = 'xlarge'
    FULL = 'full'


class GridPreset(str, Enum):
    METRICS = 'metrics'
    HALVES = 'halves'
    THIRDS = 'thirds'
    FOURTHS = 'fourths'
    SIDEBAR_CONTENT = 'sidebar_content'
    CONTENT_INSPECTOR = 'content_inspector'
    MAIN_ASIDE = 'main_aside'
    AUTO = 'auto'


class StackDirection(str, Enum):
    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'
    RESPONSIVE = 'responsive'


class Align(str, Enum):
    START = 'start'
    CENTER = 'center'
    END = 'end'
    STRETCH = 'stretch'


class Gap(str, Enum):
    NONE = 'none'
    XS = 'xs'
    SM = 'sm'
    MD = 'md'
    LG = 'lg'
    XL = 'xl'


class LayoutSlot(str, Enum):
    HEADER = 'header'
    FILTERS = 'filters'
    METRICS = 'metrics'
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    DATA = 'data'
    DETAILS = 'details'
    ACTIONS = 'actions'
    CONTENT = 'content'
    NAVIGATION = 'navigation'


@dataclass(frozen=True, slots=True)
class ResponsiveRule:
    phone: str
    tablet: str
    laptop: str
    desktop: str


PANEL_WIDTHS: dict[PanelSize, int | None] = {
    PanelSize.SMALL: 320,
    PanelSize.MEDIUM: 420,
    PanelSize.LARGE: 560,
    PanelSize.XLARGE: 720,
    PanelSize.FULL: None,
}

CONTENT_WIDTHS: dict[ContentWidth, int | None] = {
    ContentWidth.READING: 760,
    ContentWidth.STANDARD: 1120,
    ContentWidth.WIDE: 1440,
    ContentWidth.FULL: None,
}

GAP_TOKEN: dict[Gap, str] = {
    Gap.NONE: '0',
    Gap.XS: '2',
    Gap.SM: '3',
    Gap.MD: '4',
    Gap.LG: '6',
    Gap.XL: '8',
}
