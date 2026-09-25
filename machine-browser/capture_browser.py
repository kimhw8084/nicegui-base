from __future__ import annotations
import hashlib, json, platform, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

TMP=Path('/tmp/CF-a25508c618dbb510eb6c7d1f-chg100-refresh2')
OUT=TMP/'machine-browser'; SHOTS=OUT/'screenshots'
OUT.mkdir(parents=True,exist_ok=True); SHOTS.mkdir(parents=True,exist_ok=True)
SERVER=json.loads((TMP/'server.json').read_text()); BASE=SERVER['url']
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
VPS={'desktop':{'width':1440,'height':900},'mobile':{'width':390,'height':844}}
SCENARIOS=[]; FOCUS=[]; NETWORK=[]; SCREENSHOTS=[]

class Recorder:
    def __init__(self,page):
        self.events={'console_errors':[],'page_errors':[],'failed_requests':[],'bad_responses':[]}
        page.on('console',lambda m:self.events['console_errors'].append({'text':m.text[:1000],'url':m.location.get('url')}) if m.type=='error' else None)
        page.on('pageerror',lambda e:self.events['page_errors'].append(str(e)[:1400]))
        page.on('requestfailed',lambda q:self.events['failed_requests'].append({'url':q.url,'resource_type':q.resource_type,'failure':q.failure}))
        page.on('response',lambda r:self.events['bad_responses'].append({'url':r.url,'status':r.status,'resource_type':r.request.resource_type}) if r.status>=400 else None)
    def reset(self):
        for value in self.events.values(): value.clear()
    def snapshot(self):
        return json.loads(json.dumps(self.events))
    def essential(self):
        output=[]
        for item in self.events['bad_responses']:
            if item['url'].startswith(BASE) or item['resource_type'] in {'document','script','stylesheet','xhr','fetch'}: output.append({'kind':'http','item':item})
        for item in self.events['failed_requests']:
            if item['url'].startswith(BASE) or item['resource_type'] in {'document','script','stylesheet','xhr','fetch'}: output.append({'kind':'failed_request','item':item})
        return output

def context(browser,viewport,color='light'):
    return browser.new_context(viewport=viewport,device_scale_factor=1,reduced_motion='reduce',color_scheme=color)
def visit(page,rec,route):
    rec.reset(); response=page.goto(BASE+route,wait_until='domcontentloaded',timeout=45000)
    page.locator('body').wait_for(state='visible',timeout=10000); page.wait_for_timeout(650)
    return response
def type_query(locator,value):
    locator.click();locator.press('ControlOrMeta+A')
    if value:locator.press_sequentially(value,delay=18)
    else:locator.press('Backspace')
def dimensions(page):
    return page.evaluate('''()=>({viewport:innerWidth,docWidth:document.documentElement.scrollWidth,docClient:document.documentElement.clientWidth,bodyWidth:document.body.scrollWidth,bodyClient:document.body.clientWidth,docHeight:document.documentElement.scrollHeight})''')
def visible(locator):
    try:return locator.is_visible()
    except Exception:return False
def screenshot(page,name):
    path=SHOTS/name; path.parent.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(path),full_page=False,animations='disabled')
    raw=path.read_bytes()
    SCREENSHOTS.append({'path':'machine-browser/screenshots/'+name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    return path
def route_checks(page,rec):
    issues=[]; d=dimensions(page)
    if max(d['docWidth']-d['docClient'],d['bodyWidth']-d['docClient'])>1:issues.append('document-body-horizontal-overflow>1px')
    if rec.essential():issues.append('essential-request-failure')
    if rec.events['page_errors']:issues.append('page-error')
    if rec.events['console_errors']:issues.append('console-error')
    return issues,d
def add_scenario(sid,title,checks,rec,extra=None):
    issues=list(checks); essential=rec.essential()
    if essential and 'essential-request-failure' not in issues:issues.append('essential-request-failure')
    if rec.events['page_errors'] and 'page-error' not in issues:issues.append('page-error')
    if rec.events['console_errors'] and 'console-error' not in issues:issues.append('console-error')
    item={'id':sid,'title':title,'status':'PASS' if not issues else 'FAIL','issues':issues,'browser_events':rec.snapshot(),'essential_request_failures':essential}
    if extra:item.update(extra)
    SCENARIOS.append(item)
    return item
def gallery_contract(page,vp):
    issues=[]; details=page.locator('details.cui-explorer-refine'); search=page.locator('input[data-explorer-search]')
    if search.count()!=1:issues.append(f'primary-search-count={search.count()}')
    if details.count()!=1:issues.append(f'refine-count={details.count()}')
    if details.count()==1 and search.count()==1 and details.first.locator('input[data-explorer-search]').count():issues.append('search-inside-refine')
    if details.count()==1:
        d=details.first; summary=d.locator('summary').first; body=d.locator('.cui-explorer-refine__body').first
        if vp=='desktop':
            if not d.evaluate('(e)=>e.open'):issues.append('desktop-refine-not-open')
            if visible(summary):issues.append('desktop-summary-visible')
            if not visible(body):issues.append('desktop-refinement-body-hidden')
            if page.locator('input[aria-label="Family"]').count()!=1:issues.append('desktop-family-authority-count')
            if page.get_by_role('button',name='Favorites only',exact=True).count()!=1:issues.append('desktop-favorites-authority-count')
        else:
            if d.evaluate('(e)=>e.open'):issues.append('mobile-refine-not-closed')
            if not visible(summary):issues.append('mobile-refine-summary-hidden')
            if visible(body):issues.append('mobile-refinement-body-visible-while-closed')
            summary.focus();page.keyboard.press('Enter');page.wait_for_timeout(140)
            if not d.evaluate('(e)=>e.open') or not visible(body):issues.append('mobile-summary-keyboard-open-failed')
            if page.locator('input[aria-label="Family"]').count()!=1:issues.append('mobile-family-authority-count')
            if page.get_by_role('button',name='Favorites only',exact=True).count()!=1:issues.append('mobile-favorites-authority-count')
            if not visible(search):issues.append('mobile-primary-search-hidden-when-open')
            page.keyboard.press('Enter');page.wait_for_timeout(140)
            if d.evaluate('(e)=>e.open') or visible(body):issues.append('mobile-summary-keyboard-close-failed')
            if not visible(search):issues.append('mobile-search-unusable-outside-refine')
    if page.locator('input[data-explorer-search]').count()!=1:issues.append('duplicate-or-missing-primary-search')
    return issues
def s1(browser):
    checks=[];samples=[];rec=None
    for route in ['/components','/analytics','/recipes']:
        for vp,size in VPS.items():
            ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,route)
            local=gallery_contract(page,vp)
            if resp is None or resp.status!=200:local.append(f'http-status={resp.status if resp else None}')
            route_issues,d=route_checks(page,rec);local.extend(route_issues)
            samples.append({'route':route,'viewport':vp,'http_status':resp.status if resp else None,'dimensions':d,'issues':local,'events':rec.snapshot(),'essential_request_failures':rec.essential()})
            checks.extend(f'{route}@{vp}:{x}' for x in local)
            screenshot(page,f's1-{route.strip("/")}-{vp}.png');ctx.close()
    add_scenario('CURRENT_MAIN_SHARED_GALLERIES','Current main shared gallery responsive contract',checks,rec,{'route_samples':samples})
def s2(browser):
    checks=[];samples=[];rec=None
    for vp,size in VPS.items():
        ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,'/patterns');local=[]
        if resp is None or resp.status!=200:local.append(f'http-status={resp.status if resp else None}')
        if page.locator('[data-unified-pattern-explorer]').count()!=1:local.append('unified-pattern-explorer-count')
        if page.locator('[data-pattern-option]').count()<1:local.append('no-pattern-options')
        selected=page.locator('.cui-field').filter(has_text='Selected application pattern')
        if selected.count()!=1 or not visible(selected.first):local.append('selected-pattern-control-missing-or-unusable')
        if page.get_by_role('button',name='Open live example').count()<1:local.append('live-pattern-controls-missing')
        if page.locator('[data-full-application-showcases]').count()!=1 or page.get_by_role('button',name='Open live application').count()<1:local.append('full-application-controls-missing')
        if page.locator('input[data-explorer-search]').count()!=0:local.append('shared-search-marker-unexpected')
        if page.locator('details.cui-explorer-refine').count()!=0:local.append('shared-refine-marker-unexpected')
        ri,d=route_checks(page,rec);local.extend(ri)
        samples.append({'route':'/patterns','viewport':vp,'http_status':resp.status if resp else None,'dimensions':d,'issues':local,'events':rec.snapshot(),'essential_request_failures':rec.essential()})
        checks.extend(f'/patterns@{vp}:{x}' for x in local)
        screenshot(page,f's2-patterns-{vp}.png');ctx.close()
    add_scenario('CURRENT_MAIN_PATTERNS_IDENTITY','Current main patterns chooser identity and distinct contract',checks,rec,{'route_samples':samples})
def family_select(page,value):
    control=page.locator('input[role="combobox"][aria-label="Family"]').first;control.click();page.wait_for_timeout(80)
    opt=page.get_by_role('option',name=value,exact=True)
    if not opt.count():opt=page.locator('.q-menu .q-item').filter(has_text=re.compile('^'+re.escape(value)+'$')).first
    opt.click();page.wait_for_timeout(420)
def gallery_workflow(browser,vp,size):
    ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,'/components');checks=[];steps=[]
    if resp is None or resp.status!=200:checks.append(f'http-status={resp.status if resp else None}')
    checks.extend('gallery-contract:'+x for x in gallery_contract(page,vp))
    search=page.locator('input[data-explorer-search]').first
    if search.count()!=1:ctx.close();return checks,[{'step':'workflow','status':'BLOCKED','reason':'primary search unavailable'}],rec
    cards=page.locator('.cui-explorer-card[data-entry-key]')
    if vp=='mobile' and page.locator('details.cui-explorer-refine').evaluate('(e)=>e.open'):page.locator('details.cui-explorer-refine summary').press('Enter')
    type_query(search,'MultiSelect');page.wait_for_timeout(500)
    keys=cards.evaluate_all('(es)=>es.map(e=>e.getAttribute("data-entry-key"))');texts=cards.all_inner_texts()
    ok=len(keys)==1 and 'MultiSelect' in texts[0]
    if not ok:checks.append(f'known-search-incoherent:{keys}:{texts[:1]}')
    steps.append({'step':'known-match','query':'MultiSelect','keys':keys,'status':'PASS' if ok else 'FAIL'})
    screenshot(page,f's3-components-{vp}-matching.png')
    type_query(search,'zzzz-no-such-component-2026');page.wait_for_timeout(500);empty=page.locator('.cui-workbench-preview-empty')
    ok=cards.count()==0 and empty.count()==1 and 'No governed reference matches' in empty.inner_text()
    if not ok:checks.append('truthful-no-results-state-missing')
    steps.append({'step':'no-match','query':'zzzz-no-such-component-2026','search_value':search.input_value(),'count':cards.count(),'result_keys':cards.evaluate_all('(es)=>es.map(e=>e.getAttribute("data-entry-key"))'),'empty_text':empty.inner_text() if empty.count() else None,'status':'PASS' if ok else 'FAIL'})
    screenshot(page,f's3-components-{vp}-no-results.png')
    type_query(search,'');page.wait_for_timeout(550);full=cards.count()
    if full<2:checks.append(f'clear-search-did-not-recover:{full}')
    steps.append({'step':'clear-search','count':full,'status':'PASS' if full>=2 else 'FAIL'})
    if vp=='mobile' and not page.locator('details.cui-explorer-refine').evaluate('(e)=>e.open'):page.locator('details.cui-explorer-refine summary').focus();page.keyboard.press('Enter');page.wait_for_timeout(100)
    try:
        ctrl=page.locator('input[role="combobox"][aria-label="Family"]').first;ctrl.click();page.wait_for_timeout(100)
        vals=[x.strip() for x in page.locator('.q-menu .q-item').all_inner_texts() if x.strip() and x.strip()!='All families']
        if not vals:raise RuntimeError('no family options')
        chosen=vals[0];opt=page.locator('.q-menu .q-item').filter(has_text=re.compile('^'+re.escape(chosen)+'$')).first;opt.click();page.wait_for_timeout(450)
        n=cards.count();ok=0<n<full
        if not ok:checks.append(f'family-refinement-not-applied:{chosen}:{n}/{full}')
        steps.append({'step':'family-refinement','family':chosen,'count':n,'full_count':full,'status':'PASS' if ok else 'FAIL'})
        if vp=='mobile' and not visible(search):checks.append('search-not-usable-with-mobile-refine-open')
        if vp=='mobile':screenshot(page,'s3-components-mobile-family.png')
        family_select(page,'All families')
        if cards.count()!=full:checks.append('family-clear-failed-to-recover')
    except Exception as e:
        checks.append('family-refinement-exception:'+str(e)[:300]);steps.append({'step':'family-refinement','status':'FAIL','reason':str(e)[:300]})
    type_query(search,'MultiSelect');page.wait_for_timeout(420);card=cards.first;key=card.get_attribute('data-entry-key')
    try:
        card.get_by_role('button',name='☆ Favorite',exact=True).click();page.wait_for_timeout(220)
        saved=card.get_by_role('button',name='★ Saved',exact=True).count()==1
        if not saved:checks.append('favorite-toggle-did-not-save')
        fave=page.get_by_role('button',name='Favorites only',exact=True)
        if vp=='mobile' and not visible(fave):page.locator('details.cui-explorer-refine summary').press('Enter');page.wait_for_timeout(100)
        fave.click();page.wait_for_timeout(420)
        filtered=cards.evaluate_all('(es)=>es.map(e=>e.getAttribute("data-entry-key"))')
        ok=filtered==[key] and page.get_by_role('button',name='All references',exact=True).count()==1
        if not ok:checks.append(f'favorites-filter-incoherent:{filtered}:{key}')
        steps.append({'step':'favorites-only','key':key,'visible_keys':filtered,'status':'PASS' if ok else 'FAIL'})
        screenshot(page,f's3-components-{vp}-favorites.png')
        card=cards.first;card.get_by_role('button',name='Open example',exact=True).click()
        page.wait_for_url('**/studio/**',timeout=12000);page.wait_for_timeout(250)
        page.go_back(wait_until='domcontentloaded',timeout=12000);page.wait_for_timeout(450)
        search=page.locator('input[data-explorer-search]').first;cards=page.locator('.cui-explorer-card[data-entry-key]')
        state=page.get_by_role('button',name='All references',exact=True).count()==1 and search.input_value()=='MultiSelect' and cards.count()==1 and cards.first.get_attribute('data-entry-key')==key
        if vp=='mobile':
            d=page.locator('details.cui-explorer-refine').first
            if not d.evaluate('(e)=>e.open'):d.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_timeout(160)
        state=page.get_by_role('button',name='All references',exact=True).count()==1 and search.input_value()=='MultiSelect' and cards.count()==1 and cards.first.get_attribute('data-entry-key')==key
        if not state:checks.append('favorites-search-return-context-not-preserved')
        steps.append({'step':'browser-back-context','url':page.url,'query':search.input_value(),'visible_keys':cards.evaluate_all('(es)=>es.map(e=>e.getAttribute("data-entry-key"))'),'status':'PASS' if state else 'FAIL'})
        type_query(search,'');page.wait_for_timeout(500)
        if cards.count()!=1:checks.append('clear-query-did-not-preserve-favorites-filter')
        page.get_by_role('button',name='All references',exact=True).click();page.wait_for_timeout(420)
        restored=cards.count()==full
        if not restored:checks.append(f'all-references-recovery:{cards.count()}/{full}')
        steps.append({'step':'return-to-all','count':cards.count(),'full_count':full,'status':'PASS' if restored else 'FAIL'})
    except Exception as e:
        checks.append('favorites-return-context-exception:'+str(e)[:350]);steps.append({'step':'favorites-return-context','status':'FAIL','reason':str(e)[:350]})
    ri,d=route_checks(page,rec);checks.extend(ri)
    steps.append({'step':'final-layout-network','dimensions':d,'essential_request_failures':rec.essential(),'events':rec.snapshot(),'status':'PASS' if not ri else 'FAIL'})
    ctx.close();return checks,steps,rec
def s3(browser):
    checks=[];workflows=[];rec=None
    for vp,size in VPS.items():
        c,steps,rec=gallery_workflow(browser,vp,size);checks.extend(f'{vp}:{x}' for x in c);workflows.append({'viewport':vp,'steps':steps})
    add_scenario('CURRENT_MAIN_COMPONENTS_WORKFLOW','Components search, no-results, family, favorites and return context',checks,rec,{'viewport_workflows':workflows})
def row_detail(page):
    q=page.locator('section[data-pattern-region="selected_detail"]')
    return q.inner_text() if q.count() else ''
def choose_tool(page,value):
    ctrl=page.locator('input[role="combobox"][aria-label="Tool"]').first;ctrl.click();page.wait_for_timeout(80)
    opt=page.get_by_role('option',name=value,exact=True)
    if not opt.count():opt=page.locator('.q-menu .q-item').filter(has_text=re.compile('^'+re.escape(value)+'$')).first
    opt.click();page.wait_for_timeout(500)
def data_workflow(browser,vp,size):
    ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);route='/studio/pattern%3Adata_explorer';resp=visit(page,rec,route);issues=[];steps=[]
    if resp is None or resp.status!=200:issues.append(f'http-status={resp.status if resp else None}')
    if page.locator('[data-pattern-semantic="data_explorer"]').count()!=1:issues.append('data-explorer-pattern-missing')
    rows=page.locator('.ag-root[role="grid"] .ag-row[role="row"]:not(.ag-row-pinned)');initial=rows.count()
    if initial<4:issues.append(f'populated-table-too-small:{initial}')
    actual=[]
    for i in range(rows.count()):
        line=[x.strip() for x in rows.nth(i).inner_text().splitlines() if x.strip()]
        if len(line)>=2:actual.append({'id':line[0],'tool':line[1]})
    chosen=next((r for r in actual if r['tool']=='ETCH-03'),None)
    if not chosen:issues.append('no-ETCH-03-record')
    else:
        rows.filter(has_text=chosen['id']).first.click();page.wait_for_timeout(320);detail=row_detail(page)
        ok=chosen['id'] in detail
        if not ok:issues.append(f'selected-record-detail-mismatch:{chosen["id"]}:{detail[:350]}')
        steps.append({'step':'select-row','selected_id':chosen['id'],'tool':chosen['tool'],'detail':detail[:700],'status':'PASS' if ok else 'FAIL'})
        screenshot(page,f's4-data-{vp}-selected.png')
        choose_tool(page,'ETCH-03');rows=page.locator('.ag-root[role="grid"] .ag-row[role="row"]:not(.ag-row-pinned)');detail=row_detail(page)
        preserved=rows.filter(has_text=chosen['id']).count()==1 and chosen['id'] in detail
        if not preserved:issues.append(f'filter-preserving-selected-row-failed:{detail[:350]}')
        steps.append({'step':'filter-preserves-row','filter':'ETCH-03','detail':detail[:700],'visible_count':rows.count(),'status':'PASS' if preserved else 'FAIL'})
        choose_tool(page,'ETCH-07');rows=page.locator('.ag-root[role="grid"] .ag-row[role="row"]:not(.ag-row-pinned)');detail=row_detail(page)
        selected_any=rows.evaluate_all('(rs)=>rs.some(r=>r.classList.contains("ag-row-selected")||r.getAttribute("aria-selected")==="true")')
        cleared='No lot selected' in detail and not selected_any and chosen['id'] not in detail
        if not cleared:issues.append(f'removed-selected-row-not-cleared:{detail[:350]}:selected={selected_any}')
        steps.append({'step':'filter-removes-row','filter':'ETCH-07','detail':detail[:700],'any_row_selected':selected_any,'status':'PASS' if cleared else 'FAIL'})
        screenshot(page,f's4-data-{vp}-cleared.png')
        choose_tool(page,'All tools');rows=page.locator('.ag-root[role="grid"] .ag-row[role="row"]:not(.ag-row-pinned)');detail=row_detail(page)
        restored=rows.count()==initial and 'No lot selected' in detail
        if not restored:issues.append(f'clear-filter-recovery-failed:{rows.count()}/{initial}:{detail[:250]}')
        steps.append({'step':'clear-filters','visible_count':rows.count(),'initial_count':initial,'detail':detail[:500],'status':'PASS' if restored else 'FAIL'})
    search=page.locator('input[aria-label="Search lots"]').first
    if not visible(search):issues.append('search-lots-not-visible')
    else:
        search.focus();focus_path=[]
        for _ in range(4):
            page.keyboard.press('Tab');page.wait_for_timeout(60)
            f=page.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {tag:e.tagName,role:e.getAttribute('role'),label:e.getAttribute('aria-label'),className:String(e.className||''),focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,outlineWidth:s.outlineWidth,shadow:s.boxShadow,centerUnobscured:!!h&&(h===e||e.contains(h)),rect:{x:r.x,y:r.y,width:r.width,height:r.height}}}''')
            focus_path.append(f)
            if f['label']=='Tool':break
        FOCUS.append({'step':'search-filter-tab-path','viewport':vp,'focus_path':focus_path})
        if not focus_path or focus_path[-1]['label']!='Tool':issues.append(f'keyboard-search-to-filter-failed:{focus_path}')
        cell=page.locator('.ag-root [role="gridcell"]').first
        if cell.count():
            cell.focus();page.keyboard.press('ArrowDown');page.wait_for_timeout(100)
            g=page.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {role:e.getAttribute('role'),className:String(e.className||''),focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,outlineWidth:s.outlineWidth,shadow:s.boxShadow,rect:{x:r.x,y:r.y,width:r.width,height:r.height},centerUnobscured:!!h&&(h===e||e.contains(h))}}''')
            g['step']='table-keyboard-focus';FOCUS.append(g)
            ok=g['role']=='gridcell' and g['centerUnobscured'] and g['rect']['width']>0
            if not ok:issues.append(f'table-keyboard-focus-not-visible-or-obscured:{g}')
            steps.append({'step':'keyboard-focus-path','filter_focus':f,'table_focus':g,'status':'PASS' if ok else 'FAIL'})
    ri,d=route_checks(page,rec);issues.extend(ri);steps.append({'step':'layout-network','dimensions':d,'essential_request_failures':rec.essential(),'events':rec.snapshot(),'status':'PASS' if not ri else 'FAIL'})
    screenshot(page,f's4-data-{vp}-final.png');ctx.close();return issues,steps,rec
def s4(browser):
    checks=[];flows=[];rec=None
    for vp,size in VPS.items():
        c,steps,rec=data_workflow(browser,vp,size);checks.extend(f'{vp}:{x}' for x in c);flows.append({'viewport':vp,'steps':steps})
    add_scenario('CURRENT_MAIN_DATA_EXPLORER','Populated Data Explorer selection/filter/detail and keyboard focus',checks,rec,{'viewport_workflows':flows})
def select_workflow(browser,vp,size):
    ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);route='/studio/component%3Aselect';resp=visit(page,rec,route);issues=[];steps=[]
    if resp is None or resp.status!=200:issues.append(f'http-status={resp.status if resp else None}')
    target=page.locator('input[role="combobox"][aria-label="Process area"]')
    if target.count()!=1:issues.append(f'select-target-count={target.count()}')
    else:
        before=target.evaluate('(e)=>({role:e.getAttribute("role"),name:e.getAttribute("aria-label"),expanded:e.getAttribute("aria-expanded"),tabindex:e.tabIndex})')
        if before['role']!='combobox' or before['name']!='Process area':issues.append(f'select-accessibility-name-role:{before}')
        page.evaluate('document.activeElement?.blur()')
        tab_path=[]
        for _ in range(80):
            page.keyboard.press('Tab');page.wait_for_timeout(12)
            current=page.evaluate('''()=>({tag:document.activeElement?.tagName,role:document.activeElement?.getAttribute('role'),label:document.activeElement?.getAttribute('aria-label')})''')
            tab_path.append(current)
            if current.get('label')=='Process area':break
        reached=target.evaluate('(e)=>document.activeElement===e')
        if not reached:issues.append('keyboard-could-not-reach-governed-select')
        before['keyboard_tab_count']=len(tab_path);before['keyboard_active']=reached
        page.keyboard.press('Enter');page.wait_for_timeout(180)
        opts=page.locator('[role="option"]:visible');listbox=page.locator('[role="listbox"]:visible').last;opened=opts.count()>0 and listbox.count()>0
        if not opened:issues.append('keyboard-open-listbox-failed')
        if opened:
            pop=page.locator('.q-menu:visible').last
            if not pop.count():pop=listbox
            metrics=pop.evaluate('''e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height},role:e.getAttribute('role'),name:e.getAttribute('aria-label'),display:s.display,visibility:s.visibility,viewport:{width:innerWidth,height:innerHeight}}}''')
            rr=metrics['rect'];vw=metrics['viewport']['width'];vh=metrics['viewport']['height'];inside=rr['x']>=0 and rr['y']>=0 and rr['right']<=vw+1 and rr['bottom']<=vh+1
            op=target.evaluate('''e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}}''')
            overlap=rr['x']<op['right'] and rr['right']>op['x'] and rr['y']<op['bottom'] and rr['bottom']>op['y']
            focus=target.evaluate('''e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e),w=e.closest(".q-field"),ws=w&&getComputedStyle(w),wr=w?.getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);const outline=ws?.outlineStyle!=="none"&&parseFloat(ws?.outlineWidth||"0")>=2;const shadow=!!ws&&ws.boxShadow!=="none";return {active:document.activeElement===e,focusVisible:e.matches(":focus-visible"),outline:s.outlineStyle,outlineWidth:s.outlineWidth,shadow:s.boxShadow,wrapperOutline:ws?.outline||"",wrapperShadow:ws?.boxShadow||"",wrapperRect:wr?.toJSON()||null,indicatorVisible:outline||shadow,centerUnobscured:!!h&&(h===e||e.contains(h))}}''')
            if not inside:issues.append(f'popup-outside-viewport:{metrics}')
            if overlap:issues.append('popup-covers-select-opener')
            if not focus['active'] or not focus['focusVisible'] or not focus['indicatorVisible'] or not focus['centerUnobscured']:issues.append(f'focus-not-visible-or-obscured:{focus}')
            expanded=target.get_attribute('aria-expanded')
            if expanded!='true':issues.append(f'combobox-expanded-state-not-true:{expanded}')
            steps.append({'step':'open-overlay','select':before,'expanded':expanded,'options':opts.count(),'popup':metrics,'inside_viewport':inside,'covers_opener':overlap,'focus':focus})
            screenshot(page,f's5-select-{vp}-open.png')
            initial_focus=page.locator('.q-menu .q-manual-focusable--focused').first.inner_text() if page.locator('.q-menu .q-manual-focusable--focused').count() else None
            if not initial_focus:
                initial_focus=page.locator('.q-menu .q-item--active').first.inner_text() if page.locator('.q-menu .q-item--active').count() else None
            page.keyboard.press('ArrowUp');page.wait_for_timeout(100)
            active=page.evaluate('''()=>({role:document.activeElement?.getAttribute("role"),name:document.activeElement?.getAttribute("aria-label"),activeDescendant:document.activeElement?.getAttribute("aria-activedescendant"),activeOption:[...document.querySelectorAll('.q-menu .q-item')].find(e=>e.classList.contains('q-manual-focusable--focused'))?.innerText||null,expanded:document.activeElement?.getAttribute("aria-expanded")})''')
            navigated=bool(active['activeDescendant'] or active['activeOption']) and (not initial_focus or active['activeOption']!=initial_focus)
            if not navigated:issues.append(f'keyboard-arrow-navigation-not-observed:{active}:initial={initial_focus}')
            page.keyboard.press('Enter');page.wait_for_timeout(150)
            selected_value=target.input_value();selected=bool(navigated and selected_value==active['activeOption'])
            if not selected:issues.append(f'keyboard-option-selection-not-observed:{selected_value}:{active}')
            page.keyboard.press('Enter');page.wait_for_timeout(120)
            if page.locator('[role="listbox"]:visible').count()==0:page.keyboard.press('Enter');page.wait_for_timeout(120)
            page.keyboard.press('Escape');page.wait_for_timeout(200)
            closed=page.locator('[role="listbox"]:visible').count()==0 and page.locator('.q-menu:visible').count()==0
            returned=target.evaluate('(e)=>document.activeElement===e')
            if not closed:issues.append('escape-does-not-close-popup')
            if not returned:issues.append('escape-focus-does-not-return-to-opener')
            steps.append({'step':'keyboard-navigation-selection-and-escape','initial_focus':initial_focus,'active_after_arrow':active,'selected_value':selected_value,'keyboard_selection':selected,'popup_closed':closed,'focus_returned':returned})
            if closed:
                page.keyboard.press('Tab');page.wait_for_timeout(100);no_trap=page.evaluate('()=>document.activeElement!==document.body&&document.activeElement!==document.documentElement')
                if not no_trap:issues.append('focus-trapped-after-popup-close')
                steps.append({'step':'tab-after-close','no_focus_trap':no_trap,'active':page.evaluate('''()=>({tag:document.activeElement?.tagName,role:document.activeElement?.getAttribute("role"),label:document.activeElement?.getAttribute("aria-label")})''')})
    ri,d=route_checks(page,rec);issues.extend(ri);steps.append({'step':'layout-network','dimensions':d,'essential_request_failures':rec.essential(),'status':'PASS' if not ri else 'FAIL'})
    ctx.close();return issues,steps,rec
def s5(browser):
    checks=[];flows=[];rec=None
    for vp,size in VPS.items():
        c,steps,rec=select_workflow(browser,vp,size);checks.extend(f'{vp}:{x}' for x in c);flows.append({'viewport':vp,'steps':steps})
    add_scenario('CURRENT_MAIN_SELECT_OVERLAY','Governed Select accessible overlay and keyboard focus return',checks,rec,{'viewport_workflows':flows})
def s6(browser):
    checks=[];flows=[];rec=None
    for route in ['/components','/analytics']:
        ctx=context(browser,VPS['mobile']);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,route);issues=[];steps=[]
        if resp is None or resp.status!=200:issues.append(f'http-status={resp.status if resp else None}')
        opener=page.locator('button.cui-shell-mobile-menu');count=opener.evaluate_all('(es)=>es.filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=="hidden").length')
        if count!=1:issues.append(f'visible-mobile-menu-opener-count={count}')
        elif opener.get_attribute('aria-label')!='Open navigation':issues.append(f'opener-name={opener.get_attribute("aria-label")}')
        else:
            opener.click();page.wait_for_timeout(230)
            state=page.evaluate('''()=>{const d=document.querySelector("aside.cui-mobile-nav-drawer"),l=document.querySelector(".cui-mobile-nav-layer"),b=document.querySelector("button.cui-shell-mobile-menu"),r=d?.getBoundingClientRect(),s=d&&getComputedStyle(d);return {nav:document.documentElement.dataset.mobileNav,expanded:b?.getAttribute("aria-expanded"),name:b?.getAttribute("aria-label"),layerHidden:l?.getAttribute("aria-hidden"),drawer:d?{visible:!!r&&r.width>0&&r.height>0&&s.display!=="none"&&s.visibility!=="hidden",role:d.getAttribute("role"),name:d.getAttribute("aria-label"),rect:{x:r.x,y:r.y,width:r.width,height:r.height}}:null}}''')
            ok=state['nav']=='open' and state['expanded']=='true' and state['name']=='Close navigation' and state['layerHidden']=='false' and state['drawer'] and state['drawer']['visible'] and state['drawer']['role']=='dialog' and state['drawer']['name']=='Mobile navigation'
            if not ok:issues.append(f'open-contract:{state}')
            steps.append({'step':'open','state':state,'status':'PASS' if ok else 'FAIL'});screenshot(page,f's6-shell-{route.strip("/")}-open.png')
            page.keyboard.press('Escape');page.wait_for_timeout(220)
            after=page.evaluate('''()=>{const b=document.querySelector("button.cui-shell-mobile-menu");return {nav:document.documentElement.dataset.mobileNav,expanded:b?.getAttribute("aria-expanded"),name:b?.getAttribute("aria-label"),focus:document.activeElement===b}}''')
            ok=after['nav']=='closed' and after['expanded']=='false' and after['name']=='Open navigation' and after['focus']
            if not ok:issues.append(f'escape-close-contract:{after}')
            steps.append({'step':'escape-close','state':after,'status':'PASS' if ok else 'FAIL'})
            page.locator('button.cui-shell-mobile-menu').click();page.wait_for_timeout(180)
            close=page.locator('aside.cui-mobile-nav-drawer button[aria-label="Close navigation"]');has=close.count()==1 and visible(close)
            if has:close.click();page.wait_for_timeout(230)
            after=page.evaluate('''()=>{const b=document.querySelector("button.cui-shell-mobile-menu");return {nav:document.documentElement.dataset.mobileNav,expanded:b?.getAttribute("aria-expanded"),name:b?.getAttribute("aria-label"),focus:document.activeElement===b}}''')
            ok=has and after['nav']=='closed' and after['expanded']=='false' and after['name']=='Open navigation' and after['focus']
            if not ok:issues.append(f'close-control-contract:{after}:found={has}')
            steps.append({'step':'control-close','state':after,'status':'PASS' if ok else 'FAIL'})
        ri,d=route_checks(page,rec);issues.extend(ri);steps.append({'step':'layout-network','dimensions':d,'essential_request_failures':rec.essential(),'status':'PASS' if not ri else 'FAIL'})
        checks.extend(f'{route}:{x}' for x in issues);flows.append({'route':route,'steps':steps});ctx.close()
    add_scenario('CURRENT_MAIN_MOBILE_SHELL','Mobile shell navigation open/close and focus return',checks,rec,{'route_workflows':flows})
def s7(browser):
    ctx=context(browser,VPS['desktop']);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,'/components');checks=[];steps=[]
    if resp is None or resp.status!=200:checks.append(f'http-status={resp.status if resp else None}')
    d=page.locator('details.cui-explorer-refine').first;target=d.locator('input[role="combobox"][aria-label="Family"]').first
    search=page.locator('input[data-explorer-search]').first
    if search.count()!=1:checks.append(f'primary-search-count-before-breakpoint={search.count()}')
    else:
        search.focus();page.keyboard.press('Tab');page.wait_for_timeout(80)
    focus_path=[page.evaluate('''()=>({tag:document.activeElement?.tagName,label:document.activeElement?.getAttribute("aria-label"),role:document.activeElement?.getAttribute("role")})''')]
    before=page.evaluate('''()=>({activeTag:document.activeElement?.tagName,label:document.activeElement?.getAttribute("aria-label"),inside:!!document.querySelector(".cui-explorer-refine")?.contains(document.activeElement),searches:document.querySelectorAll("input[data-explorer-search]").length})''')
    if before['label']!='Family':checks.append(f'keyboard-could-not-reach-family-before-breakpoint:{focus_path}')
    if not before['inside']:checks.append(f'desktop-focus-not-inside-refinement:{before}')
    FOCUS.append({'step':'breakpoint-before','state':before})
    page.set_viewport_size(VPS['mobile']);page.wait_for_timeout(220)
    mobile=page.evaluate('''()=>{const d=document.querySelector("details.cui-explorer-refine"),s=d?.querySelector("summary"),a=document.activeElement;return {width:innerWidth,open:d?.open,summaryVisible:!!s&&s.getClientRects().length>0&&getComputedStyle(s).display!=="none",activeInsideSummary:!!s?.contains(a),activeBody:a===document.body||a===document.documentElement,searches:document.querySelectorAll("input[data-explorer-search]").length,doc:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}}''')
    ok=not mobile['open'] and mobile['summaryVisible'] and mobile['activeInsideSummary'] and not mobile['activeBody'] and mobile['searches']==1 and mobile['doc']<=mobile['client']+1
    if not ok:checks.append(f'desktop-to-mobile-focus-contract:{mobile}')
    steps.append({'step':'desktop-to-mobile','state':mobile,'status':'PASS' if ok else 'FAIL'});screenshot(page,'s7-breakpoint-mobile.png')
    page.set_viewport_size(VPS['desktop']);page.wait_for_timeout(220)
    desk=page.evaluate('''()=>{const d=document.querySelector("details.cui-explorer-refine"),s=d?.querySelector("summary"),a=document.activeElement;return {width:innerWidth,open:d?.open,summaryVisible:!!s&&s.getClientRects().length>0&&getComputedStyle(s).display!=="none",activeInsideSummary:!!s?.contains(a),activeTag:a?.tagName,activeLabel:a?.getAttribute("aria-label"),activeBody:a===document.body||a===document.documentElement,searches:document.querySelectorAll("input[data-explorer-search]").length,doc:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}}''')
    ok=desk['open'] and not desk['activeBody'] and desk['searches']==1 and desk['doc']<=desk['client']+1
    if not ok:checks.append(f'mobile-to-desktop-focus-contract:{desk}')
    recovery_path=[]
    if desk['activeBody']:
        for _ in range(100):
            page.keyboard.press('Tab');page.wait_for_timeout(12)
            f=page.evaluate('''()=>({tag:document.activeElement?.tagName,label:document.activeElement?.getAttribute("aria-label"),role:document.activeElement?.getAttribute("role"),body:document.activeElement===document.body})''');recovery_path.append(f)
            if f.get('label')=='Family':break
    active=page.evaluate('''()=>({tag:document.activeElement?.tagName,label:document.activeElement?.getAttribute("aria-label"),body:document.activeElement===document.body})''')
    if desk['activeBody'] and (not recovery_path or recovery_path[-1].get('label')!='Family'):checks.append(f'keyboard-focus-recovery-path-incoherent:{recovery_path}')
    steps.append({'step':'mobile-to-desktop','state':desk,'operability_probe':active,'recovery_path':recovery_path,'status':'PASS' if ok else 'FAIL'});FOCUS.append({'step':'breakpoint-after','state':desk,'operability_probe':active})
    d=dimensions(page)
    if max(d['docWidth']-d['docClient'],d['bodyWidth']-d['docClient'])>1:checks.append(f'final-overflow:{d}')
    screenshot(page,'s7-breakpoint-desktop-return.png')
    add_scenario('CURRENT_MAIN_BREAKPOINT_FOCUS_RECOVERY','Same-context desktop/mobile breakpoint focus recovery',checks,rec,{'steps':steps,'final_dimensions':d});ctx.close()
def set_theme(page,theme):
    page.goto(BASE+'/settings',wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(450)
    label={'system_dark':'System'}.get(theme,theme.title())
    page.get_by_role('radio',name=label,exact=True).click(timeout=10000);page.wait_for_timeout(150)
    page.get_by_role('radio',name='Reduced',exact=True).click(timeout=10000);page.wait_for_timeout(250)
    resolved='dark' if theme in {'dark','system_dark'} else 'light'
    page.wait_for_function('(v)=>document.documentElement.dataset.theme===v',arg=resolved,timeout=6000)
    return page.evaluate('''()=>({theme:document.documentElement.dataset.theme,requested:localStorage.getItem("cui_lab_theme"),motion:document.documentElement.dataset.motion,forceReduced:document.documentElement.classList.contains("cui-force-reduced-motion"),prefersReduced:matchMedia("(prefers-reduced-motion: reduce)").matches,prefersDark:matchMedia("(prefers-color-scheme: dark)").matches})''')
def theme_state(page,route):
    return page.evaluate('''route=>{const pick=s=>{const e=document.querySelector(s);if(!e)return null;const c=getComputedStyle(e),r=e.getBoundingClientRect();return {className:String(e.className||"").slice(0,120),text:(e.innerText||"").slice(0,200),background:c.backgroundColor,color:c.color,rect:{x:r.x,y:r.y,width:r.width,height:r.height}}};const root=getComputedStyle(document.documentElement),body=getComputedStyle(document.body);return {route,theme:document.documentElement.dataset.theme,motion:document.documentElement.dataset.motion,bodyBackground:body.backgroundColor,bodyColor:body.color,page:pick(".cui-page"),surfaceToken:root.getPropertyValue("--cui-surface").trim(),textToken:root.getPropertyValue("--cui-text-primary").trim(),captions:[...document.querySelectorAll("[data-visual-contract],.cui-workbench-preview-caption")].map(e=>e.innerText).filter(Boolean).slice(0,8),semantics:[...document.querySelectorAll("[data-visual-semantic]")].map(e=>({value:e.getAttribute("data-visual-semantic"),text:(e.innerText||"").slice(0,160)})),charts:[...document.querySelectorAll(".cui-chart-panel")].map(e=>{const c=getComputedStyle(e),r=e.getBoundingClientRect();return {background:c.backgroundColor,color:c.color,rect:{x:r.x,y:r.y,width:r.width,height:r.height},text:(e.innerText||"").slice(0,260),canvas:[...e.querySelectorAll("canvas")].map(x=>({width:x.width,height:x.height}))}}),chart_contracts:[...document.querySelectorAll(".cui-chart-panel")].map(e=>{const by=e.getAttribute("aria-labelledby"),des=e.getAttribute("aria-describedby");return {role:e.getAttribute("role"),title_text:document.getElementById(by)?.innerText||"",description_text:document.getElementById(des)?.innerText||"",axis_x:e.getAttribute("data-chart-x")||"",axis_y:e.getAttribute("data-chart-y")||"",theme:e.getAttribute("data-chart-theme")||"",series_count:Number(e.getAttribute("data-series-count")||0),series_labels:e.getAttribute("data-series-labels")||""}}),dimensions:{doc:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,body:document.body.scrollWidth}}}''',route)
def white_fraction(path,rect):
    try:
        from PIL import Image
        im=Image.open(path).convert('RGB');x0=max(0,int(rect['x']));y0=max(0,int(rect['y']));x1=min(im.width,int(rect['x']+rect['width']));y1=min(im.height,int(rect['y']+rect['height']))
        if x1<=x0 or y1<=y0:return None
        crop=im.crop((x0,y0,x1,y1));px=list(crop.get_flattened_data() if hasattr(crop,'get_flattened_data') else crop.getdata())
        return {'pixels':len(px),'near_white_fraction':round(sum(1 for r,g,b in px if r>238 and g>238 and b>238)/max(1,len(px)),5),'mean_rgb':[round(sum(c[i] for c in px)/len(px),2) for i in range(3)]}
    except Exception as e:return {'error':str(e)}
def s8(browser):
    checks=[];states=[];rec=None
    for theme in ['light','dark','system_dark']:
        ctx=context(browser,VPS['desktop'],'dark' if theme=='system_dark' else 'light');page=ctx.new_page();rec=Recorder(page)
        try:pref=set_theme(page,theme)
        except Exception as e:
            checks.append(f'{theme}:theme-motion-control-failure:{str(e)[:250]}');states.append({'theme':theme,'status':'FAIL','reason':str(e)[:250]});ctx.close();continue
        wanted='dark' if theme in {'dark','system_dark'} else 'light';pok=pref['theme']==wanted and pref['motion']=='reduced' and pref['forceReduced'] and pref['prefersReduced'] and (theme!='system_dark' or pref['prefersDark'])
        if not pok:checks.append(f'{theme}:theme-motion-state:{pref}')
        for route in ['/analytics/spc_i_mr','/analytics/capability_histogram','/components','/patterns']:
            rec.reset();resp=page.goto(BASE+route,wait_until='domcontentloaded',timeout=45000);page.wait_for_timeout(800);state=theme_state(page,route);local=[]
            if resp is None or resp.status!=200:local.append(f'http-status={resp.status if resp else None}')
            if state['theme']!=wanted:local.append(f'resolved-theme={state["theme"]},expected={wanted}')
            if state['motion']!='reduced':local.append(f'motion-state={state["motion"]}')
            if max(state['dimensions']['doc']-state['dimensions']['client'],state['dimensions']['body']-state['dimensions']['client'])>1:local.append('route-level-overflow')
            path=screenshot(page,f's8-{theme}-{route.strip("/").replace("/","-")}.png')
            if route.startswith('/analytics/'):
                if not state['semantics']:local.append('chart-semantic-contract-missing')
                if not state['charts']:local.append('chart-panel-missing')
                figures=state['chart_contracts']
                expected_figures=2 if route.endswith('spc_i_mr') else 1
                if len(figures)<expected_figures:local.append(f'chart-figure-count={len(figures)},expected-at-least={expected_figures}')
                for figure in figures:
                    if figure['role']!='figure' or not figure['title_text'] or not figure['description_text'] or not figure['axis_x'] or not figure['axis_y'] or figure['theme']!=wanted or not figure['series_count']:
                        local.append(f'incomplete-chart-semantic-contract:{figure}')
                if wanted=='dark' and state['charts']:
                    chart=page.locator('.cui-chart-panel').first;chart.scroll_into_view_if_needed();page.wait_for_timeout(160)
                    rect=chart.evaluate('''e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}}''')
                    path=screenshot(page,f's8-{theme}-{route.strip("/").replace("/","-")}-canvas.png')
                    pixel=white_fraction(path,rect);state['dark_chart_pixel_check']=pixel
                    if pixel and pixel.get('near_white_fraction',0)>0.30:local.append(f'white-or-mixed-dark-chart-canvas:{pixel}')
                if route.endswith('spc_i_mr'):
                    caption=' '.join(state['captions']).casefold()
                    if not any(x in caption for x in ('sample order','measurement','moving range')):local.append('spc-axis-semantics-caption-missing')
                    vals=' '.join(x['value'].casefold() for x in state['semantics'])
                    if 'individual' not in vals or 'moving-range' not in vals:local.append('spc-individual-moving-range-semantics-missing')
                    if not any(c['axis_x']=='Sample order' and c['axis_y']=='Measurement' for c in figures):local.append('spc-individual-axis-contract-missing')
                    if not any(c['axis_x']=='Adjacent samples' and c['axis_y']=='Absolute difference' for c in figures):local.append('spc-moving-range-axis-contract-missing')
                if route.endswith('capability_histogram'):
                    cap=' '.join(state['captions']).casefold()
                    if 'measurement bins' not in cap or 'count' not in cap:local.append('histogram-axis-semantics-caption-missing')
            elif route=='/patterns':
                if page.locator('[data-unified-pattern-explorer]').count()!=1 or page.locator('[data-pattern-semantic]').count()<1:local.append('pattern-live-surface-missing')
            elif page.locator('input[data-explorer-search]').count()!=1:local.append('components-gallery-surface-missing')
            if rec.essential():local.append('essential-request-failure')
            if rec.events['page_errors']:local.append('page-error')
            if rec.events['console_errors']:local.append('console-error')
            checks.extend(f'{theme}:{route}:{x}' for x in local)
            states.append({'theme':theme,'route':route,'preference_state':pref,'http_status':resp.status if resp else None,'computed':state,'screenshot':'machine-browser/screenshots/'+path.name,'essential_request_failures':rec.essential(),'browser_events':rec.snapshot(),'status':'PASS' if not local and pok else 'FAIL','issues':local})
        ctx.close()
    add_scenario('CURRENT_MAIN_THEME_MOTION_SMOKE','Fresh Light/Dark/System-dark and reduced-motion browser smoke',checks,rec,{'route_theme_states':states})
def button_snapshot(page):
    return page.evaluate('''()=>{const name=e=>{const ids=(e.getAttribute("aria-labelledby")||"").trim().split(/\\s+/).filter(Boolean),labelled=ids.map(i=>document.getElementById(i)?.innerText||"").join(" ").trim();return(e.getAttribute("aria-label")||labelled||e.innerText||e.getAttribute("title")||e.querySelector("img[alt]")?.getAttribute("alt")||"").replace(/\\s+/g," ").trim()};return[...document.querySelectorAll("button,[role=button]")].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=="none"&&s.visibility!=="hidden"}).map(e=>({name:name(e),tag:e.tagName,role:e.getAttribute("role"),className:String(e.className||"").slice(0,150)}))}''')
def s9(browser):
    checks=[];samples=[];rec=None
    routes=['/components','/analytics','/recipes','/patterns','/studio/pattern%3Adata_explorer','/studio/component%3Aselect']
    for route in routes:
        for vp,size in VPS.items():
            ctx=context(browser,size);page=ctx.new_page();rec=Recorder(page);resp=visit(page,rec,route);local=[]
            if resp is None or resp.status!=200:local.append(f'http-status={resp.status if resp else None}')
            buttons=button_snapshot(page);unnamed=[b for b in buttons if not b['name']]
            if unnamed:local.append(f'visible-unnamed-button-actions={len(unnamed)}')
            if route in ['/components','/analytics','/recipes']:
                if page.locator('input[data-explorer-search]').count()!=1:local.append('primary-search-authority-count')
                if page.locator('details.cui-explorer-refine').count()!=1:local.append('refinement-authority-count')
            if route=='/patterns' and (page.locator('input[data-explorer-search]').count()!=0 or page.locator('details.cui-explorer-refine').count()!=0):local.append('patterns-distinct-contract')
            if vp=='mobile' and route in ['/components','/analytics','/recipes']:
                n=page.locator('button.cui-shell-mobile-menu').evaluate_all('(es)=>es.filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=="hidden").length')
                if n!=1:local.append(f'visible-mobile-opener-count={n}')
            ri,d=route_checks(page,rec);local.extend(ri);checks.extend(f'{route}@{vp}:{x}' for x in local)
            samples.append({'route':route,'viewport':vp,'http_status':resp.status if resp else None,'button_count':len(buttons),'unnamed_buttons':unnamed,'buttons':buttons,'dimensions':d,'issues':local,'events':rec.snapshot(),'essential_request_failures':rec.essential()})
            screenshot(page,f's9-a11y-{route.strip("/").replace("/","-").replace("%3A","-")}-{vp}.png');ctx.close()
    add_scenario('CURRENT_MAIN_BUTTON_ACCESSIBILITY_ENVELOPE','Visible governed button names and route/viewport envelope',checks,rec,{'route_viewports':samples})
def main():
    started=datetime.now(timezone.utc).isoformat()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=CHROME,headless=True,args=['--no-sandbox'])
        version=browser.version
        for fn in [s1,s2,s3,s4,s5,s6,s7,s8,s9]:fn(browser)
        browser.close()
    failed=[x for x in SCENARIOS if x['status']=='FAIL']
    aggregate='CURRENT_MAIN_MACHINE_BROWSER_PRODUCT_FAIL' if failed else 'CURRENT_MAIN_MACHINE_BROWSER_PASS_AWAITING_HUMAN_AND_AUTHENTIC_ZOOM'
    env={'browser':{'product':'Google Chrome','executable':CHROME,'version':version,'automation':'Playwright Python sync API','headless':True},'viewports':{'desktop':'1440x900','mobile':'390x844','device_scale_factor':1,'reduced_motion':'reduce'},'runtime':{'python_executable':SERVER['python'],'python_version':'3.11.7','nicegui':'3.15.0','nicegui_base_framework':'3.0.0a8','build_id':'NGB-20260907-G2.6','server_pid':SERVER['pid'],'command':SERVER['command'],'cwd':SERVER['cwd'],'port':SERVER['port'],'url':SERVER['url'],'source_sha':'7b126d431215e8aac038bd5935d39d118a1ea68b','source_tree':'d8b510a85f7767bb8d67dba3f0e2b1d44f8fc87b','launcher':'root run_nicegui_base.py; source/ inserted by canonical launcher','server_log':SERVER['log']},'platform':platform.platform(),'authentic_browser_chrome_zoom_200':'NOT_EXECUTED_BY_DESIGN','alternate_zoom_substitute_used':False}
    matrix={'schema_version':1,'project':'nicegui-base','change':'CHG-100','request':'stable3-browser-ui-current-main-refresh-2','fabric_job':'CF-a25508c618dbb510eb6c7d1f','source_sha':'7b126d431215e8aac038bd5935d39d118a1ea68b','source_tree':'d8b510a85f7767bb8d67dba3f0e2b1d44f8fc87b','aggregate':aggregate,'scenarios':SCENARIOS,'screenshot_count':len(SCREENSHOTS),'screenshots':SCREENSHOTS,'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat()}
    focus={'source_sha':matrix['source_sha'],'source_tree':matrix['source_tree'],'observations':FOCUS,'summary':{'focus_samples':len(FOCUS)}}
    net={'source_sha':matrix['source_sha'],'source_tree':matrix['source_tree'],'scenario_count':len(SCENARIOS),'route_samples':[x.get('route_samples',[]) for x in SCENARIOS if x.get('route_samples')],'viewport_workflows':[x.get('viewport_workflows',[]) for x in SCENARIOS if x.get('viewport_workflows')],'route_theme_states':[x.get('route_theme_states',[]) for x in SCENARIOS if x.get('route_theme_states')],'route_viewports':[x.get('route_viewports',[]) for x in SCENARIOS if x.get('route_viewports')],'summary':{'scenario_records':len(SCENARIOS),'screenshot_count':len(SCREENSHOTS)}}
    for name,payload in [('scenario-matrix.json',matrix),('browser-environment.json',env),('focus-accessibility.json',focus),('console-network.json',net)]:
        (OUT/name).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'aggregate':aggregate,'scenarios':[{'id':x['id'],'status':x['status'],'issue_count':len(x['issues'])} for x in SCENARIOS],'screenshot_count':len(SCREENSHOTS),'output':str(OUT)},indent=2))
if __name__=='__main__':main()
