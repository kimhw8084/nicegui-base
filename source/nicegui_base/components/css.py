from __future__ import annotations


def build_component_css() -> str:
    return r'''
:root {
  --cui-field-medium-width: 260px;
  --cui-field-wide-width: 420px;
}

/* Shared control geometry */
.cui-control--small { min-height: var(--cui-control-small); }
.cui-control--medium { min-height: var(--cui-control-medium); }
.cui-control--large { min-height: var(--cui-control-large); }

/* Buttons */
.cui-button,
.cui-icon-button {
  appearance: none;
  border: 1px solid transparent;
  border-radius: var(--cui-radius-sm);
  font-size: var(--cui-type-label-size);
  line-height: var(--cui-type-label-line);
  font-weight: var(--cui-font-weight-600);
  letter-spacing: var(--cui-type-label-tracking);
  transition:
    background-color var(--cui-motion-fast) var(--cui-ease-standard),
    border-color var(--cui-motion-fast) var(--cui-ease-standard),
    color var(--cui-motion-fast) var(--cui-ease-standard),
    box-shadow var(--cui-motion-fast) var(--cui-ease-standard),
    transform var(--cui-motion-instant) var(--cui-ease-standard);
  cursor: pointer;
  user-select: none;
}
.cui-button { padding-inline: var(--cui-control-padding-x); gap: var(--cui-space-2); }
.cui-button--primary { background: var(--cui-accent); color: var(--cui-text-inverse); border-color: var(--cui-accent); }
.cui-button--primary:hover { background: var(--cui-accent-hover); border-color: var(--cui-accent-hover); }
.cui-button--secondary { background: var(--cui-surface); color: var(--cui-text-primary); border-color: var(--cui-border-default); }
.cui-button--secondary:hover { background: var(--cui-surface-hover); border-color: var(--cui-border-strong); }
.cui-button--tertiary { background: var(--cui-surface-secondary); color: var(--cui-text-primary); border-color: transparent; }
.cui-button--tertiary:hover { background: var(--cui-surface-hover); }
.cui-button--ghost { background: transparent; color: var(--cui-text-secondary); border-color: transparent; }
.cui-button--ghost:hover { background: var(--cui-surface-hover); color: var(--cui-text-primary); }
.cui-button--danger { background: var(--cui-danger); color: var(--cui-text-inverse); border-color: var(--cui-danger); }
.cui-button--danger:hover { filter: brightness(.94); }
.cui-button:active:not(:disabled), .cui-icon-button:active:not(:disabled) { transform: translateY(.5px); }
.cui-button:focus-visible, .cui-icon-button:focus-visible,
.cui-field-control:focus-within, .cui-choice:focus-within {
  outline: 3px solid color-mix(in srgb, var(--cui-focus-ring) 46%, transparent);
  outline-offset: 2px;
}
.cui-button:disabled, .cui-icon-button:disabled, .cui-button.is-disabled, .cui-icon-button.is-disabled {
  cursor: not-allowed; opacity: .48; box-shadow: none; transform: none;
}
.cui-button.is-loading { position: relative; pointer-events: none; }
.cui-button.is-loading::before {
  content: ''; width: 12px; height: 12px; border-radius: var(--cui-radius-circle); border: 1.7px solid currentColor;
  border-right-color: transparent; animation: cui-spin var(--cui-duration-spinner) var(--cui-easing-linear) infinite;
}
.cui-button.is-full-width { width: 100%; justify-content: center; }
@keyframes cui-spin { to { transform: rotate(360deg); } }

.cui-icon-button {
  width: var(--cui-icon-button-size); min-width: var(--cui-icon-button-size); height: var(--cui-icon-button-size);
  padding: 0; display: inline-grid; place-items: center; background: transparent; color: var(--cui-text-secondary);
}
.cui-icon-button--primary { background: var(--cui-accent); color: var(--cui-text-inverse); }
.cui-icon-button--secondary { background: var(--cui-surface); border-color: var(--cui-border-default); color: var(--cui-text-primary); }
.cui-icon-button--tertiary { background: var(--cui-surface-secondary); color: var(--cui-text-primary); }
.cui-icon-button--danger { color: var(--cui-danger); }
.cui-icon-button:hover { background: var(--cui-surface-hover); color: var(--cui-text-primary); }
.cui-icon-button.is-selected { background: var(--cui-accent-soft); color: var(--cui-accent); }

/* Surfaces */
.cui-surface { color: var(--cui-text-primary); min-width: 0; }
.cui-surface--panel { background: var(--cui-surface); border: 1px solid var(--cui-border-subtle); border-radius: var(--cui-radius-md); }
.cui-surface--card { background: var(--cui-surface); border: 1px solid var(--cui-border-default); border-radius: var(--cui-radius-lg); box-shadow: var(--cui-shadow-1); }
.cui-surface--well { background: var(--cui-surface-secondary); border: 1px solid var(--cui-border-subtle); border-radius: var(--cui-radius-md); }
.cui-surface--outlined { background: transparent; border: 1px solid var(--cui-border-default); border-radius: var(--cui-radius-md); }
.cui-surface--interactive { background: var(--cui-surface); border: 1px solid var(--cui-border-default); border-radius: var(--cui-radius-md); transition: background var(--cui-motion-fast) var(--cui-ease-standard), border-color var(--cui-motion-fast) var(--cui-ease-standard), box-shadow var(--cui-motion-fast) var(--cui-ease-standard); }
.cui-surface.is-interactive { cursor: pointer; }
.cui-surface.is-interactive:hover { background: var(--cui-surface-hover); border-color: var(--cui-border-strong); }
.cui-surface.is-selected { border-color: color-mix(in srgb, var(--cui-accent) 48%, var(--cui-border-default)); background: var(--cui-surface-selected); }

/* Badges */
.cui-badge {
  display: inline-flex; align-items: center; gap: var(--cui-space-1); min-height: 22px; padding: 2px 8px;
  border-radius: var(--cui-radius-pill); border: 1px solid currentColor;
  font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); font-weight: var(--cui-font-weight-600);
}
.cui-badge--neutral { color: var(--cui-text-secondary); background: var(--cui-surface-secondary); border-color: var(--cui-border-default); }
.cui-badge--info { color: var(--cui-info); background: var(--cui-info-soft); }
.cui-badge--success { color: var(--cui-success); background: var(--cui-success-soft); }
.cui-badge--warning { color: var(--cui-warning); background: var(--cui-warning-soft); }
.cui-badge--danger { color: var(--cui-danger); background: var(--cui-danger-soft); }
.cui-badge--subtle { border-color: color-mix(in srgb, currentColor 22%, transparent); }

/* Field anatomy */
.cui-field { display: flex; flex-direction: column; gap: var(--cui-space-1); min-width: 0; }
.cui-field-label-row { display: flex; align-items: baseline; justify-content: space-between; gap: var(--cui-space-2); }
.cui-field-label { color: var(--cui-text-primary); font-size: var(--cui-type-label-size); line-height: var(--cui-type-label-line); font-weight: var(--cui-type-label-weight); }
.cui-field-required { color: var(--cui-danger); margin-left: 2px; }
.cui-field-description { color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); }
.cui-field-error { display: flex; align-items: flex-start; gap: var(--cui-space-1); color: var(--cui-danger); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); }
.cui-field-width--auto { width: auto; }
.cui-field-width--medium { width: min(100%, var(--cui-field-medium-width)); }
.cui-field-width--wide { width: min(100%, var(--cui-field-wide-width)); }
.cui-field-width--full { width: 100%; }
.cui-field-control {
  display: flex; align-items: center; width: 100%; min-width: 0; gap: var(--cui-space-2);
  padding-inline: var(--cui-space-3); border: 1px solid var(--cui-border-default); border-radius: var(--cui-radius-sm);
  background: var(--cui-surface); color: var(--cui-text-primary);
  transition: border-color var(--cui-motion-fast) var(--cui-ease-standard), background var(--cui-motion-fast) var(--cui-ease-standard), box-shadow var(--cui-motion-fast) var(--cui-ease-standard);
}
.cui-field-control:hover:not(.cui-field-control--readonly) { border-color: var(--cui-border-strong); }
.cui-field-control--error { border-color: color-mix(in srgb, var(--cui-danger) 70%, var(--cui-border-default)); }
.cui-field-control--readonly { background: var(--cui-surface-secondary); color: var(--cui-text-secondary); }
.cui-field-control.is-disabled, .cui-field-control[aria-disabled='true'] { opacity: .55; cursor: not-allowed; background: var(--cui-surface-secondary); }
.cui-field-control input, .cui-field-control textarea, .cui-field-control select {
  width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: inherit; font: inherit;
}
.cui-field-control input::placeholder, .cui-field-control textarea::placeholder { color: var(--cui-text-tertiary); opacity: .9; }
.cui-field-control textarea { min-height: 88px; resize: vertical; padding-block: var(--cui-space-2); }
.cui-field-leading, .cui-field-trailing { flex: 0 0 auto; color: var(--cui-text-tertiary); }
.cui-field-unit { color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); white-space: nowrap; }

/* Normalize Quasar-backed NiceGUI fields without relying on app-local styling. */
.cui-field-control.q-field { padding-inline: 0; }
.cui-field-control.q-field .q-field__control { min-height: inherit; height: inherit; color: var(--cui-text-primary); padding: 0 var(--cui-space-3); border-radius: inherit; }
.cui-field-control.q-field .q-field__control::before,
.cui-field-control.q-field .q-field__control::after { display: none; }
.cui-field-control.q-field .q-field__native,
.cui-field-control.q-field .q-field__input { color: var(--cui-text-primary); padding: 0; min-height: auto; }
.cui-field-control.q-field .q-field__label { color: var(--cui-text-secondary); }
.cui-field-control.q-field.q-field--focused { border-color: var(--cui-accent); }

/* Choice controls */
.cui-choice { display: inline-flex; align-items: flex-start; gap: var(--cui-space-2); color: var(--cui-text-primary); cursor: pointer; min-height: 24px; }
.cui-choice.is-disabled { opacity: .5; cursor: not-allowed; }
.cui-choice__control {
  flex: 0 0 auto; width: 18px; height: 18px; border: 1px solid var(--cui-border-strong); background: var(--cui-surface);
  border-radius: var(--cui-radius-micro); display: grid; place-items: center; transition: background var(--cui-motion-fast) var(--cui-ease-standard), border-color var(--cui-motion-fast) var(--cui-ease-standard);
}
.cui-choice--radio .cui-choice__control { border-radius: var(--cui-radius-circle); }
.cui-choice.is-checked .cui-choice__control { background: var(--cui-accent); border-color: var(--cui-accent); color: var(--cui-text-inverse); }
.cui-choice__label { font-size: var(--cui-type-body-size); line-height: var(--cui-type-body-line); }
.cui-choice__description { color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); }

/* Slider */
.cui-slider { accent-color: var(--cui-accent); width: 100%; }
.cui-slider-meta { display: flex; justify-content: space-between; color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); }

/* Upload */
.cui-upload {
  border: 1px dashed var(--cui-border-strong); background: var(--cui-surface-secondary); border-radius: var(--cui-radius-md);
  min-height: 112px; padding: var(--cui-space-4); display: grid; place-items: center; text-align: center;
  transition: background var(--cui-motion-fast) var(--cui-ease-standard), border-color var(--cui-motion-fast) var(--cui-ease-standard);
}
.cui-upload:hover { border-color: var(--cui-accent); background: var(--cui-accent-soft); }
.cui-upload.is-disabled { opacity: .5; pointer-events: none; }
.cui-upload__title { font-size: var(--cui-type-body-size); font-weight: var(--cui-font-weight-600); color: var(--cui-text-primary); }
.cui-upload__help { font-size: var(--cui-type-caption-size); color: var(--cui-text-tertiary); }


/* Button groups and split actions */
.cui-button-group { display: inline-flex; align-items: stretch; }
.cui-button-group > .cui-button { border-radius: 0; margin-left: -1px; }
.cui-button-group > .cui-button:first-child { border-radius: var(--cui-radius-sm) 0 0 var(--cui-radius-sm); margin-left: 0; }
.cui-button-group > .cui-button:last-child { border-radius: 0 var(--cui-radius-sm) var(--cui-radius-sm) 0; }
.cui-split-button { display: inline-flex; }
.cui-split-button .cui-button:first-child { border-radius: var(--cui-radius-sm) 0 0 var(--cui-radius-sm); }
.cui-split-button .cui-icon-button:last-child { border-radius: 0 var(--cui-radius-sm) var(--cui-radius-sm) 0; margin-left: -1px; }

/* Additional surfaces */
.cui-divider { width: 100%; height: 1px; background: var(--cui-border-subtle); border: 0; margin: var(--cui-space-2) 0; }
.cui-collapsible { border: 1px solid var(--cui-border-subtle); border-radius: var(--cui-radius-md); background: var(--cui-surface); overflow: hidden; }
.cui-collapsible__header { min-height: 40px; padding: var(--cui-space-2) var(--cui-space-3); display: flex; align-items: center; justify-content: space-between; gap: var(--cui-space-3); font-size: var(--cui-type-body-size); font-weight: var(--cui-font-weight-600); cursor: pointer; }
.cui-collapsible__header:hover { background: var(--cui-surface-hover); }
.cui-collapsible__body { padding: var(--cui-space-3); border-top: 1px solid var(--cui-border-subtle); }

/* Metadata */
.cui-chip { display: inline-flex; align-items: center; gap: var(--cui-space-1); min-height: 26px; padding: 3px 9px; border: 1px solid var(--cui-border-default); border-radius: var(--cui-radius-pill); background: var(--cui-surface); color: var(--cui-text-secondary); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); transition: background var(--cui-motion-fast) var(--cui-ease-standard), border-color var(--cui-motion-fast) var(--cui-ease-standard); }
.cui-chip:hover { background: var(--cui-surface-hover); }
.cui-chip.is-selected { background: var(--cui-accent-soft); border-color: color-mix(in srgb, var(--cui-accent) 36%, var(--cui-border-default)); color: var(--cui-accent); }
.cui-count-badge { min-width: 20px; height: 20px; padding: 0 6px; border-radius: var(--cui-radius-pill); display: inline-grid; place-items: center; background: var(--cui-accent); color: var(--cui-text-inverse); font-size: var(--cui-type-caption-size); font-weight: var(--cui-font-weight-650); font-variant-numeric: tabular-nums; }
.cui-semantic-indicator { display: inline-flex; align-items: center; gap: var(--cui-space-1); font-size: var(--cui-type-caption-size); color: var(--cui-text-secondary); }
.cui-semantic-indicator::before { content: ''; width: 7px; height: 7px; border-radius: var(--cui-radius-circle); background: currentColor; }
.cui-semantic-indicator--success { color: var(--cui-success); }
.cui-semantic-indicator--info { color: var(--cui-info); }
.cui-semantic-indicator--warning { color: var(--cui-warning); }
.cui-semantic-indicator--danger { color: var(--cui-danger); }
.cui-semantic-indicator--neutral { color: var(--cui-text-tertiary); }

.cui-date-range-row { display:flex; align-items:center; gap:var(--cui-space-2); width:100%; }
.cui-date-range-row > * { flex:1 1 0; min-width:0; }

@media (pointer: coarse) {
  .cui-button, .cui-icon-button, .cui-field-control, .cui-choice { min-height: 44px; }
  .cui-icon-button { width: 44px; min-width: 44px; height: 44px; }
}

@media (max-width: 599px) {
  .cui-date-range-row { flex-direction:column; align-items:stretch; }
  .cui-field-width--auto, .cui-field-width--medium, .cui-field-width--wide { width: 100%; }
  .cui-button.mobile-full-width { width: 100%; justify-content: center; }
}
'''.strip() + '\n'
