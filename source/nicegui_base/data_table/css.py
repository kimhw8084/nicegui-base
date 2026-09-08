from __future__ import annotations


def build_data_table_css() -> str:
    return r'''
:root {
  --cui-table-row-comfortable: 44px;
  --cui-table-row-compact: 38px;
  --cui-table-row-dense: 34px;
  --cui-table-header-comfortable: 46px;
  --cui-table-header-compact: 40px;
  --cui-table-header-dense: 36px;
  --cui-table-header: var(--cui-table-header-compact);
  --cui-table-cell-x: 12px;
}
.cui-table-shell { border:1px solid var(--cui-border-subtle); border-radius:var(--cui-radius-md); background:var(--cui-surface); overflow:hidden; min-width:0; contain:layout; }
.cui-table-headline { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--cui-space-4); padding:var(--cui-space-4); border-bottom:1px solid var(--cui-border-subtle); }
.cui-table-title { font-size:var(--cui-type-heading-size); font-weight:var(--cui-font-weight-600); color:var(--cui-text-primary); }
.cui-table-description { color:var(--cui-text-secondary); font-size:var(--cui-type-caption-size); margin-top:2px; }
.cui-table-toolbar { min-height:50px; padding:7px 10px; display:flex; align-items:center; gap:10px; flex-wrap:nowrap; border-bottom:1px solid var(--cui-border-subtle); background:var(--cui-surface); }
.cui-table-search { height:34px; min-width:220px; max-width:440px; flex:1 1 340px; display:flex; align-items:center; gap:7px; padding:0 9px; border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-control); background:var(--cui-surface-secondary); color:var(--cui-text-secondary); transition:border-color var(--cui-duration-fast) var(--cui-easing-native),box-shadow var(--cui-duration-fast) var(--cui-easing-native),background var(--cui-duration-fast) var(--cui-easing-native); }
.cui-table-search:focus-within { border-color:var(--cui-accent); background:var(--cui-surface); box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 28%,transparent); }
.cui-table-search__icon { width:16px; height:16px; display:grid; place-items:center; flex:0 0 16px; color:var(--cui-text-tertiary); }
.cui-table-search__icon .cui-svg-icon { width:16px; height:16px; }
.cui-table-search__input { width:100%; min-width:0; height:32px; padding:0; border:0; outline:0; appearance:none; background:transparent; color:var(--cui-text-primary); font:inherit; font-size:var(--cui-font-size-13); line-height:var(--cui-line-height-32); }
.cui-table-search__input::placeholder { color:var(--cui-text-tertiary); opacity:1; }
.cui-table-search__input::-webkit-search-cancel-button { opacity:.55; cursor:pointer; }
.cui-table-search__shortcut { min-width:20px; height:20px; display:grid; place-items:center; padding:0 5px; border:1px solid var(--cui-border-subtle); border-bottom-color:var(--cui-border-default); border-radius:var(--cui-radius-micro); background:var(--cui-surface); color:var(--cui-text-tertiary); font:var(--cui-font-weight-600) var(--cui-font-size-10)/var(--cui-line-height-ratio-1) ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; box-shadow:0 1px 0 var(--cui-border-subtle); }
.cui-table-toolbar__actions { margin-left:auto; display:flex; align-items:center; justify-content:flex-end; gap:4px; flex:0 0 auto; }
.cui-table-tool-button { min-height:34px !important; height:34px !important; padding:0 9px !important; border-radius:var(--cui-radius-inner) !important; border:1px solid transparent !important; background:transparent !important; color:var(--cui-text-secondary) !important; box-shadow:none !important; }
.cui-table-tool-button:hover { background:var(--cui-surface-secondary) !important; color:var(--cui-text-primary) !important; }
.cui-table-tool-button:focus-visible { box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent) !important; }
.cui-table-tool-button .q-btn__content { gap:6px !important; min-height:32px; display:flex; align-items:center; justify-content:center; }
.cui-table-tool-button .cui-svg-icon-host { width:16px; height:16px; display:grid; place-items:center; }
.cui-table-tool-button .q-label { font-size:var(--cui-font-size-12); font-weight:var(--cui-font-weight-620); line-height:var(--cui-line-height-16); white-space:nowrap; }
.cui-table-toolbar__spacer { flex:1 1 auto; }
.cui-table-density-menu { min-width:220px; }
.cui-table-density-option { width:100%; min-height:44px !important; justify-content:flex-start !important; }
.cui-table-density-option__copy { display:flex; flex-direction:column; align-items:flex-start; gap:1px; }
.cui-table-density-option__meta { font-size:var(--cui-font-size-10); line-height:var(--cui-line-height-14); color:var(--cui-text-tertiary); }
.cui-table-view-menu { min-width:240px; }
.cui-table-view-option { width:100%; min-height:40px !important; justify-content:space-between !important; gap:14px !important; }
.cui-table-view-option__meta { color:var(--cui-text-tertiary); font-size:var(--cui-font-size-10); line-height:var(--cui-line-height-14); }
.cui-table-column-menu { min-width:240px; }
.cui-table-column-list { display:flex; flex-direction:column; gap:2px; max-height:320px; overflow:auto; padding:2px 0; }
.cui-table-column-option { position:relative; min-height:34px; display:flex; align-items:center; gap:9px; padding:6px 8px; border-radius:var(--cui-radius-inner); cursor:pointer; color:var(--cui-text-primary); }
.cui-table-column-option:hover { background:var(--cui-surface-hover); }
.cui-table-column-option__native { position:absolute; inline-size:1px; block-size:1px; opacity:0; pointer-events:none; }
.cui-table-column-option__check { width:16px; height:16px; display:grid; place-items:center; border:1.5px solid var(--cui-border-strong); border-radius:var(--cui-radius-micro); background:var(--cui-surface); transition:background var(--cui-duration-fast) var(--cui-easing-native),border-color var(--cui-duration-fast) var(--cui-easing-native),box-shadow var(--cui-duration-fast) var(--cui-easing-native); }
.cui-table-column-option__native:checked + .cui-table-column-option__check { background:var(--cui-accent); border-color:var(--cui-accent); }
.cui-table-column-option__native:checked + .cui-table-column-option__check::after { content:''; width:7px; height:4px; border-left:1.7px solid var(--cui-text-inverse); border-bottom:1.7px solid var(--cui-text-inverse); transform:translateY(-1px) rotate(-45deg); }
.cui-table-column-option__native:focus-visible + .cui-table-column-option__check { box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent); }
.cui-table-column-option__label { font-size:var(--cui-font-size-12); line-height:var(--cui-line-height-18); font-weight:var(--cui-font-weight-520); }
.cui-table-selection-bar { display:flex; align-items:center; gap:8px; padding:6px 10px; min-height:44px; background:var(--cui-accent-soft); border-bottom:1px solid color-mix(in srgb,var(--cui-accent) 22%,var(--cui-border-subtle)); color:var(--cui-text-primary); }
.cui-table-viewport { width:100%; overflow:auto; position:relative; }
.cui-data-table { width:100%; border-collapse:separate; border-spacing:0; table-layout:auto; color:var(--cui-text-primary); font-size:var(--cui-type-data-size); font-variant-numeric:tabular-nums; }
.cui-data-table th { position:relative; height:var(--cui-table-header); padding:0 var(--cui-table-cell-x); background:var(--cui-surface-secondary); color:var(--cui-text-secondary); font-size:var(--cui-type-label-size); font-weight:var(--cui-font-weight-600); text-align:left; white-space:nowrap; border-bottom:1px solid var(--cui-border-default); }
.cui-data-table td { padding:0 var(--cui-table-cell-x); border-bottom:1px solid var(--cui-border-subtle); white-space:nowrap; vertical-align:middle; }
.cui-data-table--comfortable td { height:var(--cui-table-row-comfortable); }
.cui-data-table--compact td { height:var(--cui-table-row-compact); }
.cui-data-table--dense td { height:var(--cui-table-row-dense); }
.cui-data-table tr:last-child td { border-bottom:0; }
.cui-data-table tbody tr { transition:background-color var(--cui-motion-fast) var(--cui-ease-standard); }
.cui-data-table tbody tr:hover { background:var(--cui-surface-hover); }
.cui-data-table tbody tr.is-selected { background:var(--cui-accent-soft); }
.cui-data-table tbody tr:focus-within { outline:2px solid var(--cui-focus-ring); outline-offset:-2px; }
.cui-data-table .is-numeric { text-align:right; }
.cui-data-table .is-center { text-align:center; }
.cui-data-table .is-muted { color:var(--cui-text-tertiary); }
.cui-data-table .is-pinned-left { position:sticky; left:0; z-index:2; background:inherit; box-shadow:1px 0 var(--cui-border-subtle); }
.cui-data-table .is-pinned-right { position:sticky; right:0; z-index:2; background:inherit; box-shadow:-1px 0 var(--cui-border-subtle); }
.cui-table-sort { display:inline-flex; gap:4px; align-items:center; }
.cui-table-sort__icon { opacity:.45; }
.cui-table-sort.is-active .cui-table-sort__icon { opacity:1; color:var(--cui-accent); }
.cui-table-status { min-height:22px; display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:3px 7px; border-radius:var(--cui-radius-pill); font-size:var(--cui-font-size-11); font-weight:var(--cui-font-weight-600); background:var(--cui-surface-secondary); }
.cui-table-status::before { content:''; width:6px; height:6px; border-radius:var(--cui-radius-circle); background:currentColor; }
.cui-table-status--success { color:var(--cui-success); background:var(--cui-success-soft); }
.cui-table-status--warning { color:var(--cui-warning); background:var(--cui-warning-soft); }
.cui-table-status--danger { color:var(--cui-danger); background:var(--cui-danger-soft); }
.cui-table-status--info { color:var(--cui-info); background:var(--cui-info-soft); }
.cui-table-cell--warning { background:var(--cui-warning-soft); color:var(--cui-text-primary); }
.cui-table-cell--danger { background:var(--cui-danger-soft); color:var(--cui-text-primary); }
.cui-table-cell--success { background:var(--cui-success-soft); color:var(--cui-text-primary); }
.cui-data-table .ag-cell.cui-table-cell--pending { background:color-mix(in srgb,var(--cui-accent) 8%,var(--cui-surface)); position:relative; }
.cui-data-table .ag-cell.cui-table-cell--pending::after { content:''; position:absolute; right:6px; top:6px; width:5px; height:5px; border-radius:var(--cui-radius-circle); background:var(--cui-accent); opacity:.75; }
.cui-table-expanded { background:var(--cui-surface-secondary); }
.cui-table-expanded > td { padding:var(--cui-space-4); white-space:normal; }
.cui-table-footer { min-height:40px; display:flex; align-items:center; gap:10px; padding:6px 10px; border-top:1px solid var(--cui-border-subtle); color:var(--cui-text-secondary); font-size:var(--cui-type-caption-size); }
.cui-table-footer__spacer { flex:1; }
.cui-table-footer-density { color:var(--cui-text-tertiary); font-variant-numeric:tabular-nums; }
.cui-table-empty { min-height:220px; display:grid; place-items:center; text-align:center; color:var(--cui-text-secondary); padding:var(--cui-space-6); }
.cui-table-empty strong { display:block; color:var(--cui-text-primary); margin-bottom:4px; }
.cui-table-error { display:grid; gap:var(--cui-gap-control-content); padding:var(--cui-gap-content); border:1px solid var(--cui-danger); border-radius:var(--cui-radius-surface); background:var(--cui-danger-soft); color:var(--cui-text-primary); }
.cui-table-refreshing { display:flex; align-items:center; gap:var(--cui-gap-control-content); min-height:34px; padding:var(--cui-gap-control-content) var(--cui-gap-content); border:1px solid var(--cui-warning); border-radius:var(--cui-radius-control); background:var(--cui-warning-soft); color:var(--cui-text-primary); }
.cui-table-loading { min-height:220px; padding:12px; display:grid; gap:7px; }
.cui-table-loading__row { height:28px; border-radius:var(--cui-radius-inner); background:linear-gradient(90deg,var(--cui-surface-secondary),var(--cui-surface-hover),var(--cui-surface-secondary)); background-size:200% 100%; animation:cui-table-shimmer var(--cui-duration-table-shimmer) infinite var(--cui-easing-linear); }
@keyframes cui-table-shimmer { to { background-position:-200% 0; } }
.cui-table-editable { border:1px solid transparent; border-radius:var(--cui-radius-inner); padding:3px 5px; margin:-4px -6px; }
.cui-table-editable:hover { border-color:var(--cui-border-default); background:var(--cui-surface); }
.cui-table-editable.is-error { border-color:var(--cui-danger); background:var(--cui-danger-soft); }
.cui-table-sparkline { width:76px; height:22px; display:block; overflow:visible; color:var(--cui-accent); }
.cui-table-sparkline polyline { stroke:currentColor; stroke-width:1.6; stroke-linejoin:round; stroke-linecap:round; opacity:.88; }
.cui-table-sparkline circle { fill:currentColor; }
.cui-table-mobile-card { display:none; }

/* AG Grid: NiceGUI Base owns the complete visible grid grammar. */
.cui-data-table {
  --ag-font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --ag-font-size:var(--cui-type-data-size);
  --ag-foreground-color:var(--cui-text-primary);
  --ag-secondary-foreground-color:var(--cui-text-secondary);
  --ag-disabled-foreground-color:var(--cui-text-tertiary);
  --ag-background-color:var(--cui-surface);
  --ag-header-background-color:var(--cui-surface-secondary);
  --ag-odd-row-background-color:var(--cui-surface);
  --ag-row-hover-color:var(--cui-surface-hover);
  --ag-selected-row-background-color:var(--cui-accent-soft);
  --ag-border-color:var(--cui-border-subtle);
  --ag-secondary-border-color:var(--cui-border-subtle);
  --ag-row-border-color:var(--cui-border-subtle);
  --ag-input-border-color:var(--cui-border-default);
  --ag-input-focus-border-color:var(--cui-accent);
  --ag-checkbox-checked-color:var(--cui-accent);
  --ag-checkbox-unchecked-color:var(--cui-border-strong);
  --ag-checkbox-indeterminate-color:var(--cui-accent);
  --ag-range-selection-border-color:var(--cui-accent);
  --ag-range-selection-background-color:color-mix(in srgb,var(--cui-accent) 10%,transparent);
  --ag-header-height:var(--cui-table-header);
  --ag-row-height:var(--cui-table-row-compact);
  --ag-list-item-height:32px;
  --ag-grid-size:6px;
  --ag-cell-horizontal-padding:var(--cui-table-cell-x);
  --ag-wrapper-border-radius:var(--cui-radius-md);
  --ag-card-radius:var(--cui-radius-md);
  --ag-card-shadow:var(--cui-shadow-2);
  --ag-popup-shadow:var(--cui-shadow-2);
  --ag-focus-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 34%,transparent);
  font-variant-numeric:tabular-nums;
  background:var(--cui-surface);
  color:var(--cui-text-primary);
}
.cui-data-table--comfortable { --ag-row-height:var(--cui-table-row-comfortable); --ag-header-height:var(--cui-table-header-comfortable); }
.cui-data-table--compact { --ag-row-height:var(--cui-table-row-compact); --ag-header-height:var(--cui-table-header-compact); }
.cui-data-table--dense { --ag-row-height:var(--cui-table-row-dense); --ag-header-height:var(--cui-table-header-dense); }
.cui-data-table .ag-root-wrapper { border:0 !important; border-radius:0; background:var(--cui-surface); color:var(--cui-text-primary); }
.cui-data-table .ag-header { border-bottom:1px solid var(--cui-border-default); background:var(--cui-surface-secondary); }
.cui-data-table .ag-header-cell, .cui-data-table .ag-header-group-cell { padding-inline:var(--cui-table-cell-x); color:var(--cui-text-secondary); font-size:var(--cui-type-label-size); font-weight:var(--cui-font-weight-650); letter-spacing:var(--cui-type-label-tracking); }
.cui-data-table .ag-header-cell:hover { background:var(--cui-surface-hover); color:var(--cui-text-primary); }
.cui-data-table .ag-header-cell-resize::after { width:1px; height:50%; background:var(--cui-border-default); }
.cui-data-table .ag-header-cell-resize:hover::after { width:2px; background:var(--cui-accent); }
.cui-data-table .ag-sort-indicator-icon, .cui-data-table .ag-header-icon { color:var(--cui-text-tertiary); opacity:.82; }
.cui-data-table .ag-header-cell-sorted-asc .ag-sort-indicator-icon, .cui-data-table .ag-header-cell-sorted-desc .ag-sort-indicator-icon { color:var(--cui-accent); opacity:1; }
.cui-data-table .ag-row { border-bottom:1px solid var(--cui-border-subtle); color:var(--cui-text-primary); }
.cui-data-table--striped .ag-row-even { background:var(--cui-surface-secondary); }
.cui-data-table--striped .ag-row-odd { background:var(--cui-surface); }
.cui-data-table--striped .ag-row:nth-child(even) { background:var(--cui-surface-secondary); }
.cui-data-table--striped .ag-row-even:hover, .cui-data-table--striped .ag-row-odd:hover { background:var(--cui-surface-hover); }
.cui-data-table .ag-row-hover { background:var(--cui-surface-hover) !important; }
.cui-data-table .ag-row-selected { background:var(--cui-accent-soft) !important; }
.cui-data-table .ag-row-selected::before { background:transparent !important; }
.cui-data-table .ag-cell { display:flex; align-items:center; padding-inline:var(--cui-table-cell-x); border-right:0; line-height:normal; }
.cui-data-table .ag-cell:focus, .cui-data-table .ag-cell-focus { border:1px solid var(--cui-accent) !important; box-shadow:inset 0 0 0 1px var(--cui-accent); }
.cui-data-table .ag-cell-inline-editing { background:var(--cui-surface-elevated); border:1px solid var(--cui-accent) !important; border-radius:var(--cui-radius-sm); box-shadow:var(--cui-shadow-1); }
.cui-data-table .ag-cell-inline-editing input, .cui-data-table .ag-cell-inline-editing textarea { color:var(--cui-text-primary); background:transparent; font:inherit; }
.cui-data-table .ag-pinned-left-header, .cui-data-table .ag-pinned-left-cols-container { box-shadow:1px 0 var(--cui-border-default); }
.cui-data-table .ag-pinned-right-header, .cui-data-table .ag-pinned-right-cols-container { box-shadow:-1px 0 var(--cui-border-default); }
.cui-data-table .ag-checkbox-input-wrapper { width:16px; height:16px; border:1.5px solid var(--cui-border-strong); border-radius:var(--cui-radius-micro); background:var(--cui-surface); box-shadow:none; }
.cui-data-table .ag-checkbox-input-wrapper.ag-checked { background:var(--cui-accent); border-color:var(--cui-accent); }
.cui-data-table .ag-checkbox-input-wrapper::after { color:var(--cui-text-inverse); }
.cui-data-table .ag-paging-panel { min-height:44px; padding:6px 10px; border-top:1px solid var(--cui-border-subtle); color:var(--cui-text-secondary); font-size:var(--cui-type-caption-size); background:var(--cui-surface); }
.cui-data-table .ag-paging-button { width:30px; height:30px; border-radius:var(--cui-radius-sm); color:var(--cui-text-secondary); }
.cui-data-table .ag-paging-button:hover:not(.ag-disabled) { background:var(--cui-surface-hover); color:var(--cui-text-primary); }
.cui-data-table .ag-paging-button.ag-disabled { opacity:.35; }
.cui-data-table .ag-popup, .cui-data-table .ag-menu, .cui-data-table .ag-tabs-body, .ag-popup .ag-menu { color:var(--cui-text-primary); background:var(--cui-surface); }
.cui-data-table .ag-menu, .ag-popup .ag-menu { border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); box-shadow:var(--cui-shadow-2); overflow:hidden; }
.cui-data-table .ag-menu-option, .ag-popup .ag-menu-option { min-height:32px; color:var(--cui-text-primary); }
.cui-data-table .ag-menu-option:hover, .ag-popup .ag-menu-option:hover { background:var(--cui-surface-hover); }
.cui-data-table .ag-filter-toolpanel-header, .cui-data-table .ag-column-panel-column, .cui-data-table .ag-filter-condition { color:var(--cui-text-primary); background:var(--cui-surface); }
.cui-data-table .ag-input-field-input, .ag-popup .ag-input-field-input { min-height:30px; border:1px solid var(--cui-border-default) !important; border-radius:var(--cui-radius-sm) !important; background:var(--cui-surface) !important; color:var(--cui-text-primary) !important; padding:0 8px !important; font:inherit; }
.cui-data-table .ag-input-field-input:focus, .ag-popup .ag-input-field-input:focus { border-color:var(--cui-accent) !important; box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent); }
.cui-data-table .ag-overlay { background:color-mix(in srgb,var(--cui-surface) 92%,transparent); color:var(--cui-text-secondary); }
.cui-data-table .ag-overlay-loading-center, .cui-data-table .ag-overlay-no-rows-center { padding:12px 16px; border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); background:var(--cui-surface-elevated); color:var(--cui-text-secondary); box-shadow:var(--cui-shadow-1); }
.cui-data-table .ag-tooltip { padding:6px 8px; border:0; border-radius:var(--cui-radius-sm); background:var(--cui-text-primary); color:var(--cui-surface); box-shadow:var(--cui-shadow-1); font-size:var(--cui-font-size-11); }
.cui-data-table .ag-body-viewport, .cui-data-table .ag-body-horizontal-scroll-viewport, .cui-data-table .ag-center-cols-viewport { scrollbar-color:var(--cui-border-strong) transparent; scrollbar-width:thin; }
.cui-data-table .ag-body-viewport::-webkit-scrollbar, .cui-data-table .ag-body-horizontal-scroll-viewport::-webkit-scrollbar { width:10px; height:10px; }
.cui-data-table .ag-body-viewport::-webkit-scrollbar-thumb, .cui-data-table .ag-body-horizontal-scroll-viewport::-webkit-scrollbar-thumb { background:var(--cui-border-strong); border:3px solid transparent; background-clip:padding-box; border-radius:var(--cui-radius-pill); }

@media (max-width:899px) {
  .cui-table-toolbar { flex-wrap:wrap; gap:6px; }
  .cui-table-search { max-width:none; flex:1 1 100%; min-width:0; }
  .cui-table-toolbar__actions { width:100%; justify-content:flex-end; }
  .cui-data-table .cui-priority-low, .cui-data-table .ag-header-cell.cui-priority-low { display:none; }
  .cui-table-headline { padding:12px; }
  .cui-table-viewport { max-width:100%; }
  .cui-table-footer { flex-wrap:wrap; }
}
@media (max-width:620px) {
  .cui-table-tool-button .q-label { display:none; }
  .cui-table-tool-button { width:34px !important; min-width:34px !important; padding:0 !important; }
  .cui-table-tool-button .q-btn__content { gap:0 !important; }
  .cui-table-search__shortcut { display:none; }
}
@media (prefers-reduced-motion: reduce) { .cui-table-loading__row { animation:none; } }
'''

__all__=['build_data_table_css']
