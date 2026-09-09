from __future__ import annotations

from dataclasses import replace
from typing import Any, MutableMapping

from nicegui_base.state import SidebarPreference, UserPreferences


class PreferenceService:
    def __init__(self, backing: MutableMapping[str, Any], *, key: str = 'nicegui_base_preferences'):
        self.backing = backing; self.key = key

    def load(self) -> UserPreferences:
        return UserPreferences.from_mapping(self.backing.get(self.key, {}))

    def save(self, preferences: UserPreferences) -> UserPreferences:
        self.backing[self.key] = preferences.to_dict(); return preferences

    def update(self, **changes: Any) -> UserPreferences:
        current = self.load()
        updated = replace(current, **changes)
        return self.save(updated)

    def save_table_state(self, table_key: str, state: dict[str, Any]) -> UserPreferences:
        current = self.load(); states = {k: dict(v) for k, v in current.table_states.items()}; states[table_key] = dict(state)
        return self.save(replace(current, table_states=states))

    def save_filter_view(self, view_key: str, values: dict[str, Any]) -> UserPreferences:
        current = self.load(); views = {k: dict(v) for k, v in current.filter_views.items()}; views[view_key] = dict(values)
        return self.save(replace(current, filter_views=views))

    def delete_filter_view(self, view_key: str) -> UserPreferences:
        current = self.load(); views = {k: dict(v) for k, v in current.filter_views.items()}; views.pop(view_key, None)
        return self.save(replace(current, filter_views=views))


class WorkspacePreferenceService:
    """Persists complete analysis workspace state under the existing user preference backing."""
    def __init__(self, backing: MutableMapping[str, Any], *, key: str='nicegui_base_workspaces', max_recent:int=20):
        self.backing=backing; self.key=key; self.max_recent=max_recent
    def save_workspace(self,name:str,state:dict[str,Any])->dict[str,Any]:
        if not name.strip():raise ValueError('workspace name is required')
        all_=dict(self.backing.get(self.key,{}) or {}); all_[name]=dict(state); self.backing[self.key]=all_; return dict(state)
    def load_workspace(self,name:str)->dict[str,Any]|None:
        value=(self.backing.get(self.key,{}) or {}).get(name); return dict(value) if value is not None else None
    def list_workspaces(self)->tuple[str,...]:return tuple(sorted((self.backing.get(self.key,{}) or {}).keys()))
    def delete_workspace(self,name:str)->bool:
        all_=dict(self.backing.get(self.key,{}) or {}); existed=name in all_; all_.pop(name,None); self.backing[self.key]=all_; return existed
    def add_favorite(self,value:str)->UserPreferences:
        p=PreferenceService(self.backing).load(); items=tuple(dict.fromkeys((*p.favorites,value))); return PreferenceService(self.backing).save(replace(p,favorites=items))
    def remove_favorite(self,value:str)->UserPreferences:
        p=PreferenceService(self.backing).load(); return PreferenceService(self.backing).save(replace(p,favorites=tuple(x for x in p.favorites if x!=value)))
    def touch_recent(self,value:str)->UserPreferences:
        p=PreferenceService(self.backing).load(); items=(value,*[x for x in p.recent_entities if x!=value])[:self.max_recent]; return PreferenceService(self.backing).save(replace(p,recent_entities=tuple(items)))
