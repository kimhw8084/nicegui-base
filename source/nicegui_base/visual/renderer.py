from __future__ import annotations
import html,re
from pathlib import Path
from .models import IconSize, ICON_SIZE_PX
from .registry import icon_path, illustration_path

_FORBIDDEN=(r'<script\b',r'javascript:',r'<foreignObject\b',r'https?://',r'url\s*\(')

def _safe_svg(path:Path)->str:
    text=path.read_text(encoding='utf-8')
    lower=text.lower().replace('http://www.w3.org/2000/svg','')
    for pattern in _FORBIDDEN:
        if re.search(pattern,lower,re.I): raise ValueError(f'Unsafe SVG resource: {path.name}')
    return text

def render_icon_svg(key:str, *, size:IconSize|str=IconSize.MD, label:str|None=None, css_class:str='cui-icon')->str:
    size=IconSize(size); px=ICON_SIZE_PX[size]
    text=_safe_svg(icon_path(key))
    text=re.sub(r'width="24" height="24"',f'width="{px}" height="{px}"',text,count=1)
    aria=' aria-hidden="true"' if label is None else f' role="img" aria-label="{html.escape(label,quote=True)}"'
    text=text.replace(' aria-hidden="true" focusable="false"',aria+' focusable="false"',1)
    text=text.replace('<svg ',f'<svg class="{html.escape(css_class,quote=True)}" ',1)
    return text

def render_illustration_svg(key:str, *, label:str|None=None, css_class:str='cui-illustration')->str:
    text=_safe_svg(illustration_path(key))
    aria=' aria-hidden="true"' if label is None else f' role="img" aria-label="{html.escape(label,quote=True)}"'
    text=text.replace(' aria-hidden="true" focusable="false"',aria+' focusable="false"',1)
    return text.replace('<svg ',f'<svg class="{html.escape(css_class,quote=True)}" ',1)
