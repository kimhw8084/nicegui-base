#!/usr/bin/env python3
"""Optional live-browser checks against the already-running D1 server; never modifies source."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import quote, urlparse

BUILD_ID = 'NGB-20260905-D1'


def verify_identity(base: str) -> dict:
    with urllib.request.urlopen(base+'/_nicegui_base/workbench',timeout=15) as r:
        data=json.load(r)
    if data.get('build_id')!=BUILD_ID:
        raise RuntimeError(f'This is not the updated server: {data}. Expected {BUILD_ID}.')
    return data


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8091')
    p.add_argument('--all',action='store_true',help='Check all 463 Studio routes, not only focused regressions')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    url=args.url.rstrip('/')
    parsed=urlparse(url)
    if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'}:
        p.error('This verifier is restricted to your local development server.')
    output=args.output or Path.home()/'Downloads'/('nicegui_base_D1_browser_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True,exist_ok=False)
    report={'build_id':BUILD_ID,'passed':False,'results':[],'errors':[],'scope':'all Studio entries' if args.all else 'focused Studio regression checks'}
    try:
        report['identity']=verify_identity(url)
        # Late imports keep --help usable before installing optional browser tools.
        from playwright.sync_api import sync_playwright, expect
        root=Path(__file__).absolute().parents[1]
        sys.path.insert(0,str(root/'source'))
        from nicegui_base.workbench.registry_adapters import build_registry_entries
        entries={e.key:e for e in build_registry_entries()}
        keys=list(entries) if args.all else [
            'component:split_button','component:select','component:file_upload','component:switch',
            'framework:content:property_grid','framework:content:json_viewer',
            'framework:visualizations:ChamberFingerprintMatrix','framework:tables:data_table',
            'analytics:spc_i_mr','pattern:settings','pattern:crud',
        ]
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page()
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            for key in keys:
                result={'key':key,'passed':False}
                before_errors=len(report['errors'])
                try:
                    response=page.goto(url+'/studio/'+quote(key,safe=''),wait_until='domcontentloaded',timeout=30000)
                    if response is None or response.status!=200:
                        raise AssertionError(f'HTTP {response.status if response else None}')
                    specimen=page.locator('.cui-studio-preview-frame [data-catalog-key]').first
                    expect(specimen).to_be_visible(timeout=20000)
                    if specimen.get_attribute('data-catalog-key')!=key:
                        raise AssertionError('Wrong capability rendered')
                    if page.locator('.cui-studio-preview-frame iframe').count():
                        raise AssertionError('A preview iframe is still present')
                    if page.locator('[data-preview-input-error]').count():
                        raise AssertionError(page.locator('[data-preview-input-error]').first.inner_text())
                    if key=='framework:content:property_grid':
                        expect(specimen).to_contain_text('M-001')
                    if key=='component:split_button':
                        buttons=specimen.locator('button')
                        if buttons.count()<2:raise AssertionError('Split action missing')
                        buttons.nth(1).click()
                        page.get_by_text('Export JSON',exact=True).last.click()
                        expect(page.locator('.cui-studio-event-log__events')).to_contain_text('Export JSON')
                    if key=='component:file_upload':
                        if specimen.locator('input[type="file"]').count()==0:raise AssertionError('Real file input missing')
                    if key=='component:switch':
                        before=specimen.locator('[role="checkbox"]').first
                        if before.count():
                            old=before.get_attribute('aria-checked');before.click()
                            expect(before).not_to_have_attribute('aria-checked',old or 'false')
                    if key=='framework:content:property_grid':
                        page.get_by_role('tab',name='Configure',exact=True).click()
                        # canonical TextInput exposes its editable control within the field
                        title=page.locator('.q-tab-panel').filter(has=page.get_by_text('Apply configuration',exact=True)).locator('input').first
                        title.fill('D1 verification title')
                        page.get_by_role('button',name='Apply configuration',exact=True).click()
                        expect(page.locator('[data-preview-title]')).to_have_text('D1 verification title')
                        page.get_by_role('tab',name='Code',exact=True).click()
                        expect(page.locator('.cui-studio-code')).to_contain_text('D1 verification title')
                    if len(report['errors'])!=before_errors:
                        raise AssertionError('Browser page exception recorded')
                    result['passed']=True
                except Exception as exc:
                    result['error']=f'{type(exc).__name__}: {exc}'
                if not args.all or not result['passed']:
                    name=key.replace(':','_').replace('/','_')+'.png'
                    try:
                        page.screenshot(path=str(output/name),full_page=True)
                        result['screenshot']=name
                    except Exception as exc:result['screenshot_error']=str(exc)
                report['results'].append(result)
                print(f"{'PASS' if result['passed'] else 'FAIL'} {key}",flush=True)
            browser.close()
        report['passed']=bool(report['results']) and all(r['passed'] for r in report['results']) and not report['errors']
    except Exception as exc:
        report['fatal_error']=f'{type(exc).__name__}: {exc}'
    finally:
        (output/'BROWSER_RESULT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"LIVE_BROWSER={'PASS' if report['passed'] else 'FAIL'}\nEvidence: {output}")
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
