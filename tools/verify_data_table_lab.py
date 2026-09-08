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


def _switch_lab(page, label: str, *, wait: int = 500) -> None:
    page.keyboard.press('Escape')
    control = page.get_by_role('radio', name=label, exact=True)
    control.scroll_into_view_if_needed()
    control.click()
    page.locator(f'[data-active-lab="{label.lower()}"]').wait_for(state='visible', timeout=5000)
    page.wait_for_timeout(wait)
    expected_title = {
        'Grid': 'Lot and wafer monitoring',
        'Actions': 'Disposition queue',
        'Edit': 'Engineering disposition',
        'Visualize': 'Filtered engineering records',
        'Server': 'Provider-backed event history',
    }.get(label)
    if expected_title:
        page.get_by_text(expected_title, exact=True).wait_for(state='visible', timeout=15000)
    if label in {'Grid', 'Actions', 'Edit', 'Visualize', 'Detail', 'Server'}:
        page.locator('.cui-data-table').wait_for(state='visible', timeout=10000)
        page.locator('.ag-center-cols-container .ag-row').first.wait_for(state='visible', timeout=10000)
    if label in {'Actions', 'Visualize'}:
        page.locator('.ag-center-cols-container .ag-row').first.locator('.ag-selection-checkbox').wait_for(state='visible', timeout=10000)


def _ensure_column(page, key: str) -> None:
    """Use the public AG Grid bridge only for visual verification geometry."""
    page.locator('.nicegui-aggrid').evaluate(
        """(element, key) => {
            const id = Number(String(element.id).slice(1));
            getElement(id).api.ensureColumnVisible(key);
        }""",
        key,
    )
    page.wait_for_timeout(80)


def _wait_status(page, selector: str, text: str, *, timeout: int = 4000) -> None:
    page.locator(selector).filter(has_text=text).wait_for(state='visible', timeout=timeout)


def _select_row(page, index: int) -> None:
    row = page.locator('.ag-center-cols-container .ag-row').nth(index)
    checkbox = row.locator('.ag-selection-checkbox')
    checkbox.wait_for(state='visible', timeout=8000)
    checkbox.click(force=True)


def _interaction_smoke(page, url: str, evidence_dir: Path | None = None) -> list[str]:
    """Exercise behavior, not just mounting, once after the visual matrix."""
    issues: list[str] = []
    page_context = page.context
    local_console_errors: list[str] = []
    local_page_errors: list[str] = []

    def capture(name: str) -> None:
        if evidence_dir is not None:
            page.screenshot(path=str(evidence_dir / f'{name}.png'), full_page=True)

    def new_client_page() -> None:
        nonlocal page
        try:
            page.close()
        except Exception:
            pass
        page = page_context.new_page()
        page.on('console', lambda message: local_console_errors.append(message.text) if message.type == 'error' else None)
        page.on('pageerror', lambda error: local_page_errors.append(str(error)))
        page.set_default_timeout(8000)

    new_client_page()
    page.set_default_timeout(8000)
    page.goto(url.rstrip('/') + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
    page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
    page.get_by_role('button', name='Choose columns', exact=True).wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(250)

    def open_lab(label: str, wait: int = 600) -> None:
        # Each interaction family starts from a clean live page. This prevents a
        # prior AG Grid update from being mistaken for a hidden-lab lifecycle
        # failure while still exercising the real websocket/browser contract.
        new_client_page()
        page.goto(url.rstrip('/') + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
        page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
        _switch_lab(page, label, wait=wait)
    try:
        # Grid: displayed population, quick filter, density, column visibility and
        # canonical pin menu all operate on the one mounted grid.
        search = page.get_by_label('Search table')
        before = page.locator('.cui-table-footer-label').inner_text()
        search.fill('OOS'); page.wait_for_timeout(350)
        if page.locator('.cui-table-footer-label').inner_text() == before:
            issues.append('grid-search-did-not-filter')
        if not page.locator('[aria-label="Table summary"] .cui-workbench-kpi').first.inner_text().strip().startswith('8'):
            issues.append('grid-summary-not-filtered')
        search.fill(''); page.wait_for_timeout(220)
        before_quick = page.locator('.cui-table-footer-label').inner_text()
        page.get_by_role('button', name='Watch / OOS', exact=True).click(); page.wait_for_timeout(350)
        if page.locator('.cui-table-footer-label').inner_text() == before_quick:
            issues.append('grid-quick-filter-did-not-filter')
        if 'filter(s)' not in page.locator('[data-grid-view-status]').inner_text():
            issues.append('grid-filter-context-missing')
        page.get_by_role('button', name='Clear filters', exact=True).click(); page.wait_for_timeout(180)
        page.get_by_role('button', name='Choose columns', exact=True).click()
        # The themed checkbox intentionally draws a check span over the native
        # input; activate the accessible input rather than treating that paint
        # layer as a product hit-target.
        page.get_by_label('Show Comment column', exact=True).click(force=True); page.wait_for_timeout(140)
        if page.locator('.ag-header-cell[col-id="comment"]').count() != 0:
            issues.append('grid-column-hide-failed')
        page.get_by_role('button', name='Pin Tool column', exact=True).click()
        page.get_by_role('menu').last.get_by_role('button', name='Pin left', exact=True).click()
        page.wait_for_timeout(160)
        if page.locator('.ag-pinned-left-header .ag-header-cell[col-id="tool_id"]').count() != 1:
            issues.append('grid-pin-left-failed')
        page.get_by_role('button', name='Table density', exact=True).click()
        page.get_by_role('menu').get_by_role('button', name='Dense', exact=False).click()
        page.wait_for_timeout(150)
        if 'Dense' not in page.locator('.cui-table-footer-density').inner_text():
            issues.append('grid-density-failed')
        page.get_by_role('button', name='Reset view', exact=True).click(); page.wait_for_timeout(220)
    except Exception as exc:
        issues.append(f'grid-interaction:{type(exc).__name__}:{exc}')

    try:
        # Actions: mutations are reflected in the currently mounted grid and the
        # delete path reconciles selected identities after confirmation.
        open_lab('Actions', wait=650)
        _select_row(page, 0)
        page.locator('.ag-header .ag-checkbox-input').first.click(force=True)
        page.wait_for_timeout(250)
        selected_status = page.locator('[data-actions-status]').inner_text()
        if 'selected' not in selected_status or int(selected_status.split()[0]) < 2:
            issues.append('selection-callback-not-normalized')
        page.get_by_role('button', name='Hold selected', exact=True).click(); page.wait_for_timeout(280)
        _ensure_column(page, 'status')
        if page.locator('.ag-center-cols-container .ag-row').nth(0).locator('[col-id="status"]').inner_text().strip() != 'Hold':
            issues.append('hold-not-reflected-in-grid')
        page.wait_for_timeout(160)
        page.get_by_role('button', name='Mark reviewed', exact=True).click(force=True); page.wait_for_timeout(280)
        if 'Marked ' not in page.locator('[data-actions-status]').inner_text():
            issues.append('review-not-reflected-in-grid')
        page.get_by_role('button', name='Compare selected', exact=True).click(force=True); page.wait_for_timeout(220)
        if page.get_by_text('Compare selected records', exact=True).count() != 1:
            issues.append('compare-dialog-missing')
        compare_text = page.locator('.cui-dialog').inner_text()
        if 'R-000001' not in compare_text or 'R-000002' not in compare_text:
            issues.append('compare-dialog-missing-record-ids')
        capture('actions_compare')
        page.get_by_role('button', name='Close', exact=True).click(); page.wait_for_timeout(1200)
        # The selected population remains selected after comparison.
        delete_button = page.get_by_role('button', name='Delete selected', exact=True)
        if delete_button.count() != 1:
            issues.append('delete-action-missing')
        else:
            # The action bar can be outside the viewport after the compare
            # overlay closes; its governed DOM button remains the same action.
            delete_button.evaluate('(element) => element.click()')
        page.wait_for_timeout(150)
        if page.get_by_role('button', name='Delete', exact=True).count() != 1:
            issues.append('delete-confirmation-missing')
        page.get_by_role('button', name='Delete', exact=True).click(force=True); page.wait_for_timeout(800)
        if not page.get_by_text('Deleted ', exact=False).count():
            issues.append('delete-status-missing')
        if '0 selected' not in page.locator('[data-actions-status]').inner_text() and page.locator('.cui-table-selection-bar').is_visible():
            issues.append('delete-selection-not-reconciled')
    except Exception as exc:
        issues.append(f'actions-interaction:{type(exc).__name__}:{exc}')

    try:
        # Edit: add validation and all three semantic editor families.
        open_lab('Edit', wait=600)
        page.get_by_role('button', name='Add record', exact=True).click(); page.wait_for_timeout(120)
        if page.locator('input[type="number"]').count() < 1:
            issues.append('add-number-editor-missing')
        add_drawer = page.locator('.cui-drawer').last
        capture('edit_add_record')
        record_input = add_drawer.get_by_role('textbox', name='Record ID', exact=True)
        record_input.fill('R-VERIFY-ADD')
        add_drawer.get_by_role('spinbutton', name='Measurement', exact=True).fill('51.125')
        add_drawer.get_by_role('button', name='Add record', exact=True).click(); page.wait_for_timeout(300)
        if page.get_by_text('Added R-VERIFY-ADD.', exact=True).count() != 1:
            issues.append('add-record-not-committed')
        page.get_by_role('button', name='Add record', exact=True).first.click(); page.wait_for_timeout(100)
        current_drawer = page.locator('.cui-drawer').last
        current_drawer.get_by_role('textbox', name='Record ID', exact=True).fill('R-000001')
        current_drawer.get_by_role('button', name='Add record', exact=True).click(); page.wait_for_timeout(120)
        if 'already exists' not in page.locator('[data-edit-status]').inner_text():
            issues.append('duplicate-add-not-rejected')
        page.keyboard.press('Escape'); page.wait_for_timeout(100)
        _ensure_column(page, 'measurement_nm')
        cell = page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="measurement_nm"]')
        cell.dblclick(); page.locator('.ag-cell-editor input').fill('51.111'); page.locator('.ag-cell-editor input').press('Enter'); page.wait_for_timeout(320)
        if 'measurement_nm' not in page.locator('[data-edit-status]').inner_text():
            issues.append('numeric-editor-save-missing')
        _ensure_column(page, 'status')
        page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="status"]').dblclick(); page.wait_for_timeout(80)
        page.locator('.ag-cell-editor [role="combobox"]').click(); page.get_by_role('option', name='Hold', exact=True).click(); page.wait_for_timeout(240)
        if page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="status"]').inner_text().strip() != 'Hold':
            issues.append('status-editor-save-missing')
        _ensure_column(page, 'reviewed')
        page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="reviewed"]').dblclick(); page.wait_for_timeout(80)
        page.locator('.ag-cell-editor [role="combobox"]').click(); page.get_by_role('option', name='Yes', exact=True).click(); page.wait_for_timeout(240)
        if page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="reviewed"]').inner_text().strip() not in {'Yes', 'true', 'True'}:
            issues.append('boolean-editor-save-missing')
    except Exception as exc:
        issues.append(f'edit-interaction:{type(exc).__name__}:{exc}')

    try:
        # Visualize: filtered and selected populations drive the same chart host.
        open_lab('Visualize', wait=650)
        initial_status = page.locator('[data-visualize-population]').inner_text()
        linked_search = page.get_by_role('textbox', name='Search linked records')
        linked_search.fill('OOS'); page.wait_for_timeout(400)
        filtered_status = page.locator('[data-visualize-population]').inner_text()
        if filtered_status == initial_status or 'Filtered records: 8' not in filtered_status:
            issues.append('linked-search-did-not-update-chart-population')
        _select_row(page, 0); page.wait_for_timeout(260)
        if 'Selected records: 1' not in page.locator('[data-visualize-population]').inner_text() or 'selected population' not in page.locator('[data-visualize-population]').inner_text():
            issues.append('linked-selection-did-not-update-chart-population')
        capture('visualize_selected')
        for label, kind in (('Trend', 'line'), ('Distribution', 'bar'), ('Scatter', 'scatter'), ('SPC', 'control'), ('Wafer', 'wafer')):
            page.get_by_role('radio', name=label, exact=True).click(); page.wait_for_timeout(180)
            if page.locator('[data-chart-kind="%s"]' % kind).count() != 1:
                issues.append(f'chart-kind-missing:{kind}')
        _select_row(page, 0); page.wait_for_timeout(220)
        if 'Selected records: 0' not in page.locator('[data-visualize-population]').inner_text():
            issues.append('linked-deselect-did-not-restore-filtered-population')
    except Exception as exc:
        issues.append(f'visualize-interaction:{type(exc).__name__}:{exc}')

    try:
        # Import: stage, cancel without mutation, then confirm a second stage.
        open_lab('Import', wait=650)
        before = page.get_by_text('64 active rows', exact=False).count()
        page.get_by_role('radio', name='Paste example', exact=True).click(); page.wait_for_timeout(100)
        paste = page.locator('textarea[aria-label="Paste data"]')
        paste.wait_for(state='visible', timeout=8000)
        paste.fill('record_id\tmeasurement_nm\tstatus\nR-STAGED\t52.2\tWatch\n')
        page.get_by_role('button', name='Preview import', exact=True).click(); page.wait_for_timeout(220)
        if page.locator('[data-import-preview]').count() != 1:
            issues.append('import-preview-missing')
        capture('import_staged_preview')
        if page.get_by_text('64 active rows', exact=False).count() != before:
            issues.append('import-mutated-before-confirm')
        page.get_by_role('button', name='Cancel', exact=True).click(); page.wait_for_timeout(180)
        if page.locator('[data-import-preview]').count() != 0:
            issues.append('import-cancel-did-not-discard')
        page.get_by_role('radio', name='Paste example', exact=True).click(); page.wait_for_timeout(100)
        committed_paste = page.locator('textarea[aria-label="Paste data"]')
        committed_paste.wait_for(state='visible', timeout=8000)
        committed_paste.fill('record_id\tmeasurement_nm\tstatus\nR-COMMIT\t52.4\tNominal\n')
        page.get_by_role('button', name='Preview import', exact=True).click(); page.wait_for_timeout(180)
        page.get_by_role('button', name='Confirm import', exact=True).click(); page.wait_for_timeout(260)
        if 'Imported 1 row' not in page.locator('body').inner_text():
            issues.append('import-confirm-status-missing')
    except Exception as exc:
        issues.append(f'import-interaction:{type(exc).__name__}:{exc}')

    try:
        # Detail and state anatomy.
        open_lab('Detail', wait=1000)
        page.locator('.ag-center-cols-container .ag-row').first.dblclick(); page.wait_for_timeout(260)
        detail_text = page.locator('body').inner_text()
        if 'Related records' not in detail_text or 'Audit trail' not in detail_text:
            issues.append('detail-content-missing')
        capture('detail_drawer')
        page.keyboard.press('Escape'); page.wait_for_timeout(150)

        # Server: force a real provider request through the canonical toolbar
        # refresh path, then verify stale retention and successful retry.
        open_lab('Server', wait=950)
        server_status = page.locator('[data-server-status]')
        page_label = page.locator('.cui-table-page-label')
        if 'page 1 of 25000' not in server_status.inner_text().casefold():
            issues.append('server-initial-page-contract-missing')
        page.get_by_role('button', name='Next page', exact=True).click(); page.wait_for_timeout(450)
        if 'Page 2 of 25000' not in page_label.inner_text():
            issues.append('server-page-two-missing')
        page.get_by_role('combobox').click(); page.get_by_role('option', name='25', exact=True).click(); page.wait_for_timeout(450)
        if 'Page 1 of 10000' not in page_label.inner_text() or page.locator('.ag-center-cols-container .ag-row').count() != 25:
            issues.append('server-page-size-not-applied')
        server_search = page.get_by_label('Search table')
        server_search.fill('ETCH-021'); page.wait_for_timeout(1200)
        if '62,500 matching records' not in server_status.inner_text():
            issues.append('server-search-total-invalid')
        page.get_by_role('button', name='Fail next request', exact=True).click(); page.wait_for_timeout(180)
        page.get_by_role('button', name='Refresh table', exact=True).click(); page.wait_for_timeout(500)
        if 'Stale data' not in page.locator('.cui-table-footer').inner_text() or 'Provider request failed' not in server_status.inner_text():
            issues.append('server-stale-failure-not-visible')
        capture('server_stale_failure')
        page.get_by_role('button', name='Retry', exact=True).click(); page.wait_for_timeout(600)
        if 'Retry succeeded' not in server_status.inner_text() or 'Stale data' in page.locator('.cui-table-footer').inner_text():
            issues.append('server-retry-did-not-recover')
        page.get_by_role('button', name='Initial-load error', exact=True).click(); page.wait_for_timeout(450)
        if 'Unable to load records' not in page.locator('.cui-table-footer').inner_text():
            issues.append('server-initial-error-anatomy-missing')
        capture('server_initial_error')
        page.get_by_role('button', name='Retry', exact=True).click(); page.wait_for_timeout(600)
        if 'Retry succeeded' not in server_status.inner_text():
            issues.append('server-initial-error-retry-failed')

        open_lab('States', wait=550)
        for label, state in (('Loading', 'loading'), ('Empty', 'empty'), ('No results', 'no-results'), ('Refreshing', 'refreshing'), ('Error', 'error'), ('Stale', 'stale'), ('Read only', 'read-only'), ('Restricted', 'restricted'), ('Populated', 'populated')):
            page.get_by_role('radio', name=label, exact=True).click(); page.wait_for_timeout(280)
            if page.locator(f'[data-table-state="{state}"]').count() == 0 and state not in {'empty', 'no-results', 'read-only', 'restricted', 'populated'}:
                issues.append(f'state-anatomy-missing:{state}')
            if label in {'Loading', 'Error', 'Restricted'}:
                capture(f'states_{state}')
        page.get_by_role('radio', name='Restricted', exact=True).click(); page.wait_for_timeout(100)
        if page.get_by_role('button', name='Export', exact=True).count() != 0 or page.get_by_role('button', name='Delete selected', exact=True).count() != 0:
            issues.append('restricted-actions-visible')
    except Exception as exc:
        issues.append(f'detail-state-interaction:{type(exc).__name__}:{exc}')

    try:
        # Repeated switching leaves one active heavy specimen and no stale page errors.
        for label in ('Grid', 'Server', 'Visualize', 'Grid'):
            _switch_lab(page, label, wait=300)
            if page.locator('.cui-data-table').count() != 1:
                issues.append(f'heavy-table-count-after-{label.lower()}')
    except Exception as exc:
        issues.append(f'lab-switching:{type(exc).__name__}:{exc}')
    if local_console_errors or local_page_errors:
        issues.append(f'browser-error:{len(local_console_errors)} console/{len(local_page_errors)} page')
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
                page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
                page.wait_for_timeout(300)
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
        interaction_issues = _interaction_smoke(smoke_page, args.url, screenshots)
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
