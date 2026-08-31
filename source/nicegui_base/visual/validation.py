from __future__ import annotations
import json,re,xml.etree.ElementTree as ET
from pathlib import Path
from .models import AssetValidationIssue
from .registry import VISUAL_ROOT, ICON_REGISTRY, ILLUSTRATION_REGISTRY

FORBIDDEN_PATTERNS={
 'VIS002':r'<script\b', 'VIS003':r'https?://', 'VIS004':r'<foreignObject\b', 'VIS005':r'javascript:', 'VIS006':r'url\s*\(',
}

def validate_svg_file(path:Path)->list[AssetValidationIssue]:
    issues=[]; text=path.read_text(encoding='utf-8')
    try: ET.fromstring(text)
    except ET.ParseError as e: return [AssetValidationIssue(str(path),'VIS001',f'Invalid SVG/XML: {e}')]
    low=text.lower()
    scan=low.replace('http://www.w3.org/2000/svg','')
    for code,pattern in FORBIDDEN_PATTERNS.items():
        if re.search(pattern,scan,re.I): issues.append(AssetValidationIssue(str(path),code,'Forbidden SVG construct detected'))
    if '<svg' not in low or 'viewbox=' not in low: issues.append(AssetValidationIssue(str(path),'VIS007','SVG must define a viewBox'))
    # runtime icons must be semantic-currentColor, not hard-coded presentational colors
    rel=str(path.relative_to(VISUAL_ROOT))
    if rel.startswith('icons/') and 'currentColor' not in text: issues.append(AssetValidationIssue(str(path),'VIS008','Icon must use currentColor'))
    return issues

def validate_visual_package()->list[AssetValidationIssue]:
    issues=[]
    for rec in list(ICON_REGISTRY.values())+list(ILLUSTRATION_REGISTRY.values()):
        p=VISUAL_ROOT/rec.path
        if not p.exists(): issues.append(AssetValidationIssue(rec.path,'VIS009','Manifest points to missing asset')); continue
        issues.extend(validate_svg_file(p))
    for sub in ('dataviz/markers','dataviz/patterns'):
        for p in (VISUAL_ROOT/sub).glob('*.svg'): issues.extend(validate_svg_file(p))
    return issues
