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


def _matches_filter(values: tuple[str, ...], requested: str | None) -> bool:
    if not requested or requested == 'all':
        return True
    requested_terms = set(tokens(requested))
    value_terms = set(tokens(' '.join(values)))
    return requested_terms <= value_terms


def _matches_reference_filters(
    entry: WorkbenchEntry,
    *,
    intent: str | None,
    data_shape: str | None,
    domain: str | None,
    related_to: str | None,
) -> bool:
    contract = entry.reference_contract
    if not _matches_filter((*contract.best_for, *entry.aliases, *entry.tags), intent):
        return False
    if not _matches_filter(contract.data_contract, data_shape):
        return False
    if not _matches_filter(contract.domain_tags, domain):
        return False
    if related_to and related_to != 'all':
        related = (*contract.alternatives, *contract.complements, *entry.related_keys)
        requested = normalize(related_to)
        if requested != normalize(entry.key) and not any(requested == normalize(value) for value in related):
            return False
    return True


def _filter_score(entry: WorkbenchEntry, requested: str) -> int:
    """Rank filter-only results by contract evidence, without title exact-match bias."""
    terms = tokens(requested)
    contract = entry.reference_contract
    searchable = normalize(' '.join((*contract.best_for, *contract.domain_tags, *contract.data_contract, *entry.tags, *entry.aliases)))
    score = 2 * _KIND_BONUS.get(entry.kind, 0)
    score += sum(18 for term in terms if term in searchable.split())
    return score


def search_entries(
    entries: Iterable[WorkbenchEntry],
    query: str,
    *,
    limit: int = 30,
    intent: str | None = None,
    data_shape: str | None = None,
    domain: str | None = None,
    related_to: str | None = None,
) -> tuple[SearchResult, ...]:
    """Search one catalog projection with deterministic contract-aware filters.

    An empty query is useful for filter-only Reference Explorer views; it remains
    empty when no filter is supplied so the legacy search contract is unchanged.
    """
    has_filter = any(value and value != 'all' for value in (intent, data_shape, domain, related_to))
    source = tuple(entry for entry in entries if _matches_reference_filters(
        entry, intent=intent, data_shape=data_shape, domain=domain, related_to=related_to,
    ))
    if not tokens(query) and not has_filter:
        return ()
    if not tokens(query):
        filter_query = ' '.join(value for value in (intent, data_shape, domain) if value and value != 'all')
        filtered = tuple(
            SearchResult(entry, _filter_score(entry, filter_query), ())
            for entry in source
        )
        return tuple(
            result for result in sorted(
                filtered,
                key=lambda item: (-item.score, item.entry.kind.value, item.entry.title.casefold(), item.entry.key),
            )[:max(0, limit)]
        )
    scored = (
        result for entry in source
        if (result := score_entry(entry, query)) is not None
    )
    return tuple(sorted(scored, key=lambda item: (-item.score, item.entry.kind.value, item.entry.title.casefold(), item.entry.key))[:max(0, limit)])
