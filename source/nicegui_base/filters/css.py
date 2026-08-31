from __future__ import annotations


def build_filter_css() -> str:
    return r'''
.cui-filter-bar{display:flex;flex-direction:column;gap:var(--cui-space-2);padding:var(--cui-space-3);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-md);background:var(--cui-surface)}
.cui-filter-bar__controls{display:flex;align-items:flex-end;gap:var(--cui-space-2);flex-wrap:wrap}.cui-filter-bar__controls>.cui-field{min-width:160px;flex:1 1 170px}.cui-filter-bar__controls>.is-search{flex:2 1 260px}
.cui-filter-bar__actions{display:flex;align-items:center;gap:var(--cui-space-1);margin-left:auto}
.cui-filter-bar__active{display:flex;gap:var(--cui-space-1);align-items:center;flex-wrap:wrap;padding-top:var(--cui-space-2);border-top:1px solid var(--cui-border-subtle)}
.cui-filter-chip{display:inline-flex;align-items:center;gap:var(--cui-space-1);padding:4px 8px;border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-pill);background:var(--cui-surface-secondary);font-size:var(--cui-type-caption-size);color:var(--cui-text-secondary)}
.cui-filter-chip__label{color:var(--cui-text-secondary);font-size:var(--cui-type-caption-size)}.cui-filter-chip__value{color:var(--cui-text-primary);font-weight:var(--cui-font-weight-600)}.cui-filter-chip strong{color:var(--cui-text-primary);font-weight:var(--cui-font-weight-600)}.cui-filter-chip button{border:0;background:transparent;color:var(--cui-text-tertiary);cursor:pointer;padding:0;line-height:var(--cui-line-height-ratio-1)}.cui-filter-chip button:hover{color:var(--cui-text-primary)}
.cui-filter-count{display:inline-grid;place-items:center;min-width:18px;height:18px;padding:0 5px;border-radius:var(--cui-radius-pill);background:var(--cui-accent);color:var(--cui-text-inverse);font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-700)}
.cui-preset-strip{display:flex;align-items:center;gap:var(--cui-space-1);overflow:auto;scrollbar-width:none}.cui-preset-strip::-webkit-scrollbar{display:none}
.cui-preset{white-space:nowrap;border:1px solid var(--cui-border-default);background:var(--cui-surface);color:var(--cui-text-secondary);border-radius:var(--cui-radius-pill);padding:5px 9px;font-size:var(--cui-type-caption-size);cursor:pointer}.cui-preset:hover,.cui-preset.is-active{background:var(--cui-accent-soft);border-color:color-mix(in srgb,var(--cui-accent) 28%,var(--cui-border-default));color:var(--cui-accent)}
@media(max-width:899px){.cui-filter-bar{padding:var(--cui-space-2)}.cui-filter-bar__controls>.cui-field{display:none}.cui-filter-bar__controls>.is-search{display:flex;min-width:0}.cui-filter-bar__actions{margin-left:0}.cui-filter-bar__mobile-trigger{display:inline-flex!important}.cui-filter-bar__active{overflow:auto;flex-wrap:nowrap}}
@media(min-width:900px){.cui-filter-bar__mobile-trigger{display:none!important}}
'''
