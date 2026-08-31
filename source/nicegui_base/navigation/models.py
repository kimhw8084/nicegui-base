from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

_ID = re.compile(r"^[a-z][a-z0-9_-]*$")


def _valid_id(value: str) -> None:
    if not _ID.match(value):
        raise ValueError(f"Invalid semantic id {value!r}; use lowercase letters, digits, '_' or '-'.")


def _valid_route(route: str | None) -> None:
    if route is not None and not route.startswith('/'):
        raise ValueError(f"Routes must start with '/': {route!r}")


@dataclass(frozen=True, slots=True)
class NavItem:
    id: str
    label: str
    route: str | None = None
    icon: str | None = None
    badge: str | int | None = None
    permission: str | None = None
    children: tuple['NavItem', ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _valid_id(self.id)
        _valid_route(self.route)
        if not self.label.strip():
            raise ValueError('Navigation labels cannot be empty.')
        if self.route is None and not self.children:
            raise ValueError(f"Navigation item {self.id!r} needs a route or children.")
        child_ids = [child.id for child in self.children]
        if len(child_ids) != len(set(child_ids)):
            raise ValueError(f"Navigation item {self.id!r} has duplicate child ids.")


@dataclass(frozen=True, slots=True)
class NavSection:
    id: str
    label: str | None
    items: tuple[NavItem, ...]

    def __post_init__(self) -> None:
        _valid_id(self.id)
        if not self.items:
            raise ValueError('Navigation sections cannot be empty.')
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Navigation section {self.id!r} has duplicate item ids.")


@dataclass(frozen=True, slots=True)
class Breadcrumb:
    label: str
    route: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError('Breadcrumb labels cannot be empty.')
        _valid_route(self.route)


@dataclass(frozen=True, slots=True)
class TabSpec:
    id: str
    label: str
    icon: str | None = None
    badge: str | int | None = None
    lazy: bool = True
    url_segment: str | None = None
    disabled: bool = False

    def __post_init__(self) -> None:
        _valid_id(self.id)
        if not self.label.strip():
            raise ValueError('Tab labels cannot be empty.')
        if self.url_segment is not None and '/' in self.url_segment:
            raise ValueError('Tab url_segment must be one path segment.')


@dataclass(frozen=True, slots=True)
class NavigationModel:
    sections: tuple[NavSection, ...]

    def __post_init__(self) -> None:
        ids = [section.id for section in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError('Navigation section ids must be unique.')

    def iter_items(self) -> Iterable[NavItem]:
        def walk(item: NavItem) -> Iterable[NavItem]:
            yield item
            for child in item.children:
                yield from walk(child)
        for section in self.sections:
            for item in section.items:
                yield from walk(item)

    def route_index(self) -> dict[str, NavItem]:
        index: dict[str, NavItem] = {}
        for item in self.iter_items():
            if item.route is None:
                continue
            if item.route in index:
                raise ValueError(f"Duplicate navigation route: {item.route}")
            index[item.route] = item
        return index
