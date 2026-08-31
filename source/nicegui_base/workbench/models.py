from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class WorkbenchKind(str, Enum):
    COMPONENT = 'component'
    PATTERN = 'pattern'
    ANALYTIC = 'analytic'
    RECIPE = 'recipe'
    REFERENCE = 'reference'


@dataclass(frozen=True, slots=True)
class WorkbenchEntry:
    """Presentation metadata for one discoverable NiceGUI Base capability.

    This model never becomes domain truth. ``source_authority`` identifies the
    canonical registry/catalog that owns the capability, while preview/sample and
    relationship fields describe only how the Workbench exposes that authority.
    """

    key: str
    kind: WorkbenchKind
    title: str
    description: str
    route: str
    category: str = ''
    aliases: tuple[str, ...] = ()
    use_when: tuple[str, ...] = ()
    avoid_when: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    source_authority: str = ''
    maturity: str = ''
    live_preview: bool = False
    sample_data: bool = False
    related_keys: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        parts = (
            self.key, self.kind.value, self.title, self.description, self.category,
            self.source_authority, self.maturity,
            *self.aliases, *self.use_when, *self.avoid_when, *self.tags, *self.related_keys,
        )
        return ' '.join(str(part) for part in parts if part)


@dataclass(frozen=True, slots=True)
class SearchResult:
    entry: WorkbenchEntry
    score: int
    matched_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkbenchCoverage:
    total: int
    components: int
    patterns: int
    analytics: int
    recipes: int
    categories: tuple[str, ...]
