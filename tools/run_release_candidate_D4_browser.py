#!/usr/bin/env python3
"""Browser/visual acceptance for already-running installed D4 candidate apps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


CANDIDATE_ID = 'NGB-20260905-D4'
VIEWPORTS = {'desktop': (1440, 900), 'tablet': (1024, 768), 'phone': (390, 844)}
THEMES = ('light', 'dark')
WORKBENCH_SURFACES = {
    'overview': '/',
    'catalog': '/catalog',
    'studio': '/studio/framework%3Avisualizations%3ALineChart',
    'data': '/workbench/data',
    'builder': '/build',
    'settings': '/patterns/settings',
}


def _theme(page, value: str) -> None:
    page.emulate_media(color_scheme=value)
    page.evaluate("value => { document.documentElement.dataset.theme=value; document.documentElement.style.colorScheme=value; }", value)


def _chart_values(page) -> list[float]:
    return page.evaluate("""() => {
      const roots=[...document.querySelectorAll('.cui-chart-canvas')];
      for(const root of roots){
        const nodes=[root,...root.querySelectorAll('*')];
        const niceguiElement=root && typeof getElement === 'function' ? getElement(root.id?.slice(1)) : null;
        const vueElement=nodes.map(node=>node.__vueParentComponent?.proxy).find(proxy=>proxy?.chart?.getOption);
        const dom=nodes.find(n=>n.getAttribute&&n.getAttribute('_echarts_instance_'));
        const chart=vueElement?.chart || niceguiElement?.chart || (dom&&window.echarts?.getInstanceByDom(dom));
        const series=chart?.getOption?.().series||[];
        const values=[];
        for(const item of series){ for(const point of (item.data||[])){ const value=Array.isArray(point)?point[1]:typeof point==='object'?point.value:point; if(typeof value==='number') values.push(value); } }
        if(values.length) return values;
      }
      return [];
    }""")


def _geometry(page) -> dict[str, Any]:
    return page.evaluate("""() => {
      const main=document.querySelector('main,[role="main"]');
      return {viewport:innerWidth, scrollWidth:Math.max(document.documentElement.scrollWidth,document.body?.scrollWidth||0),
        overflow:Math.max(document.documentElement.scrollWidth,document.body?.scrollWidth||0)>innerWidth+1,
        main:main ? {width:main.getBoundingClientRect().width,height:main.getBoundingClientRect().height} : null,
        focus:!!document.activeElement && document.activeElement!==document.body};
    }""")


def _contact_sheet(paths: list[Path], target: Path) -> None:
    if not paths:
        return
    thumbnails = []
    for path in paths:
        image = Image.open(path).convert('RGB')
        image.thumbnail((360, 240))
        thumbnails.append((path, image.copy()))
    columns = 3
    cell_w, cell_h = 380, 280
    rows = (len(thumbnails) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * cell_w, rows * cell_h), '#f4f5f7')
    draw = ImageDraw.Draw(sheet)
    for index, (path, image) in enumerate(thumbnails):
        x = index % columns * cell_w + 10
        y = index // columns * cell_h + 24
        sheet.paste(image, (x, y))
        draw.text((x, 6 + index // columns * cell_h), path.stem[:54], fill='#111827')
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workbench', default='http://127.0.0.1:18091')
    parser.add_argument('--studio', default='http://127.0.0.1:18092')
    parser.add_argument('--builder', default='http://127.0.0.1:18093')
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ngb_d4_rc_evidence/browser'))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []
    page_errors: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    overflow: list[dict[str, Any]] = []
    surfaces: set[str] = set()
    outcomes: dict[str, Any] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.on('pageerror', lambda exc: page_errors.append({'url': page.url, 'error': str(exc)}))
        page.on('console', lambda message: console_errors.append({'url': page.url, 'type': message.type, 'text': message.text}) if message.type == 'error' else None)

        for viewport_name, (width, height) in VIEWPORTS.items():
            page.set_viewport_size({'width': width, 'height': height})
            for theme in THEMES:
                for surface, route in WORKBENCH_SURFACES.items():
                    page.goto(args.workbench.rstrip('/') + route, wait_until='networkidle', timeout=20000)
                    _theme(page, theme)
                    page.wait_for_timeout(120)
                    surfaces.add(surface)
                    geometry = _geometry(page)
                    if geometry['overflow']:
                        overflow.append({'surface': surface, 'viewport': viewport_name, 'theme': theme, 'geometry': geometry})
                    if not page.locator('main,[role="main"]').count():
                        page_errors.append({'url': page.url, 'error': 'main landmark missing'})
                    if surface == 'builder':
                        body = page.locator('body').inner_text()
                        required = ('Goal', 'Recommendation', 'Data', 'Compose', 'Review', 'Generate')
                        missing = [label for label in required if label not in body]
                        if missing:
                            page_errors.append({'url': page.url, 'error': f'Builder stages missing: {missing}'})
                        outcomes['builder_stages'] = {'required': list(required), 'missing': missing}
                    if surface == 'studio':
                        count = page.locator('.cui-studio-preview-frame').count()
                        if count != 1:
                            page_errors.append({'url': page.url, 'error': f'Studio preview host count={count}'})
                        outcomes['studio_preview_host_count'] = count
                    shot = output / f'workbench_{surface}_{viewport_name}_{theme}.png'
                    page.screenshot(path=str(shot), full_page=False)
                    screenshots.append(shot)

                for generated_surface, base in (('generated_studio', args.studio), ('generated_builder', args.builder)):
                    page.goto(base, wait_until='networkidle', timeout=20000)
                    _theme(page, theme)
                    page.wait_for_timeout(160)
                    surfaces.add(generated_surface)
                    geometry = _geometry(page)
                    if geometry['overflow']:
                        overflow.append({'surface': generated_surface, 'viewport': viewport_name, 'theme': theme, 'geometry': geometry})
                    disclosure = page.locator('.cui-chart-data-disclosure summary').first
                    if disclosure.count():
                        disclosure.click()
                        page.wait_for_timeout(80)
                    body = page.locator('body').inner_text()
                    tokens = ('0.125', '3.125') if generated_surface == 'generated_studio' else ('0000', '0.125', '3.125')
                    for token in tokens:
                        if token not in body:
                            page_errors.append({'url': page.url, 'error': f'{generated_surface} missing fixture value {token}'})
                    if generated_surface == 'generated_studio':
                        values = _chart_values(page)
                        if values and (min(values) != .125 or max(values) != 3.125):
                            page_errors.append({'url': page.url, 'error': f'generated Studio chart values are not thickness: {values[:8]}'})
                        outcomes['generated_studio_chart_values'] = values
                    shot = output / f'{generated_surface}_{viewport_name}_{theme}.png'
                    page.screenshot(path=str(shot), full_page=False)
                    screenshots.append(shot)

        page.goto(args.workbench.rstrip('/') + '/build', wait_until='networkidle', timeout=20000)
        page.keyboard.press('Tab')
        if not _geometry(page)['focus']:
            page_errors.append({'url': page.url, 'error': 'keyboard focus did not move to a focusable control'})
        outcomes['keyboard_focus'] = 'PASS' if _geometry(page)['focus'] else 'FAIL'
        browser.close()

    result = {
        'candidate_id': CANDIDATE_ID,
        'status': 'PASS' if not page_errors and not console_errors and not overflow else 'FAIL',
        'browser_backend': 'local pinned Playwright Chromium (in-app browser connector unavailable)',
        'viewports': list(VIEWPORTS), 'themes': list(THEMES), 'surfaces': sorted(surfaces),
        'page_errors': page_errors, 'console_errors': console_errors, 'overflow': overflow,
        'screenshots': [str(path) for path in screenshots], 'contact_sheet': str(output / 'contact_sheet.png'),
        'outcomes': outcomes,
    }
    _contact_sheet(screenshots, output / 'contact_sheet.png')
    (output / 'BROWSER_ACCEPTANCE.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
