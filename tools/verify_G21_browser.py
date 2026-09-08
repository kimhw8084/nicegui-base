from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

BUILD_ID='NGB-20260907-G2.1'


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--url',default='http://127.0.0.1:8091')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    from playwright.sync_api import sync_playwright
    result={'build_id':BUILD_ID,'url':args.url,'checks':[],'page_errors':[],'console_errors':[],'status':'PASS'}

    def check(name, passed, detail=''):
        result['checks'].append({'name':name,'status':'PASS' if passed else 'FAIL','detail':detail})
        if not passed: result['status']='FAIL'

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for mode, viewport, scheme in (
            ('desktop-light',{'width':1440,'height':1000},'light'),
            ('desktop-dark',{'width':1440,'height':1000},'dark'),
            ('phone-light',{'width':430,'height':932},'light'),
        ):
            ctx=browser.new_context(viewport=viewport,color_scheme=scheme)
            page=ctx.new_page(); errors=[]; consoles=[]
            page.on('pageerror',lambda exc,e=errors:e.append(str(exc)))
            page.on('console',lambda msg,c=consoles:c.append(msg.text) if msg.type=='error' else None)
            resp=page.goto(args.url,wait_until='networkidle',timeout=30000)
            check(f'{mode}: root HTTP 200',bool(resp and resp.status==200),str(getattr(resp,'status',None)))
            check(f'{mode}: build identity',page.locator(f'[data-build-id="{BUILD_ID}"]').count()==1)
            if mode=='desktop-light':
                labels=[x.strip() for x in page.locator('.cui-nav-section-label').all_inner_texts()]
                check('grouped navigation',labels==['DISCOVER','FOUNDATIONS','COMPOSE','SEMICONDUCTOR','DEVELOP','SYSTEM'],str(labels))
                check('intent-first start',page.get_by_text('Choose an intent',exact=True).count()==1)
                check('authority previews',page.locator('.cui-explorer-authority-card .cui-explorer-preview__image').count()>=8)

                expected=(('/analytics',58,'analytics'),('/components',34,'components'),('/patterns',10,'patterns'),('/recipes',8,'recipes'))
                for route,count,section in expected:
                    page.goto(args.url+route,wait_until='networkidle',timeout=30000)
                    cards=page.locator('.cui-explorer-card')
                    check(f'{section}: full gallery count',cards.count()==count,f'{cards.count()} / {count}')
                    check(f'{section}: thumbnail coverage',page.locator('.cui-explorer-card .cui-explorer-preview__image').count()==count)
                    if section=='analytics':
                        search=page.locator('[data-explorer-search="analytics"]')
                        if search.count() and search.evaluate("e=>e.tagName.toLowerCase()")!='input':
                            nested=search.locator('input')
                            if nested.count(): search=nested
                        check('analytics search control',search.count()==1)
                        started=time.perf_counter(); search.fill('spc'); page.wait_for_timeout(350); elapsed=(time.perf_counter()-started)*1000
                        filtered=page.locator('.cui-explorer-card').count()
                        check('analytics search filters without detail clicks',0<filtered<count,f'{filtered} visible')
                        check('analytics perceived search under 700 ms browser budget',elapsed<700,f'{elapsed:.1f} ms')
                        first=page.locator('.cui-explorer-card').first
                        first.get_by_role('button',name='Compare',exact=True).click(); page.wait_for_timeout(120)
                        page.locator('.cui-explorer-card').nth(1).get_by_role('button',name='Compare',exact=True).click(); page.wait_for_timeout(120)
                        check('bounded inline comparison',page.locator('.cui-explorer-compare-card').count()==2)
                        page.locator('.cui-explorer-card').first.get_by_role('button',name='☆ Favorite',exact=True).click(); page.wait_for_timeout(120)
                        page.reload(wait_until='networkidle'); page.wait_for_timeout(200)
                        saved_search=page.locator('[data-explorer-search="analytics"]')
                        if saved_search.count() and saved_search.evaluate("e=>e.tagName.toLowerCase()")!='input':
                            nested=saved_search.locator('input'); saved_search=nested if nested.count() else saved_search
                        check('search state survives reload',saved_search.input_value()=='spc',saved_search.input_value())
                        check('favorite survives reload',page.get_by_role('button',name='★ Saved',exact=True).count()>=1)
                        page.screenshot(path=str(args.output/'analytics_gallery.png'),full_page=True)
                page.goto(args.url+'/applications',wait_until='networkidle')
                check('full applications gallery count',page.locator('.cui-explorer-card').count()==3)
                page.screenshot(path=str(args.output/'applications_gallery.png'),full_page=True)
            else:
                page.goto(args.url+'/components',wait_until='networkidle',timeout=30000)
                overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 2')
                check(f'{mode}: no horizontal overflow',not overflow)
                if mode=='phone-light':
                    first_y=page.locator('.cui-explorer-card').first.bounding_box()
                    check('phone content reached without filter overload',bool(first_y and first_y['y'] < 932),str(first_y))
                page.screenshot(path=str(args.output/f'components_{mode}.png'),full_page=True)
            result['page_errors'].extend(f'{mode}: {e}' for e in errors)
            result['console_errors'].extend(f'{mode}: {e}' for e in consoles)
            if errors or consoles: result['status']='FAIL'
            ctx.close()
        browser.close()
    check('zero page errors',not result['page_errors'],str(result['page_errors'][:5]))
    check('zero console errors',not result['console_errors'],str(result['console_errors'][:5]))
    (args.output/'G21_BROWSER_RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':len(result['checks']),'failures':sum(c['status']=='FAIL' for c in result['checks'])},indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
