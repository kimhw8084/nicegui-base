#!/usr/bin/env python3
"""Focused D6B browser acceptance for the Reference Explorer surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


VIEWPORTS = {'desktop': (1440, 900), 'tablet': (1024, 768), 'phone': (390, 844)}
THEMES = ('light', 'dark')
PRIMARY = (
    ('start', '/'), ('design', '/design'), ('catalog', '/catalog'), ('components', '/components'),
    ('data', '/workbench/data'), ('visualizations', '/analytics'), ('layouts', '/layouts'),
    ('patterns', '/patterns'), ('recipes', '/recipes'), ('applications', '/applications'),
    ('ai-guide', '/ai-guide'), ('diagnostics', '/quality'),
)
FULL_APPLICATIONS = (
    ('spc-control-center', '/applications/spc-control-center', 'SPC Control Center'),
    ('fdc-health-center', '/applications/fdc-health-center', 'FDC Tool Health Center'),
    ('excursion-investigation', '/applications/excursion-investigation', 'Excursion Investigation'),
)


def _geometry(page) -> dict[str, object]:
    return page.evaluate("""() => {
      const root=document.documentElement;
      const main=document.querySelector('main,[role="main"]');
      return {viewport:innerWidth, scrollWidth:Math.max(root.scrollWidth, document.body?.scrollWidth||0),
        overflow:Math.max(root.scrollWidth, document.body?.scrollWidth||0)>innerWidth+1,
        mainWidth:main?.getBoundingClientRect().width ?? null,
        focusable:!!document.activeElement && document.activeElement!==document.body};
    }""")


def _contact_sheet(paths: list[Path], target: Path) -> None:
    if not paths:
        return
    cells = []
    for path in paths:
        image = Image.open(path).convert('RGB')
        image.thumbnail((360, 230))
        cells.append((path, image.copy()))
    columns, cell_w, cell_h = 3, 380, 270
    sheet = Image.new('RGB', (columns * cell_w, ((len(cells) + columns - 1) // columns) * cell_h), '#f4f5f7')
    draw = ImageDraw.Draw(sheet)
    for index, (path, image) in enumerate(cells):
        x = index % columns * cell_w + 10
        y = index // columns * cell_h + 28
        sheet.paste(image, (x, y))
        draw.text((x, y - 22), path.stem[:54], fill='#111827')
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--result-name', default='D6B_BROWSER_RESULT.json')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    overflow: list[dict[str, object]] = []
    screenshots: list[Path] = []
    checks: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport_name, (width, height) in VIEWPORTS.items():
            for theme in THEMES:
                context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                context.add_init_script(f"localStorage.setItem('nicegui_base_theme', {theme!r})")
                page = context.new_page()
                page.on('pageerror', lambda exc, viewport=viewport_name, theme=theme: errors.append({'viewport': viewport, 'theme': theme, 'error': str(exc)}))
                page.on('console', lambda message, viewport=viewport_name, theme=theme: console_errors.append({'viewport': viewport, 'theme': theme, 'text': message.text}) if message.type == 'error' else None)
                try:
                    for name, route in PRIMARY:
                        response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
                        page.wait_for_timeout(180)
                        if response is None or response.status != 200:
                            raise AssertionError(f'{route} returned {response.status if response else None}')
                        geometry = _geometry(page)
                        if geometry['overflow']:
                            overflow.append({'viewport': viewport_name, 'theme': theme, 'route': route, 'geometry': geometry})
                        if name == 'start':
                            nav_text = page.locator('nav').filter(has_text='Start Here').first.inner_text()
                            expected = ('Start Here', 'Design System', 'Components', 'Data & Tables', 'Visualizations', 'Layouts', 'Application Patterns', 'Semiconductor Recipes', 'Full Applications', 'AI Development Guide', 'Diagnostics')
                            missing = [label for label in expected if label not in nav_text]
                            if missing or 'Build' in nav_text:
                                raise AssertionError(f'primary navigation mismatch: missing={missing}; build={"Build" in nav_text}')
                        if name == 'data' and 'example data playground' not in page.locator('body').inner_text().casefold():
                            raise AssertionError('example-data playground label missing')
                        if name == 'design':
                            body = page.locator('body').inner_text()
                            if 'Design System Authority' not in body or page.locator('[data-design-token-family]').count() < 12:
                                raise AssertionError('complete live Design System reference missing')
                            for label in ('Desktop', 'Tablet', 'Phone', 'Comfortable', 'Compact', 'Dense', 'Ready', 'Blocked'):
                                if label not in body:
                                    raise AssertionError(f'Design System example missing: {label}')
                        if name == 'components' and 'Components' not in page.locator('body').inner_text():
                            raise AssertionError('component reference page missing')
                        if name == 'catalog':
                            body = page.locator('body').inner_text()
                            for label in ('Intent / problem', 'Required data', 'Domain', 'Related capability'):
                                if label not in body:
                                    raise AssertionError(f'catalog contract filter missing: {label}')
                            search_input = page.locator('input[placeholder*="Name, tag"]')
                            if not search_input.count():
                                raise AssertionError('contract-aware catalog search input missing')
                            search_input.first.fill('monitor equipment health')
                            page.wait_for_timeout(260)
                            if 'FdcToolHealth' not in page.locator('body').inner_text():
                                raise AssertionError('intent search did not return the canonical tool-health reference')
                            search_input.first.fill('')
                        shot = output / f'{name}_{viewport_name}_{theme}.png'
                        page.screenshot(path=str(shot), full_page=False)
                        screenshots.append(shot)
                        checks.append({'route': route, 'viewport': viewport_name, 'theme': theme, 'passed': True, 'geometry': geometry})
                    for app_name, app_route, app_title in FULL_APPLICATIONS:
                        response = page.goto(args.url.rstrip('/') + app_route, wait_until='domcontentloaded', timeout=45000)
                        page.wait_for_timeout(220)
                        body = page.locator('body').inner_text()
                        if response is None or response.status != 200 or app_title not in body:
                            raise AssertionError(f'{app_route} did not render its full application')
                        for required_text in ('Search records', 'Primary analytical view', 'Supporting records', 'Open selected detail', 'Caveats'):
                            if required_text not in body:
                                raise AssertionError(f'{app_route} missing composition surface: {required_text}')
                        geometry = _geometry(page)
                        if geometry['overflow']:
                            overflow.append({'viewport': viewport_name, 'theme': theme, 'route': app_route, 'geometry': geometry})
                        shot = output / f'{app_name}_{viewport_name}_{theme}.png'
                        page.screenshot(path=str(shot), full_page=False)
                        screenshots.append(shot)
                        checks.append({'route': app_route, 'viewport': viewport_name, 'theme': theme, 'passed': True, 'geometry': geometry})
                    compatibility = page.goto(args.url.rstrip('/') + '/build', wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(120)
                    if compatibility is None or compatibility.status != 200 or 'Compatibility authoring surface' not in page.locator('body').inner_text():
                        raise AssertionError('legacy Builder compatibility route is not explicit')
                    if 'Use this pattern in Builder' in page.locator('body').inner_text():
                        raise AssertionError('reference route exposes Builder handoff')
                    page.goto(args.url.rstrip('/') + '/studio/framework%3Avisualizations%3ALineChart', wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(220)
                    body = page.locator('body').inner_text()
                    if 'Reference session · example data stays on this page' not in body or 'Send data and configuration to Builder' in body:
                        raise AssertionError('Studio is still exposing project-authoring controls')
                    if 'Reference contract · variants, states, data, and production guidance' not in body:
                        raise AssertionError('Studio reference contract is not exposed')
                    page.goto(args.url.rstrip('/') + '/studio/framework%3Aanalysis%3Aanalysis_context', wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(180)
                    if 'Explicit nonvisual variant' not in page.locator('body').inner_text() or 'No live visual required' not in page.locator('body').inner_text():
                        raise AssertionError('nonvisual catalog contract is not explicit')
                except Exception as exc:
                    errors.append({'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                    fail = output / f'FAIL_{viewport_name}_{theme}.png'
                    page.screenshot(path=str(fail), full_page=False)
                    screenshots.append(fail)
                finally:
                    context.close()
        browser.close()

    result = {
        'status': 'PASS' if not errors and not console_errors and not overflow else 'FAIL',
        'browser_backend': 'local pinned Playwright Chromium; in-app browser connector unavailable',
        'viewports': list(VIEWPORTS), 'themes': list(THEMES),
        'checks': checks, 'errors': errors, 'console_errors': console_errors, 'overflow': overflow,
        'screenshots': [str(path) for path in screenshots], 'contact_sheet': str(output / 'contact_sheet.png'),
    }
    _contact_sheet(screenshots, output / 'contact_sheet.png')
    (output / args.result_name).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
