from __future__ import annotations


def build_visual_normalization_css() -> str:
    """Normalize NiceGUI/Quasar internals so NiceGUI Base owns visible styling.

    These selectors intentionally target stable public Quasar class names while all
    application code continues to use semantic NiceGUI Base wrappers.
    """
    return r'''
:root {
  --cui-on-accent: var(--cui-text-inverse);
  --cui-control-border: var(--cui-border-default);
  --cui-control-border-hover: var(--cui-border-strong);
  --cui-control-bg: var(--cui-surface);
  --cui-control-bg-muted: var(--cui-surface-secondary);
  --q-primary: var(--cui-accent);
  --q-positive: var(--cui-success);
  --q-negative: var(--cui-danger);
  --q-info: var(--cui-info);
  --q-warning: var(--cui-warning);
}
html, body, .nicegui-content, .q-layout, .q-page, .q-drawer, .q-dialog, .q-menu, .q-tooltip {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
body { font-size: var(--cui-type-body-size); line-height: var(--cui-type-body-line); }
::selection { background: color-mix(in srgb, var(--cui-accent) 24%, transparent); color: var(--cui-text-primary); }

/* Quasar button reset: keep event/ripple/runtime mechanics, replace visible grammar. */
.cui-button.q-btn, .cui-icon-button.q-btn, .cui-chip.q-btn, .cui-menu-item.q-btn,
.cui-back-navigation.q-btn, .cui-page-navigation .q-btn, .cui-shell-menu.q-btn,
.cui-user-menu-trigger.q-btn {
  min-width: 0; min-height: 0; box-shadow: none !important; text-transform: none;
}
.cui-button.q-btn::before, .cui-icon-button.q-btn::before, .cui-chip.q-btn::before,
.cui-menu-item.q-btn::before, .cui-user-menu-trigger.q-btn::before { box-shadow: none !important; }
.cui-button.q-btn .q-focus-helper, .cui-icon-button.q-btn .q-focus-helper,
.cui-chip.q-btn .q-focus-helper, .cui-menu-item.q-btn .q-focus-helper,
.cui-user-menu-trigger.q-btn .q-focus-helper { display:none !important; }
.cui-button.q-btn .q-btn__content, .cui-icon-button.q-btn .q-btn__content,
.cui-chip.q-btn .q-btn__content, .cui-menu-item.q-btn .q-btn__content { gap:var(--cui-space-2); line-height:inherit; }

/* Fields and selects. */
.cui-field-control.q-field { box-shadow:none !important; }
.cui-field-control.q-field .q-field__inner { min-width:0; }
.cui-field-control.q-field .q-field__control-container { padding-top:0; }
.cui-field-control.q-field .q-field__prepend,
.cui-field-control.q-field .q-field__append { height:100%; color:var(--cui-text-tertiary); padding:0 0 0 var(--cui-space-2); }
.cui-field-control.q-field .q-field__append .q-icon,
.cui-field-control.q-field .q-field__prepend .q-icon { color:var(--cui-text-tertiary); font-size:0; width:18px; height:18px; position:relative; }
.cui-field-control.q-select .q-field__append .q-icon:not(.q-field__focusable-action)::after {
  content:''; position:absolute; inset:5px 4px 7px; border-right:1.5px solid currentColor; border-bottom:1.5px solid currentColor; transform:rotate(45deg);
}
.cui-field-control.q-field .q-field__focusable-action { opacity:.72; }
.cui-field-control.q-field .q-field__focusable-action:hover { opacity:1; color:var(--cui-text-primary); }
.cui-field-control.q-field.q-field--disabled { opacity:.55; }
.cui-field-control.q-field.q-field--readonly .q-field__control { background:var(--cui-surface-secondary); }
.cui-field-control.q-select .q-chip { margin:2px 4px 2px 0; min-height:24px; padding:2px 8px; border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-pill); background:var(--cui-surface-secondary); color:var(--cui-text-secondary); font-size:var(--cui-type-caption-size); box-shadow:none; }
.cui-field-control.q-select .q-chip .q-icon { font-size:var(--cui-font-size-15); color:var(--cui-text-tertiary); }
.q-menu[role='listbox'], .q-menu .q-virtual-scroll__content { background:var(--cui-surface); color:var(--cui-text-primary); }
.q-menu[role='listbox'] { border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); box-shadow:var(--cui-shadow-2); padding:5px; }
.q-menu[role='listbox'] .q-item { min-height:32px; padding:6px 8px; border-radius:var(--cui-radius-sm); color:var(--cui-text-primary); font-size:var(--cui-type-label-size); }
.q-menu[role='listbox'] .q-item:hover, .q-menu[role='listbox'] .q-item.q-manual-focusable--focused { background:var(--cui-surface-hover); }
.q-menu[role='listbox'] .q-item.q-item--active { background:var(--cui-accent-soft); color:var(--cui-accent); }

/* Choice controls. */
.cui-choice.q-checkbox, .cui-choice.q-radio { min-height:28px; color:var(--cui-text-primary); }
.cui-choice.q-checkbox .q-checkbox__inner, .cui-choice.q-radio .q-radio__inner { width:20px; min-width:20px; height:20px; color:var(--cui-accent); }
.cui-choice.q-checkbox .q-checkbox__bg { inset:1px; border:1.5px solid var(--cui-border-strong); border-radius:var(--cui-radius-micro); background:var(--cui-surface); }
.cui-choice.q-checkbox .q-checkbox__inner--truthy .q-checkbox__bg,
.cui-choice.q-checkbox .q-checkbox__inner--indet .q-checkbox__bg { background:var(--cui-accent); border-color:var(--cui-accent); }
.cui-choice.q-checkbox .q-checkbox__svg { color:var(--cui-text-inverse); }
.cui-choice.q-radio .q-radio__bg { inset:1px; border:1.5px solid var(--cui-border-strong); border-radius:var(--cui-radius-circle); background:var(--cui-surface); }
.cui-choice.q-radio .q-radio__inner--truthy .q-radio__bg { border-color:var(--cui-accent); }
.cui-choice.q-radio .q-radio__inner--truthy .q-radio__bg::after { content:''; position:absolute; inset:4px; border-radius:var(--cui-radius-circle); background:var(--cui-accent); }
.cui-choice.q-checkbox .q-checkbox__label, .cui-choice.q-radio .q-radio__label { padding-left:var(--cui-space-2); font-size:var(--cui-type-body-size); line-height:var(--cui-type-body-line); }
.cui-choice.q-checkbox:focus-within, .cui-choice.q-radio:focus-within { outline:3px solid color-mix(in srgb,var(--cui-focus-ring) 42%,transparent); outline-offset:2px; border-radius:var(--cui-radius-sm); }

/* Slider and range controls. */
.cui-slider.q-slider { color:var(--cui-accent); min-height:32px; padding:6px 0; }
.cui-slider.q-slider .q-slider__track-container { height:4px; }
.cui-slider.q-slider .q-slider__track { border-radius:var(--cui-radius-pill); background:var(--cui-border-default); opacity:1; }
.cui-slider.q-slider .q-slider__selection { background:var(--cui-accent); border-radius:var(--cui-radius-pill); }
.cui-slider.q-slider .q-slider__thumb { width:18px; height:18px; color:var(--cui-surface-elevated); border:2px solid var(--cui-accent); box-shadow:var(--cui-shadow-1); }
.cui-slider.q-slider .q-slider__focus-ring { color:color-mix(in srgb,var(--cui-focus-ring) 30%,transparent); }
.cui-slider.q-slider .q-slider__pin { background:var(--cui-text-primary); color:var(--cui-surface); border-radius:var(--cui-radius-sm); }

/* Tabs and tab panels. */
.cui-tabs-region.q-tabs { min-height:38px; border-bottom:1px solid var(--cui-border-subtle); color:var(--cui-text-secondary); }
.cui-tabs-region.q-tabs .q-tabs__content { gap:2px; }
.cui-tab.q-tab { min-height:38px; padding:0 10px; color:var(--cui-text-secondary); border-radius:var(--cui-radius-sm) var(--cui-radius-sm) 0 0; font-size:var(--cui-type-label-size); font-weight:var(--cui-font-weight-600); text-transform:none; }
.cui-tab.q-tab:hover { background:var(--cui-surface-hover); color:var(--cui-text-primary); }
.cui-tab.q-tab.q-tab--active { color:var(--cui-text-primary); }
.cui-tab.q-tab .q-tab__indicator { height:2px; background:var(--cui-accent); border-radius:var(--cui-radius-micro) var(--cui-radius-micro) 0 0; }
.cui-tab.q-tab .q-focus-helper { display:none; }
.cui-tab.q-tab:focus-visible { outline:3px solid color-mix(in srgb,var(--cui-focus-ring) 42%,transparent); outline-offset:-3px; }
.cui-tab-panels.q-tab-panels { background:transparent; color:inherit; }
.cui-tab-panels.q-tab-panels .q-tab-panel { padding:var(--cui-space-4) 0 0; }

/* Segmented control. */
.cui-segmented-control.q-btn-toggle { display:inline-flex; gap:2px; padding:3px; border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); background:var(--cui-surface-secondary); box-shadow:none; }
.cui-segmented-control.q-btn-toggle > .q-btn { min-height:28px; padding:0 10px; border:0 !important; border-radius:var(--cui-radius-sm) !important; background:transparent !important; color:var(--cui-text-secondary) !important; box-shadow:none !important; font-size:var(--cui-type-label-size); font-weight:var(--cui-font-weight-600); }
.cui-segmented-control.q-btn-toggle > .q-btn[aria-pressed='true'], .cui-segmented-control.q-btn-toggle > .q-btn.q-btn--active { background:var(--cui-surface) !important; color:var(--cui-text-primary) !important; box-shadow:var(--cui-shadow-1) !important; }
.cui-segmented-control.q-btn-toggle .q-focus-helper { display:none; }

/* Expansion/collapsible. */
.cui-collapsible.q-expansion-item, .cui-nav-expansion.q-expansion-item { background:var(--cui-surface); color:var(--cui-text-primary); }
.cui-collapsible.q-expansion-item > .q-expansion-item__container > .q-item { min-height:40px; padding:0 var(--cui-space-3); color:var(--cui-text-primary); }
.cui-collapsible.q-expansion-item > .q-expansion-item__container > .q-item:hover { background:var(--cui-surface-hover); }
.cui-collapsible.q-expansion-item .q-expansion-item__toggle-icon { color:var(--cui-text-tertiary); font-size:var(--cui-font-size-18); }
.cui-collapsible.q-expansion-item .q-expansion-item__content { border-top:1px solid var(--cui-border-subtle); padding:var(--cui-space-3); }
.cui-nav-expansion.q-expansion-item > .q-expansion-item__container > .q-item { min-height:34px; padding:0 8px; border-radius:var(--cui-radius-sm); color:var(--cui-text-secondary); }
.cui-nav-expansion.q-expansion-item > .q-expansion-item__container > .q-item:hover { background:var(--cui-surface-hover); color:var(--cui-text-primary); }

/* Stepper. */
.cui-stepper.q-stepper { background:transparent; color:var(--cui-text-primary); box-shadow:none; border:0; }
.cui-stepper.q-stepper .q-stepper__header { border:0; border-bottom:1px solid var(--cui-border-subtle); box-shadow:none; background:transparent; }
.cui-stepper.q-stepper .q-stepper__tab { min-height:56px; padding:8px 10px; color:var(--cui-text-tertiary); }
.cui-stepper.q-stepper .q-stepper__tab--active { color:var(--cui-accent); }
.cui-stepper.q-stepper .q-stepper__tab--done { color:var(--cui-success); }
.cui-stepper.q-stepper .q-stepper__dot { width:26px; height:26px; min-width:26px; border:1px solid var(--cui-border-default); background:var(--cui-surface); color:var(--cui-text-secondary); box-shadow:none; font-size:var(--cui-font-size-11); }
.cui-stepper.q-stepper .q-stepper__tab--active .q-stepper__dot { border-color:var(--cui-accent); background:var(--cui-accent-soft); color:var(--cui-accent); box-shadow:0 0 0 3px var(--cui-accent-soft); }
.cui-stepper.q-stepper .q-stepper__tab--done .q-stepper__dot { border-color:var(--cui-success); background:var(--cui-success-soft); color:var(--cui-success); }
.cui-stepper.q-stepper .q-stepper__label { font-size:var(--cui-type-caption-size); font-weight:var(--cui-font-weight-600); }
.cui-stepper.q-stepper .q-stepper__step-inner { padding:var(--cui-space-4) 0; }
.cui-stepper.q-stepper .q-stepper__nav { padding:var(--cui-space-3) 0 0; }

/* Tree. */
.cui-tree.q-tree .q-tree__node-header { min-height:32px; padding:2px 6px; border-radius:var(--cui-radius-sm); color:var(--cui-text-primary); }
.cui-tree.q-tree .q-tree__node-header:hover { background:var(--cui-surface-hover); }
.cui-tree.q-tree .q-tree__node--selected > .q-tree__node-header { background:var(--cui-accent-soft); color:var(--cui-accent); }
.cui-tree.q-tree .q-tree__arrow { color:var(--cui-text-tertiary); font-size:var(--cui-font-size-18); }
.cui-tree.q-tree .q-tree__node-header:focus-visible { outline:3px solid color-mix(in srgb,var(--cui-focus-ring) 42%,transparent); outline-offset:-2px; }
.cui-tree.q-tree .q-checkbox { transform:scale(.9); }

/* Upload. */
.cui-upload.q-uploader { display:flex; flex-direction:column; width:100%; max-width:none; min-height:132px; padding:0; border:1px dashed var(--cui-border-strong); border-radius:var(--cui-radius-md); background:var(--cui-surface-secondary); box-shadow:none; overflow:hidden; color:var(--cui-text-primary); }
.cui-upload.q-uploader:hover { border-color:var(--cui-accent); background:var(--cui-accent-soft); }
.cui-upload.q-uploader .q-uploader__header { min-height:62px; padding:12px; background:transparent; color:var(--cui-text-primary); box-shadow:none; border-bottom:1px solid var(--cui-border-subtle); }
.cui-upload.q-uploader .q-uploader__title { font-size:var(--cui-type-label-size); font-weight:var(--cui-font-weight-650); }
.cui-upload.q-uploader .q-uploader__subtitle { color:var(--cui-text-tertiary); font-size:var(--cui-type-caption-size); }
.cui-upload.q-uploader .q-uploader__list { min-height:66px; padding:8px; background:transparent; }
.cui-upload.q-uploader .q-uploader__file { margin:4px 0; padding:8px; border:1px solid var(--cui-border-subtle); border-radius:var(--cui-radius-sm); background:var(--cui-surface); color:var(--cui-text-primary); box-shadow:none; }
.cui-upload.q-uploader .q-uploader__file-header-content { color:var(--cui-text-primary); }
.cui-upload.q-uploader .q-uploader__file-status { color:var(--cui-text-secondary); }
.cui-upload.q-uploader .q-btn { color:var(--cui-text-secondary); }

/* Progress and spinner: normalize Quasar DOM to NiceGUI Base visuals. */
.cui-progress.q-linear-progress { height:5px !important; border-radius:var(--cui-radius-pill); overflow:hidden; background:var(--cui-surface-secondary); color:var(--cui-accent); }
.cui-progress.q-linear-progress .q-linear-progress__track { background:var(--cui-surface-secondary) !important; opacity:1 !important; }
.cui-progress.q-linear-progress .q-linear-progress__model { background:var(--cui-accent) !important; border-radius:inherit; }
.cui-spinner.q-spinner { width:18px !important; height:18px !important; color:var(--cui-accent); }
.cui-spinner.q-spinner * { stroke-width:4; }

/* Menus, tooltips and dialog host surfaces. */
.q-dialog__backdrop { background:var(--cui-overlay-scrim) !important; backdrop-filter:blur(2px); }
.cui-menu.q-menu, .cui-popover.q-menu, .cui-user-menu.q-menu { background:color-mix(in srgb,var(--cui-surface) 97%,transparent); color:var(--cui-text-primary); border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); box-shadow:var(--cui-shadow-2); padding:6px; backdrop-filter:blur(16px); }
.cui-tooltip.q-tooltip, .q-tooltip.cui-tooltip { max-width:320px; padding:6px 8px; border-radius:var(--cui-radius-sm); background:var(--cui-text-primary); color:var(--cui-surface); font-size:var(--cui-font-size-11); line-height:var(--cui-line-height-ratio-1_35); box-shadow:var(--cui-shadow-1); }

/* Splitter and drawers. */
.cui-splitter.q-splitter .q-splitter__separator { width:1px; background:var(--cui-border-subtle); }
.cui-splitter.q-splitter .q-splitter__separator:hover { background:var(--cui-accent); }
.cui-app-sidebar.q-drawer { background:var(--cui-surface); color:var(--cui-text-primary); border-color:var(--cui-border-subtle) !important; }

/* Stock notification should never be used; normalize defensively if a third-party path creates one. */
.q-notification { border:1px solid var(--cui-border-default); border-radius:var(--cui-radius-md); background:var(--cui-surface) !important; color:var(--cui-text-primary) !important; box-shadow:var(--cui-shadow-2); font-size:var(--cui-type-label-size); }

/* High contrast / forced-colors. */
@media (forced-colors: active) {
  .cui-button,.cui-icon-button,.cui-field-control,.cui-choice,.cui-surface,.cui-dialog,.cui-drawer,
  .cui-menu,.cui-popover,.cui-data-table,.cui-metric-card,.cui-viewer { forced-color-adjust:auto; border-color:CanvasText; }
  .cui-button:focus-visible,.cui-icon-button:focus-visible,.cui-field-control:focus-within,.cui-choice:focus-within,.cui-tab:focus-visible { outline:2px solid Highlight; }
  .cui-button--primary,.cui-button--danger,.cui-choice.q-checkbox .q-checkbox__inner--truthy .q-checkbox__bg,
  .cui-choice-row--switch:has(.cui-choice-native:checked) .cui-switch-track { background:Highlight !important; color:HighlightText !important; border-color:Highlight !important; }
  .cui-tab.q-tab .q-tab__indicator { background:Highlight; }
}

@media (prefers-reduced-motion: reduce) {
  .q-ripple, .q-transition--fade-enter-active, .q-transition--fade-leave-active { animation:none !important; transition:none !important; }
}
'''.strip() + '\n'


__all__ = ['build_visual_normalization_css']
