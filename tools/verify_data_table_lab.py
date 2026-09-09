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
    action_columns = page.locator('.ag-header-cell[col-id="__actions"]')
    legacy_action_columns = page.locator('.ag-header-cell[col-id^="__action_"]')
    if legacy_action_columns.count():
        issues.append('legacy-per-row-action-columns-present')
    if page.locator('.cui-table-row-actions-trigger').count() and action_columns.count() != 1:
        issues.append(f'action-column-count:{action_columns.count()}')
    width = (page.viewport_size or {}).get('width', 1440)
    # Responsive closure checks the failure modes that a route/overflow smoke
    # cannot catch: normal labels must remain whole, and the analytical split
    # must stack before its chart becomes narrower than its readable contract.
    for selector in ('.cui-data-lab-intro .cui-workbench-title', '.cui-data-lab-active-head .cui-workbench-section-title'):
        for item in page.locator(selector).all():
            metrics = item.evaluate("el => ({clientWidth: el.clientWidth, scrollWidth: el.scrollWidth, wordBreak: getComputedStyle(el).wordBreak, overflowWrap: getComputedStyle(el).overflowWrap})")
            if metrics['scrollWidth'] > metrics['clientWidth'] + 1:
                issues.append('data-lab-heading-overflow')
            if metrics['wordBreak'] == 'break-all':
                issues.append('data-lab-heading-character-wrap')
    if expected_lab == 'Visualize':
        table_panel = page.locator('.cui-data-lab-visual-table')
        chart_panel = page.locator('.cui-data-lab-visual-chart')
        if table_panel.count() == 1 and chart_panel.count() == 1:
            table_rect, chart_rect = page.locator('.cui-data-lab-visual-table, .cui-data-lab-visual-chart').evaluate_all(
                "els => els.map(el => { const r=el.getBoundingClientRect(); return {left:r.left, top:r.top, width:r.width, height:r.height, right:r.right, bottom:r.bottom}; })"
            )
            stacked = chart_rect['top'] >= table_rect['bottom'] - 4
            if width <= 1100 and not stacked:
                issues.append('visualize-table-chart-not-stacked')
            if not stacked and chart_rect['width'] < 380:
                issues.append('visualize-chart-too-narrow')
            if chart_rect['width'] > 0 and chart_rect['height'] > chart_rect['width'] * 4:
                issues.append('visualize-chart-height-collapse')
    if expected_lab == 'States' and width <= 600:
        for button in page.locator('.cui-data-lab-state-selector .q-btn').all():
            metrics = button.evaluate("el => ({width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight, whiteSpace: getComputedStyle(el).whiteSpace})")
            if metrics['width'] < 44 or metrics['scrollHeight'] > metrics['clientHeight'] * 1.35 or metrics['whiteSpace'] != 'nowrap':
                issues.append('states-selector-not-readable')
                break
    if expected_lab == 'Server' and width <= 600:
        pagination = page.locator('.cui-table-footer__pagination')
        if pagination.count() != 1 or not pagination.is_visible() or pagination.locator('.cui-table-page-label').count() != 1:
            issues.append('server-mobile-pagination-not-coherent')
    theme_values = page.evaluate("""() => {
        const root = document.documentElement;
        const sample = document.querySelector('.cui-data-lab') || document.body;
        const style = getComputedStyle(sample);
        return {dark: document.body.classList.contains('body--dark'), theme: root.dataset.theme || '', background: style.backgroundColor, color: style.color};
    }""")
    if theme_values['theme'] == 'dark' and not theme_values['dark']:
        issues.append('dark-theme-not-applied')
    if theme_values['theme'] == 'dark' and theme_values['background'] in {'rgb(255, 255, 255)', 'white'}:
        issues.append('dark-theme-white-surface')
    return issues


def _set_actual_theme(page, desired: str) -> None:
    """Use the Explorer appearance authority, not a test-only CSS toggle."""
    if desired not in {'light', 'dark'}:
        raise ValueError(desired)
    button = page.locator('[aria-label^="Appearance theme:"]').first
    button.wait_for(state='visible', timeout=10000)
    for _ in range(3):
        label = button.get_attribute('aria-label') or ''
        if label.endswith(f': {desired.title()}'):
            break
        button.click()
        page.wait_for_timeout(450)
    page.wait_for_function(
        "desired => document.documentElement.dataset.theme === desired && document.body.classList.contains(desired === 'dark' ? 'body--dark' : 'body--light')",
        arg=desired,
        timeout=8000,
    )


def _switch_lab(page, label: str, *, wait: int = 500) -> None:
    page.keyboard.press('Escape')
    control = page.get_by_role('radio', name=label, exact=True)
    control.scroll_into_view_if_needed()
    control.click()
    page.locator(f'[data-active-lab="{label.lower()}"]').wait_for(state='visible', timeout=10000)
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


def _bulk_action_button(page, label: str):
    """Select the visible desktop action, excluding the phone overflow copy."""
    return page.locator('.cui-table-selection-bar:not(.cui-table-selection-bar--mobile):visible').get_by_role('button', name=label, exact=True)


def _grid_column_state(page) -> list[dict[str, object]]:
    return page.locator('.nicegui-aggrid').evaluate(
        "element => getElement(Number(String(element.id).slice(1))).api.getColumnState()"
    )


def _open_row_actions(page, index: int = 0):
    # The governed Actions column is pinned right, so its row is outside the
    # center-row container used by the other cells.
    trigger = page.locator('.cui-table-row-actions-trigger').nth(index)
    trigger.wait_for(state='visible', timeout=8000)
    trigger.click(force=True)
    menu = page.get_by_role('menu').last
    menu.wait_for(state='visible', timeout=5000)
    return menu


def _choose_table_view(page, name: str) -> None:
    page.get_by_role('button', name='Table view', exact=True).click()
    menu = page.get_by_role('menu').last
    menu.wait_for(state='visible', timeout=5000)
    # Each saved-view entry includes its density label in the accessible button
    # name (for example, "Process engineeringDense").  Match the stable view
    # label within the open menu without weakening the exact menu scope.
    menu.get_by_role('button').filter(has_text=name).click(force=True)
    page.get_by_role('button', name='Table view', exact=True).get_by_text(name, exact=True).wait_for(state='visible', timeout=8000)


def _choose_select_option(page, label: str, option: str) -> None:
    labels = {'Measurement / Y': 0, 'X (scatter)': 1, 'Y (scatter)': 2}
    page.get_by_role('combobox').nth(labels[label]).click()
    page.get_by_role('option', name=option, exact=True).last.click()
    page.wait_for_timeout(220)


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
        if page.get_by_role('button', name='Table view', exact=True).inner_text().strip() != 'Default':
            issues.append('grid-initial-view-label-not-default')
        _choose_table_view(page, 'Process engineering')
        if not any(item.get('colId') == 'delta_nm' and item.get('sort') == 'desc' for item in _grid_column_state(page)):
            issues.append('process-engineering-sort-not-applied')
        _choose_table_view(page, 'Quality review')
        if any(item.get('sort') in {'asc', 'desc'} for item in _grid_column_state(page) if item.get('colId') != '__actions'):
            issues.append('preset-sort-leaked-into-quality-review')
        page.get_by_role('button', name='Choose columns', exact=True).click()
        # The themed checkbox intentionally draws a check span over the native
        # input; activate the accessible input rather than treating that paint
        # layer as a product hit-target.
        # The governed checkbox intentionally uses a native input under a
        # themed paint layer.  Dispatch its real click on the accessible input
        # so browser automation exercises the same change event without relying
        # on the decorative layer's hit geometry.
        page.get_by_label('Show Comment column', exact=True).evaluate('(element) => element.click()'); page.wait_for_timeout(180)
        if page.locator('.ag-header-cell[col-id="comment"]').count() != 0:
            issues.append('grid-column-hide-failed')
        page.get_by_role('button', name='Pin Tool column', exact=True).click()
        page.get_by_role('menu').last.get_by_role('button', name='Pin left', exact=True).click()
        page.wait_for_timeout(160)
        if page.locator('.ag-pinned-left-header .ag-header-cell[col-id="tool_id"]').count() != 1:
            issues.append('grid-pin-left-failed')
        # Nested column menus retain the parent menu in the DOM.  Click the
        # page surface to close the child menu before opening the next column's
        # pin menu; Escape alone only closes the child in this Quasar version.
        page.mouse.click(10, 10); page.wait_for_timeout(80)
        page.get_by_role('button', name='Choose columns', exact=True).click()
        for _ in range(3):
            try:
                page.get_by_role('button', name='Pin Status column', exact=True).scroll_into_view_if_needed()
                break
            except Exception:
                page.wait_for_timeout(100)
        page.get_by_role('button', name='Pin Status column', exact=True).click(force=True)
        page.get_by_role('menu').last.get_by_role('button', name='Pin right', exact=True).click()
        page.wait_for_timeout(160)
        _ensure_column(page, 'status')
        if page.locator('.ag-pinned-right-header .ag-header-cell[col-id="status"]').count() != 1:
            issues.append('grid-pin-right-failed')
        page.mouse.click(10, 10); page.wait_for_timeout(80)
        page.get_by_role('button', name='Choose columns', exact=True).click()
        for _ in range(3):
            try:
                page.get_by_role('button', name='Pin Status column', exact=True).scroll_into_view_if_needed()
                break
            except Exception:
                page.wait_for_timeout(100)
        page.get_by_role('button', name='Pin Status column', exact=True).click(force=True)
        page.get_by_role('menu').last.get_by_role('button', name='Unpin', exact=True).click()
        page.wait_for_timeout(160)
        if page.locator('.ag-pinned-right-header .ag-header-cell[col-id="status"]').count() != 0:
            issues.append('grid-unpin-failed')
        page.get_by_role('button', name='Table density', exact=True).click()
        page.locator('.cui-table-density-menu').get_by_role('button', name='Dense 34 px rows', exact=True).click()
        page.wait_for_timeout(350)
        if 'Dense' not in page.locator('.cui-table-footer-density').inner_text():
            issues.append('grid-density-failed')
        page.get_by_role('button', name='Reset view', exact=True).click(); page.wait_for_timeout(500)
        if page.get_by_label('Search table').input_value() != '':
            issues.append('grid-reset-search-not-cleared')
        if page.locator('.cui-table-footer-label').inner_text() != '64 records':
            issues.append('grid-reset-records-not-restored')
        if 'Compact' not in page.locator('.cui-table-footer-density').inner_text():
            issues.append('grid-reset-density-not-restored')
        if page.get_by_role('button', name='Table view', exact=True).inner_text().strip() != 'Default':
            issues.append('grid-reset-view-label-not-default')
        # Personal views use the governed preference service, then reset returns
        # the live control and persisted default to the authored contract.
        page.get_by_label('Search table').fill('OOS'); page.wait_for_timeout(250)
        page.get_by_role('button', name='Table density', exact=True).click()
        page.locator('.cui-table-density-menu').get_by_role('button', name='Dense 34 px rows', exact=True).click()
        page.wait_for_timeout(180)
        page.get_by_role('button', name='Table view', exact=True).click()
        page.get_by_role('button', name='Save current as Personal', exact=True).click()
        page.wait_for_timeout(180)
        page.get_by_label('Search table').fill('Nominal'); page.wait_for_timeout(180)
        page.get_by_role('button', name='Table density', exact=True).click()
        page.locator('.cui-table-density-menu').get_by_role('button', name='Compact 38 px rows', exact=True).click()
        page.wait_for_timeout(120)
        page.get_by_role('button', name='Table view', exact=True).click()
        page.get_by_role('button', name='Load Personal', exact=True).click()
        page.wait_for_timeout(700)
        if page.get_by_label('Search table').input_value() != 'OOS' or 'Dense' not in page.locator('.cui-table-footer-density').inner_text():
            issues.append('grid-personal-view-not-restored')
        page.reload(wait_until='domcontentloaded', timeout=45000); page.wait_for_timeout(900)
        if page.get_by_label('Search table').input_value() != 'OOS' or 'Dense' not in page.locator('.cui-table-footer-density').inner_text():
            issues.append('grid-personal-view-not-restored-after-reload')
        page.get_by_role('button', name='Table view', exact=True).click()
        page.get_by_role('menu').last.get_by_role('button', name='Delete Personal', exact=True).click()
        page.wait_for_timeout(500)
        page.get_by_role('button', name='Reset view', exact=True).click(); page.wait_for_timeout(700)
        page.get_by_role('button', name='Table view', exact=True).get_by_text('Default', exact=True).wait_for(state='visible', timeout=5000)
        page.reload(wait_until='domcontentloaded', timeout=45000); page.wait_for_timeout(900)
        if page.get_by_label('Search table').input_value() != '' or 'Compact' not in page.locator('.cui-table-footer-density').inner_text() or page.get_by_role('button', name='Table view', exact=True).inner_text().strip() != 'Default':
            issues.append('grid-reset-not-persistent-after-reload')
    except Exception as exc:
        issues.append(f'grid-interaction:{type(exc).__name__}:{exc}')

    try:
        # Actions: mutations are reflected in the currently mounted grid and the
        # delete path reconciles selected identities after confirmation.
        open_lab('Actions', wait=650)
        _select_row(page, 0)
        _select_row(page, 1)
        page.wait_for_timeout(500)
        selected_status = page.locator('[data-actions-status]').inner_text()
        if 'selected' not in selected_status or int(selected_status.split()[0]) < 2:
            issues.append('selection-callback-not-normalized')
        _bulk_action_button(page, 'Hold selected').click(); page.wait_for_timeout(650)
        _ensure_column(page, 'status')
        if page.locator('.ag-center-cols-container .ag-row').nth(0).locator('[col-id="status"]').inner_text().strip() != 'Hold':
            issues.append('hold-not-reflected-in-grid')
        action_menu = _open_row_actions(page)
        if action_menu.get_by_role('button', name='Release row', exact=True).get_attribute('aria-disabled') == 'true':
            issues.append('release-row-policy-not-refreshed')
        if action_menu.get_by_role('button', name='Hold row', exact=True).get_attribute('aria-disabled') != 'true':
            issues.append('hold-row-policy-not-refreshed')
        page.keyboard.press('Escape'); page.wait_for_timeout(100)
        _bulk_action_button(page, 'Release selected').click(force=True); page.wait_for_timeout(650)
        _ensure_column(page, 'status')
        if page.locator('.ag-center-cols-container .ag-row').nth(0).locator('[col-id="status"]').inner_text().strip() != 'Nominal':
            issues.append('release-not-reflected-in-grid')
        action_menu = _open_row_actions(page)
        if action_menu.get_by_role('button', name='Hold row', exact=True).get_attribute('aria-disabled') == 'true':
            issues.append('hold-row-policy-not-refreshed-after-release')
        if action_menu.get_by_role('button', name='Release row', exact=True).get_attribute('aria-disabled') != 'true':
            issues.append('release-row-policy-not-refreshed-after-release')
        page.keyboard.press('Escape'); page.wait_for_timeout(100)
        _bulk_action_button(page, 'Assign selected').click(force=True); page.wait_for_timeout(550)
        _ensure_column(page, 'owner')
        if page.locator('.ag-center-cols-container .ag-row').nth(0).locator('[col-id="owner"]').inner_text().strip() != 'M. Chen':
            issues.append('assign-not-reflected-in-grid')
        try:
            with page.expect_download(timeout=8000) as download_info:
                _bulk_action_button(page, 'Export selected').click(force=True)
            if not download_info.value.suggested_filename.endswith('.csv'):
                issues.append('selected-export-filename-invalid')
        except Exception as exc:
            issues.append(f'selected-export-failed:{type(exc).__name__}')
        page.wait_for_timeout(160)
        _bulk_action_button(page, 'Mark reviewed').click(force=True); page.wait_for_timeout(650)
        _ensure_column(page, 'reviewed')
        if 'Marked ' not in page.locator('[data-actions-status]').inner_text():
            issues.append('review-not-reflected-in-grid')
        _bulk_action_button(page, 'Compare selected').click(force=True); page.wait_for_timeout(350)
        if page.get_by_text('Compare selected records', exact=True).count() != 1:
            issues.append('compare-dialog-missing')
        compare_text = page.locator('.cui-dialog').inner_text()
        if 'R-000001' not in compare_text or 'R-000002' not in compare_text:
            issues.append('compare-dialog-missing-record-ids')
        capture('actions_compare')
        page.get_by_role('button', name='Close', exact=True).click(); page.wait_for_timeout(1200)
        # The selected population remains selected after comparison.
        delete_button = _bulk_action_button(page, 'Delete selected')
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
        if '0 selected' not in page.locator('[data-actions-status]').inner_text() and page.locator('.cui-table-selection-bar:not(.cui-table-selection-bar--mobile)').is_visible():
            issues.append('delete-selection-not-reconciled')

        # Tablet and phone use the same governed compact overflow surface once
        # the shell leaves less than the direct action group's useful width.
        # There is still one table and one policy/action authority.
        for responsive_width, evidence_name in ((1024, 'actions_overflow_tablet_light'), (390, 'actions_overflow_phone_light')):
            # Use a fresh context per responsive surface.  Keeping the prior
            # desktop/tablet websocket alive in one context can deliver a late
            # visibility update to the next page; that is harness cross-talk,
            # not a product state.  The browser surface remains the same.
            compact_context = page_context.browser.new_context(viewport={'width': responsive_width, 'height': 844 if responsive_width < 600 else 900})
            compact_page = compact_context.new_page()
            compact_page.set_default_timeout(8000)
            compact_page.on('console', lambda message: local_console_errors.append(message.text) if message.type == 'error' else None)
            compact_page.on('pageerror', lambda error: local_page_errors.append(str(error)))
            compact_page.goto(url.rstrip('/') + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
            compact_page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
            _switch_lab(compact_page, 'Actions', wait=700)
            _select_row(compact_page, 0)
            compact_bar = compact_page.locator('.cui-table-selection-bar--mobile')
            compact_bar.wait_for(state='visible', timeout=8000)
            if compact_page.locator('.cui-table-selection-bar:not(.cui-table-selection-bar--mobile):visible').count() != 0:
                issues.append(f'compact-actions-desktop-bar-visible:{responsive_width}')
            # The bar is a client-owned visibility surface and can receive one
            # late websocket visibility mutation after selection. Re-check
            # visibility before using the same normal accessible button action.
            compact_page.wait_for_timeout(180)
            if not compact_bar.is_visible():
                issues.append(f'compact-actions-bar-lost-visibility:{responsive_width}')
                compact_context.close()
                continue
            compact_bar.locator('.cui-table-selection-overflow').click()
            compact_menu = compact_bar.locator('.cui-table-selection-menu--inline')
            compact_menu.wait_for(state='visible', timeout=5000)
            for label in ('Hold selected', 'Assign selected', 'Compare selected', 'Delete selected'):
                if compact_menu.get_by_role('button', name=label, exact=True).count() != 1:
                    issues.append(f'compact-bulk-action-missing:{responsive_width}:{label}')
            if evidence_dir is not None:
                compact_page.screenshot(path=str(evidence_dir / f'{evidence_name}.png'), full_page=True)
            compact_context.close()
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
        # Native number inputs reject non-numeric text before the application
        # receives it; exercise the semantic range validator with a finite
        # out-of-range value instead.
        current_drawer.get_by_role('textbox', name='Record ID', exact=True).fill('R-VERIFY-BAD')
        current_drawer.get_by_role('spinbutton', name='Measurement', exact=True).fill('101')
        current_drawer.get_by_role('button', name='Add record', exact=True).click(); page.wait_for_timeout(120)
        if 'finite number' not in page.locator('[data-edit-status]').inner_text() and 'between 0 and 100' not in page.locator('[data-edit-status]').inner_text():
            issues.append('invalid-add-number-not-rejected')
        page.keyboard.press('Escape'); page.wait_for_timeout(100)
        _ensure_column(page, 'measurement_nm')
        cell = page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="measurement_nm"]')
        cell.dblclick(); page.locator('.ag-cell-editor input').fill('51.111'); page.locator('.ag-cell-editor input').press('Enter'); page.wait_for_timeout(320)
        if 'measurement_nm' not in page.locator('[data-edit-status]').inner_text():
            issues.append('numeric-editor-save-missing')
        _ensure_column(page, 'status')
        page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="status"]').dblclick(); page.wait_for_timeout(80)
        page.locator('.ag-cell-editor [role="combobox"]').click(); page.get_by_role('option', name='Hold', exact=True).click(); page.wait_for_timeout(240)
        _ensure_column(page, 'status')
        if page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="status"]').inner_text().strip() != 'Hold':
            issues.append('status-editor-save-missing')
        _ensure_column(page, 'reviewed')
        page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="reviewed"]').dblclick(); page.wait_for_timeout(80)
        page.locator('.ag-cell-editor [role="combobox"]').click(); page.get_by_role('option', name='Yes', exact=True).click(); page.wait_for_timeout(240)
        _ensure_column(page, 'reviewed')
        if page.locator('.ag-center-cols-container .ag-row').first.locator('[col-id="reviewed"]').inner_text().strip() not in {'Yes', 'true', 'True'}:
            issues.append('boolean-editor-save-missing')
        action_menu = _open_row_actions(page)
        edit_action = action_menu.get_by_role('button', name='Edit record', exact=True)
        if edit_action.count():
            edit_action.click(force=True); page.wait_for_timeout(150)
            edit_drawer = page.locator('.cui-drawer').last
            edit_drawer.get_by_role('textbox', name='Owner', exact=True).fill('M. Chen')
            edit_drawer.get_by_role('button', name='Save record', exact=True).click(); page.wait_for_timeout(800)
            if 'Updated ' not in page.locator('[data-edit-status]').inner_text():
                issues.append('full-record-edit-not-committed')
        action_menu = _open_row_actions(page)
        duplicate_action = action_menu.get_by_role('button', name='Duplicate record', exact=True)
        if duplicate_action.count():
            duplicate_action.click(force=True)
            try:
                page.locator('[data-edit-status]').filter(has_text='Duplicated ').wait_for(state='visible', timeout=8000)
            except Exception:
                issues.append('duplicate-record-not-committed')
        action_menu = _open_row_actions(page)
        delete_action = action_menu.get_by_role('button', name='Delete record', exact=True)
        if delete_action.count():
            delete_action.click(force=True); page.wait_for_timeout(120)
            if page.get_by_role('button', name='Delete', exact=True).count() != 1:
                issues.append('edit-delete-confirmation-missing')
            else:
                page.get_by_role('button', name='Delete', exact=True).click(force=True); page.wait_for_timeout(280)
                if 'Deleted ' not in page.locator('[data-edit-status]').inner_text():
                    issues.append('edit-delete-not-committed')
    except Exception as exc:
        issues.append(f'edit-interaction:{type(exc).__name__}:{exc}')

    try:
        # Visualize: filtered and selected populations drive the same chart host.
        open_lab('Visualize', wait=650)
        initial_status = page.locator('[data-visualize-population]').inner_text()
        linked_search = page.get_by_role('textbox', name='Search linked records')
        linked_search.fill('OOS'); page.wait_for_timeout(400)
        try:
            page.locator('[data-visualize-population]').filter(has_text='Filtered records: 8').wait_for(state='visible', timeout=5000)
        except Exception:
            pass
        filtered_status = page.locator('[data-visualize-population]').inner_text()
        if filtered_status == initial_status or 'Filtered records: 8' not in filtered_status:
            issues.append('linked-search-did-not-update-chart-population')
        _select_row(page, 0); page.wait_for_timeout(260)
        if 'Selected records: 1' not in page.locator('[data-visualize-population]').inner_text() or 'selected population' not in page.locator('[data-visualize-population]').inner_text():
            issues.append('linked-selection-did-not-update-chart-population')
        capture('visualize_selected')
        _choose_select_option(page, 'Measurement / Y', 'Yield (%)')
        if page.locator('[data-visual-metric]').get_attribute('data-visual-metric') != 'yield_pct' or 'Y: Yield (%)' not in page.locator('[data-visual-contract]').inner_text():
            issues.append('yield-metric-semantics-missing')
        page.get_by_role('radio', name='Trend', exact=True).click(); page.wait_for_timeout(180)
        if 'X: Timestamp / record order' not in page.locator('[data-visual-contract]').inner_text():
            issues.append('trend-x-is-not-time-sequence')
        _choose_select_option(page, 'Measurement / Y', 'Delta (nm)')
        if page.locator('[data-visual-metric]').get_attribute('data-visual-metric') != 'delta_nm' or 'Y: Delta (nm)' not in page.locator('[data-visual-contract]').inner_text():
            issues.append('delta-metric-semantics-missing')
        _choose_select_option(page, 'Measurement / Y', 'Measurement (nm)')
        if page.locator('[data-visual-metric]').get_attribute('data-visual-metric') != 'measurement_nm':
            issues.append('measurement-metric-semantics-missing')
        page.get_by_role('radio', name='Scatter', exact=True).click(); page.wait_for_timeout(180)
        _choose_select_option(page, 'X (scatter)', 'Target (nm)')
        _choose_select_option(page, 'Y (scatter)', 'Yield (%)')
        if 'X: Target (nm) · Y: Yield (%)' not in page.locator('[data-visual-contract]').inner_text():
            issues.append('scatter-field-mapping-not-applied')
        for label, kind in (('Trend', 'line'), ('Distribution', 'bar'), ('Scatter', 'scatter'), ('SPC', 'control'), ('Wafer', 'wafer')):
            page.get_by_role('radio', name=label, exact=True).click(); page.wait_for_timeout(180)
            if page.locator('[data-chart-kind="%s"]' % kind).count() != 1:
                issues.append(f'chart-kind-missing:{kind}')
        _select_row(page, 0); page.wait_for_timeout(650)
        if 'Selected records: 0' not in page.locator('[data-visualize-population]').inner_text():
            issues.append('linked-deselect-did-not-restore-filtered-population')
    except Exception as exc:
        issues.append(f'visualize-interaction:{type(exc).__name__}:{exc}')

    try:
        # Import: stage, cancel without mutation, then confirm a second stage.
        open_lab('Import', wait=650)
        before = page.get_by_text('64 active rows', exact=False).count()
        page.get_by_role('button', name='Show missing', exact=True).click(); page.wait_for_timeout(100)
        if 'Missing values' not in page.locator('.cui-data-dock-quality-results').inner_text():
            issues.append('import-missing-quality-action-missing')
        page.get_by_role('button', name='Show duplicates', exact=True).click(); page.wait_for_timeout(100)
        if 'Duplicate rows' not in page.locator('.cui-data-dock-quality-results').inner_text():
            issues.append('import-duplicate-quality-action-missing')
        page.get_by_role('button', name='Show issues', exact=True).click(); page.wait_for_timeout(100)
        if 'Quality issues' not in page.locator('.cui-data-dock-quality-results').inner_text():
            issues.append('import-issues-quality-action-missing')
        page.get_by_role('radio', name='Paste example', exact=True).click(force=True); page.wait_for_timeout(180)
        paste = page.locator('textarea[aria-label="Paste data"]')
        paste.wait_for(state='visible', timeout=8000)
        paste.fill('record_id\tmeasurement_nm\tstatus\nR-STAGED\t52.2\tWatch\n')
        page.get_by_role('button', name='Preview import', exact=True).click(); page.wait_for_timeout(220)
        if page.locator('[data-import-preview]').count() != 1:
            issues.append('import-preview-missing')
        capture('import_staged_preview')
        if page.get_by_text('64 active rows', exact=False).count() != before:
            issues.append('import-mutated-before-confirm')
        page.get_by_role('button', name='Cancel', exact=True).wait_for(state='visible', timeout=5000)
        page.get_by_role('button', name='Cancel', exact=True).click()
        page.locator('[data-import-preview]').wait_for(state='detached', timeout=5000)
        if page.locator('[data-import-preview]').count() != 0:
            issues.append('import-cancel-did-not-discard')
        page.get_by_role('radio', name='Paste example', exact=True).click(); page.wait_for_timeout(100)
        committed_paste = page.locator('textarea[aria-label="Paste data"]')
        committed_paste.wait_for(state='visible', timeout=8000)
        committed_paste.fill('record_id\tmeasurement_nm\tstatus\nR-COMMIT\t52.4\tNominal\n')
        page.get_by_role('button', name='Preview import', exact=True).click(); page.wait_for_timeout(400)
        page.get_by_role('button', name='Confirm import', exact=True).wait_for(state='visible', timeout=5000)
        page.get_by_role('button', name='Confirm import', exact=True).click(); page.wait_for_timeout(900)
        if 'Imported 1 row' not in page.locator('body').inner_text() and 'Imported 1 rows' not in page.locator('body').inner_text():
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
        page.get_by_role('button', name='Last page', exact=True).click(); page.wait_for_timeout(550)
        if 'Page 25000 of 25000' not in page_label.inner_text() or page.locator('.ag-center-cols-container .ag-row').count() != 10:
            issues.append('server-last-page-contract-invalid')
        page.get_by_role('combobox').click(); page.get_by_role('option', name='25', exact=True).click(); page.wait_for_timeout(450)
        if 'Page 1 of 10000' not in page_label.inner_text() or page.locator('.ag-center-cols-container .ag-row').count() != 25:
            issues.append('server-page-size-not-applied')
        page.get_by_role('button', name='Last page', exact=True).click(); page.wait_for_timeout(550)
        if 'Page 10000 of 10000' not in page_label.inner_text() or page.locator('.ag-center-cols-container .ag-row').count() != 25:
            issues.append('server-page-size-last-page-invalid')
        server_search = page.get_by_label('Search table')
        server_search.fill('ETCH-021'); page.wait_for_timeout(2200)
        if '62,500 matching records' not in server_status.inner_text():
            issues.append('server-search-total-invalid')
        page.get_by_role('button', name='Fail next request', exact=True).click(); page.wait_for_timeout(250)
        page.get_by_role('button', name='Refresh table', exact=True).click(); page.wait_for_timeout(1200)
        if 'Stale data' not in page.locator('.cui-table-footer').inner_text() or 'Provider request failed' not in server_status.inner_text():
            issues.append('server-stale-failure-not-visible')
        capture('server_stale_failure')
        page.get_by_role('button', name='Retry', exact=True).click(); page.wait_for_timeout(1400)
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
                _set_actual_theme(page, theme)
                for label in LABS:
                    if label != 'Grid':
                        page.get_by_role('radio', name=label).click()
                        page.locator(f'[data-active-lab="{label.lower()}"]').wait_for(state='visible', timeout=10000)
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
