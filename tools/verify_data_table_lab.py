#!/usr/bin/env python3
"""Browser acceptance for the single-active-lab Data & Tables reference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


CANDIDATE = 'NGB-20260907-G2.6'
LABS = ('Grid', 'Actions', 'Edit', 'Visualize', 'Import', 'Detail', 'Server', 'States')
TABLE_LABS = {'Grid', 'Actions', 'Edit', 'Visualize', 'Detail', 'Server', 'States'}


def _check_page(page, response, *, expected_lab: str) -> list[str]:
    issues: list[str] = []
    if response is None or response.status != 200:
        issues.append(f'http:{response.status if response else None}')
    identity = ' '.join(page.locator('[data-build-id]').all_text_contents())
    if CANDIDATE not in page.locator('body').inner_text() + identity:
        issues.append('missing-candidate')
    if page.locator('[data-active-lab]').get_attribute('data-active-lab') != expected_lab.lower():
        issues.append('wrong-active-lab')
    if page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 1'):
        issues.append('page-horizontal-overflow')
    table_count = page.locator('.cui-data-table').count()
    if expected_lab in TABLE_LABS and table_count != 1:
        issues.append(f'table-count:{table_count}')
    if expected_lab not in TABLE_LABS and table_count > 1:
        issues.append('multiple-heavy-tables-mounted')
    return issues


def _interaction_smoke(page, url: str) -> list[str]:
    """Exercise the high-value table contract once after the visual matrix."""
    issues: list[str] = []
    page.goto(url.rstrip('/') + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(500)
    search = page.get_by_label('Search table')
    before = page.locator('.cui-table-footer-label').inner_text()
    search.fill('OOS')
    page.wait_for_timeout(350)
    if page.locator('.cui-table-footer-label').inner_text() == before:
        issues.append('grid-search-did-not-filter')
    search.fill('')
    page.wait_for_timeout(220)
    before_quick = page.locator('.cui-table-footer-label').inner_text()
    page.get_by_role('button', name='Watch / OOS').click()
    page.wait_for_timeout(350)
    if page.locator('.cui-table-footer-label').inner_text() == before_quick:
        issues.append('grid-quick-filter-did-not-filter')
    page.get_by_role('radio', name='Actions').click()
    page.wait_for_timeout(650)
    page.locator('.ag-row .ag-checkbox-input').nth(1).click()
    page.wait_for_timeout(300)
    if '1 selected' not in page.locator('[data-actions-status]').inner_text():
        issues.append('selection-callback-not-normalized')
    if page.get_by_role('button', name='Hold selected').count() != 1:
        issues.append('bulk-action-bar-missing')
    page.get_by_role('radio', name='Visualize').click()
    page.wait_for_timeout(650)
    initial_chart = page.locator('[data-chart-kind]').get_attribute('data-chart-kind')
    page.get_by_role('radio', name='Distribution').click()
    page.wait_for_timeout(250)
    if page.locator('[data-chart-kind]').get_attribute('data-chart-kind') == initial_chart:
        issues.append('linked-chart-selector-did-not-change')
    page.get_by_role('radio', name='Detail').click()
    page.wait_for_timeout(650)
    page.locator('.ag-center-cols-container .ag-row').first.dblclick()
    page.wait_for_timeout(300)
    if page.get_by_text('Related records').count() < 1:
        issues.append('detail-drawer-missing')
    page.keyboard.press('Escape')
    page.wait_for_timeout(180)
    page.get_by_role('radio', name='States').click()
    page.wait_for_timeout(500)
    page.get_by_role('radio', name='Error').click()
    page.wait_for_timeout(120)
    if page.get_by_role('alert').count() != 1:
        issues.append('error-state-missing')
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); screenshots = output / 'screenshots'; screenshots.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport, size in (('desktop', (1440, 1000)), ('tablet', (1024, 900)), ('small-tablet', (768, 900)), ('phone', (390, 844))):
            for theme in ('light', 'dark'):
                context = browser.new_context(viewport={'width': size[0], 'height': size[1]})
                page = context.new_page(); console: list[str] = []; page_errors: list[str] = []
                page.on('console', lambda message: console.append(message.text) if message.type == 'error' else None)
                page.on('pageerror', lambda error: page_errors.append(str(error)))
                response = page.goto(args.url.rstrip('/') + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
                page.wait_for_timeout(500)
                page.evaluate('(theme) => { document.documentElement.dataset.theme = theme; document.body.classList.toggle("q-dark", theme === "dark") }', theme)
                for label in LABS:
                    if label != 'Grid':
                        page.get_by_role('radio', name=label).click()
                        page.locator(f'[data-active-lab="{label.lower()}"]').wait_for(state='visible', timeout=5000)
                        page.wait_for_timeout(120)
                    issues = _check_page(page, response, expected_lab=label)
                    if label == 'Visualize':
                        if page.locator('[data-chart-kind]').count() != 1:
                            issues.append('visualize-chart-missing')
                        page.get_by_role('radio', name='Wafer').click()
                        try:
                            page.locator('[data-chart-kind="wafer"]').wait_for(state='visible', timeout=5000)
                        except Exception:
                            issues.append('wafer-chart-missing')
                    if label == 'Server' and page.locator('[data-server-status]').count() != 1:
                        issues.append('server-status-missing')
                    if label == 'States':
                        page.get_by_role('radio', name='Error').click(); page.wait_for_timeout(100)
                        if page.get_by_role('alert').count() != 1:
                            issues.append('error-state-missing')
                        page.get_by_role('radio', name='Populated').click(); page.wait_for_timeout(100)
                    if console or page_errors:
                        issues.append('browser-error')
                    if label == 'Grid' and viewport in {'desktop', 'phone'} and theme in {'light', 'dark'}:
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(screenshots / f'grid_{viewport}_{theme}.png'), full_page=True)
                    if label == 'Visualize' and viewport == 'desktop' and theme == 'dark':
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(screenshots / 'visualize_desktop_dark.png'), full_page=True)
                    if label == 'Server' and viewport == 'phone' and theme == 'light':
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(screenshots / 'server_phone_light.png'), full_page=True)
                    results.append({'lab': label, 'viewport': viewport, 'theme': theme, 'issues': issues, 'console': console[:3], 'page_errors': page_errors[:3]})
                context.close()
        smoke_context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        smoke_page = smoke_context.new_page()
        smoke_console: list[str] = []; smoke_page_errors: list[str] = []
        smoke_page.on('console', lambda message: smoke_console.append(message.text) if message.type == 'error' else None)
        smoke_page.on('pageerror', lambda error: smoke_page_errors.append(str(error)))
        interaction_issues = _interaction_smoke(smoke_page, args.url)
        if smoke_console or smoke_page_errors:
            interaction_issues.append('browser-error')
        smoke_context.close()
        browser.close()
    passed = sum(not item['issues'] for item in results)
    payload = {
        'candidate': CANDIDATE,
        'total': len(results),
        'passed': passed,
        'interaction_smoke': {
            'passed': not interaction_issues,
            'issues': interaction_issues,
            'console_errors': smoke_console[:3],
            'page_errors': smoke_page_errors[:3],
        },
        'results': results,
    }
    (output / 'DATA_LAB_BROWSER_RESULT.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps({'candidate': CANDIDATE, 'total': payload['total'], 'passed': payload['passed'], 'failed': payload['total'] - payload['passed'], 'interaction_smoke': payload['interaction_smoke'], 'output': str(output)}))
    return 0 if payload['passed'] == payload['total'] and payload['interaction_smoke']['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
