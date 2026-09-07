from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urljoin

from .mac_lab import ROUTES
from nicegui_base.design.responsive import CANONICAL_VIEWPORTS


KEY_ROUTES = ('/','/foundation','/shell','/controls','/forms','/data','/charts','/content','/engineering','/states','/performance')
REFERENCE_ROUTES = ('/patterns/dashboard','/patterns/explorer','/patterns/master-detail','/patterns/crud','/patterns/monitoring','/patterns/search','/patterns/settings','/patterns/wizard','/patterns/comparison','/patterns/analysis')
EDGE_SMOKE_ROUTES = ('/','/controls','/data','/charts','/engineering','/states')


@dataclass(frozen=True, slots=True)
class BrowserScenario:
    browser: str
    viewport: str
    width: int
    height: int
    theme: str
    density: str
    routes: tuple[str, ...]

    @property
    def key(self) -> str:
        return f'{self.browser}-{self.viewport}-{self.theme}-{self.density}'


@dataclass(frozen=True, slots=True)
class RouteBrowserResult:
    scenario: str
    route: str
    status: str
    detail: str
    screenshot: str | None = None
    duration_ms: float | None = None
    audit: dict[str, object] = field(default_factory=dict)
    visual_diff: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class MacBrowserReport:
    results: tuple[RouteBrowserResult, ...]
    browsers: dict[str, str]
    baseline_dir: str | None

    @property
    def failures(self) -> tuple[RouteBrowserResult, ...]:
        return tuple(r for r in self.results if r.status == 'fail')

    @property
    def warnings(self) -> tuple[RouteBrowserResult, ...]:
        return tuple(r for r in self.results if r.status == 'warning')

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def summary(self) -> dict[str, int]:
        return {s: sum(r.status == s for r in self.results) for s in ('pass','warning','fail')}

    def to_dict(self) -> dict[str, object]:
        return {'passed':self.passed,'summary':self.summary,'browsers':self.browsers,'baseline_dir':self.baseline_dir,'results':[asdict(r) for r in self.results]}


def standard_scenarios(*, include_edge: bool = True) -> tuple[BrowserScenario, ...]:
    all_routes=tuple(r.path for r in ROUTES)
    result=[
        BrowserScenario('chrome','desktop',1440,1000,'light','compact',all_routes),
        BrowserScenario('chrome','phone',390,844,'dark','compact',all_routes),
        BrowserScenario('chrome','tablet',1024,900,'dark','dense',KEY_ROUTES+REFERENCE_ROUTES),
        BrowserScenario('chrome','desktop',1440,1000,'light','comfortable',('/controls','/forms','/data','/content')),
    ]
    if include_edge:
        result.extend((
            BrowserScenario('msedge','desktop',1440,1000,'light','compact',EDGE_SMOKE_ROUTES),
            BrowserScenario('msedge','phone',390,844,'dark','compact',EDGE_SMOKE_ROUTES),
        ))
    return tuple(result)


def exhaustive_scenarios(*, include_edge: bool = True) -> tuple[BrowserScenario, ...]:
    all_routes=tuple(r.path for r in ROUTES)
    result=[]
    for profile in CANONICAL_VIEWPORTS.values():
        for theme in ('light','dark'):
            result.append(BrowserScenario('chrome',profile.key,profile.width,profile.height,theme,'compact',all_routes))
    result.extend((
        BrowserScenario('chrome','desktop',1440,1000,'light','comfortable',KEY_ROUTES),
        BrowserScenario('chrome','desktop',1440,1000,'dark','dense',KEY_ROUTES),
    ))
    if include_edge:
        for viewport,width,height in (('desktop',1440,1000),('phone',390,844)):
            for theme in ('light','dark'):
                result.append(BrowserScenario('msedge',viewport,width,height,theme,'compact',EDGE_SMOKE_ROUTES))
    return tuple(result)


_DOM_AUDIT = r'''() => {
  const visible=el=>{const st=getComputedStyle(el);const r=el.getBoundingClientRect();return st.display!=='none'&&st.visibility!=='hidden'&&Number(st.opacity)!==0&&r.width>1&&r.height>1;};
  const cls=el=>(el.className||'').toString().slice(0,180);
  const interactive=[...document.querySelectorAll('button,a[href],input,select,textarea,[role=button],[tabindex]')].filter(visible);
  const missingNames=interactive.filter(el=>{
    if(el.getAttribute('aria-hidden')==='true'||el.disabled||el.tabIndex<0)return false;
    const name=(el.getAttribute('aria-label')||'').trim(); const labelled=el.getAttribute('aria-labelledby'); const text=(el.innerText||el.value||el.getAttribute('title')||'').trim();
    return !name&&!labelled&&!text;
  }).length;
  const ids=[...document.querySelectorAll('[id]')].map(el=>el.id);
  const duplicateIds=ids.length-new Set(ids).size;
  const imagesMissingAlt=[...document.querySelectorAll('img')].filter(img=>!img.hasAttribute('alt')).length;
  const leakRules=[
    ['q-notification','.q-notification',el=>false],['q-checkbox','.q-checkbox',el=>el.classList.contains('cui-choice')||!!el.closest('.cui-data-table,.cui-tree')],
    ['q-radio','.q-radio',el=>el.classList.contains('cui-choice')],['q-toggle','.q-toggle',el=>false],
    ['q-slider','.q-slider',el=>el.classList.contains('cui-slider')],['q-tabs','.q-tabs',el=>el.classList.contains('cui-tabs-region')],
    ['q-stepper','.q-stepper',el=>el.classList.contains('cui-stepper')],['q-tree','.q-tree',el=>el.classList.contains('cui-tree')],
    ['q-uploader','.q-uploader',el=>el.classList.contains('cui-upload')],['q-field','.q-field',el=>el.classList.contains('cui-field-control')||!!el.closest('.cui-data-table,.cui-command-palette')],
    ['q-expansion','.q-expansion-item',el=>!!el.closest('.cui-collapsible,.cui-nav-expansion,.cui-form-section')],
    ['q-menu','.q-menu',el=>el.classList.contains('cui-menu')||el.classList.contains('cui-popover')||!!el.closest('.cui-menu,.cui-popover')],
    ['ag-grid','.ag-root-wrapper',el=>!!el.closest('.cui-data-table')],
  ];
  const stockLeaks=[]; for(const [kind,selector,approved] of leakRules){for(const el of document.querySelectorAll(selector)){if(visible(el)&&!approved(el))stockLeaks.push({kind,cls:cls(el)});}}
  const visibleMaterialIcons=[...document.querySelectorAll('.material-icons,.material-symbols-outlined,.q-icon')].filter(el=>visible(el)&&!el.closest('.cui-field-control,.cui-collapsible,.cui-nav-expansion,.cui-stepper,.cui-tree,.cui-upload,.cui-data-table,.cui-select,.cui-slider'));
  const focusRings=interactive.filter(el=>getComputedStyle(el).outlineStyle!=='none'||getComputedStyle(el).boxShadow!=='none').length;

  const geometry=[]; const add=(kind,el,detail)=>geometry.push({kind,cls:cls(el),detail});
  const page=document.querySelector('.cui-page'), main=document.querySelector('.cui-app-main'), header=document.querySelector('.cui-app-header'), sidebar=document.querySelector('.cui-app-sidebar:not(.q-drawer)');
  if(main&&visible(main)){
    const mr=main.getBoundingClientRect();
    const expectedLeft=(sidebar&&visible(sidebar)&&innerWidth>=900)?sidebar.getBoundingClientRect().right:0;
    if(Math.abs(mr.left-expectedLeft)>2||Math.abs(mr.right-innerWidth)>3){
      add('MAIN_CANVAS_WIDTH_MISMATCH',main,`left=${mr.left.toFixed(1)} expected=${expectedLeft.toFixed(1)}, right=${mr.right.toFixed(1)} viewport=${innerWidth}`);
    }
  }
  if(page&&visible(page)){
    const pr=page.getBoundingClientRect(), rootStyle=getComputedStyle(document.documentElement), expectedGutter=parseFloat(rootStyle.getPropertyValue('--cui-page-gutter'))||0;
    const ps=getComputedStyle(page), actualLeft=parseFloat(ps.paddingLeft)||0, actualRight=parseFloat(ps.paddingRight)||0, actualTop=parseFloat(ps.paddingTop)||0;
    if(actualLeft+1<expectedGutter||actualRight+1<expectedGutter||Math.abs(actualLeft-actualRight)>1)add('PAGE_GUTTER_MISSING',page,`padding=${actualLeft}/${actualRight}, expected symmetric >=${expectedGutter}`);
    if(Math.abs(actualTop-expectedGutter)>2)add('PAGE_TOP_GUTTER_MISMATCH',page,`paddingTop=${actualTop}, expected≈${expectedGutter}`);
    if(main&&visible(main)){const mr=main.getBoundingClientRect();if(Math.abs(pr.left-mr.left)>2||Math.abs(pr.right-mr.right)>3)add('PAGE_CANVAS_NOT_FULL_WIDTH',page,`page=${pr.left.toFixed(1)}..${pr.right.toFixed(1)}, main=${mr.left.toFixed(1)}..${mr.right.toFixed(1)}`);}
    if(header&&visible(header)){const hr=header.getBoundingClientRect();if(pr.top<hr.bottom-2)add('CONTENT_OVERLAPS_HEADER',page,`page.top=${pr.top.toFixed(1)}, header.bottom=${hr.bottom.toFixed(1)}`);}
    if(sidebar&&visible(sidebar)&&innerWidth>=900){const sr=sidebar.getBoundingClientRect();if(pr.left<sr.right-2)add('CONTENT_OVERLAPS_SIDEBAR',page,`page.left=${pr.left.toFixed(1)}, sidebar.right=${sr.right.toFixed(1)}`);}
  }
  for(const host of document.querySelectorAll('.cui-lab-sample,.cui-panel,.cui-card,.cui-well,.cui-form-section,.cui-pattern-slot,.cui-table-shell,.cui-chart-panel')){
    if(!visible(host))continue; if(host.scrollWidth>host.clientWidth+3){const st=getComputedStyle(host);if(st.overflowX!=='auto'&&st.overflowX!=='scroll')add('CHILD_EXCEEDS_CONTAINER',host,`scrollWidth=${host.scrollWidth}, clientWidth=${host.clientWidth}`);}
  }
  const textSelectors='.cui-page-title,.cui-page-description,.cui-field-label,.cui-lab-section__title,.cui-lab-section__description,.cui-lab-sample__title,.cui-dialog__title,.cui-dialog__description';
  for(const el of document.querySelectorAll(textSelectors)){if(!visible(el))continue;const st=getComputedStyle(el);if(el.scrollWidth>el.clientWidth+2&&st.textOverflow!=='ellipsis'&&st.overflow!=='visible')add('TEXT_CLIPPED',el,`scrollWidth=${el.scrollWidth}, clientWidth=${el.clientWidth}`);}
  for(const host of document.querySelectorAll('.cui-lab-section,.cui-lab-stack,.cui-form-stack,.cui-alert-stack,.cui-content-column')){
    if(!visible(host))continue;const children=[...host.children].filter(visible);
    for(let i=0;i<children.length;i++)for(let j=i+1;j<children.length;j++){
      const a=children[i],b=children[j],sa=getComputedStyle(a),sb=getComputedStyle(b); if(['absolute','fixed'].includes(sa.position)||['absolute','fixed'].includes(sb.position))continue;
      const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect(); const ox=Math.min(ar.right,br.right)-Math.max(ar.left,br.left), oy=Math.min(ar.bottom,br.bottom)-Math.max(ar.top,br.top);
      if(ox>4&&oy>4)add('SIBLING_OVERLAP',host,`${cls(a)} <> ${cls(b)} overlap ${ox.toFixed(1)}x${oy.toFixed(1)}`);
    }
  }
  for(const host of document.querySelectorAll('.cui-lab-inline,.cui-button-cluster,.cui-action-row,.cui-toolbar-group')){
    if(!visible(host)||host.closest('.cui-button-group,.cui-split-button,.cui-segmented-control'))continue;
    const children=[...host.children].filter(el=>visible(el)&&el.matches('button,.q-btn,[role=button],.cui-button,.cui-icon-button'));
    const ordered=children.map(el=>({el,r:el.getBoundingClientRect()})).sort((a,b)=>a.r.top-b.r.top||a.r.left-b.r.left);
    for(let i=1;i<ordered.length;i++){const a=ordered[i-1],b=ordered[i];if(Math.abs(a.r.top-b.r.top)>Math.max(a.r.height,b.r.height)/2)continue;const gap=b.r.left-a.r.right;if(gap>=-1&&gap<6)add('ACTION_GAP_TOO_SMALL',host,`gap=${gap.toFixed(1)}px`);}
  }
  for(const host of document.querySelectorAll('.cui-lab-section,.cui-lab-stack,.cui-form-stack,.cui-alert-stack,.cui-content-column,.cui-section,.cui-form-section')){
    if(!visible(host))continue;const st=getComputedStyle(host), gap=parseFloat(st.rowGap||st.gap)||0;if(gap<10)add('VERTICAL_GAP_TOO_SMALL',host,`gap=${gap}px`);
  }
  for(const host of document.querySelectorAll('.cui-lab-grid,.cui-grid,.cui-surface-grid,.cui-metric-strip')){
    if(!visible(host))continue;const st=getComputedStyle(host), rg=parseFloat(st.rowGap||st.gap)||0,cg=parseFloat(st.columnGap||st.gap)||0;if(rg<10||cg<10)add('GRID_GAP_TOO_SMALL',host,`row=${rg}px column=${cg}px`);
  }
  for(const host of document.querySelectorAll('.cui-lab-sample,.cui-surface--panel,.cui-surface--card,.cui-surface--well,.cui-eng-entity')){
    if(!visible(host))continue;const st=getComputedStyle(host), vals=[st.paddingTop,st.paddingRight,st.paddingBottom,st.paddingLeft].map(v=>parseFloat(v)||0);if(Math.min(...vals)<10)add('SURFACE_PADDING_MISSING',host,`padding=${vals.join('/')}`);
  }
  for(const overlay of document.querySelectorAll('.q-menu.cui-menu,.q-menu.cui-popover,.cui-tooltip,.cui-dialog,.cui-drawer')){
    if(!visible(overlay))continue;const r=overlay.getBoundingClientRect(), edge=4;if(r.left<edge||r.right>innerWidth-edge||r.top<edge||r.bottom>innerHeight-edge)add('OVERLAY_OUTSIDE_VIEWPORT',overlay,`rect=${r.left.toFixed(1)},${r.top.toFixed(1)},${r.right.toFixed(1)},${r.bottom.toFixed(1)} viewport=${innerWidth}x${innerHeight}`);
  }
  const znum=el=>{const z=parseInt(getComputedStyle(el).zIndex,10);return Number.isFinite(z)?z:0;};
  const visibleMenus=[...document.querySelectorAll('.q-menu.cui-menu,.q-menu.cui-popover')].filter(visible);
  const visibleModals=[...document.querySelectorAll('.q-dialog')].filter(visible);
  const visibleTips=[...document.querySelectorAll('.cui-tooltip--company')].filter(visible);
  const visibleToasts=[...document.querySelectorAll('.cui-toast-stack')].filter(visible);
  for(const modal of visibleModals){
    for(const menu of visibleMenus){if(znum(menu)>=znum(modal))add('POPOVER_ABOVE_MODAL',menu,`menu z=${znum(menu)} modal z=${znum(modal)}`);}
    for(const toolbar of document.querySelectorAll('.cui-table-toolbar,.cui-lab-controlbar')){if(visible(toolbar)&&znum(toolbar)>=znum(modal))add('APP_CONTROL_ABOVE_MODAL',toolbar,`control z=${znum(toolbar)} modal z=${znum(modal)}`);}
  }
  for(const tip of visibleTips){for(const modal of visibleModals){if(znum(tip)<=znum(modal))add('TOOLTIP_LAYER_ORDER',tip,`tooltip z=${znum(tip)} modal z=${znum(modal)}`);}}
  for(const stack of visibleToasts){for(const tip of visibleTips){if(znum(stack)<=znum(tip))add('TOAST_LAYER_ORDER',stack,`toast z=${znum(stack)} tooltip z=${znum(tip)}`);}}
  for(const toast of document.querySelectorAll('.cui-toast')){
    if(!visible(toast)||!header||!visible(header))continue;const tr=toast.getBoundingClientRect(),hr=header.getBoundingClientRect();if(tr.top<hr.bottom+8)add('TOAST_HEADER_COLLISION',toast,`toast.top=${tr.top.toFixed(1)} header.bottom=${hr.bottom.toFixed(1)}`);
  }
  for(const button of document.querySelectorAll('.cui-icon-button,.cui-sidebar-footer__action')){
    if(!visible(button))continue;const icon=button.querySelector('.cui-svg-icon-host,svg');if(!icon||!visible(icon))continue;const br=button.getBoundingClientRect(),ir=icon.getBoundingClientRect();
    const dx=Math.abs((br.left+br.width/2)-(ir.left+ir.width/2)),dy=Math.abs((br.top+br.height/2)-(ir.top+ir.height/2));if(dx>2.5||dy>2.5)add('ICON_NOT_CENTERED',button,`delta=${dx.toFixed(1)},${dy.toFixed(1)}`);
  }
  for(const badge of document.querySelectorAll('.cui-badge,.cui-chip')){
    if(!visible(badge))continue;const child=badge.querySelector('.q-label');if(!child||!visible(child))continue;const br=badge.getBoundingClientRect(),cr=child.getBoundingClientRect();const dy=Math.abs((br.top+br.height/2)-(cr.top+cr.height/2));if(dy>2.5)add('BADGE_TEXT_NOT_CENTERED',badge,`delta=${dy.toFixed(1)}px`);
  }
  for(const row of document.querySelectorAll('.cui-choice-row')){
    if(!visible(row))continue;const visual=row.querySelector('.cui-choice-visual');if(!visual||!visible(visual))continue;const rr=row.getBoundingClientRect(),vr=visual.getBoundingClientRect();const dy=Math.abs((rr.top+rr.height/2)-(vr.top+vr.height/2));if(dy>3)add('CHOICE_CONTROL_NOT_CENTERED',row,`delta=${dy.toFixed(1)}px`);
  }
  for(const head of document.querySelectorAll('.cui-dialog__head,.cui-drawer__header')){
    if(!visible(head))continue;const title=head.querySelector('.cui-dialog__title,.cui-drawer__title'),close=head.querySelector('.cui-dialog__close,.cui-icon-button[aria-label="Close"]');
    if(!title||!close||!visible(title)||!visible(close))continue;const tr=title.getBoundingClientRect(),cr=close.getBoundingClientRect();const dy=Math.abs((tr.top+tr.height/2)-(cr.top+cr.height/2));if(dy>6)add('DIALOG_HEADER_ALIGNMENT',head,`title/close center delta=${dy.toFixed(1)}px`);
  }
  for(const field of document.querySelectorAll('.cui-field-control')){
    if(!visible(field))continue;const fr=field.getBoundingClientRect();for(const append of field.querySelectorAll('.q-field__append,.q-field__prepend,.q-field__marginal')){
      if(!visible(append))continue;const ar=append.getBoundingClientRect();if(ar.top<fr.top-2||ar.bottom>fr.bottom+2||ar.left<fr.left-2||ar.right>fr.right+2)add('FIELD_APPEND_OUTSIDE_CONTROL',field,`field=${fr.left.toFixed(1)},${fr.top.toFixed(1)},${fr.right.toFixed(1)},${fr.bottom.toFixed(1)} append=${ar.left.toFixed(1)},${ar.top.toFixed(1)},${ar.right.toFixed(1)},${ar.bottom.toFixed(1)}`);
    }
  }
  const radiusChecks=[['.cui-button',10,'BUTTON_RADIUS'],['.cui-field-control',10,'FIELD_RADIUS'],['.cui-panel',14,'SURFACE_RADIUS'],['.cui-card',14,'SURFACE_RADIUS'],['.cui-dialog',18,'OVERLAY_RADIUS']];
  for(const [selector,expected,kind] of radiusChecks){for(const el of document.querySelectorAll(selector)){if(!visible(el))continue;const r=parseFloat(getComputedStyle(el).borderTopLeftRadius)||0;if(Math.abs(r-expected)>1)add(kind,el,`radius=${r}px expected=${expected}px`);}}
  const density=document.documentElement.dataset.density||'compact', expectedHeight={comfortable:44,compact:38,dense:34}[density]||38;
  for(const el of [...document.querySelectorAll('.cui-button,.cui-icon-button')].filter(visible).slice(0,20)){const h=el.getBoundingClientRect().height;if(Math.abs(h-expectedHeight)>2)add('DENSITY_CONTROL_HEIGHT',el,`density=${density}, height=${h.toFixed(1)}, expected=${expectedHeight}`);}
  return {
    horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1, mainLandmark:!!document.querySelector('main,[role=main]'),
    missingAccessibleNames:missingNames,duplicateIds,imagesMissingAlt,interactiveCount:interactive.length,
    stockVisualLeakCount:stockLeaks.length,stockVisualLeakSamples:stockLeaks.slice(0,10),unapprovedMaterialIconCount:visibleMaterialIcons.length,focusStyledCount:focusRings,
    geometryViolationCount:geometry.length,geometryViolationSamples:geometry.slice(0,20),theme:document.documentElement.dataset.theme||'',density,
  };
}'''


def _slug(route: str) -> str:
    return 'overview' if route == '/' else re.sub(r'[^a-z0-9]+','-',route.strip('/').lower()).strip('-')


def _compare_images(current: Path, baseline: Path) -> dict[str, object]:
    try:
        from PIL import Image, ImageChops, ImageStat  # type: ignore
    except Exception:
        return {'status':'unavailable','detail':'Pillow not installed'}
    if not baseline.exists(): return {'status':'missing','detail':'No approved baseline exists yet'}
    with Image.open(current).convert('RGB') as a, Image.open(baseline).convert('RGB') as b:
        if a.size != b.size: return {'status':'fail','detail':f'image size changed {b.size} -> {a.size}','mean_abs':255.0,'changed_ratio':1.0}
        diff=ImageChops.difference(a,b); stat=ImageStat.Stat(diff)
        mean_abs=sum(stat.mean)/len(stat.mean)
        thresholded=diff.convert('L').point(lambda p:255 if p>12 else 0)
        hist=thresholded.histogram(); changed=hist[255] if len(hist)>255 else 0; pixels=a.size[0]*a.size[1]
        changed_ratio=changed/pixels if pixels else 0.0
        ok=mean_abs<=1.25 and changed_ratio<=0.025
        return {'status':'pass' if ok else 'fail','detail':f'mean_abs={mean_abs:.3f}, changed={changed_ratio:.2%}','mean_abs':mean_abs,'changed_ratio':changed_ratio}


def _set_controls(page, theme: str, density: str) -> None:
    bar=page.locator('.cui-lab-controlbar').first
    if bar.count()==0: return
    try:
        bar.get_by_text(theme.title(),exact=True).first.click(timeout=3000)
    except Exception:
        page.evaluate("([theme])=>{document.documentElement.dataset.theme=theme;document.body.classList.toggle('body--dark',theme==='dark');}",[theme])
    density_label={'comfortable':'Comfort','compact':'Compact','dense':'Dense'}[density]
    try: bar.get_by_text(density_label,exact=True).first.click(timeout=3000)
    except Exception: page.evaluate("([density])=>document.documentElement.dataset.density=density",[density])
    page.wait_for_timeout(180)


def _route_performance_probe(page) -> dict[str, float | int]:
    """Reusable browser probe for frame stalls, long tasks and resize response."""
    return page.evaluate(r'''async () => {
      const longTasks=[];
      let observer=null;
      if ('PerformanceObserver' in window && PerformanceObserver.supportedEntryTypes?.includes('longtask')) {
        observer=new PerformanceObserver(list => {
          for (const entry of list.getEntries()) longTasks.push(entry.duration);
        });
        observer.observe({entryTypes:['longtask']});
      }
      const startY=window.scrollY;
      const frameGaps=[];
      let last=performance.now();
      await new Promise(resolve => {
        let frames=0;
        const step=now => {
          frameGaps.push(now-last); last=now;
          window.scrollBy(0, frames % 2 === 0 ? 180 : -120);
          frames += 1;
          if (frames < 12) requestAnimationFrame(step);
          else resolve();
        };
        requestAnimationFrame(step);
      });
      window.scrollTo(0,startY);
      const resizeStart=performance.now();
      dispatchEvent(new Event('resize'));
      await new Promise(resolve => requestAnimationFrame(() => resolve()));
      const resizeFrameMs=performance.now()-resizeStart;
      await new Promise(resolve => setTimeout(resolve,0));
      observer?.disconnect();
      const maxFrameMs=Math.max(0,...frameGaps);
      const avgFrameMs=frameGaps.length ? frameGaps.reduce((a,b)=>a+b,0)/frameGaps.length : 0;
      const longestTaskMs=Math.max(0,...longTasks);
      return {maxFrameMs,avgFrameMs,resizeFrameMs,longTaskCount:longTasks.length,longestTaskMs};
    }''')


def _performance_issues(metrics: dict[str, float | int]) -> list[str]:
    issues=[]
    max_frame=float(metrics.get('maxFrameMs',0)); avg_frame=float(metrics.get('avgFrameMs',0))
    resize=float(metrics.get('resizeFrameMs',0)); long_count=int(metrics.get('longTaskCount',0)); longest=float(metrics.get('longestTaskMs',0))
    if max_frame>180 or avg_frame>80:
        issues.append(f'route frame-stall budget exceeded (max {max_frame:.1f}ms, avg {avg_frame:.1f}ms)')
    if resize>140:
        issues.append(f'route resize response exceeded 140ms budget ({resize:.1f}ms)')
    if long_count>=3 and longest>80:
        issues.append(f'route produced sustained long tasks ({long_count} observed, longest {longest:.1f}ms)')
    return issues


def _interaction_smoke(page, route: str, *, density: str = 'compact') -> list[str]:
    issues: list[str]=[]
    try:
        if route=='/':
            header=page.locator('.cui-app-header').first
            settings=page.get_by_role('button',name='Application settings').first
            if settings.count():
                settings.click(); page.wait_for_timeout(100)
                menu=page.locator('.cui-shell-settings-menu').first
                if not menu.count() or not menu.is_visible(): issues.append('application settings menu did not become visible')
                elif header.count():
                    mr=menu.bounding_box(); hr=header.bounding_box()
                    if mr and hr and mr['y'] < hr['y']+hr['height']+4: issues.append('application settings menu collided with header')
                page.keyboard.press('Escape'); page.wait_for_timeout(60)
            else: issues.append('Application settings trigger missing')
            user=page.get_by_role('button',name='User profile').first
            if user.count():
                user.click(); page.wait_for_timeout(100)
                menu=page.locator('.cui-user-menu').first
                if not menu.count() or not menu.is_visible(): issues.append('user menu did not become visible')
                elif header.count():
                    mr=menu.bounding_box(); hr=header.bounding_box()
                    if mr and hr and mr['y'] < hr['y']+hr['height']+4: issues.append('user menu collided with header')
                page.keyboard.press('Escape'); page.wait_for_timeout(60)
            else: issues.append('User profile trigger missing')
            title=page.locator('.cui-shell-title').first
            if title.count():
                title_metrics=title.evaluate("e=>{const s=getComputedStyle(e);return {size:parseFloat(s.fontSize),weight:parseFloat(s.fontWeight)||0}}")
                if title_metrics['size'] < 17 or title_metrics['weight'] < 750: issues.append('application title lacks required 17px/750 hierarchy')
            name=page.locator('.cui-shell-greeting__name').first
            hello=page.locator('.cui-shell-greeting__hello').first
            if name.count() and hello.count():
                nm=name.evaluate("e=>{const s=getComputedStyle(e);return {size:parseFloat(s.fontSize),weight:parseFloat(s.fontWeight)||0,color:s.color}}")
                hm=hello.evaluate("e=>{const s=getComputedStyle(e);return {size:parseFloat(s.fontSize),weight:parseFloat(s.fontWeight)||0,color:s.color}}")
                if nm['color']==hm['color'] or nm['size']-hm['size']<1.5 or nm['weight']-hm['weight']<120: issues.append('profile greeting hierarchy is too weak')
        elif route=='/foundation':
            status=page.locator('.cui-motion-status').first
            before=status.inner_text() if status.count() else ''
            page.get_by_role('button',name='Replay motion examples').click(); page.wait_for_timeout(140)
            after=status.inner_text() if status.count() else ''
            if not after or after==before or 'Replaying' not in after: issues.append('motion replay did not visibly change state')
            badges=page.locator('.cui-environment-badge')
            if badges.count() < 3: issues.append('environment semantic badge set missing')
            else:
                if page.locator('.q-badge.cui-environment-badge').count(): issues.append('environment metadata still uses Quasar badge anatomy')
                backgrounds=[badges.nth(i).evaluate("e=>getComputedStyle(e).backgroundColor") for i in range(3)]
                if len(set(backgrounds)) < 3: issues.append('environment badges are not visually differentiated')
                for i in range(3):
                    ratio=badges.nth(i).evaluate("""e=>{const parse=c=>{const m=c.match(/[0-9.]+/g)||[];return m.slice(0,3).map(Number)};const lum=c=>{const [r,g,b]=parse(c).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*r+.7152*g+.0722*b};const s=getComputedStyle(e),a=lum(s.color),b=lum(s.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)}""")
                    if ratio < 4.5: issues.append('environment badge text contrast is below 4.5:1')
        elif route=='/shell':
            sidebar=page.locator('.cui-app-sidebar:not(.q-drawer)').first; main=page.locator('.cui-app-main').first
            if page.viewport_size['width']>=900:
                if not sidebar.count() or not sidebar.is_visible(): issues.append('desktop sidebar missing at desktop viewport')
                elif main.count():
                    before=sidebar.bounding_box(); main_before=main.bounding_box()
                    page.get_by_role('button',name='Collapse or expand navigation').click(); page.wait_for_timeout(260)
                    after=sidebar.bounding_box(); main_after=main.bounding_box()
                    if not before or not after or before['width']-after['width']<60: issues.append('sidebar did not physically collapse')
                    if main_before and main_after and main_after['width']-main_before['width']<60: issues.append('main canvas did not expand with collapsed sidebar')
                    footer=page.locator('.cui-sidebar-footer').first
                    if footer.count():
                        fb=footer.bounding_box(); sb=sidebar.bounding_box()
                        labels=footer.locator('.cui-sidebar-footer__action-label')
                        if any(labels.nth(i).is_visible() for i in range(labels.count())): issues.append('collapsed sidebar footer leaked text labels')
                        if fb and sb and (fb['x'] < sb['x']-1 or fb['x']+fb['width'] > sb['x']+sb['width']+1): issues.append('collapsed sidebar footer escaped rail bounds')
                    page.get_by_role('button',name='Collapse or expand navigation').click(); page.wait_for_timeout(220)
                mobile_trigger=page.get_by_role('button',name='Open navigation').first
                if mobile_trigger.count() and mobile_trigger.is_visible(): issues.append('mobile navigation trigger visible at desktop viewport')
            else:
                if sidebar.count() and sidebar.is_visible(): issues.append('desktop sidebar remained interactive at mobile viewport')
                mobile_trigger=page.get_by_role('button',name='Open navigation').first
                if not mobile_trigger.count() or not mobile_trigger.is_visible(): issues.append('mobile navigation trigger missing below breakpoint')
                else:
                    mobile_trigger.click(); page.wait_for_timeout(240)
                    drawer=page.locator('.cui-mobile-nav-drawer').first
                    if not drawer.count() or not drawer.is_visible(): issues.append('mobile navigation overlay did not open')
                    close=page.get_by_role('button',name='Close navigation').first
                    if close.count(): close.click(); page.wait_for_timeout(220)
                    if drawer.count() and drawer.is_visible(): issues.append('mobile navigation overlay did not close')
        elif route=='/forms':
            note=page.get_by_label('Operator note').first
            if note.count():
                note.fill('Phase 23 overlay interaction proof');
                if note.input_value()!='Phase 23 overlay interaction proof': issues.append('Operator Note is not editable')
            # Confirm: footer cancel and primary action must both close the real modal.
            page.get_by_role('button',name='Confirm dialog').click(); page.wait_for_timeout(120)
            dialog=page.locator('.cui-dialog').filter(has_text='Apply configuration?').first
            if not dialog.count() or not dialog.is_visible(): issues.append('confirm dialog did not open')
            else:
                cancel=dialog.get_by_role('button',name='Cancel').first
                if not cancel.count(): issues.append('confirm dialog cancel button missing')
                else:
                    cancel.click(); page.wait_for_timeout(120)
                    if dialog.is_visible(): issues.append('confirm dialog cancel did not close modal')
            page.get_by_role('button',name='Confirm dialog').click(); page.wait_for_timeout(100)
            dialog=page.locator('.cui-dialog').filter(has_text='Apply configuration?').first
            if dialog.count() and dialog.is_visible():
                confirm=dialog.get_by_role('button',name='Confirm').first
                if confirm.count(): confirm.click(); page.wait_for_timeout(140)
                if dialog.is_visible(): issues.append('confirm dialog primary action did not close modal')
            # Danger confirm must accept text, enable only after exact phrase, and close through primary action.
            page.get_by_role('button',name='Danger dialog').click(); page.wait_for_timeout(120)
            danger=page.locator('.cui-dialog').filter(has_text='Delete saved view?').first
            if not danger.count() or not danger.is_visible(): issues.append('danger dialog did not open')
            else:
                typed=danger.get_by_label('Type DELETE to confirm').first
                delete=danger.get_by_role('button',name='Delete').first
                if not typed.count(): issues.append('danger confirmation input missing')
                else:
                    typed.fill('DELETE'); page.wait_for_timeout(160)
                    if typed.input_value()!='DELETE': issues.append('danger confirmation input is not editable')
                if not delete.count(): issues.append('danger dialog primary button missing')
                elif delete.is_disabled(): issues.append('danger dialog primary action did not enable after exact phrase')
                else:
                    delete.click(); page.wait_for_timeout(150)
                    if danger.is_visible(): issues.append('danger dialog primary action did not close modal')
            # Drawer body interaction must not dismiss; explicit X and Escape both work.
            page.get_by_role('button',name='Detail drawer').click(); page.wait_for_timeout(140)
            drawer=page.locator('.cui-drawer').filter(has_text='Measurement detail').first
            if not drawer.count() or not drawer.is_visible(): issues.append('detail drawer did not open')
            else:
                db=drawer.bounding_box(); vw=page.viewport_size['width']; vh=page.viewport_size['height']
                if db and page.viewport_size['width']>=600:
                    if abs((db['x']+db['width'])-vw)>2: issues.append('detail drawer is not anchored to viewport edge')
                    if db['y']>2 or abs(db['height']-vh)>3: issues.append('detail drawer rendered as floating popup instead of full-height side sheet')
                body=drawer.locator('.cui-drawer__body').first
                if body.count(): body.click(position={'x':30,'y':30}); page.wait_for_timeout(70)
                if not drawer.is_visible(): issues.append('drawer closed after internal content click')
                close=drawer.get_by_role('button',name='Close').first
                if not close.count(): issues.append('drawer close button missing')
                else:
                    close.click(); page.wait_for_timeout(120)
                    if drawer.is_visible(): issues.append('drawer X did not close')
            page.get_by_role('button',name='Inspector').click(); page.wait_for_timeout(120)
            inspector=page.locator('.cui-drawer').filter(has_text='Inspector').first
            if inspector.count() and inspector.is_visible():
                page.keyboard.press('Escape'); page.wait_for_timeout(120)
                if inspector.is_visible(): issues.append('dismissible drawer did not close with Escape')
            # Company toast exposes close control and lifetime gauge; no stock notification.
            page.get_by_role('button',name='Success toast').click(); page.wait_for_timeout(100)
            if page.locator('.q-notification').count(): issues.append('stock q-notification appeared after toast action')
            toast=page.locator('.cui-toast').first
            if toast.count()==0: issues.append('Company toast did not appear')
            else:
                if toast.locator('.cui-toast__lifetime-bar').count()==0: issues.append('toast lifetime gauge missing')
                dismiss=toast.get_by_role('button',name='Dismiss notification').first
                if not dismiss.count(): issues.append('toast close button missing')
                else:
                    dismiss.click(); page.wait_for_timeout(190)
                    if toast.count() and toast.is_visible(): issues.append('toast close button did not dismiss')
            # Tooltip has deterministic transient lifetime rather than a sticky Quasar portal.
            target=page.get_by_role('button',name='Tooltip target').first
            if target.count():
                target.hover(); page.wait_for_timeout(520)
                tip=page.locator('.cui-tooltip--company').first
                if not tip.count() or not tip.is_visible(): issues.append('Company tooltip did not appear after hover delay')
                page.mouse.move(2,2); page.wait_for_timeout(100)
                if tip.count() and tip.is_visible(): issues.append('Company tooltip remained visible after pointer left target')
            # Popover must sit above ordinary controls and close after an action.
            page.get_by_role('button',name='Open popover').click(); page.wait_for_timeout(100)
            pop=page.locator('.cui-popover').first
            if not pop.count() or not pop.is_visible(): issues.append('popover did not open')
            else:
                refresh=pop.get_by_role('button',name='Refresh').first
                if refresh.count(): refresh.click(); page.wait_for_timeout(120)
                if pop.is_visible(): issues.append('popover action did not dismiss overlay')
            # Feedback states live on /forms; certify them on the route that actually renders them.
            tracks=page.locator('.cui-progress:not(.q-linear-progress)')
            if tracks.count()<2: issues.append('Company-owned progress tracks missing')
            else:
                determinate=tracks.nth(0)
                if determinate.inner_text().strip(): issues.append('determinate progress rendered text inside track')
                metric=page.locator('.cui-progress-metric').first
                if metric.count():
                    value=metric.locator('.cui-progress-metric__value').first; track=metric.locator('.cui-progress').first
                    if value.count() and track.count():
                        vb=value.bounding_box(); tb=track.bounding_box()
                        if not vb or not tb or vb['y']+vb['height'] > tb['y']+1: issues.append('progress metric value is not externally separated from the track')
                indeterminate=page.locator('.cui-progress.is-indeterminate').first
                if not indeterminate.count(): issues.append('indeterminate progress track missing')
                else:
                    bar=indeterminate.locator('.cui-progress__bar').first
                    if not bar.count() or bar.evaluate("e=>getComputedStyle(e).animationName")=='none': issues.append('indeterminate progress animation is inactive')
        elif route=='/controls':
            page.get_by_role('button',name='About this lab').click(); page.wait_for_timeout(120)
            info=page.locator('.cui-app-info-dialog').first
            if not info.count() or not info.is_visible(): issues.append('App info dialog did not open')
            else:
                close=info.get_by_role('button',name='Close').first
                if not close.count(): issues.append('App info close button missing')
                else:
                    close.click(); page.wait_for_timeout(120)
                    if info.is_visible(): issues.append('App info close button did not close dialog')
            # Density must change real control geometry, not merely a dataset flag.
            bar=page.locator('.cui-lab-controlbar').first; button=page.locator('.cui-button').filter(has_text='Primary').first
            if bar.count() and button.count():
                bar.get_by_text('Comfort',exact=True).first.click(); page.wait_for_timeout(160); comfortable=button.bounding_box()
                bar.get_by_text('Dense',exact=True).first.click(); page.wait_for_timeout(160); dense_box=button.bounding_box()
                if comfortable and dense_box and comfortable['height']-dense_box['height']<7: issues.append('density modes did not materially change control height')
                restore={'comfortable':'Comfort','compact':'Compact','dense':'Dense'}.get(density,'Compact')
                bar.get_by_text(restore,exact=True).first.click(); page.wait_for_timeout(120)
            # Intent hierarchy must be visually distinct, not five identical Quasar buttons.
            intent_buttons=[page.get_by_role('button',name=n).first for n in ('Primary','Secondary','Tertiary','Ghost','Danger')]
            signatures=[]
            for control in intent_buttons:
                if control.count():
                    signatures.append(control.evaluate("e=>{const s=getComputedStyle(e);return [s.backgroundImage,s.backgroundColor,s.boxShadow,s.color].join('|')}"))
            if len(set(signatures)) < 4: issues.append('button intent hierarchy is not visually distinct')
            processing=page.get_by_role('button',name='Processing').first
            spinner=processing.locator('.cui-button__spinner').first if processing.count() else None
            if spinner is not None and spinner.count():
                br=processing.bounding_box(); sr=spinner.bounding_box()
                if br and sr and (sr['x']<br['x'] or sr['y']<br['y'] or sr['x']+sr['width']>br['x']+br['width'] or sr['y']+sr['height']>br['y']+br['height']): issues.append('processing spinner escaped button bounds')
            # Company-owned native choice rows must be directly interactive.
            radio=page.locator('.cui-choice-row--radio').filter(has_text='CVD').first
            if radio.count():
                radio.click(); page.wait_for_timeout(60)
                if not radio.locator('input[type=radio]').is_checked(): issues.append('Company radio row did not select')
            switch=page.locator('.cui-choice-row--switch').filter(has_text='Auto refresh').first
            if switch.count():
                native=switch.locator('input[type=checkbox]').first
                track=switch.locator('.cui-switch-track').first
                thumb=switch.locator('.cui-switch-thumb').first
                if not track.count() or not thumb.count():
                    issues.append('Company switch is missing the canonical track/thumb DOM anatomy')
                else:
                    def switch_geometry():
                        tb=track.bounding_box(); hb=thumb.bounding_box(); sb=switch.bounding_box()
                        if not tb or not hb: return None
                        return {
                            'track_w':tb['width'],'track_h':tb['height'],'thumb_w':hb['width'],'thumb_h':hb['height'],
                            'left_gap':hb['x']-tb['x'],'right_gap':tb['x']+tb['width']-(hb['x']+hb['width']),
                            'top_gap':hb['y']-tb['y'],'bottom_gap':tb['y']+tb['height']-(hb['y']+hb['height']),
                            'track':tb,'row':sb,
                        }
                    def geometry_ok(g, checked):
                        if g is None: return False
                        expected_left, expected_right=(22,2) if checked else (2,22)
                        return (abs(g['track_w']-51)<=1 and abs(g['track_h']-31)<=1 and
                                abs(g['thumb_w']-27)<=1 and abs(g['thumb_h']-27)<=1 and
                                abs(g['left_gap']-expected_left)<=0.75 and abs(g['right_gap']-expected_right)<=0.75 and
                                abs(g['top_gap']-2)<=0.75 and abs(g['bottom_gap']-2)<=0.75)
                    # Establish ON, then OFF, then restore ON so both endpoints are physically measured.
                    if not native.is_checked():
                        switch.click(); page.wait_for_timeout(180)
                    on_geometry=switch_geometry()
                    if not geometry_ok(on_geometry, True): issues.append('Company switch ON endpoint violates 51x31 / 27px / 2px containment geometry')
                    switch.click(); page.wait_for_timeout(180)
                    if native.is_checked(): issues.append('Company switch did not toggle')
                    off_geometry=switch_geometry()
                    if not geometry_ok(off_geometry, False): issues.append('Company switch OFF endpoint violates 51x31 / 27px / 2px containment geometry')
                    switch.click(); page.wait_for_timeout(180)
                    if on_geometry and on_geometry['track'] and on_geometry['row']:
                        vb=on_geometry['track']; sb=on_geometry['row']
                        if vb['x']<sb['x']-1 or vb['x']+vb['width']>sb['x']+sb['width']+1: issues.append('switch visual escaped interaction row')
            disabled_switch=page.locator('.cui-choice-row--switch').filter(has_text='Unavailable switch').first
            if disabled_switch.count():
                disabled_native=disabled_switch.locator('input[type=checkbox]').first
                dtrack=disabled_switch.locator('.cui-switch-track').first
                dthumb=disabled_switch.locator('.cui-switch-thumb').first
                if not disabled_native.is_disabled(): issues.append('disabled Company switch is not natively disabled')
                if dtrack.count() and dthumb.count():
                    dt=dtrack.bounding_box(); dh=dthumb.bounding_box()
                    if dt and dh:
                        left=dh['x']-dt['x']; right=dt['x']+dt['width']-(dh['x']+dh['width'])
                        top=dh['y']-dt['y']; bottom=dt['y']+dt['height']-(dh['y']+dh['height'])
                        if any(abs(a-b)>0.75 for a,b in ((left,2),(right,22),(top,2),(bottom,2))):
                            issues.append('disabled Company switch geometry drifted from the OFF endpoint')
            range_box=page.locator('.cui-native-range').first
            if not range_box.count(): issues.append('Company dual-native range control missing')
            else:
                if range_box.locator('.q-slider').count(): issues.append('range slider still exposes Quasar slider anatomy')
                if range_box.locator('input[type=range]').count()!=2: issues.append('range slider does not expose two native handles')
                track=range_box.locator('.cui-native-range__track').first
                single=page.locator('.cui-native-slider').first
                if track.count() and single.count():
                    geometry=page.evaluate("""() => {const root=getComputedStyle(document.documentElement);const rt=document.querySelector('.cui-native-range__track');const s=document.querySelector('.cui-native-slider');return {rangeTrack:parseFloat(getComputedStyle(rt).height),singleTrack:parseFloat(root.getPropertyValue('--cui-v17-slider-track')),singleThumb:parseFloat(root.getPropertyValue('--cui-v17-thumb')),rangeThumb:parseFloat(getComputedStyle(document.querySelector('.cui-native-range__input'),'::-webkit-slider-thumb').width)||parseFloat(root.getPropertyValue('--cui-v17-thumb'))}}""")
                    if abs(geometry['rangeTrack']-geometry['singleTrack'])>0.5 or abs(geometry['rangeThumb']-geometry['singleThumb'])>0.5: issues.append('single/range slider track geometry drifted')
            card=page.locator('.cui-surface--interactive').filter(has_text='click to toggle selection').first
            if card.count():
                before=card.get_attribute('aria-pressed'); card.click(); page.wait_for_timeout(80); after=card.get_attribute('aria-pressed')
                if before==after: issues.append('interactive card did not toggle selected state')
            slider=page.locator('.cui-native-slider').first
            if slider.count():
                old=slider.input_value(); slider.evaluate("e=>{e.value=Number(e.min)+(Number(e.max)-Number(e.min))*.35;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}"); page.wait_for_timeout(60)
                if slider.input_value()==old: issues.append('native slider did not accept direct manipulation')
            # A real select selection must update the control model.
            select=page.locator('.cui-select').first
            if select.count():
                select.click(); page.wait_for_timeout(80)
                option=page.get_by_text('CVD',exact=True).last
                if option.count(): option.click(); page.wait_for_timeout(100)
                if 'CVD' not in (select.inner_text() or ''): issues.append('select option did not update visible value')
        elif route=='/content':
            markers=page.locator('.cui-progress-step__marker')
            for i in range(min(markers.count(),4)):
                marker=markers.nth(i); glyph=marker.locator('svg,.cui-svg-icon-host,.q-icon,.cui-progress-step__number').first
                if glyph.count():
                    mb=marker.bounding_box(); gb=glyph.bounding_box()
                    if mb and gb and (abs((mb['x']+mb['width']/2)-(gb['x']+gb['width']/2))>2.5 or abs((mb['y']+mb['height']/2)-(gb['y']+gb['height']/2))>2.5): issues.append('workflow marker content is not optically centered')
            viewer=page.locator('[data-cui-image-viewer=true]').first
            viewport=viewer.locator('.cui-image-viewer__viewport').first if viewer.count() else None
            if not viewer.count() or viewport is None or not viewport.count(): issues.append('Image Viewer evidence surface missing')
            else:
                initial=float(viewport.get_attribute('data-cui-spatial-scale') or '1')
                zoom_in=viewer.get_by_role('button',name='Zoom in').first
                if zoom_in.count(): zoom_in.click(); page.wait_for_timeout(120)
                after=float(viewport.get_attribute('data-cui-spatial-scale') or '1')
                if after<=initial: issues.append('Image Viewer Zoom in did not change inspect scale')
                zoom_label=viewer.locator('.cui-image-viewer__zoom').first
                if zoom_label.count() and zoom_label.inner_text().strip()=='100%': issues.append('Image Viewer zoom readout did not update')
                box=viewport.bounding_box()
                if box and after>1:
                    before_x=float(viewport.get_attribute('data-cui-spatial-x') or '0')
                    page.mouse.move(box['x']+box['width']*.58,box['y']+box['height']*.55); page.mouse.down(); page.mouse.move(box['x']+box['width']*.68,box['y']+box['height']*.62,steps=5); page.mouse.up(); page.wait_for_timeout(90)
                    after_x=float(viewport.get_attribute('data-cui-spatial-x') or '0')
                    if abs(after_x-before_x)<1: issues.append('Image Viewer drag did not pan zoomed evidence')
                fit=viewer.get_by_role('button',name='Fit image').first
                if fit.count(): fit.click(); page.wait_for_timeout(100)
                if abs(float(viewport.get_attribute('data-cui-spatial-scale') or '1')-1)>0.01: issues.append('Image Viewer Fit did not restore scale')
                if zoom_label.count() and zoom_label.inner_text().strip()!='100%': issues.append('Image Viewer Fit did not restore 100% readout')
            step=page.locator('.cui-progress-step').first
            if step.count():
                legacy=step.evaluate("e=>getComputedStyle(e,'::after').content")
                if legacy not in ('none','normal','""'): issues.append('obsolete workflow connector pseudo-element is still visible')
            rails=page.locator('.cui-progress-step__rail')
            if rails.count() >= 2:
                for i in range(rails.count()-1):
                    rail=rails.nth(i); after=rail.evaluate("e=>{const s=getComputedStyle(e,'::after');return {content:s.content,width:parseFloat(s.width),display:s.display}}")
                    if after['display']=='none' or after['content'] in ('none','normal','""') or after['width']<8: issues.append('workflow rail is visually discontinuous'); break
            page.get_by_role('button',name='Open command palette').click(); page.wait_for_timeout(120)
            palette=page.locator('.cui-command-palette').first
            if palette.count()==0: issues.append('Command palette did not open')
            else:
                if palette.locator('.q-field').count(): issues.append('command palette search still exposes Quasar field anatomy')
                if palette.locator('button.cui-command-palette__item').count()<1: issues.append('command palette actions are not native buttons')
                command=palette.get_by_text('Open RCA workspace',exact=True).first
                if command.count():
                    command.click(); page.wait_for_url(re.compile(r'.*/engineering/?$'),timeout=3000); page.wait_for_timeout(100)
                    page.goto(page.url.rsplit('/engineering',1)[0]+'/content',wait_until='domcontentloaded'); page.wait_for_selector('main, [role=main]'); page.wait_for_timeout(180)
                else: issues.append('RCA command not present in command palette')
        elif route=='/engineering':
            context=page.locator('.cui-investigation-context').first
            if not context.count() or 'EXC-1042' not in (context.inner_text() or ''): issues.append('RCA investigation context strip missing')
            card=page.locator('.cui-eng-entity').filter(has_text='ETCH-021').first
            if card.count():
                cb=card.bounding_box()
                card_radius=card.evaluate("e=>({actual:parseFloat(getComputedStyle(e).borderTopLeftRadius),expected:parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--cui-radius-surface'))})")
                if abs(card_radius['actual']-card_radius['expected'])>0.5: issues.append('EngineeringEntityCard radius violates surface token')
                for i in range(card.locator('.cui-eng-property').count()):
                    prop=card.locator('.cui-eng-property').nth(i); pb=prop.bounding_box()
                    pr=prop.evaluate("e=>({actual:parseFloat(getComputedStyle(e).borderTopLeftRadius),expected:parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--cui-radius-control'))})")
                    if abs(pr['actual']-pr['expected'])>0.5: issues.append('EngineeringEntity property radius violates control token')
                    if cb and pb and (pb['x']<cb['x']-1 or pb['y']<cb['y']-1 or pb['x']+pb['width']>cb['x']+cb['width']+1 or pb['y']+pb['height']>cb['y']+cb['height']+1): issues.append('RCA metadata property escaped EngineeringEntityCard bounds')
            else: issues.append('RCA engineering entity card missing')
        elif route=='/data':
            initial_grids=page.locator('.cui-data-table .ag-root-wrapper')
            if initial_grids.count()!=1: issues.append(f'DataTable lab mounted {initial_grids.count()} AG Grid instances initially; expected exactly 1')
            for label in ('Load configuration editor','Load maintenance planner','Load incident queue','Load reconciliation review'):
                if not page.get_by_role('button',name=label).count(): issues.append(f'DataTable deferred certification control missing: {label}')
            page_scroll=page.evaluate("""async () => {
              const startY=window.scrollY; const gaps=[]; let last=performance.now(); let frames=0;
              return await new Promise(resolve => {
                const step=(now)=>{ gaps.push(now-last); last=now; window.scrollBy(0,220); frames+=1;
                  if(frames<8) requestAnimationFrame(step); else { window.scrollTo(0,startY); resolve({max:Math.max(...gaps),avg:gaps.reduce((a,b)=>a+b,0)/gaps.length}); }
                }; requestAnimationFrame(step);
              });
            }""")
            if page_scroll['max']>140 or page_scroll['avg']>65: issues.append(f"DataTable page scroll frame latency is too high (max {page_scroll['max']:.1f}ms, avg {page_scroll['avg']:.1f}ms)")
            grid=initial_grids.first
            if grid.count(): grid.evaluate("el => el.dataset.cuiPhase4Probe='stable'")
            search=page.get_by_label('Search table').first
            if search.count():
                before_rows=page.locator('.cui-data-table .ag-center-cols-container .ag-row').count()
                search_started=time.perf_counter(); search.fill('ETCH-021')
                footer=page.locator('.cui-table-footer-label').first
                try: page.wait_for_function("() => (document.querySelector('.cui-table-footer-label')?.textContent || '').includes(' of ')",timeout=1200)
                except Exception: pass
                search_elapsed=time.perf_counter()-search_started
                if search_elapsed > .9: issues.append(f'table quick filter exceeded 900ms interaction budget ({search_elapsed:.3f}s)')
                if footer.count() and 'of' not in (footer.inner_text() or ''): issues.append('table search did not expose filtered record count')
                filtered_rows=page.locator('.cui-data-table .ag-center-cols-container .ag-row').count()
                if before_rows and filtered_rows > before_rows: issues.append('table quick filter increased rendered row count unexpectedly')
                if grid.count() and grid.get_attribute('data-cui-phase4-probe')!='stable': issues.append('table search remounted AG Grid root')
                search.fill(''); page.wait_for_timeout(220)
            else: issues.append('Company table search input missing')
            viewport=page.locator('.cui-data-table .ag-body-viewport').first
            if viewport.count():
                before_max=page.locator('.cui-data-table .ag-center-cols-container .ag-row').evaluate_all("els => Math.max(-1,...els.map(e=>Number(e.getAttribute('row-index')||-1)))")
                scroll_started=time.perf_counter()
                viewport.evaluate("e => { e.scrollTop=Math.min(e.scrollHeight-e.clientHeight, Math.max(760,e.scrollTop+760)); }")
                try:
                    page.wait_for_function("before => Math.max(-1,...[...document.querySelectorAll('.cui-data-table .ag-center-cols-container .ag-row')].map(e=>Number(e.getAttribute('row-index')||-1))) >= before + 5",arg=before_max,timeout=350)
                except Exception:
                    issues.append('table vertical scroll did not render later rows within 350ms')
                scroll_elapsed=time.perf_counter()-scroll_started
                if scroll_elapsed > .35: issues.append(f'table vertical scroll exceeded 350ms responsiveness budget ({scroll_elapsed:.3f}s)')
                viewport.evaluate("e => { e.scrollTop=0; }"); page.wait_for_timeout(60)
            else: issues.append('DataTable vertical viewport missing')
            density=page.get_by_role('button',name='Table density').first
            if density.count():
                first_row=page.locator('.cui-data-table .ag-row').first
                before_h=first_row.bounding_box()['height'] if first_row.count() and first_row.bounding_box() else None
                density.click(); page.wait_for_timeout(60)
                dense=page.locator('.cui-table-density-option').filter(has_text='Dense').first
                density_started=time.perf_counter()
                if dense.count(): dense.click()
                try: page.wait_for_function("() => (document.querySelector('.cui-table-footer-density')?.textContent || '').includes('Dense')",timeout=900)
                except Exception: pass
                density_elapsed=time.perf_counter()-density_started
                if density_elapsed > .7: issues.append(f'table density change exceeded 700ms interaction budget ({density_elapsed:.3f}s)')
                after_h=first_row.bounding_box()['height'] if first_row.count() and first_row.bounding_box() else None
                if before_h is not None and after_h is not None and before_h-after_h < 2: issues.append('Dense table mode did not materially reduce row height')
                footer_density=page.locator('.cui-table-footer-density').first
                if footer_density.count() and 'Dense' not in (footer_density.inner_text() or ''): issues.append('table density state not reflected in footer')
                if grid.count() and grid.get_attribute('data-cui-phase4-probe')!='stable': issues.append('table density change remounted AG Grid root')
            else: issues.append('table density control missing')
            inspect_action=page.locator('.cui-table-row-action').filter(has_text='Inspect').first
            if inspect_action.count():
                inspect_action.click(); page.wait_for_timeout(140)
                action_drawer=page.locator('.cui-drawer').first
                if not action_drawer.count() or not action_drawer.is_visible(): issues.append('Inspect row action did not open inspector')
                else:
                    close=action_drawer.get_by_role('button',name='Close').first
                    if close.count(): close.click(); page.wait_for_timeout(100)
            else: issues.append('Inspect row action missing')
            row=page.locator('.cui-data-table .ag-row').first
            if row.count():
                row.dblclick(); page.wait_for_timeout(140)
                drawer=page.locator('.cui-drawer').first
                if not drawer.count() or not drawer.is_visible(): issues.append('table row double-click did not open inspector')
                else:
                    modal_owns=page.evaluate("""() => {
                      const drawer=document.querySelector('.cui-drawer'), toolbar=document.querySelector('.cui-table-toolbar');
                      if(!drawer||!toolbar)return true; const dr=drawer.getBoundingClientRect(),tr=toolbar.getBoundingClientRect();
                      const y=Math.max(dr.top+12,Math.min(dr.bottom-12,tr.top+tr.height/2)),x=dr.left+18;
                      const top=document.elementFromPoint(x,y); return !!top?.closest?.('.q-dialog');
                    }""")
                    if not modal_owns: issues.append('DataTable toolbar rendered above inspector overlay')
                    close=drawer.get_by_role('button',name='Close').first
                    if close.count(): close.click(); page.wait_for_timeout(100)
            else: issues.append('data table rendered no inspectable rows')
            # Secondary grids stay absent during normal page use but remain fully certifiable on demand.
            expected=1
            for label in ('Load configuration editor','Load maintenance planner','Load incident queue','Load reconciliation review'):
                button=page.get_by_role('button',name=label).first
                if button.count():
                    button.scroll_into_view_if_needed(); button.click(); expected+=1
                    try: page.wait_for_function("n => document.querySelectorAll('.cui-data-table .ag-root-wrapper').length >= n",arg=expected,timeout=1200)
                    except Exception: issues.append(f'DataTable deferred surface failed to mount: {label}')
            if page.locator('.cui-data-table .ag-root-wrapper').count()<5: issues.append('DataTable deferred certification surfaces are incomplete after explicit load')
        elif route=='/charts':
            zoom=page.get_by_role('button',name='Zoom in').first
            script="""() => { const root=document.querySelector('.cui-chart-canvas'); if(!root||!window.echarts)return null; const nodes=[root,...root.querySelectorAll('*')]; const dom=nodes.find(n=>n.getAttribute&&n.getAttribute('_echarts_instance_')); const chart=dom?window.echarts.getInstanceByDom(dom):null; const z=chart?.getOption?.().dataZoom||[]; return z.slice(0,2).map(x=>({id:x.id,start:x.start,end:x.end})); }"""
            if zoom.count():
                before=page.evaluate(script); zoom.click(); page.wait_for_timeout(220); after=page.evaluate(script)
                if before is not None and after is not None and before==after: issues.append('chart zoom control did not change dataZoom range')
                if after and len(after)>=2 and (after[0].get('start')==0 and after[0].get('end')==100 or after[1].get('start')==0 and after[1].get('end')==100): issues.append('chart Zoom in did not adjust both x and y ranges')
            else: issues.append('chart Zoom in control missing')
            range_button=page.get_by_role('button',name='View range').first
            if range_button.count():
                range_button.click(); page.wait_for_timeout(100)
                yzoom=page.get_by_role('button',name='Y axis zoom in').first
                if yzoom.count():
                    before_y=page.evaluate(script); yzoom.click(); page.wait_for_timeout(180); after_y=page.evaluate(script)
                    if before_y and after_y and len(before_y)>=2 and before_y[1]==after_y[1]: issues.append('explicit Y-axis range control did not change y dataZoom')
                else: issues.append('Y-axis range control missing')
                page.keyboard.press('Escape'); page.wait_for_timeout(60)
            else: issues.append('View range control missing')
            canvas=page.locator('.cui-chart-canvas').first
            if canvas.count():
                before_wheel=page.evaluate(script); canvas.hover(); page.mouse.wheel(0,-420); page.wait_for_timeout(240); after_wheel=page.evaluate(script)
                if before_wheel and after_wheel and before_wheel==after_wheel: issues.append('chart wheel did not directly change 2D zoom range')
            heat_band=page.locator('.cui-chart-scale-band').first
            if not heat_band.count() or not heat_band.is_visible(): issues.append('heatmap Company scale band missing')
            else:
                scale_ok=heat_band.evaluate("""band=>{const panel=band.closest('.cui-chart-panel');const canvas=panel?.querySelector('.cui-chart-canvas');if(!canvas)return false;const b=band.getBoundingClientRect(),c=canvas.getBoundingClientRect();return b.top>=c.bottom-2&&b.width<=panel.getBoundingClientRect().width+1;}""")
                if not scale_ok: issues.append('heatmap scale band overlaps chart plot area')
            if page.locator('.cui-wafer-dies[clip-path]').count() < 1: issues.append('wafer dies are not clipped to wafer boundary')
            if not page.locator('.cui-fingerprint-outline').count(): issues.append('chamber fingerprint visualization missing')
            if not page.locator('.cui-commonality-outline').count(): issues.append('commonality matrix visualization missing')
            chart_semantics=page.evaluate("""() => {
              if(!window.echarts)return {donut:[],stack:[]}; const out={donut:[],stack:[]};
              for(const host of document.querySelectorAll('.cui-chart-canvas')){
                const dom=[host,...host.querySelectorAll('*')].find(n=>n.getAttribute&&n.getAttribute('_echarts_instance_'));
                const chart=dom?window.echarts.getInstanceByDom(dom):null; if(!chart)continue; const opt=chart.getOption();
                for(const s of opt.series||[]){
                  if(s.type==='pie') out.donut.push(...(s.data||[]).map(d=>d.itemStyle?.color).filter(Boolean));
                  if(s.type==='bar'&&s.stack) out.stack.push(s.itemStyle?.borderRadius);
                }
              } return out;
            }""")
            if chart_semantics.get('donut') and len(set(chart_semantics['donut']))<2: issues.append('donut categories still render with one color')
            stack=chart_semantics.get('stack') or []
            if len(stack)>=2 and stack[0]==stack[-1]: issues.append('stacked bar outer/interior corner geometry is not differentiated')
        elif route in REFERENCE_ROUTES:
            pattern=page.locator('.cui-pattern').first
            if not pattern.count(): issues.append('canonical reference application is missing PatternPage root')
            if page.locator('.cui-lab-controlbar').count(): issues.append('reference application leaked certification control bar above product content')
            header=page.locator('.cui-pattern > .cui-page-header').first
            if not header.count(): issues.append('reference application page header missing from governed pattern root')
            slots=page.locator('.cui-pattern-slot')
            if slots.count():
                page_box=pattern.bounding_box()
                for i in range(slots.count()):
                    box=slots.nth(i).bounding_box()
                    if page_box and box and (box['x'] < page_box['x']-1 or box['x']+box['width'] > page_box['x']+page_box['width']+1):
                        issues.append('reference pattern slot escaped page canvas'); break
            width=page.viewport_size['width']
            # Desktop relationships are intentional; mobile/tablet below breakpoint becomes one ordered column.
            pairs={
                '/patterns/dashboard':('primary','secondary'), '/patterns/explorer':('primary','secondary'),
                '/patterns/master-detail':('data','details'), '/patterns/search':('filters','data'),
                '/patterns/settings':('navigation','content'), '/patterns/analysis':('primary','details'),
            }
            pair=pairs.get(route)
            if pair:
                left=page.locator(f'.cui-pattern-slot--{pair[0]}').first; right=page.locator(f'.cui-pattern-slot--{pair[1]}').first
                if left.count() and right.count():
                    lb=left.bounding_box(); rb=right.bounding_box()
                    if lb and rb:
                        if width>=900 and rb['x'] <= lb['x']+lb['width']+8: issues.append(f'{route} desktop composition did not preserve side-by-side hierarchy')
                        if width<900 and abs(rb['x']-lb['x'])>3: issues.append(f'{route} mobile composition did not collapse to one column')
            if route=='/patterns/crud':
                create=page.get_by_role('button',name='New saved view').first
                if not create.count(): issues.append('CRUD primary create action missing')
                else:
                    create.click(); page.wait_for_timeout(120); drawer=page.locator('.cui-drawer').filter(has_text='New saved view').first
                    if not drawer.count() or not drawer.is_visible(): issues.append('CRUD create action did not open form drawer')
                    elif drawer.get_by_label('View name').count()==0: issues.append('CRUD create drawer missing editable form')
                    if drawer.count() and drawer.is_visible():
                        close=drawer.get_by_role('button',name='Close').first
                        if close.count(): close.click(); page.wait_for_timeout(80)
            elif route=='/patterns/search':
                result=page.locator('.cui-search-result').first
                if result.count():
                    result.click(); page.wait_for_timeout(120); drawer=page.locator('.cui-drawer').first
                    if not drawer.count() or not drawer.is_visible(): issues.append('Search result did not open contextual inspector')
                    elif drawer.get_by_role('button',name='Close').count(): drawer.get_by_role('button',name='Close').click(); page.wait_for_timeout(80)
                else: issues.append('Search pattern rendered no selectable results')
            elif route=='/patterns/wizard':
                review=page.get_by_role('button',name='Review controls').first
                if not review.count(): issues.append('Wizard review action missing')
                else:
                    review.click(); page.wait_for_timeout(120); dialog=page.locator('.cui-dialog').filter(has_text='Review investigation setup').first
                    if not dialog.count() or not dialog.is_visible(): issues.append('Wizard review action did not open review dialog')
                    elif dialog.get_by_role('button',name='Back').count(): dialog.get_by_role('button',name='Back').click(); page.wait_for_timeout(80)
            elif route=='/patterns/comparison':
                if page.locator('.cui-wafer-boundary').count()<2: issues.append('Comparison pattern missing synchronized affected/control wafer evidence')
            elif route=='/patterns/analysis':
                if not page.locator('.cui-investigation-context').count(): issues.append('Analysis workspace missing investigation context')
                if not page.locator('.cui-commonality-outline').count(): issues.append('Analysis workspace missing semiconductor-native commonality evidence')
            elif route=='/patterns/settings':
                if not page.locator('.cui-settings-navigation').count(): issues.append('Settings pattern missing governed local navigation')
        elif route=='/states':
            retry=page.get_by_role('button',name='Retry').first
            if retry.count(): retry.click(); page.wait_for_timeout(80)
            stress=page.locator('.cui-v2-i18n-stress')
            if stress.count()<2: issues.append('mixed Korean/English content stress fixtures are missing')
            else:
                for i in range(stress.count()):
                    metrics=stress.nth(i).evaluate("e=>({scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,text:e.innerText})")
                    if metrics['scrollWidth']>metrics['clientWidth']+2: issues.append('mixed Korean/English stress content overflowed its governed surface')
                if '설비 이상 분석' not in stress.nth(0).inner_text(): issues.append('Korean content stress fixture lost expected text')
    except Exception as exc: issues.append(f'interaction smoke failed: {exc}')
    try:
        issues.extend(_performance_issues(_route_performance_probe(page)))
    except Exception as exc:
        issues.append(f'route performance probe failed: {exc}')
    return issues


def run_mac_browser_matrix(base_url: str, *, output_dir: Path, baseline_dir: Path | None = None,
                           exhaustive: bool = False, include_edge: bool = True, browser_executables: dict[str,str] | None = None,
                           report_name: str = 'MAC_BROWSER_REPORT.json') -> MacBrowserReport:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        return MacBrowserReport((RouteBrowserResult('browser','/','fail',f'Playwright unavailable: {exc}'),),{},str(baseline_dir) if baseline_dir else None)
    output_dir.mkdir(parents=True,exist_ok=True)
    screenshots=output_dir/'screenshots'; screenshots.mkdir(parents=True,exist_ok=True)
    scenarios=exhaustive_scenarios(include_edge=include_edge) if exhaustive else standard_scenarios(include_edge=include_edge)
    results: list[RouteBrowserResult]=[]; versions: dict[str,str]={}
    with sync_playwright() as p:
        for scenario in scenarios:
            browser_type=p.chromium
            try:
                executable=(browser_executables or {}).get(scenario.browser)
                launch_kwargs={'headless':True}
                if executable:
                    launch_kwargs['executable_path']=executable
                else:
                    launch_kwargs['channel']=scenario.browser
                browser=browser_type.launch(**launch_kwargs)
                versions.setdefault(scenario.browser,browser.version)
            except Exception as exc:
                status='warning' if scenario.browser=='msedge' else 'fail'
                results.append(RouteBrowserResult(scenario.key,'/',status,f'{scenario.browser} launch failed: {exc}'))
                continue
            context=browser.new_context(viewport={'width':scenario.width,'height':scenario.height},color_scheme='dark' if scenario.theme=='dark' else 'light')
            try:
                for index,route in enumerate(scenario.routes):
                    page=context.new_page(); console_errors=[]; page_errors=[]; websockets=[]
                    page.on('console',lambda msg,bag=console_errors: bag.append(msg.text) if msg.type=='error' else None)
                    page.on('pageerror',lambda exc,bag=page_errors: bag.append(str(exc)))
                    page.on('websocket',lambda ws,bag=websockets: bag.append(ws.url))
                    url=base_url.rstrip('/')+('/' if route=='/' else route)
                    started=time.perf_counter()
                    try:
                        response=page.goto(url,wait_until='domcontentloaded',timeout=30_000); page.wait_for_selector('main, [role=main]',state='attached',timeout=10_000); page.wait_for_timeout(350)
                        _set_controls(page,scenario.theme,scenario.density)
                        interaction_issues=_interaction_smoke(page,route,density=scenario.density) if route in KEY_ROUTES else []
                        audit=page.evaluate(_DOM_AUDIT)
                        page.keyboard.press('Tab'); keyboard_focus=bool(page.evaluate("document.activeElement && document.activeElement !== document.body"))
                        audit['keyboardFocus']=keyboard_focus; audit['websocketCount']=len(websockets); audit['consoleErrors']=console_errors[:10]; audit['pageErrors']=page_errors[:10]; audit['interactionIssues']=interaction_issues
                        file_name=f'{scenario.key}__{_slug(route)}.png'; shot=screenshots/file_name; page.screenshot(path=str(shot),full_page=True)
                        visual=None
                        if baseline_dir is not None: visual=_compare_images(shot,baseline_dir/file_name)
                        failures=[]
                        if not response or not response.ok: failures.append(f'HTTP {response.status if response else "?"}')
                        if console_errors: failures.append(f'{len(console_errors)} console error(s)')
                        if page_errors: failures.append(f'{len(page_errors)} page error(s)')
                        if audit['horizontalOverflow']: failures.append('horizontal overflow')
                        if not audit['mainLandmark']: failures.append('main landmark missing')
                        if audit['missingAccessibleNames']: failures.append(f"{audit['missingAccessibleNames']} missing accessible name(s)")
                        if audit['duplicateIds']: failures.append(f"{audit['duplicateIds']} duplicate id(s)")
                        if audit['imagesMissingAlt']: failures.append(f"{audit['imagesMissingAlt']} image(s) missing alt")
                        if audit['stockVisualLeakCount']: failures.append(f"{audit['stockVisualLeakCount']} stock visual leak(s)")
                        if audit['unapprovedMaterialIconCount']: failures.append(f"{audit['unapprovedMaterialIconCount']} unapproved material icon(s)")
                        if audit.get('geometryViolationCount'): failures.append(f"{audit['geometryViolationCount']} geometry constitution violation(s)")
                        if not keyboard_focus: failures.append('keyboard focus smoke failed')
                        failures.extend(interaction_issues)
                        if visual and visual.get('status')=='fail': failures.append('visual baseline drift')
                        status='fail' if failures else ('warning' if visual and visual.get('status') in {'missing','unavailable'} else 'pass')
                        detail='; '.join(failures) if failures else 'DOM, accessibility, stock-leak, console, responsive and interaction checks passed'
                        results.append(RouteBrowserResult(scenario.key,route,status,detail,str(shot),round((time.perf_counter()-started)*1000,2),audit,visual))
                    except Exception as exc:
                        results.append(RouteBrowserResult(scenario.key,route,'fail',str(exc),duration_ms=round((time.perf_counter()-started)*1000,2)))
                    finally: page.close()
            finally: context.close(); browser.close()
    report=MacBrowserReport(tuple(results),versions,str(baseline_dir) if baseline_dir else None)
    (output_dir/report_name).write_text(json.dumps(report.to_dict(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return report


def screenshot_manifest(directory: Path) -> dict[str, str]:
    result={}
    for path in sorted(directory.glob('*.png')): result[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


__all__=['BrowserScenario','RouteBrowserResult','MacBrowserReport','KEY_ROUTES','EDGE_SMOKE_ROUTES','standard_scenarios','exhaustive_scenarios','run_mac_browser_matrix','screenshot_manifest']
