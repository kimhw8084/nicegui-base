from __future__ import annotations


def build_constitution_css() -> str:
    """Final v1.6 visual/geometry constitution.

    This layer is intentionally loaded last. Earlier module CSS remains useful for
    component-specific anatomy, while this file owns cross-component laws that must
    never drift independently: radius, density, spacing, containment, alignment,
    surface hierarchy and modern visual treatment.
    """
    return r'''
/* ================================================================
   COMPANY UI v1.6 DESIGN CONSTITUTION
   NiceGUI/Quasar are mechanics. These rules own the rendered product.
   ================================================================ */
/* Core geometry, density, typography, palette and motion variables are emitted
   by design.css from nicegui_base.design.tokens. This constitution consumes them;
   it does not redeclare a second authority. */

*, *::before, *::after { box-sizing:border-box; }
html { background:var(--cui-page); }
body { margin:0; overflow-x:hidden; }
.nicegui-content, .cui-nicegui-content { width:100%; min-width:0; max-width:none; margin:0; padding:0 !important; gap:0 !important; }
:where(.cui-app-main,.cui-page,.cui-section,.cui-surface,.cui-panel,.cui-card,.cui-well,.cui-form,.cui-form-section,.cui-table-shell,.cui-chart-panel,.cui-viewer,.cui-eng-entity,.cui-evidence,.cui-dialog,.cui-drawer,.cui-pattern,.cui-pattern-slot) * { min-width:0; }
:where(.cui-page,.cui-section,.cui-surface,.cui-form,.cui-table-shell,.cui-chart-panel,.cui-viewer,.cui-eng-entity,.cui-evidence,.cui-pattern-slot) :where(.q-label,label,p,span,div) { overflow-wrap:anywhere; }
img,svg,canvas { max-width:100%; }

/* Geometry primitives. */
.cui-page { padding:var(--cui-page-gutter) !important; gap:var(--cui-section-gap) !important; align-items:stretch !important; }
.cui-section { gap:var(--cui-stack-gap) !important; align-items:stretch !important; }
.cui-stack { gap:var(--cui-stack-gap) !important; }
.cui-grid { gap:var(--cui-stack-gap) !important; align-items:stretch; }
.cui-layout-stack { display:flex; flex-direction:column; gap:var(--cui-gap-stack); min-width:0; }
.cui-layout-cluster { display:flex; align-items:center; flex-wrap:wrap; gap:var(--cui-gap-cluster); min-width:0; }
.cui-layout-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:var(--cui-gap-stack); min-width:0; }
.cui-surface-token { background:var(--cui-surface); color:var(--cui-text-primary); border:var(--cui-border-width-subtle) solid var(--cui-border-subtle); border-radius:var(--cui-radius-surface); box-shadow:var(--cui-elevation-raised); }
.cui-focus-ring:focus-visible { outline:var(--cui-state-focus-width) solid color-mix(in srgb,var(--cui-focus-ring) 58%,transparent); outline-offset:var(--cui-state-focus-offset); }
.cui-button:disabled,.cui-icon-button:disabled { opacity:var(--cui-state-disabled-opacity); }
.cui-pattern { gap:var(--cui-content-gap) !important; align-items:start !important; width:100%; min-width:0; }
.cui-pattern-slot { min-width:0; max-width:100%; overflow:visible; }
.cui-action-row,.cui-button-cluster,.cui-toolbar-group,.cui-inline-group { display:flex; align-items:center; gap:var(--cui-cluster-gap); flex-wrap:wrap; min-width:0; }
.cui-action-row { justify-content:flex-end; width:100%; }
.cui-form-stack,.cui-alert-stack,.cui-content-column { display:flex; flex-direction:column; gap:var(--cui-stack-gap); min-width:0; width:100%; }
.cui-content-column { max-width:880px; }
.cui-surface-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:var(--cui-stack-gap); width:100%; min-width:0; }
.cui-lab-inline { gap:var(--cui-cluster-gap) !important; }
.cui-lab-stack { gap:var(--cui-stack-gap) !important; }
.cui-lab-grid { gap:var(--cui-stack-gap) !important; }
.cui-lab-sample { overflow:hidden; }
.cui-lab-sample > * + * { margin-top:var(--cui-cluster-gap); }
.cui-lab-sample .cui-lab-inline > * { margin:0 !important; }

/* Surface hierarchy: neutral structural boundaries; no decorative colored outlines. */
.cui-surface--panel,.cui-surface--card,.cui-surface--well,.cui-surface--outlined,
.cui-panel,.cui-card,.cui-well,.cui-table-shell,.cui-chart-panel,.cui-viewer,.cui-eng-entity,.cui-evidence {
  border-radius:var(--cui-radius-surface) !important;
  border:1px solid var(--cui-border-subtle) !important;
  overflow:hidden;
}
.cui-surface--panel,.cui-panel { background:var(--cui-surface); box-shadow:none; }
.cui-surface--card,.cui-card { background:var(--cui-surface); box-shadow:var(--cui-shadow-1); }
.cui-surface--well,.cui-well { background:var(--cui-surface-secondary); box-shadow:none; }
.cui-surface.is-selected,.cui-surface--interactive.is-selected { border-color:var(--cui-border-subtle) !important; background:var(--cui-accent-soft) !important; box-shadow:0 0 0 1px color-mix(in srgb,var(--cui-accent) 18%,transparent); }
.cui-surface--panel,.cui-surface--card,.cui-surface--well { padding:var(--cui-surface-padding); }

/* Design System reference anatomy. Values remain token-driven so the live
   reference is an executable example of the same contract consumers import. */
.cui-d6c-reference-hero { display:flex; flex-direction:column; gap:var(--cui-gap-cluster); }
.cui-d6c-reference-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--cui-gap-section); min-width:0; }
.cui-d6c-token-family { display:flex; flex-direction:column; gap:var(--cui-gap-stack); min-width:0; padding:var(--cui-surface-padding); }
.cui-d6c-token-family__head { display:flex; flex-direction:column; gap:var(--cui-gap-control-content); }
.cui-d6c-token-list { display:flex; flex-direction:column; gap:var(--cui-gap-cluster); min-width:0; max-height:var(--cui-chart-standard-height); overflow:auto; }
.cui-d6c-token-row { display:grid; grid-template-columns:minmax(112px,.7fr) minmax(0,1.3fr); gap:var(--cui-gap-cluster); align-items:start; min-width:0; }
.cui-d6c-token-name { color:var(--cui-text-secondary); font-weight:var(--cui-font-weight-600); text-transform:capitalize; }
.cui-d6c-token-value { color:var(--cui-text-primary); overflow-wrap:anywhere; }
.cui-d6c-theme-grid,.cui-d6c-viewport-grid,.cui-d6c-density-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--cui-gap-stack); min-width:0; }
.cui-d6c-theme-card,.cui-d6c-viewport-card,.cui-d6c-density-card { display:flex; flex-direction:column; gap:var(--cui-gap-cluster); min-width:0; padding:var(--cui-gap-content); border:var(--cui-border-width-subtle) solid var(--cui-border-subtle); border-radius:var(--cui-radius-control); background:var(--cui-surface-secondary); }
.cui-d6c-color-row { display:grid; grid-template-columns:var(--cui-control-content-gap) minmax(0,1fr); gap:var(--cui-gap-cluster); align-items:center; min-width:0; }
.cui-d6c-swatch { width:var(--cui-control-content-gap); height:var(--cui-control-content-gap); border-radius:var(--cui-radius-control); border:var(--cui-border-width-subtle) solid var(--cui-border-default); }
.cui-d6c-viewport-card__title { font-weight:var(--cui-font-weight-650); text-transform:capitalize; }
.cui-d6c-state-row { display:flex; align-items:center; flex-wrap:wrap; gap:var(--cui-gap-cluster); padding-top:var(--cui-gap-stack); }
@media(max-width:900px) { .cui-d6c-reference-grid { grid-template-columns:1fr; } }
@media(max-width:600px) { .cui-d6c-theme-grid,.cui-d6c-viewport-grid,.cui-d6c-density-grid { grid-template-columns:1fr; } .cui-d6c-token-row { grid-template-columns:1fr; gap:var(--cui-gap-control-content); } }

/* Modern action grammar. */
.cui-button.q-btn,.cui-button,.cui-icon-button.q-btn,.cui-icon-button {
  min-height:var(--cui-control-height) !important;
  height:var(--cui-control-height);
  border:0 !important;
  border-radius:var(--cui-radius-control) !important;
  box-shadow:none !important;
  font-weight:var(--cui-font-weight-600);
  transition:background-color var(--cui-duration-feedback) var(--cui-ease-standard),color var(--cui-duration-feedback) var(--cui-ease-standard),box-shadow var(--cui-duration-feedback) var(--cui-ease-standard),transform var(--cui-duration-instant) var(--cui-ease-standard) !important;
}
.cui-button.q-btn { padding-inline:var(--cui-control-padding-x) !important; }
.cui-button.q-btn .q-btn__content,.cui-icon-button.q-btn .q-btn__content { min-height:100%; width:100%; display:flex; align-items:center; justify-content:center; gap:var(--cui-gap-control-content); line-height:var(--cui-line-height-ratio-1); }
.cui-button .cui-svg-icon-host,.cui-icon-button .cui-svg-icon-host { display:inline-grid; place-items:center; flex:0 0 auto; line-height:0; }
.cui-button .cui-svg-icon-host svg,.cui-icon-button .cui-svg-icon-host svg { display:block; margin:auto; }
.cui-button--primary { background:var(--cui-accent) !important; color:white !important; }
.cui-button--primary:hover { background:var(--cui-accent-hover) !important; }
.cui-button--secondary { background:var(--cui-surface-secondary) !important; color:var(--cui-text-primary) !important; }
.cui-button--secondary:hover { background:var(--cui-surface-hover) !important; }
.cui-button--tertiary { background:color-mix(in srgb,var(--cui-accent-soft) 70%,var(--cui-surface)) !important; color:var(--cui-accent) !important; }
.cui-button--ghost { background:transparent !important; color:var(--cui-text-secondary) !important; }
.cui-button--ghost:hover { background:var(--cui-surface-hover) !important; color:var(--cui-text-primary) !important; }
.cui-button--danger { background:var(--cui-danger) !important; color:white !important; }
.cui-button--danger:hover { background:color-mix(in srgb,var(--cui-danger) 88%,black) !important; }
.cui-icon-button { width:var(--cui-icon-button-size) !important; min-width:var(--cui-icon-button-size) !important; padding:0 !important; background:transparent !important; color:var(--cui-text-secondary) !important; }
.cui-icon-button:hover { background:var(--cui-surface-hover) !important; color:var(--cui-text-primary) !important; }
.cui-icon-button--primary { background:var(--cui-accent-soft) !important; color:var(--cui-accent) !important; }
.cui-icon-button--secondary,.cui-table-toolbar .cui-icon-button { background:var(--cui-surface-secondary) !important; color:var(--cui-text-secondary) !important; }
.cui-icon-button--danger { background:var(--cui-danger-soft) !important; color:var(--cui-danger) !important; }
.cui-button:focus-visible,.cui-icon-button:focus-visible { outline:none !important; box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 35%,transparent) !important; }
.cui-button:active:not(:disabled),.cui-icon-button:active:not(:disabled) { transform:scale(var(--cui-state-pressed-scale)); }

/* Joined controls are the only controls allowed to touch. */
.cui-button-group,.cui-split-button,.cui-segmented-control.q-btn-toggle {
  display:inline-flex; align-items:center; gap:2px !important; padding:3px !important;
  border:0 !important; border-radius:var(--cui-radius-control) !important; background:var(--cui-surface-secondary) !important; box-shadow:none !important;
}
.cui-button-group .cui-button,.cui-split-button .cui-button,.cui-segmented-control.q-btn-toggle>.q-btn {
  border:0 !important; border-radius:calc(var(--cui-radius-control) - 3px) !important; min-height:calc(var(--cui-control-height) - 6px) !important; height:calc(var(--cui-control-height) - 6px) !important;
}
.cui-button-group .cui-button--primary,.cui-segmented-control.q-btn-toggle>.q-btn[aria-pressed='true'],.cui-segmented-control.q-btn-toggle>.q-btn.q-btn--active {
  background:var(--cui-surface) !important; color:var(--cui-text-primary) !important; box-shadow:0 1px 3px rgba(0,0,0,.08) !important;
}

/* Status: semantic tinted fills, never colored outline decoration. */
.cui-badge,.cui-semantic-indicator,.cui-table-status,.cui-eng-status {
  border:0 !important; box-shadow:none !important;
}
.cui-badge { min-height:24px; padding:3px 9px; }
.cui-tag { display:inline-flex;align-items:center;gap:4px;min-height:22px;padding:2px 8px;border-radius:var(--cui-radius-pill);background:var(--cui-surface-secondary);color:var(--cui-text-secondary);font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-600); }
.cui-tag--info{color:var(--cui-info);}.cui-tag--success{color:var(--cui-success);}.cui-tag--warning{color:var(--cui-warning);}.cui-tag--danger{color:var(--cui-danger);}
.cui-badge--neutral { background:var(--cui-surface-secondary) !important; }

/* Unified field anatomy. */
.cui-form-field,.cui-field { gap:6px !important; }
.cui-field-label-row { min-height:18px; align-items:center; }
.cui-field-label { color:var(--cui-text-secondary); font-weight:var(--cui-font-weight-600); }
.cui-field-control.q-field,.cui-field-control {
  min-height:var(--cui-control-height) !important;
  border:0 !important; border-radius:var(--cui-radius-control) !important;
  background:var(--cui-surface-secondary) !important;
  box-shadow:inset 0 0 0 1px transparent !important;
  transition:background-color var(--cui-duration-feedback) var(--cui-ease-standard),box-shadow var(--cui-duration-feedback) var(--cui-ease-standard) !important;
}
.cui-field-control.q-field:hover:not(.q-field--disabled) { background:var(--cui-surface-hover) !important; }
.cui-field-control.q-field.q-field--focused { background:var(--cui-surface) !important; box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent),inset 0 0 0 1px color-mix(in srgb,var(--cui-accent) 32%,transparent) !important; }
.cui-field-control.q-field .q-field__control { min-height:var(--cui-control-height) !important; height:auto !important; border-radius:var(--cui-radius-control) !important; color:var(--cui-text-primary); padding:0 12px; }
.cui-field-control.q-field .q-field__control::before,.cui-field-control.q-field .q-field__control::after { border:0 !important; display:none !important; }
.cui-field-control.q-field .q-field__native,.cui-field-control.q-field .q-field__input,.cui-field-control.q-field .q-field__control-container { min-height:calc(var(--cui-control-height) - 2px); display:flex; align-items:center; color:var(--cui-text-primary); line-height:var(--cui-line-height-ratio-1_3); padding-top:0 !important; padding-bottom:0 !important; }
.cui-field-control.q-field .q-field__prepend,.cui-field-control.q-field .q-field__append { height:var(--cui-control-height) !important; display:flex; align-items:center; justify-content:center; padding:0 0 0 8px !important; }
.cui-field-control.q-textarea .q-field__control,.cui-field-control.q-textarea .q-field__native { height:auto !important; min-height:88px !important; align-items:flex-start; padding-top:10px !important; padding-bottom:10px !important; }
.cui-field-control--error,.has-error .cui-field-control { background:var(--cui-danger-soft) !important; box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--cui-danger) 20%,transparent) !important; }
.cui-field-error { margin-top:2px; }
.cui-choice.q-checkbox,.cui-choice.q-radio { min-height:var(--cui-control-height); display:flex; align-items:center; }
.cui-slider.q-slider { min-height:var(--cui-control-height); }

/* Forms and repeated vertical groups. */
.cui-form { gap:var(--cui-section-gap) !important; }
.cui-form-section { gap:var(--cui-stack-gap) !important; }
.cui-form-section__head { padding-bottom:12px !important; }
.cui-form-grid { gap:var(--cui-stack-gap) !important; }
.cui-form-actions { gap:var(--cui-cluster-gap) !important; padding-top:16px !important; }
.cui-validation-summary { border:0 !important; border-radius:var(--cui-radius-surface) !important; padding:16px 18px !important; background:var(--cui-danger-soft) !important; }

/* Alerts/progress: usable vertical rhythm and modern filled semantics. */
.cui-alert-stack > .cui-alert + .cui-alert,.cui-lab-sample > .cui-alert + .cui-alert { margin-top:10px; }
.cui-alert,.cui-banner { border:0 !important; border-radius:var(--cui-radius-surface) !important; padding:14px 16px !important; min-height:52px; align-items:flex-start !important; }
.cui-alert--neutral,.cui-banner--neutral { background:var(--cui-surface-secondary) !important; }
.cui-alert--success,.cui-banner--success { background:var(--cui-success-soft) !important; }
.cui-alert--warning,.cui-banner--warning { background:var(--cui-warning-soft) !important; }
.cui-alert--danger,.cui-banner--danger { background:var(--cui-danger-soft) !important; }
.cui-progress.q-linear-progress,.cui-progress { height:8px !important; min-height:8px !important; border-radius:var(--cui-radius-pill) !important; }
.cui-progress-metric { gap:10px !important; }
.cui-progress-metric__value { font-size:var(--cui-font-size-13) !important; font-weight:var(--cui-font-weight-650); }
.cui-skeleton { gap:10px !important; }

/* Shell: guaranteed non-overlap, premium title/subtitle and user area. */
.cui-app-header.q-header,.cui-app-header {
  min-height:var(--cui-shell-header-height) !important; height:var(--cui-shell-header-height) !important;
  padding:0 20px !important; background:color-mix(in srgb,var(--cui-surface) 92%,transparent) !important;
  color:var(--cui-text-primary) !important; border-bottom:1px solid var(--cui-border-subtle) !important;
  box-shadow:none !important; backdrop-filter:blur(22px); -webkit-backdrop-filter:blur(22px);
}
.cui-shell-brand { display:flex; align-items:center; gap:12px; min-width:0; }
.cui-shell-title-block { display:flex; flex-direction:column; gap:2px; min-width:0; animation:cui-title-enter var(--cui-duration-title) var(--cui-ease-enter) both; }
.cui-shell-title { font-size:var(--cui-font-size-16) !important; line-height:var(--cui-line-height-20) !important; font-weight:var(--cui-font-weight-680) !important; letter-spacing:-.016em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cui-shell-subtitle { font-size:var(--cui-font-size-11); line-height:var(--cui-line-height-15); color:var(--cui-text-tertiary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:min(58vw,760px); }
.cui-shell-actions { display:flex; align-items:center; gap:8px; margin-left:auto; }
.cui-shell-user { display:flex; align-items:center; gap:10px; padding:5px 6px 5px 10px; border-radius:var(--cui-radius-surface); background:var(--cui-surface-secondary); }
.cui-shell-greeting { display:flex; flex-direction:column; align-items:flex-end; line-height:var(--cui-line-height-ratio-1_15); }
.cui-shell-greeting__hello { font-size:var(--cui-font-size-10); color:var(--cui-text-tertiary); }
.cui-shell-greeting__name { font-size:var(--cui-font-size-12); font-weight:var(--cui-font-weight-650); color:var(--cui-text-primary); }
.cui-user-menu-trigger.q-btn { width:34px !important; height:34px !important; min-height:34px !important; min-width:34px !important; background:var(--cui-accent) !important; color:white !important; border-radius:var(--cui-radius-circle) !important; font-size:var(--cui-font-size-11); font-weight:var(--cui-font-weight-700); }
.cui-shell-menu { flex:0 0 auto; }
@keyframes cui-title-enter { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }
.cui-app-sidebar.q-drawer { top:var(--cui-shell-header-height) !important; height:calc(100dvh - var(--cui-shell-header-height)) !important; width:var(--cui-shell-sidebar-width) !important; background:var(--cui-surface) !important; border-right:1px solid var(--cui-border-subtle) !important; padding:10px 8px 14px; overflow:hidden; transition:width var(--cui-duration-shell) var(--cui-ease-standard) !important; }
html[data-sidebar='compact'] .cui-app-sidebar.q-drawer { width:var(--cui-shell-sidebar-compact-width) !important; }
.cui-sidebar-controls { display:flex; align-items:center; justify-content:flex-end; padding:2px 4px 10px; }
.cui-app-main { width:100%; min-width:0; min-height:calc(100dvh - var(--cui-shell-header-height)); padding-top:var(--cui-shell-header-height); background:var(--cui-page); }
.cui-app-main--with-sidebar { padding-left:var(--cui-shell-sidebar-width); transition:padding-left var(--cui-duration-shell) var(--cui-ease-standard); }
html[data-sidebar='compact'] .cui-app-main--with-sidebar { padding-left:var(--cui-shell-sidebar-compact-width); }
html[data-sidebar='compact'] .cui-app-sidebar .cui-nav-section-label,html[data-sidebar='compact'] .cui-app-sidebar .q-item__label { display:none !important; }
html[data-sidebar='compact'] .cui-app-sidebar .cui-nav-item { justify-content:center; }
.cui-nav-section-label { padding:10px 12px 6px !important; }
.cui-nav-item { min-height:38px !important; margin:2px 0 !important; padding:0 10px !important; border-radius:var(--cui-radius-control) !important; }
.cui-nav-item--active { background:var(--cui-accent-soft) !important; color:var(--cui-accent) !important; }

/* Page header/content hierarchy. */
.cui-page-header { gap:20px !important; align-items:flex-start !important; }
.cui-page-header__copy { gap:6px !important; }
.cui-page-title { font-size:var(--cui-font-size-26) !important; line-height:var(--cui-line-height-32) !important; font-weight:var(--cui-font-weight-700) !important; letter-spacing:-.03em !important; }
.cui-page-description { font-size:var(--cui-font-size-13) !important; line-height:var(--cui-line-height-19) !important; max-width:760px !important; }

/* Overlays: consistent overlay radius and composition gaps. */
.cui-dialog { border:0 !important; border-radius:var(--cui-radius-overlay) !important; box-shadow:var(--cui-shadow-2) !important; }
.cui-dialog__head { padding:20px 22px 14px !important; }
.cui-dialog__body { padding:0 22px 22px !important; display:flex; flex-direction:column; gap:var(--cui-stack-gap); }
.cui-dialog__footer { gap:var(--cui-cluster-gap) !important; padding:14px 22px 18px !important; border-top:1px solid var(--cui-border-subtle) !important; background:var(--cui-surface) !important; }
.cui-drawer { border:0 !important; }
.cui-drawer__header { padding:20px 22px 14px !important; }
.cui-drawer__body { padding:20px 22px !important; display:flex; flex-direction:column; gap:var(--cui-stack-gap); }
.cui-popover { display:flex !important; flex-direction:column; gap:6px !important; }
.cui-popover > .cui-button { width:100%; justify-content:flex-start; }
.cui-popover,.cui-menu,.cui-user-menu.q-menu { border:0 !important; border-radius:var(--cui-radius-surface) !important; padding:6px !important; box-shadow:var(--cui-shadow-2) !important; }
.cui-menu-item.q-btn,.cui-menu-item { min-height:36px !important; border-radius:var(--cui-radius-inner) !important; padding:0 10px !important; justify-content:flex-start !important; }
.cui-menu-item.q-btn .q-btn__content { justify-content:flex-start !important; width:100%; }

/* DataTable flagship visual law. */
.cui-table-shell { border:0 !important; border-radius:var(--cui-radius-surface) !important; box-shadow:inset 0 0 0 1px var(--cui-border-subtle); background:var(--cui-surface); overflow:hidden; }
.cui-table-headline { padding:18px 20px !important; }
.cui-table-toolbar { min-height:50px !important; padding:7px 10px !important; gap:10px !important; background:var(--cui-surface) !important; }
.cui-table-search { flex:1 1 340px !important; max-width:440px; }
.cui-data-table { height:min(62vh,620px); min-height:360px; --ag-row-height:var(--cui-table-row-height); --ag-header-height:var(--cui-table-header-height); --ag-wrapper-border-radius:0; }
.cui-data-table--comfortable,.cui-data-table--compact,.cui-data-table--dense { --ag-row-height:var(--cui-table-row-height); }
.cui-data-table .ag-header { border-bottom:1px solid var(--cui-border-subtle) !important; }
.cui-data-table .ag-header-cell,.cui-data-table .ag-header-group-cell { font-weight:var(--cui-font-weight-620) !important; }
.cui-data-table .ag-row { border-bottom:1px solid var(--cui-border-subtle) !important; }
.cui-data-table .ag-row-selected { background:var(--cui-accent-soft) !important; }
.cui-data-table .ag-cell-focus { border:0 !important; box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--cui-accent) 46%,transparent) !important; }
.cui-data-table .ag-menu,.ag-popup .ag-menu { border:0 !important; border-radius:var(--cui-radius-surface) !important; }
.cui-table-footer { min-height:40px !important; padding:6px 10px !important; }

/* Charts: finance/product-analytics visual language. */
.cui-chart-panel { border:0 !important; border-radius:var(--cui-radius-surface) !important; box-shadow:inset 0 0 0 1px var(--cui-border-subtle); background:var(--cui-surface); }
.cui-chart-panel__header { min-height:64px; padding:16px 18px 10px !important; gap:16px !important; align-items:flex-start !important; }
.cui-chart-panel__title { font-size:var(--cui-font-size-14) !important; font-weight:var(--cui-font-weight-680) !important; letter-spacing:-.012em; }
.cui-chart-panel__description { margin-top:3px; color:var(--cui-text-tertiary) !important; }
.cui-chart-toolbar { gap:4px !important; padding:2px !important; border-radius:var(--cui-radius-surface); background:var(--cui-surface-secondary); }
.cui-chart-toolbar .cui-icon-button { width:32px !important; min-width:32px !important; height:32px !important; min-height:32px !important; background:transparent !important; }
.cui-chart-toolbar .cui-icon-button:hover { background:var(--cui-surface) !important; box-shadow:0 1px 3px rgba(0,0,0,.08) !important; }
.cui-chart-panel__body { padding:0 8px 8px !important; }
.cui-chart-canvas { min-height:var(--cui-chart-standard-height) !important; }
.cui-chart-panel--compact .cui-chart-canvas { min-height:280px !important; }
.cui-chart-panel--large .cui-chart-canvas { min-height:var(--cui-chart-large-height) !important; }
.cui-chart-panel--workspace .cui-chart-canvas { min-height:var(--cui-chart-workspace-height) !important; }


/* Purpose-built wafer / die-residual renderer. */
.cui-spatial-panel .cui-chart-panel__body { padding:4px 12px 14px !important; }
.cui-spatial-viewport { position:relative; width:100%; min-height:390px; overflow:hidden; border-radius:var(--cui-radius-surface); background:linear-gradient(180deg,color-mix(in srgb,var(--cui-surface-secondary) 72%,transparent),transparent); cursor:grab; touch-action:none; }
.cui-spatial-viewport.is-dragging { cursor:grabbing; }
.cui-spatial-svg-host { width:100%; height:100%; min-height:390px; transform-origin:50% 50%; transition:transform var(--cui-duration-fast) var(--cui-ease-standard); will-change:transform; }
.cui-spatial-svg-host svg { width:100%; height:100%; display:block; overflow:hidden; }
.cui-wafer-boundary,.cui-spatial-grid-outline { fill:none; stroke:var(--cui-border-strong); stroke-width:1.6; vector-effect:non-scaling-stroke; }
.cui-wafer-contour-band { fill-opacity:.92; }
.cui-wafer-contour-line { stroke:var(--cui-text-primary); stroke-width:1.25; stroke-opacity:.58; vector-effect:non-scaling-stroke; }
.cui-wafer-notch { fill:var(--cui-page); stroke:var(--cui-border-strong); stroke-width:1.6; vector-effect:non-scaling-stroke; }
.cui-wafer-guides circle,.cui-wafer-guides path { fill:none; stroke:var(--cui-border-subtle); stroke-width:1; stroke-dasharray:3 5; vector-effect:non-scaling-stroke; }
.cui-wafer-die,.cui-spatial-cell { stroke:color-mix(in srgb,var(--cui-surface) 88%,transparent); stroke-width:1.2; vector-effect:non-scaling-stroke; transition:opacity var(--cui-duration-micro) var(--cui-easing-native),stroke var(--cui-duration-micro) var(--cui-easing-native); }
.cui-wafer-die:hover,.cui-spatial-cell:hover { opacity:.76; stroke:var(--cui-text-primary); stroke-width:2; }
.cui-wafer-die.is-watch { stroke:var(--cui-warning); stroke-width:2.2; }
.cui-spatial-grid-bg { fill:var(--cui-surface-secondary); }
.cui-spatial-missing { fill:var(--cui-surface-secondary); stroke:var(--cui-border-default); stroke-dasharray:3 2; }
.cui-spatial-bin-0 { fill:#2764C5; }.cui-spatial-bin-1 { fill:#4B8FE7; }.cui-spatial-bin-2 { fill:#89B7F2; }.cui-spatial-bin-3 { fill:#DCE5EF; }.cui-spatial-bin-4 { fill:#F1C078; }.cui-spatial-bin-5 { fill:#E78263; }.cui-spatial-bin-6 { fill:#C94B48; }
[data-theme='dark'] .cui-spatial-bin-0 { fill:#386FC2; }[data-theme='dark'] .cui-spatial-bin-1 { fill:#568FD7; }[data-theme='dark'] .cui-spatial-bin-2 { fill:#7FA9D9; }[data-theme='dark'] .cui-spatial-bin-3 { fill:#69717A; }[data-theme='dark'] .cui-spatial-bin-4 { fill:#C89858; }[data-theme='dark'] .cui-spatial-bin-5 { fill:#C66B55; }[data-theme='dark'] .cui-spatial-bin-6 { fill:#B84E4E; }
.cui-spatial-legend-title { fill:var(--cui-text-secondary); font:var(--cui-font-weight-600) var(--cui-font-size-11) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.cui-spatial-legend-label,.cui-spatial-annotation { fill:var(--cui-text-tertiary); font:var(--cui-font-size-10) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; letter-spacing:.02em; }

/* Content/workflow: avoid left-squash and edge collisions. */
.cui-viewer,.cui-key-value-list,.cui-property-grid,.cui-activity-feed,.cui-notification-center,.cui-search-results,.cui-progress-steps,.cui-compare-panel,.cui-before-after { width:100%; min-width:0; }
.cui-key-value-list,.cui-property-grid,.cui-activity-feed,.cui-notification-center,.cui-search-results { display:flex; flex-direction:column; gap:10px; }
.cui-metric-strip { gap:var(--cui-stack-gap) !important; }
.cui-metric-card { border:0 !important; border-radius:var(--cui-radius-surface) !important; padding:18px !important; background:var(--cui-surface); box-shadow:inset 0 0 0 1px var(--cui-border-subtle); }
.cui-command-palette { border:0 !important; border-radius:var(--cui-radius-overlay) !important; }

/* Engineering/RCA: consistent cockpit spacing. */
.cui-eng-entity,.cui-evidence,.cui-confidence,.cui-baseline,.cui-rca-balance,.cui-property-grid { min-width:0; }
.cui-eng-entity { padding:18px !important; }
.cui-evidence { padding:16px !important; border:0 !important; box-shadow:inset 0 0 0 1px var(--cui-border-subtle); }
.cui-evidence--supports { background:var(--cui-success-soft) !important; }
.cui-evidence--contradicts { background:var(--cui-danger-soft) !important; }
.cui-evidence--neutral { background:var(--cui-surface-secondary) !important; }
.cui-property-grid { gap:10px !important; }

/* Lab itself must never be the source of spacing defects. */
.cui-lab-section { gap:var(--cui-stack-gap) !important; }
.cui-lab-section + .cui-lab-section { margin-top:var(--cui-section-gap) !important; }
.cui-lab-sample { padding:var(--cui-surface-padding) !important; border-radius:var(--cui-radius-surface) !important; }
.cui-lab-swatch { border-radius:var(--cui-radius-surface) !important; }
.cui-lab-controlbar { border:0 !important; border-radius:var(--cui-radius-surface) !important; box-shadow:var(--cui-shadow-1) !important; }


/* Motion laboratory / canonical motion examples. */
.cui-motion-demo-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:var(--cui-stack-gap); width:100%; }
.cui-motion-demo { min-height:92px; padding:18px; border-radius:var(--cui-radius-surface); background:var(--cui-surface-secondary); display:flex; flex-direction:column; justify-content:center; gap:4px; }
.cui-motion-demo--title.is-replaying { animation:cui-motion-title var(--cui-duration-title-long) var(--cui-ease-enter) both; }
.cui-motion-demo--section.is-replaying { animation:cui-motion-section var(--cui-duration-section) var(--cui-ease-enter) both; }
.cui-motion-demo--selection.is-replaying { animation:cui-motion-selection var(--cui-duration-selection) var(--cui-ease-standard) both; }
@keyframes cui-motion-title { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }
@keyframes cui-motion-section { from{opacity:0;transform:translateY(10px) scale(.99)} to{opacity:1;transform:none} }
@keyframes cui-motion-selection { 0%{box-shadow:0 0 0 0 transparent} 45%{box-shadow:0 0 0 5px color-mix(in srgb,var(--cui-accent) 18%,transparent)} 100%{box-shadow:0 0 0 0 transparent} }

/* User-forced reduced motion in addition to OS preference. */
html[data-motion='reduced'] *, html[data-motion='reduced'] *::before, html[data-motion='reduced'] *::after,
html.cui-force-reduced-motion *, html.cui-force-reduced-motion *::before, html.cui-force-reduced-motion *::after {
  animation-duration:var(--cui-duration-reduced) !important; animation-iteration-count:1 !important; transition-duration:var(--cui-duration-reduced) !important; scroll-behavior:auto !important;
}

@media(max-width:1199px) {
}
@media(max-width:899px) {
  .cui-performance-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .cui-app-main--with-sidebar { padding-left:0 !important; }
  .cui-app-sidebar.q-drawer { top:var(--cui-shell-header-height) !important; }
  .cui-shell-greeting { display:none; }
  .cui-page { padding:var(--cui-page-gutter) !important; }
  .cui-action-row { justify-content:flex-start; }
  .cui-chart-canvas { min-height:320px !important; }
}
@media(max-width:599px) {
  .cui-performance-metrics { grid-template-columns:1fr; }
  .cui-performance-head { flex-direction:column; }
  .cui-app-header.q-header,.cui-app-header { padding:0 12px !important; }
  .cui-shell-subtitle,.cui-environment-badge { display:none !important; }
  .cui-page-title { font-size:var(--cui-font-size-22) !important; line-height:var(--cui-line-height-28) !important; }
  .cui-page { padding:16px !important; gap:22px !important; }
  .cui-lab-grid { grid-template-columns:minmax(0,1fr) !important; }
  .cui-motion-demo-grid { grid-template-columns:1fr; }
  .cui-lab-grid > * { grid-column:1/-1 !important; }
  .cui-dialog { border-radius:0 !important; }
  .cui-table-search { flex-basis:100% !important; max-width:none !important; }
  .cui-chart-canvas { min-height:280px !important; }
}
'''.strip() + '\n'


__all__ = ['build_constitution_css']
