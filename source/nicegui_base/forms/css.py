from __future__ import annotations


def build_form_css() -> str:
    return r'''
.cui-form-field{display:flex;flex-direction:column;gap:var(--cui-space-1)}.cui-form-field.is-full{grid-column:1/-1}.cui-form-field.has-error .cui-field-control{border-color:var(--cui-danger)}
.cui-form{display:flex;flex-direction:column;gap:var(--cui-space-5)}
.cui-form-section__copy{display:flex;flex-direction:column;gap:2px}.cui-validation-summary__item{font-size:var(--cui-type-caption-size);color:var(--cui-text-secondary)}.cui-form-actions__spacer{flex:1}
.cui-form-section{display:flex;flex-direction:column;gap:var(--cui-space-4)}
.cui-form-section__head{display:flex;align-items:flex-start;justify-content:space-between;gap:var(--cui-space-4);padding-bottom:var(--cui-space-3);border-bottom:1px solid var(--cui-border-subtle)}
.cui-form-section__title{font-size:var(--cui-type-subheading-size);line-height:var(--cui-type-subheading-line);font-weight:var(--cui-font-weight-600);color:var(--cui-text-primary)}
.cui-form-section__description{font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);color:var(--cui-text-tertiary);max-width:66ch}
.cui-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-space-4)}
.cui-form-grid--single{grid-template-columns:1fr}.cui-form-grid>.is-full{grid-column:1/-1}
.cui-form-actions{display:flex;gap:var(--cui-space-2);align-items:center;padding-top:var(--cui-space-4);border-top:1px solid var(--cui-border-subtle)}
.cui-form-actions--start{justify-content:flex-start}.cui-form-actions--center{justify-content:center}.cui-form-actions--end{justify-content:flex-end}.cui-form-actions--between{justify-content:space-between}
.cui-form-actions.is-sticky{position:sticky;bottom:0;z-index:var(--cui-layer-sticky);background:color-mix(in srgb,var(--cui-surface) 94%,transparent);backdrop-filter:blur(14px);padding:var(--cui-space-3) 0}
.cui-validation-summary{display:flex;gap:var(--cui-space-3);padding:var(--cui-space-3) var(--cui-space-4);border:1px solid color-mix(in srgb,var(--cui-danger) 34%,var(--cui-border-default));border-radius:var(--cui-radius-md);background:var(--cui-danger-soft);color:var(--cui-text-primary)}
.cui-validation-summary__icon{color:var(--cui-danger);font-weight:var(--cui-font-weight-700)}.cui-validation-summary__title{font-size:var(--cui-type-label-size);font-weight:var(--cui-font-weight-650)}.cui-validation-summary ul{margin:var(--cui-space-1) 0 0;padding-left:18px;color:var(--cui-text-secondary);font-size:var(--cui-type-caption-size)}
.cui-dirty-indicator{display:inline-flex;align-items:center;gap:var(--cui-space-1);font-size:var(--cui-type-caption-size);color:var(--cui-text-secondary)}
.cui-dirty-indicator::before{content:'';width:6px;height:6px;border-radius:var(--cui-radius-circle);background:var(--cui-warning)}
@media(max-width:899px){.cui-form-grid{grid-template-columns:1fr}.cui-form-actions{position:sticky;bottom:0;background:var(--cui-surface);padding:var(--cui-space-3) 0 calc(var(--cui-space-3) + env(safe-area-inset-bottom))}.cui-form-actions .cui-button{min-height:44px}}
'''
