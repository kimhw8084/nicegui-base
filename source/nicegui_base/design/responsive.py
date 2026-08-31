from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ViewportProfile:
    key: str
    width: int
    height: int
    tier: str

    def __post_init__(self) -> None:
        if self.width < 320 or self.height < 480:
            raise ValueError('ViewportProfile must represent a supported application viewport')


_CANONICAL = {
    'phone-compact': ViewportProfile('phone-compact', 390, 844, 'phone'),
    'phone-wide': ViewportProfile('phone-wide', 430, 932, 'phone'),
    'tablet-narrow': ViewportProfile('tablet-narrow', 768, 1024, 'tablet'),
    'tablet-wide': ViewportProfile('tablet-wide', 1024, 900, 'tablet'),
    'desktop-compact': ViewportProfile('desktop-compact', 1280, 900, 'desktop'),
    'desktop-wide': ViewportProfile('desktop-wide', 1440, 1000, 'desktop'),
}
CANONICAL_VIEWPORTS: Mapping[str, ViewportProfile] = MappingProxyType(_CANONICAL)


def canonical_viewport(key: str) -> ViewportProfile:
    try:
        return CANONICAL_VIEWPORTS[key]
    except KeyError as exc:
        raise KeyError(f'Unknown canonical viewport: {key}') from exc


__all__ = ['ViewportProfile', 'CANONICAL_VIEWPORTS', 'canonical_viewport']
