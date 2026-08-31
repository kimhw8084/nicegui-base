from __future__ import annotations
import json
from pathlib import Path
from .models import IconDefinition, IllustrationDefinition

VISUAL_ROOT=Path(__file__).resolve().parent

def _json(name:str):
    return json.loads((VISUAL_ROOT/'manifest'/name).read_text(encoding='utf-8'))

_icon_payload=_json('icons.json')
ICON_REGISTRY={r['key']:IconDefinition(key=r['key'],category=r['category'],domain=r['domain'],path=r['path'],aliases=tuple(r.get('aliases',())),theme=r.get('theme','currentColor'),source=r.get('source','nicegui-base-project-authored'),license=r.get('license','NiceGUI Base project-authored asset')) for r in _icon_payload['icons']}
ICON_ALIASES=dict(_icon_payload.get('aliases',{}))
ILLUSTRATION_REGISTRY={r['key']:IllustrationDefinition(key=r['key'],path=r['path'],category=r.get('category','state'),theme=r.get('theme','currentColor')) for r in _json('illustrations.json')['illustrations']}

def resolve_icon_key(key:str)->str:
    norm=key.strip().lower().replace(' ','-')
    return ICON_ALIASES.get(norm,norm)

def get_icon(key:str)->IconDefinition:
    canonical=resolve_icon_key(key)
    try: return ICON_REGISTRY[canonical]
    except KeyError as e: raise KeyError(f"Unknown icon {key!r}; inspect ICON_REGISTRY or search_icons().") from e

def icon_path(key:str)->Path:
    return VISUAL_ROOT/get_icon(key).path

def get_illustration(key:str)->IllustrationDefinition:
    try:return ILLUSTRATION_REGISTRY[key]
    except KeyError as e: raise KeyError(f"Unknown illustration {key!r}") from e

def illustration_path(key:str)->Path:
    return VISUAL_ROOT/get_illustration(key).path

def search_icons(query:str, *, category:str|None=None, domain:str|None=None, limit:int=30)->list[IconDefinition]:
    q=query.strip().lower()
    out=[]
    for item in ICON_REGISTRY.values():
        if category and item.category!=category: continue
        if domain and item.domain!=domain: continue
        hay=' '.join((item.key,*item.aliases)).lower()
        if not q or q in hay: out.append(item)
    return sorted(out,key=lambda x:(0 if x.key.startswith(q) else 1,x.key))[:limit]
