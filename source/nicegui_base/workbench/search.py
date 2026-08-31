from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .models import SearchResult, WorkbenchEntry, WorkbenchKind

_REPLACEMENTS = {
    '²': '2', '₂': '2', '–': '-', '—': '-', '_': ' ', '/': ' ',
}



_KIND_BONUS = {
    WorkbenchKind.RECIPE: 28,
    WorkbenchKind.PATTERN: 26,
    WorkbenchKind.ANALYTIC: 24,
    WorkbenchKind.COMPONENT: 12,
    WorkbenchKind.REFERENCE: 0,
}
_ASSET_REGISTRIES = {'icons', 'illustrations'}
_ASSET_INTENT = {'icon', 'icons', 'illustration', 'illustrations', 'svg', 'asset', 'assets'}
_APP_INTENT = {'app', 'application', 'starter', 'template', 'build', 'page'}

def normalize(text: str) -> str:
    value = unicodedata.normalize('NFKD', str(text).casefold())
    for old, new in _REPLACEMENTS.items():
        value = value.replace(old, new)
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def tokens(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(normalize(text).split()))


def score_entry(entry: WorkbenchEntry, query: str) -> SearchResult | None:
    terms = tokens(query)
    if not terms:
        return None
    key = normalize(entry.key)
    title = normalize(entry.title)
    category = normalize(entry.category)
    aliases = tuple(normalize(item) for item in entry.aliases)
    corpus = normalize(entry.searchable_text)
    score = 0
    matched: list[str] = []
    normalized_query = normalize(query)
    if normalized_query == key or normalized_query == title:
        score += 160
    elif normalized_query in title or normalized_query in key:
        score += 90
    if normalized_query in aliases:
        score += 130
    for term in terms:
        if term in key.split():
            score += 65
        elif term in title.split():
            score += 55
        elif any(term == alias or term in alias.split() for alias in aliases):
            score += 48
        elif term in category.split():
            score += 30
        elif term in corpus:
            score += 12
        else:
            continue
        matched.append(term)
    if not matched:
        return None
    # Reward complete multi-token matches; keep deterministic ordering outside this function.
    if len(matched) == len(terms):
        score += 20 * len(terms)
    score += _KIND_BONUS.get(entry.kind, 0)
    registry = normalize(entry.metadata.get('registry_name', ''))
    term_set = set(terms)
    if registry in _ASSET_REGISTRIES:
        # Semantic assets stay fully searchable, but do not eclipse an app/analytic merely
        # because an icon has the exact same noun (for example ``wafer``).
        score += 55 if term_set & _ASSET_INTENT else -110
    if term_set & _APP_INTENT and entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE}:
        score += 55
    return SearchResult(entry, score, tuple(matched))


def search_entries(entries: Iterable[WorkbenchEntry], query: str, *, limit: int = 30) -> tuple[SearchResult, ...]:
    scored = (result for entry in entries if (result := score_entry(entry, query)) is not None)
    return tuple(sorted(scored, key=lambda item: (-item.score, item.entry.kind.value, item.entry.title.casefold(), item.entry.key))[:limit])
