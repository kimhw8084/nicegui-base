from __future__ import annotations


def build_engineering_css() -> str:
    return r'''
.cui-eng-entity{display:grid;gap:var(--cui-space-3);padding:var(--cui-space-4);border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-md);background:var(--cui-surface)}
.cui-eng-entity__head{display:flex;align-items:flex-start;justify-content:space-between;gap:var(--cui-space-3)}
.cui-eng-entity__identity{display:flex;align-items:center;gap:var(--cui-space-3);min-width:0}.cui-eng-entity__icon{color:var(--cui-text-secondary);display:inline-flex}
.cui-property-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:var(--cui-space-3)}
.cui-eng-entity__title{font-size:var(--cui-type-subheading-size);line-height:var(--cui-type-subheading-line);color:var(--cui-text-primary);font-weight:var(--cui-font-weight-600)}.cui-eng-entity__secondary{font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);color:var(--cui-text-tertiary)}
.cui-eng-status{display:inline-flex;align-items:center;gap:var(--cui-space-1);padding:3px 8px;border-radius:var(--cui-radius-pill);border:1px solid var(--cui-border-default);font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);font-weight:var(--cui-font-weight-600);white-space:nowrap}
.cui-eng-status--normal{color:var(--cui-success);background:var(--cui-success-soft)}
.cui-eng-status--watch,.cui-eng-status--warning,.cui-eng-status--hold{color:var(--cui-warning);background:var(--cui-warning-soft)}
.cui-eng-status--critical{color:var(--cui-danger);background:var(--cui-danger-soft)}
.cui-eng-status--unknown,.cui-eng-status--offline,.cui-eng-status--maintenance{color:var(--cui-text-secondary);background:var(--cui-surface-secondary)}
.cui-spec{display:inline-flex;align-items:center;gap:var(--cui-space-2);font-size:var(--cui-type-label-size);line-height:var(--cui-type-label-line);font-variant-numeric:tabular-nums}.cui-spec__mark{width:7px;height:7px;border-radius:var(--cui-radius-circle);background:currentColor}
.cui-spec--in_spec{color:var(--cui-success)}.cui-spec--watch_low,.cui-spec--watch_high{color:var(--cui-warning)}.cui-spec--oos_low,.cui-spec--oos_high{color:var(--cui-danger)}.cui-spec--missing{color:var(--cui-text-tertiary)}
.cui-baseline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-space-3);padding:var(--cui-space-3);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-sm);background:var(--cui-surface-secondary)}
.cui-baseline__label{font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);color:var(--cui-text-tertiary)}.cui-baseline__value{font-size:var(--cui-type-body-size);line-height:var(--cui-type-body-line);font-weight:var(--cui-font-weight-600);font-variant-numeric:tabular-nums;color:var(--cui-text-primary)}
.cui-evidence{display:grid;gap:var(--cui-space-2);padding:var(--cui-space-3);border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-md);background:var(--cui-surface);border-left-width:3px}
.cui-evidence--supports{border-left-color:var(--cui-success)}.cui-evidence--contradicts{border-left-color:var(--cui-danger)}.cui-evidence--neutral{border-left-color:var(--cui-border-strong)}
.cui-evidence__meta{display:flex;flex-wrap:wrap;gap:var(--cui-space-2);font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);color:var(--cui-text-tertiary)}.cui-evidence__title{font-size:var(--cui-type-body-size);line-height:var(--cui-type-body-line);font-weight:var(--cui-font-weight-600);color:var(--cui-text-primary)}.cui-evidence__summary{font-size:var(--cui-type-body-size);line-height:var(--cui-type-body-line);color:var(--cui-text-secondary)}
.cui-confidence{display:grid;gap:var(--cui-space-1);min-width:120px}.cui-confidence__track{height:5px;border-radius:var(--cui-radius-pill);background:var(--cui-surface-secondary);overflow:hidden}.cui-confidence__fill{height:100%;border-radius:inherit;background:var(--cui-accent)}.cui-confidence__label{font-size:var(--cui-type-caption-size);line-height:var(--cui-type-caption-line);font-weight:var(--cui-font-weight-600);color:var(--cui-text-secondary)}
.cui-rca-balance{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-space-2)}.cui-rca-balance>div{padding:var(--cui-space-2);border-radius:var(--cui-radius-sm);background:var(--cui-surface-secondary);font-variant-numeric:tabular-nums}
@media(max-width:899px){.cui-baseline,.cui-rca-balance{grid-template-columns:1fr}.cui-eng-entity__head{align-items:stretch;flex-direction:column}}
'''.strip()


__all__ = ['build_engineering_css']
