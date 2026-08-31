from __future__ import annotations
import importlib.util, json, re, sys
from pathlib import Path
from nicegui_base.ai import load_framework_catalog, validate_python_file
from nicegui_base.components import COMPONENT_REGISTRY
from nicegui_base.content import CONTENT_REGISTRY
from nicegui_base.jobs import JOB_REGISTRY
from nicegui_base.patterns import PATTERN_REGISTRY
from nicegui_base.interaction_registry import INTERACTION_REGISTRY
from nicegui_base.data_table import TABLE_REGISTRY
from nicegui_base.visualization import VISUALIZATION_REGISTRY
from nicegui_base.engineering import ENGINEERING_REGISTRY
from nicegui_base.convenience_registry import CONVENIENCE_REGISTRY
from nicegui_base.performance import PERFORMANCE_REGISTRY
from nicegui_base.security import SECURITY_REGISTRY
from nicegui_base.runtime import RUNTIME_REGISTRY
from nicegui_base.analysis import ANALYSIS_REGISTRY
from nicegui_base.visual import ICON_REGISTRY, ILLUSTRATION_REGISTRY, validate_visual_package
from nicegui_base.design.css import build_css
from nicegui_base.layouts.css import build_layout_css
from nicegui_base.components.css import build_component_css
from nicegui_base.interaction_css import build_interaction_css
from nicegui_base.data_table.css import build_data_table_css
from nicegui_base.visualization.css import build_visualization_css
from nicegui_base.visual.css import build_visual_asset_css
from nicegui_base.engineering.css import build_engineering_css
from nicegui_base.integrations.nicegui_theme import build_framework_css
from nicegui_base.certification.mac_lab_css import build_mac_lab_css
from .models import CertificationCheck, CertificationReport, CertificationStatus
from .visual_audit import audit_framework_visual_sources, audit_visual_css
from .nicegui_runtime_contract import scan_source_contract, run_installed_runtime_contract

from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION
EXPECTED_PATTERNS=10

def _ok(key,label,detail,category='integration'): return CertificationCheck(key,label,CertificationStatus.PASS,detail,category)
def _fail(key,label,detail,category='integration'): return CertificationCheck(key,label,CertificationStatus.FAIL,detail,category)
def _warn(key,label,detail,category='integration',required=False): return CertificationCheck(key,label,CertificationStatus.WARNING,detail,category,required)

def combined_css()->str:
    return build_framework_css()

def run_certification(root: str|Path|None=None, *, require_nicegui: bool=False)->CertificationReport:
    root=Path(root) if root else Path.cwd()
    checks=[]
    registries={
      'components':len(COMPONENT_REGISTRY),'content':len(CONTENT_REGISTRY),'patterns':len(PATTERN_REGISTRY),'interactions':len(INTERACTION_REGISTRY),
      'tables':len(TABLE_REGISTRY),'visualizations':len(VISUALIZATION_REGISTRY),'engineering':len(ENGINEERING_REGISTRY),
      'convenience':len(CONVENIENCE_REGISTRY),'performance':len(PERFORMANCE_REGISTRY),'jobs':len(JOB_REGISTRY),'security':len(SECURITY_REGISTRY),'runtime':len(RUNTIME_REGISTRY),'analysis':len(ANALYSIS_REGISTRY),
      'icons':len(ICON_REGISTRY),'illustrations':len(ILLUSTRATION_REGISTRY),
    }
    checks.append(_ok('registries','Framework registries',f"{sum(registries.values())} registered semantic entries",'api'))
    checks.append(_ok('patterns','Canonical page patterns',f"{len(PATTERN_REGISTRY)}/{EXPECTED_PATTERNS} patterns present",'layout') if len(PATTERN_REGISTRY)==EXPECTED_PATTERNS else _fail('patterns','Canonical page patterns',f"Expected {EXPECTED_PATTERNS}, got {len(PATTERN_REGISTRY)}",'layout'))
    css=combined_css()
    balanced=css.count('{')==css.count('}')
    checks.append(_ok('css','Combined framework CSS',f"{len(css):,} bytes; braces balanced",'visual') if balanced else _fail('css','Combined framework CSS','Unbalanced CSS braces','visual'))
    remote=bool(re.search(r'https?://|@import\s+url',css,re.I))
    checks.append(_fail('remote-css','No remote CSS resources','Remote URL detected','visual') if remote else _ok('remote-css','No remote CSS resources','No HTTP/CDN references in generated framework CSS','visual'))
    visual_css_issues=audit_visual_css(css)
    checks.append(_ok('visual-normalization','Zero stock visual normalization','Quasar/AG Grid normalization selectors present and all Company CSS tokens resolve','visual') if not visual_css_issues else _fail('visual-normalization','Zero stock visual normalization','; '.join(i.message for i in visual_css_issues[:8]),'visual'))
    lab_css=css+'\n'+build_mac_lab_css()
    lab_visual_issues=audit_visual_css(lab_css)
    checks.append(_ok('lab-visual-css','Live lab CSS integrity','Framework + live-lab CSS is balanced and every Company custom property resolves','visual') if not lab_visual_issues else _fail('lab-visual-css','Live lab CSS integrity','; '.join(i.message for i in lab_visual_issues[:8]),'visual'))
    source_visual_issues=audit_framework_visual_sources(root)
    checks.append(_ok('stock-visual-paths','No stock NiceGUI visual paths','No ui.notify/ui.menu_item/ui.icon or unthemed tooltip paths found in framework integrations','visual') if not source_visual_issues else _fail('stock-visual-paths','No stock NiceGUI visual paths','; '.join(f'{i.code}: {i.path}' for i in source_visual_issues[:8]),'visual'))
    api_source_issues=scan_source_contract(root)
    checks.append(_ok('nicegui-source-contract','NiceGUI 3.15 adapter source contract','No known-invalid drawer/EChart/fullscreen adapter patterns detected','runtime') if not api_source_issues else _fail('nicegui-source-contract','NiceGUI 3.15 adapter source contract','; '.join(f'{i.code}: {i.path}:{i.line}' for i in api_source_issues[:8]),'runtime'))
    issues=validate_visual_package()
    checks.append(_ok('assets','Visual assets',f"{len(ICON_REGISTRY)} icons, {len(ILLUSTRATION_REGISTRY)} illustrations; 0 validation issues",'visual') if not issues else _fail('assets','Visual assets',f"{len(issues)} validation issues",'visual'))
    try:
        catalog=load_framework_catalog(); ccount=len(catalog)
        checks.append(_ok('catalog','AI framework catalog',f"Machine-readable catalog loads successfully ({ccount} top-level sections)",'ai'))
    except Exception as e: checks.append(_fail('catalog','AI framework catalog',str(e),'ai'))
    for candidate in (root/'examples/certification_app.py', root/'examples/component_gallery.py'):
        if candidate.exists():
            issues=validate_python_file(candidate, root=root)
            errs=sum(1 for i in issues if i.severity.value=='error')
            warns=sum(1 for i in issues if i.severity.value=='warning')
            checks.append(_ok(f'validate-{candidate.stem}',f'Static validation: {candidate.name}',f'{errs} errors / {warns} warnings','ai') if errs==0 and warns==0 else _fail(f'validate-{candidate.stem}',f'Static validation: {candidate.name}',f'{errs} errors / {warns} warnings','ai'))
    ng=importlib.util.find_spec('nicegui')
    if ng:
        import nicegui
        ver=getattr(nicegui,'__version__','unknown')
        checks.append(_ok('nicegui','NiceGUI runtime',f'NiceGUI {ver} installed','runtime') if ver==NICEGUI_VERSION else _fail('nicegui','NiceGUI runtime',f'Expected {NICEGUI_VERSION}, found {ver}','runtime'))
        contract=run_installed_runtime_contract()
        checks.append(_ok('nicegui-runtime-contract','Installed NiceGUI API contract',f'{contract.factories_checked} factories / {contract.calls_checked} direct calls verified','runtime') if contract.ok else _fail('nicegui-runtime-contract','Installed NiceGUI API contract','; '.join(i.detail for i in (*contract.source_issues,*contract.runtime_issues)[:8]),'runtime'))
    elif require_nicegui:
        checks.append(_fail('nicegui','NiceGUI runtime','NiceGUI 3.15.0 is not installed','runtime'))
    else:
        checks.append(_warn('nicegui','NiceGUI runtime','NiceGUI unavailable here; live browser certification remains pending','runtime'))
    return CertificationReport(FRAMEWORK_VERSION,tuple(checks),{'registries':registries,'python':sys.version.split()[0]})
