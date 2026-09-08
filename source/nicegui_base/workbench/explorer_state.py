from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, MutableMapping

STATE_ROOT = 'nicegui_base_explorer_v1'
MAX_COMPARE = 3
MAX_RECENTS = 12


@dataclass(slots=True)
class ExplorerState:
    query: str = ''
    category: str = 'all'
    favorites_only: bool = False
    favorites: tuple[str, ...] = ()
    compare: tuple[str, ...] = ()
    recents: tuple[str, ...] = ()

    def normalized(self) -> 'ExplorerState':
        def clean(values, limit: int | None = None) -> tuple[str, ...]:
            items = tuple(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))
            return items if limit is None else items[:limit]
        return ExplorerState(
            query=str(self.query or '').strip()[:240],
            category=str(self.category or 'all').strip() or 'all',
            favorites_only=bool(self.favorites_only),
            favorites=clean(self.favorites),
            compare=clean(self.compare, MAX_COMPARE),
            recents=clean(self.recents, MAX_RECENTS),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())


class ExplorerStateStore:
    """Small user-scoped storage facade for non-sensitive browsing preferences.

    This state intentionally excludes application/provider data. NiceGUI's user
    storage is browser-cookie scoped and keeps Reference Explorer navigation state
    separate from shared process caches.
    """

    def __init__(self, storage: MutableMapping[str, Any]):
        self.storage = storage

    def _root(self) -> dict[str, Any]:
        raw = self.storage.get(STATE_ROOT, {})
        return dict(raw) if isinstance(raw, dict) else {}

    def load(self, section: str) -> ExplorerState:
        root = self._root()
        raw = root.get(section, {})
        raw = raw if isinstance(raw, dict) else {}
        return ExplorerState(
            query=str(raw.get('query') or ''),
            category=str(raw.get('category') or 'all'),
            favorites_only=bool(raw.get('favorites_only', False)),
            favorites=tuple(raw.get('favorites') or ()),
            compare=tuple(raw.get('compare') or ()),
            recents=tuple(raw.get('recents') or ()),
        ).normalized()

    def save(self, section: str, state: ExplorerState) -> ExplorerState:
        normalized = state.normalized()
        root = self._root()
        root[section] = normalized.to_dict()
        self.storage[STATE_ROOT] = root
        return normalized

    def prime(self, section: str, *, query: str = '', category: str = 'all') -> ExplorerState:
        state = self.load(section)
        state.query = query
        state.category = category
        state.favorites_only = False
        return self.save(section, state)

    def toggle_favorite(self, section: str, key: str) -> ExplorerState:
        state = self.load(section)
        values = list(state.favorites)
        if key in values:
            values.remove(key)
        else:
            values.insert(0, key)
        state.favorites = tuple(values)
        return self.save(section, state)

    def toggle_compare(self, section: str, key: str) -> ExplorerState:
        state = self.load(section)
        values = list(state.compare)
        if key in values:
            values.remove(key)
        else:
            if len(values) >= MAX_COMPARE:
                values.pop(0)
            values.append(key)
        state.compare = tuple(values)
        return self.save(section, state)

    def clear_compare(self, section: str) -> ExplorerState:
        state = self.load(section)
        state.compare = ()
        return self.save(section, state)

    def add_recent(self, section: str, key: str) -> ExplorerState:
        state = self.load(section)
        state.recents = (key, *tuple(item for item in state.recents if item != key))[:MAX_RECENTS]
        return self.save(section, state)


EXPLORER_BROWSER_STATE_SCRIPT = r'''<script>(()=>{
  if(window.__niceguiBaseExplorerStateInstalled)return;
  window.__niceguiBaseExplorerStateInstalled=true;
  const scrollKey=()=>`nicegui-base:explorer-scroll:${location.pathname}`;
  const save=()=>{try{sessionStorage.setItem(scrollKey(),String(window.scrollY||0));}catch(_){}};
  const restore=()=>{try{const raw=sessionStorage.getItem(scrollKey());if(raw!==null){const y=Math.max(0,Number(raw)||0);requestAnimationFrame(()=>window.scrollTo(0,y));setTimeout(()=>window.scrollTo(0,y),160);}}catch(_){}};
  window.addEventListener('pagehide',save,{passive:true});
  window.addEventListener('beforeunload',save,{passive:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore,{once:true});else restore();
})();</script>'''


__all__ = ['ExplorerState', 'ExplorerStateStore', 'EXPLORER_BROWSER_STATE_SCRIPT', 'MAX_COMPARE', 'MAX_RECENTS', 'STATE_ROOT']
